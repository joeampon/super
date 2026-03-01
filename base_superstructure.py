"""
Base Superstructure Module for Pyomo-BioSTEAM Integration

This module provides the core framework for defining and managing process superstructures
that can be optimized using Pyomo while leveraging BioSTEAM's process simulation capabilities.

Author: David Lorenzo
Date: 2026-01-08
"""

import biosteam as bst
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class ConnectionType(Enum):
    """Types of connections between process units"""
    DIRECT = "direct"           # Direct connection
    OPTIONAL = "optional"       # Connection that may or may not exist
    SPLIT = "split"            # One input, multiple outputs
    MERGE = "merge"            # Multiple inputs, one output


@dataclass
class ProcessUnit:
    """
    Represents a process unit in the superstructure

    Attributes:
        name: Unique identifier for the unit
        unit_class: BioSTEAM unit class or custom unit
        exists: Whether this unit is included in the flowsheet (decision variable)
        parameters: Operating parameters that can be optimized
        bounds: (lower, upper) bounds for each parameter
        fixed_params: Fixed parameters that don't change
        tee_cost: Total equipment cost (from BioSTEAM TEA)
        operating_cost: Annual operating cost
        environmental_impact: LCA metrics (e.g., GWP)
    """
    name: str
    unit_class: type
    exists: bool = True
    parameters: Dict[str, float] = field(default_factory=dict)
    bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    fixed_params: Dict[str, Any] = field(default_factory=dict)
    tee_cost: float = 0.0
    operating_cost: float = 0.0
    environmental_impact: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parameter bounds"""
        for param in self.parameters:
            if param not in self.bounds:
                raise ValueError(f"Parameter '{param}' must have bounds defined")


@dataclass
class Connection:
    """
    Represents a connection between two process units

    Attributes:
        from_unit: Source unit name
        to_unit: Destination unit name
        from_outlet: Outlet index of source unit
        to_inlet: Inlet index of destination unit
        connection_type: Type of connection
        exists: Whether connection is active (for optional connections)
    """
    from_unit: str
    to_unit: str
    from_outlet: int = 0
    to_inlet: int = 0
    connection_type: ConnectionType = ConnectionType.DIRECT
    exists: bool = True


class Superstructure:
    """
    Main superstructure class that manages the process network

    This class handles:
    - Process unit definitions and their parameters
    - Connections between units
    - Interface with BioSTEAM for simulation
    - Data extraction for Pyomo optimization
    """

    def __init__(self, name: str):
        """
        Initialize superstructure

        Args:
            name: Name of the superstructure/process
        """
        self.name = name
        self.units: Dict[str, bst.Unit] = {}  # Store BioSTEAM units directly
        self.connections: List[Connection] = []
        self.feeds: Dict[str, bst.Stream] = {}
        self.products: Dict[str, bst.Stream] = {}
        self.tea: Optional[bst.TEA] = None
        self.lca: Optional[Any] = None  # BioSTEAM LCA object
        self.flowsheet: Optional[bst.Flowsheet] = None
        self.routers: Dict[str, Any] = {}  # Store AlternativeRouter units
        self.binary_variables: Dict[str, int] = {}  # Current binary variable values

    def add_unit(self, bst_unit: bst.Unit) -> None:
        """
        Add a BioSTEAM unit to the superstructure

        Args:
            bst_unit: An instance of a BioSTEAM Unit (e.g., bst.units.Pump('P1'))

        Raises:
            ValueError: If unit with same ID already exists
            TypeError: If bst_unit is not a BioSTEAM Unit instance
        """
        # Validate that it's a BioSTEAM Unit instance
        if not isinstance(bst_unit, bst.Unit):
            raise TypeError(
                f"bst_unit must be an instance of bst.Unit, got {type(bst_unit)}"
            )

        # Validate unit doesn't already exist
        if bst_unit.ID in self.units:
            raise ValueError(f"Unit '{bst_unit.ID}' already exists in superstructure")

        # Store the BioSTEAM unit directly
        self.units[bst_unit.ID] = bst_unit

        # Check if it's an AlternativeRouter and store it separately
        if bst_unit.__class__.__name__ == 'AlternativeRouter':
            self.routers[bst_unit.ID] = bst_unit
            # Initialize binary variables for this router
            for route_name in bst_unit.route_names:
                var_name = f"{bst_unit.ID}_{route_name}"
                # Set initial value based on active route
                self.binary_variables[var_name] = (
                    1 if bst_unit.route_names.index(route_name) == bst_unit.active_route else 0
                )

    def add_connection(self, connection: Connection) -> None:
        """
        Add a connection between units

        Args:
            connection: Connection object defining the link
        """
        # Validate units exist
        if connection.from_unit not in self.units:
            raise ValueError(f"Source unit '{connection.from_unit}' not found")
        if connection.to_unit not in self.units:
            raise ValueError(f"Destination unit '{connection.to_unit}' not found")

        self.connections.append(connection)

    def activate_route(self, from_unit: str, to_unit: str) -> None:
        """
        Activate a specific route (connection) and deactivate alternatives from the same unit

        Args:
            from_unit: Source unit ID
            to_unit: Destination unit ID

        Raises:
            ValueError: If connection not found
        """
        # Find and activate the target connection
        target_conn = None
        for conn in self.connections:
            if conn.from_unit == from_unit and conn.to_unit == to_unit:
                target_conn = conn
                conn.exists = True
                break

        if target_conn is None:
            raise ValueError(f"Connection from '{from_unit}' to '{to_unit}' not found")

        # Deactivate other connections from the same source unit
        for conn in self.connections:
            if (conn.from_unit == from_unit and
                conn.to_unit != to_unit and
                conn.connection_type == ConnectionType.OPTIONAL):
                conn.exists = False

    def add_feed(self, name: str, stream: bst.Stream) -> None:
        """Add a feed stream to the superstructure"""
        self.feeds[name] = stream

    def add_product(self, name: str, stream: bst.Stream) -> None:
        """Add a product stream to the superstructure"""
        self.products[name] = stream

    def build_flowsheet(self) -> bst.Flowsheet:
        """
        Build a BioSTEAM flowsheet with the current units and connections

        Returns:
            BioSTEAM Flowsheet object
        """
        # Create or reset flowsheet
        flowsheet_name = f"{self.name}_flowsheet"
        if bst.main_flowsheet.ID == flowsheet_name:
            bst.main_flowsheet.clear()
        else:
            self.flowsheet = bst.Flowsheet(flowsheet_name)
            bst.main_flowsheet.set_flowsheet(self.flowsheet)

        # Units are already created, just need to make connections
        for conn in self.connections:
            if not conn.exists:
                continue

            # Validate both units exist
            if conn.from_unit not in self.units or conn.to_unit not in self.units:
                continue

            from_unit = self.units[conn.from_unit]
            to_unit = self.units[conn.to_unit]

            # Connect streams
            from_unit.outs[conn.from_outlet].connect(to_unit.ins[conn.to_inlet])

        self.flowsheet = bst.main_flowsheet
        return self.flowsheet

    def simulate(self) -> bool:
        """
        Simulate the flowsheet with current units and connections

        Returns:
            True if simulation converged, False otherwise
        """
        try:
            # Build flowsheet
            self.build_flowsheet()

            # Simulate
            self.flowsheet.simulate()

            # Update costs and impacts
            self._update_unit_economics()

            return True

        except Exception as e:
            print(f"Simulation failed: {e}")
            return False

    def _update_unit_economics(self) -> None:
        """Update economic and environmental metrics for all units"""
        if self.tea is None:
            return

        # Costs are already in the BioSTEAM units, no need to update
        # TEA will calculate system-level costs
        pass

    def setup_tea(self, **tea_kwargs) -> bst.TEA:
        """
        Setup techno-economic analysis

        Args:
            **tea_kwargs: Arguments passed to bst.TEA

        Returns:
            BioSTEAM TEA object
        """
        self.tea = bst.TEA(
            system=self.flowsheet.create_system(),
            **tea_kwargs
        )
        return self.tea

    def setup_lca(self, **lca_kwargs) -> Any:
        """
        Setup life cycle assessment

        Args:
            **lca_kwargs: Arguments for LCA setup

        Returns:
            LCA object
        """
        # Placeholder - implement based on your LCA framework
        # (e.g., using BioSTEAM's LCA or external tools)
        self.lca = None  # Implement LCA setup
        return self.lca

    def get_decision_variables(self) -> Dict[str, Any]:
        """
        Extract decision variables for optimization
        (Placeholder for future optimization capabilities)

        Returns:
            Dictionary with unit names as binary variables
        """
        # For now, just return which units exist
        variables = {
            'unit_exists': {name: True for name in self.units.keys()}
        }

        return variables

    def get_objectives(self) -> Dict[str, float]:
        """
        Calculate objective functions

        Returns:
            Dictionary with objective values:
            - NPV: Net present value
            - CAPEX: Capital expenditure
            - OPEX: Operating expenditure
            - GWP: Global warming potential
            - etc.
        """
        objectives = {}

        if self.tea:
            objectives['NPV'] = self.tea.NPV
            objectives['CAPEX'] = self.tea.TCI
            objectives['OPEX'] = self.tea.AOC
            objectives['IRR'] = self.tea.IRR

        if self.lca:
            # Add LCA metrics
            objectives['GWP'] = 0.0  # Implement GWP calculation

        # Custom objectives - total equipment cost
        objectives['total_equipment_cost'] = sum(
            unit.purchase_cost for unit in self.units.values()
        )

        return objectives

    def export_configuration(self) -> Dict[str, Any]:
        """
        Export current configuration

        Returns:
            Dictionary with current state
        """
        config = {
            'name': self.name,
            'units': list(self.units.keys()),  # List of unit IDs
            'connections': []
        }

        for conn in self.connections:
            config['connections'].append({
                'from': conn.from_unit,
                'to': conn.to_unit,
                'exists': conn.exists
            })

        return config

    def visualize(self, filename: Optional[str] = None) -> None:
        """
        Visualize the superstructure

        Args:
            filename: Optional filename to save diagram
        """
        if self.flowsheet:
            self.flowsheet.diagram()
            if filename:
                # Save diagram
                pass

    def set_binary_variables(self, binary_vars: Dict[str, int]) -> None:
        """
        Set binary variable values and update router configurations

        Args:
            binary_vars: Dictionary mapping variable names to values (0 or 1)
                        Format: {'ROUTER1_Route_A': 1, 'ROUTER1_Route_B': 0, ...}

        Raises:
            ValueError: If binary variables are invalid
        """
        # Validate all values are 0 or 1
        for var_name, value in binary_vars.items():
            if value not in (0, 1):
                raise ValueError(f"Binary variable '{var_name}' must be 0 or 1, got {value}")

        # Update binary variables
        self.binary_variables.update(binary_vars)

        # Update each router based on binary variables
        for router_id, router in self.routers.items():
            # Find which route is active for this router
            active_route_idx = None
            for idx, route_name in enumerate(router.route_names):
                var_name = f"{router_id}_{route_name}"
                if self.binary_variables.get(var_name, 0) == 1:
                    if active_route_idx is not None:
                        raise ValueError(
                            f"Multiple routes active for router '{router_id}': "
                            f"{router.route_names[active_route_idx]} and {route_name}"
                        )
                    active_route_idx = idx

            if active_route_idx is None:
                raise ValueError(f"No active route for router '{router_id}'")

            # Set the active route
            router.set_active_route(active_route_idx)

    def get_active_units(self) -> List[bst.Unit]:
        """
        Get all units that should be active based on current binary variable configuration

        Returns:
            List of active BioSTEAM units (excluding inactive route units)
        """
        active_units = []

        # Add all non-router units that aren't in inactive routes
        inactive_unit_ids = set()
        for router in self.routers.values():
            for inactive_unit in router.get_inactive_units():
                inactive_unit_ids.add(inactive_unit.ID)

        for unit_id, unit in self.units.items():
            if unit_id not in inactive_unit_ids:
                active_units.append(unit)

        return active_units

    def build_system(self, system_name: Optional[str] = None) -> bst.System:
        """
        Build a BioSTEAM system with only the active units based on binary variables

        Args:
            system_name: Optional name for the system. If None, uses superstructure name.

        Returns:
            BioSTEAM System ready for simulation
        """
        if system_name is None:
            system_name = f"{self.name}_system"

        # Get active units
        active_units = self.get_active_units()

        # Determine the path (topological order)
        # For now, we'll use the order units were added
        # TODO: Implement proper topological sorting
        path = [u for u in active_units if u.__class__.__name__ != 'AlternativeRouter']

        # Include routers in the path at their appropriate positions
        for router in self.routers.values():
            # Find position: after inlet unit, before outlet units
            try:
                path_index = 0
                for i, unit in enumerate(path):
                    if any(router.ins[0].source is out for out in unit.outs):
                        path_index = i + 1
                        break
                path.insert(path_index, router)

                # Add active route units after router
                for active_unit in router.get_active_units():
                    if active_unit in path:
                        path.remove(active_unit)
                    path.insert(path_index + 1, active_unit)
                    path_index += 1
            except:
                # If we can't determine position, just append
                path.append(router)
                path.extend(router.get_active_units())

        # Create and return system
        system = bst.System(system_name, path=path)
        return system

    def simulate_configuration(self, binary_vars: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Simulate a specific configuration and return results

        Args:
            binary_vars: Optional binary variable configuration. If None, uses current configuration.

        Returns:
            Dictionary with simulation results:
            - success: Whether simulation converged
            - system: The BioSTEAM system
            - tea: TEA results (if TEA is set up)
            - objectives: Objective function values

        Example:
            >>> results = superstructure.simulate_configuration({
            ...     'ROUTER1_Route_A': 1,
            ...     'ROUTER1_Route_B': 0,
            ...     'ROUTER1_Route_C': 0
            ... })
            >>> if results['success']:
            ...     print(f"NPV: {results['objectives']['NPV']}")
        """
        # Update configuration if provided
        if binary_vars is not None:
            self.set_binary_variables(binary_vars)

        results = {
            'success': False,
            'system': None,
            'tea': None,
            'objectives': {},
            'error': None
        }

        try:
            # Build system with active units
            system = self.build_system()
            results['system'] = system

            # Simulate
            system.simulate()
            results['success'] = True

            # Calculate objectives
            if self.tea:
                results['tea'] = self.tea
                results['objectives'] = self.get_objectives()

        except Exception as e:
            results['error'] = str(e)
            results['success'] = False

        return results

    def get_binary_variable_info(self) -> Dict[str, Any]:
        """
        Get information about all binary variables in the superstructure

        Returns:
            Dictionary with:
            - variables: Dict of variable names and current values
            - constraints: List of constraint descriptions
            - routers: Dict of router information
        """
        info = {
            'variables': self.binary_variables.copy(),
            'constraints': [],
            'routers': {}
        }

        # Add router-specific constraints
        for router_id, router in self.routers.items():
            router_vars = [f"{router_id}_{name}" for name in router.route_names]
            info['constraints'].append({
                'type': 'single_choice',
                'description': f"Exactly one route must be active for {router_id}",
                'constraint': f"sum({router_vars}) == 1",
                'variables': router_vars
            })

            info['routers'][router_id] = {
                'n_routes': router.n_routes,
                'route_names': router.route_names,
                'active_route': router.active_route,
                'active_route_name': router.route_names[router.active_route]
            }

        return info
