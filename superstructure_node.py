"""
Superstructure Node — Routing Unit for Process Synthesis

This module implements a decision "Node" for superstructures following
the Grossmann approach. A node can have multiple alternative outlets,
where only one is active at a time.

Features:
- Accepts 1 or more inputs
- Has N alternative outlets (mutually exclusive)
- Binary variables y_i determine which outlet is active
- Only the unit connected to the active outlet is included in the system

Author: David Lorenzo
Date: 2026-01-13
"""

import biosteam as bst
from typing import Optional, List


class ConvergenceMixer(bst.Mixer):
    """
    Virtual mixer for convergence of alternative routes.

    Has no design or cost — it only collects alternative streams
    where only one carries flow at a time.
    """

    def _design(self):
        """No design — virtual unit"""
        pass

    def _cost(self):
        """No cost — virtual unit"""
        self.purchase_costs.clear()
        self.baseline_purchase_costs.clear()
        self.installed_costs.clear()


class SuperstructureNode(bst.Unit):
    """
    Decision node for superstructures with alternative routes.

    A node represents a decision point where the flow can go to one
    of N mutually exclusive alternatives (only one active).

    Attributes:
        active_outlet: Index of the active outlet (0 to N-1)
        n_outlets: Number of alternative outlets
    """

    _N_ins = 1
    _N_outs = 2  # Default, will be updated in __init__
    _ins_size_is_fixed = False  # Allow multiple inputs
    _outs_size_is_fixed = False  # Allow N outlets

    def __init__(self, ID: str = '', ins=None, outs=(), thermo=None,
                 active_outlet: int = 0):
        """
        Initialize superstructure node

        Args:
            ID: Unique identifier for the node
            ins: Input stream(s) (can be 1 or multiple)
            outs: Output streams (one per alternative)
            thermo: Thermodynamic package
            active_outlet: Index of the initially active outlet (default: 0)
        """
        # Update number of outlets before calling super().__init__
        if isinstance(outs, (tuple, list)):
            self._N_outs = len(outs)

        # Update number of inputs
        if isinstance(ins, (tuple, list)):
            self._N_ins = len(ins)
        elif ins is not None:
            self._N_ins = 1

        super().__init__(ID=ID, ins=ins, outs=outs, thermo=thermo)

        self.n_outlets = len(self.outs)

        if self.n_outlets < 2:
            raise ValueError("SuperstructureNode requires at least 2 alternative outlets")

        if not 0 <= active_outlet < self.n_outlets:
            raise ValueError(f"active_outlet must be between 0 and {self.n_outlets-1}")

        self.active_outlet = active_outlet

    def set_active_outlet(self, outlet_index: int):
        """
        Change which outlet is active and update all streams

        Args:
            outlet_index: Index of the outlet to activate (0 to N-1)
        """
        if not 0 <= outlet_index < self.n_outlets:
            raise ValueError(f"outlet_index must be between 0 and {self.n_outlets-1}")
        self.active_outlet = outlet_index
        # Re-ejecutar para actualizar todas las corrientes
        self._run()

    def _run(self):
        """
        Run the node: copy input(s) to the active outlet, empty the others
        """
        # If there are multiple inputs, mix them first
        if len(self.ins) > 1:
            # Create a temporary mixed stream
            mixed = self.ins[0].copy()
            for inlet in self.ins[1:]:
                mixed.mix_from([mixed, inlet])
            inlet_stream = mixed
        else:
            inlet_stream = self.ins[0]

        # Copy to active outlet
        self.outs[self.active_outlet].copy_like(inlet_stream)

        # Empty the inactive outlets and their downstream units
        for i, outlet in enumerate(self.outs):
            if i != self.active_outlet:
                outlet.empty()
                # Keep T and P for consistency
                outlet.T = inlet_stream.T
                outlet.P = inlet_stream.P

                # Also empty the downstream unit's outlets if it exists
                if outlet._sink:
                    for downstream_outlet in outlet._sink.outs:
                        downstream_outlet.empty()
                        downstream_outlet.T = inlet_stream.T
                        downstream_outlet.P = inlet_stream.P

    def _design(self):
        """No specific design — the node is virtual"""
        pass

    def _cost(self):
        """No cost — the node is virtual"""
        self.purchase_costs.clear()
        self.baseline_purchase_costs.clear()
        self.installed_costs.clear()

    def get_binary_variables(self) -> dict:
        """
        Get binary variables for optimization

        Returns:
            Dict of binary variables: {outlet_name: 1 if active, 0 otherwise}
        """
        return {
            self.outs[i]._sink.ID if self.outs[i]._sink else f"outlet_{i}":
            (1 if i == self.active_outlet else 0)
            for i in range(self.n_outlets)
        }

    def set_from_binary_variables(self, binary_vars: dict):
        """
        Set active outlet from binary variables

        Args:
            binary_vars: Dict {unit_id: 1 or 0} indicating which is active
        """
        # Encontrar cuál variable es 1
        active_units = [
            unit_id for unit_id, value in binary_vars.items()
            if value == 1
        ]

        if len(active_units) == 0:
            raise ValueError(f"No active outlet in node {self.ID}")
        elif len(active_units) > 1:
            raise ValueError(f"Multiple active outlets in node {self.ID}: {active_units}")

        # Encontrar el índice correspondiente
        active_unit = active_units[0]
        for i, outlet in enumerate(self.outs):
            if outlet._sink and outlet._sink.ID == active_unit:
                self.active_outlet = i
                return

        raise ValueError(f"Could not find unit {active_unit} connected to node {self.ID}")


def get_active_system_units(nodes: List[SuperstructureNode],
                            all_units: List[bst.Unit]) -> List[bst.Unit]:
    """
    Determine which units should be included in the system based on
    the active outlets of the nodes.

    Args:
        nodes: List of SuperstructureNode in the superstructure
        all_units: List of all defined units

    Returns:
        List of units that should be in the active system
    """
    active_units = []
    inactive_unit_ids = set()

    # Collect IDs of units connected to inactive outlets
    for node in nodes:
        for i, outlet in enumerate(node.outs):
            if i != node.active_outlet and outlet._sink:
                # Mark this unit and its descendants as inactive
                inactive_unit_ids.add(outlet._sink.ID)

    # Filter units
    for unit in all_units:
        if unit.ID not in inactive_unit_ids:
            active_units.append(unit)

    return active_units


def configure_node_from_binary(node: SuperstructureNode,
                               variable_name: str,
                               binary_values: dict) -> None:
    """
    Configure a node from a set of Pyomo binary variables

    Args:
        node: Node to configure
        variable_name: Base name of the variables (e.g., 'REACTOR_TYPE')
        binary_values: Dict with values of binary variables

    Example:
        >>> binary_values = {
        ...     'REACTOR_TYPE_flash': 1,
        ...     'REACTOR_TYPE_hx': 0,
        ...     'REACTOR_TYPE_mixer': 0
        ... }
        >>> configure_node_from_binary(node, 'REACTOR_TYPE', binary_values)
    """
    # Encontrar cuál variable es 1
    active_index = None
    for i, outlet in enumerate(node.outs):
        outlet_name = outlet.ID if hasattr(outlet, 'ID') else f"{variable_name}_{i}"
        var_name = f"{variable_name}_{outlet_name}"

        if binary_values.get(var_name, 0) == 1:
            if active_index is not None:
                raise ValueError(
                    f"Múltiples salidas activas para {variable_name}: "
                    f"{active_index} y {i}"
                )
            active_index = i

    if active_index is None:
        raise ValueError(f"No active outlet for {variable_name}")

    node.set_active_outlet(active_index)