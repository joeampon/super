"""
Custom unit operations for the superstructure.

Consolidated from TOD, FCC, Plasma, and CPY technology folders.
"""

import numpy as np
import biosteam as bst
import thermosteam as tmo
from biosteam import Unit
from biosteam.units.decorators import cost
from math import sqrt, pi


# ============================================================================
# Feed Handling (conveyor + hopper)
# ============================================================================
@cost(basis='feed', ID='Conveyor_hopper', units='tonnes/day',
      S=500, CE=596.2, cost=236452.39 + 297661.70, n=0.6, BM=1)
class Feed_handling(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    _units = {'feed': 'tonnes/day', 'Duty': 'kJ/hr', 'Power': 'kW'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=self.thermo)
        self.T = T
        self.P = P

    def _setup(self):
        super()._setup()

    def _run(self):
        out = self.outs[0]
        out.copy_like(self.ins[0])
        out.T = self.T
        out.P = self.P

    def _design(self):
        duty = self.H_out - self.H_in
        self.design_results['feed'] = self.ins[0].get_total_flow("tonnes/day")
        self.design_results['Duty'] = duty
        self.design_results['Power'] = 0
        self.add_heat_utility(duty, self.ins[0].T)


# ============================================================================
# Grinder
# ============================================================================
@cost(basis='Grinder_feed', ID='Grinder', units='tonnes/day',
      S=500, CE=550.8, cost=616710.94, n=0.6, BM=1)
class Grinder(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    _units = {'Grinder_feed': 'tonnes/day', 'Power': 'kW', 'Duty': 'kJ/hr'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=self.thermo)
        self.T = T
        self.P = P

    def _setup(self):
        super()._setup()

    def _run(self):
        out = self.outs[0]
        out.copy_like(self.ins[0])
        out.T = self.T
        out.P = self.P

    def _design(self):
        duty = self.H_out - self.H_in
        grinder_electricity = 300 * self.ins[0].get_total_flow("tonnes/hr")
        self.design_results['Grinder_feed'] = self.ins[0].get_total_flow("tonnes/day")
        self.design_results['Duty'] = duty
        self.design_results['Power'] = grinder_electricity
        self.add_power_utility(grinder_electricity)


# ============================================================================
# Screen (CHScreen)
# ============================================================================
@cost(basis='screenfeed', ID='Screen', units='tonnes/day',
      S=500, CE=550.8, cost=39934.31, n=0.6, BM=1)
class Screen(bst.Unit):
    _N_ins = 1
    _N_outs = 2
    _units = {'screenfeed': 'tonnes/day', 'Duty': 'kJ/hr'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325, screen_size=0.01):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=self.thermo)
        self.T = T
        self.P = P
        self.screen_size = screen_size

    def _setup(self):
        super()._setup()

    def _run(self):
        ins = self.ins[0]
        finely_crushed, recycled_feed = self.outs
        finely_crushed.copy_like(ins)
        recycled_feed.copy_like(ins)
        finely_crushed.T = self.T
        recycled_feed.T = self.T
        finely_crushed.P = self.P
        recycled_feed.P = self.P
        screened_total_flow = ins.get_total_flow('kg/hr') * 99 / 100
        finely_crushed.set_total_flow(screened_total_flow, 'kg/hr')
        recycled_feed.set_total_flow(ins.get_total_flow('kg/hr') - screened_total_flow, 'kg/hr')

    def _design(self):
        self.design_results['screenfeed'] = self.ins[0].get_total_flow("tonnes/day")


# ============================================================================
# Cyclone
# ============================================================================
@cost(basis='flowrate', ID='Cyclone', units='tonnes/day',
      S=500, CE=567.5, cost=982510.7, n=0.6, BM=4.28)
class Cyclone(Unit):
    _N_ins = 1
    _N_outs = 2
    _units = {'flowrate': 'tonnes/day', 'Duty': 'kJ/hr'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325, efficiency=0.99):
        Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=self.thermo, phases=['g', 'l', 's'])
        self.T = T
        self.P = P
        self.efficiency = efficiency

    def _setup(self):
        super()._setup()

    def _run(self):
        feed = self.ins[0]
        vapor, solid = self.outs
        ms = self._multistream
        ms.imol['g'] = feed.mol
        for k in ms.available_chemicals:
            if str(k) in ['Ash', 'Sand', 'Char']:
                solid.imol[str(k)] = ms.imol['g', str(k)] * 1
                vapor.imol[str(k)] = ms.imol['g', str(k)] * 0
            else:
                vapor.imol[str(k)] = ms.imol['g', str(k)]
        vapor.phase = 'g'
        solid.phase = 's'
        vapor.T = self.ins[0].T
        vapor.P = self.ins[0].P
        solid.T = self.ins[0].T
        solid.P = self.ins[0].P
        ms.empty()

    def _design(self):
        self.design_results['flowrate'] = self.ins[0].get_total_flow("tonnes/day")


# ============================================================================
# Combustor (Sand Furnace)
# ============================================================================
@cost(basis='duty', ID='Furnace', units='kJ/hr',
      S=74588e3, CE=567.5, cost=1566589.78, n=0.6, BM=4.28)
class Combustor(bst.Unit):
    _N_ins = 4
    _N_outs = 1
    _units = {'Infeed': 'tonnes/day', 'duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), T_out=1000 + 273.15, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T_out
        self.T = T_out

    def _setup(self):
        super()._setup()

    def _run(self):
        sand_out = self.outs[0]
        sand_out.copy_like(self.ins[0])
        sand_out.T = self.T

    def _design(self):
        reactor_duty = self.H_out - self.H_in
        self.design_results['duty'] = reactor_duty
        self.design_results['Infeed'] = self.ins[0].get_total_flow("tonnes/day") * 0.4


# ============================================================================
# RYield Reactor (pyrolysis)
# ============================================================================
@cost(basis='Infeed', ID='reactor', units='tonnes/day',
      S=500, CE=567.5, cost=8766341.78, n=0.6, BM=4.28)
class RYield(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    _units = {'Infeed': 'tonnes/day', 'Duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), yields=None, T=600 + 273.15,
                 factor=1, wt_closure=100, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T
        self.factor = factor
        self.yields = yields
        self.wt_closure = wt_closure

    def _setup(self):
        super()._setup()

    def _run(self):
        feed = self.ins[0]
        vap = self.outs[0]
        mass = (feed.get_total_flow(units='kg/hr')
                - feed.get_flow('kg/hr', 'N2')
                - feed.get_flow('kg/hr', 'O2') * self.wt_closure / 100)
        ms = bst.Stream(None, thermo=feed.thermo)
        for c, y in self.yields.items():
            if c != 'N2':
                try:
                    ms.set_flow(mass * y, "kg/hr", c)
                except Exception:
                    pass
            elif c == 'N2':
                ms.set_flow(feed.get_flow('kg/hr', 'N2'), "kg/hr", c)
        ms.set_flow(feed.get_flow('kg/hr', 'Sand'), "kg/hr", 'Sand')
        vap.copy_flow(ms)
        vap.T = self.T
        vap.P = feed.P
        vap.phase = 'g'
        ms.empty()

    def _design(self):
        self.design_results['Infeed'] = (
            self.ins[0].get_total_flow("tonnes/day") * self.factor
        )


# ============================================================================
# Compressor (custom, simple)
# ============================================================================
@cost(basis='flow_in', ID='Compressor', units='kmol/hr',
      S=521.9, CE=567.5, cost=17264.08, n=0.6, BM=3.3)
class Compressor(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    _units = {'flow_in': 'kmol/hr', 'Duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), phase='g', thermo=None, *,
                 P=101325, Q=0, eta=0.8, isentropic=False):
        bst.Unit.__init__(self, ID, ins, outs, thermo)
        self.P = P
        self.Q = Q
        self.eta = eta
        self.isentropic = isentropic
        self.phase = phase

    def _setup(self):
        super()._setup()

    def _run(self):
        self.outs[0].copy_like(self.ins[0])
        self.outs[0].T = 273.15 + 30
        self.outs[0].P = self.P
        self.outs[0].phase = self.phase

    def _design(self):
        self.design_results['flow_in'] = self.outs[0].F_mol


# ============================================================================
# Hydrocrack Reactor
# ============================================================================
@cost(basis='Infeed', ID='reactor', units='bbl/day',
      S=2250, CE=468.2, cost=30e6, n=0.65, BM=1)
class Hydrocrack(bst.Unit):
    _N_ins = 3
    _N_outs = 3
    _units = {'Infeed': 'bbl/day', 'Duty': 'kJ/hr', 'Power': 'kW'}

    def __init__(self, ID='', ins=(), outs=(), reaction=None, T=300 + 273.15,
                 *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T
        self.reaction = reaction

    def _setup(self):
        super()._setup()

    def _run(self):
        feed, h2, catalyst = self.ins
        reacted, h2_out, cat_out = self.outs

        # Combine feed and H2 for reaction
        reacted.copy_like(feed)
        reacted.imol['H2'] += h2.imol['H2']
        reacted.T = self.T
        reacted.P = feed.P

        # Apply hydrocracking reactions (wax + H2 → naphtha + diesel)
        if self.reaction:
            self.reaction(reacted)

        # H2 is mixed into reacted stream; downstream splitter handles excess
        h2_out.empty()
        h2_out.T = self.T
        h2_out.P = h2.P

        # Catalyst passes through
        cat_out.copy_like(catalyst)
        cat_out.T = self.T

    def _design(self):
        duty = self.H_out - self.H_in
        hydrocracking_power = 6.9 * self.ins[0].get_total_flow(units="bbl/hr")
        self.design_results['Power'] = hydrocracking_power
        self.design_results['Infeed'] = self.ins[0].get_total_flow(units="bbl/day")
        self.add_power_utility(hydrocracking_power)


# ============================================================================
# Fluidized Catalytic Cracking (FCC)
# ============================================================================
class FluidizedCatalyticCracking(bst.Unit):
    _N_ins = 4
    _N_outs = 3
    auxiliary_unit_names = (
        'pump', 'feed_preheater', 'air_compressor', 'condenser',
        'riser', 'stripper', 'regenerator', 'reactor',
    )

    def _init(self, reaction, vessel_material=None, feed_pressure=None,
              catalyst_to_feed_ratio=None, spent_catalyst_to_feed_ratio=None,
              product_loss=None, riser_product_residence_time=None,
              riser_length_to_diameter=None,
              reactor_vessel_dissengagement_height=None,
              reactor_vessel_exit_velocity=None,
              stripper_steam_rate=None,
              stripper_catalyst_residence_time=None,
              stripper_length_to_diameter=None,
              CO2_concentration=None,
              regenerator_catalyst_residence_time=None,
              regenerator_length_to_diameter=None,
              regenerator_pressure=None):
        if vessel_material is None: vessel_material = 'Stainless steel 316'
        if feed_pressure is None: feed_pressure = 2 * 101325
        if catalyst_to_feed_ratio is None: catalyst_to_feed_ratio = 5
        if spent_catalyst_to_feed_ratio is None: spent_catalyst_to_feed_ratio = 1e-6
        if product_loss is None: product_loss = 0.5e-2
        if riser_product_residence_time is None: riser_product_residence_time = 2.1 / 3600
        if riser_length_to_diameter is None: riser_length_to_diameter = 20
        if reactor_vessel_dissengagement_height is None: reactor_vessel_dissengagement_height = 4.572
        if reactor_vessel_exit_velocity is None: reactor_vessel_exit_velocity = 2194.56
        if stripper_steam_rate is None: stripper_steam_rate = 0.25
        if stripper_catalyst_residence_time is None: stripper_catalyst_residence_time = 75 / 3600
        if stripper_length_to_diameter is None: stripper_length_to_diameter = 1
        if CO2_concentration is None: CO2_concentration = 0.055
        if regenerator_catalyst_residence_time is None: regenerator_catalyst_residence_time = 7.5 / 60
        if regenerator_length_to_diameter is None: regenerator_length_to_diameter = 0.5
        if regenerator_pressure is None: regenerator_pressure = 282685
        self.reaction = reaction
        self.vessel_material = vessel_material
        self.feed_pressure = feed_pressure
        self.catalyst_to_feed_ratio = catalyst_to_feed_ratio
        self.spent_catalyst_to_feed_ratio = spent_catalyst_to_feed_ratio
        self.product_loss = product_loss
        self.riser_product_residence_time = riser_product_residence_time
        self.riser_length_to_diameter = riser_length_to_diameter
        self.reactor_vessel_dissengagement_height = reactor_vessel_dissengagement_height
        self.reactor_vessel_exit_velocity = reactor_vessel_exit_velocity
        self.stripper_steam_rate = stripper_steam_rate
        self.stripper_catalyst_residence_time = stripper_catalyst_residence_time
        self.stripper_length_to_diameter = stripper_length_to_diameter
        self.CO2_concentration = CO2_concentration
        self.regenerator_catalyst_residence_time = regenerator_catalyst_residence_time
        self.regenerator_length_to_diameter = regenerator_length_to_diameter
        self.regenerator_pressure = regenerator_pressure

    def _setup(self):
        super()._setup()
        pump = self.auxiliary('pump', bst.Pump, ins=self.ins[0], P=self.feed_pressure)
        self.auxiliary('feed_preheater', bst.HXutility, ins=pump - 0, V=0, rigorous=True)
        self.auxiliary('air_compressor', bst.IsentropicCompressor,
                       ins=self.ins[2], P=self.regenerator_pressure)

    def _estimate_reactor_pressure_drop(self):
        return 40530.0

    def _estimate_regenerator_pressure_drop(self):
        return 40530.0

    def _run(self):
        feed, fresh_catalyst, air, steam = self.ins
        product, discarded_catalyst, flue_gas = self.outs
        self.pump.run()
        self.feed_preheater.run()
        F_mass_feed = feed.F_mass
        fresh_catalyst.imass['Zeolite'] = discarded_catalyst.imass['Zeolite'] = (
            F_mass_feed * self.spent_catalyst_to_feed_ratio
        )
        self.catalyst_recirculation = catalyst_recirculation = (
            F_mass_feed * self.catalyst_to_feed_ratio
        )
        steam.copy_like(bst.settings.get_heating_agent('low_pressure_steam'))
        steam.imass['water'] = catalyst_recirculation * self.stripper_steam_rate
        product.P = self.feed_pressure - self._estimate_reactor_pressure_drop()
        flue_gas.P = discarded_catalyst.P = (
            self.regenerator_pressure - self._estimate_regenerator_pressure_drop()
        )
        product.mol = feed.mol + steam.mol
        product.phase = 'g'
        flue_gas.phase = 'g'
        if self.reaction:
            self.reaction.force_reaction(product)
        product.split_to(flue_gas, product, self.product_loss, energy_balance=False)
        product_loss = flue_gas.mol.copy()
        combustion = self.chemicals.get_combustion_reactions()
        combustion.force_reaction(flue_gas)
        O2 = -flue_gas.imass['O2']
        N2 = 0.79 / 0.21 * O2
        air.imass['O2', 'N2'] = [O2, N2]
        flue_gas.mol += air.mol
        F_emissions = flue_gas.F_mass
        z_CO2 = flue_gas.imass['CO2'] / F_emissions
        z_CO2_target = self.CO2_concentration
        if z_CO2 > z_CO2_target:
            F_emissions_new = z_CO2 * F_emissions / z_CO2_target
            dF_emissions = F_emissions_new - F_emissions
            air.F_mass = F_mass_O2_new = air.F_mass + dF_emissions
            flue_gas.mol += air.mol * (dF_emissions / F_mass_O2_new)
        self.air_compressor.run()
        regenerated_catalyst = bst.Stream(None, Catalyst=catalyst_recirculation, units='kg/hr')
        spent_catalyst = bst.Stream(None, Catalyst=catalyst_recirculation, units='kg/hr')
        spent_catalyst.mol += product_loss
        compressed_air = self.air_compressor - 0
        heated_feed = self.feed_preheater - 0
        regenerator_outlets = [flue_gas, regenerated_catalyst, discarded_catalyst]
        regenerator_inlets = [compressed_air, spent_catalyst, fresh_catalyst]
        reactor_outlets = [product, spent_catalyst]
        reactor_inlets = [heated_feed, steam, regenerated_catalyst]
        feed_temperature = self.feed_preheater.outs[0].T
        for i in regenerator_outlets + reactor_outlets:
            i.T = feed_temperature
        dTs = np.ones(2)
        while np.abs(dTs).sum() > 0.1:
            A = np.array([
                [sum([i.C for i in regenerator_outlets]), -spent_catalyst.C],
                [-regenerated_catalyst.C, sum([i.C for i in reactor_outlets])],
            ])
            b = np.array([
                sum([i.Hnet for i in regenerator_inlets]) - sum([i.Hnet for i in regenerator_outlets]),
                sum([i.Hnet for i in reactor_inlets]) - sum([i.Hnet for i in reactor_outlets]),
            ])
            dT_regenerator, dT_reactor = dTs = np.linalg.solve(A, b)
            for i in regenerator_outlets:
                i.T += dT_regenerator
            for i in reactor_outlets:
                i.T += dT_reactor

    def _design(self):
        self.riser_volume = riser_volume = self.riser_product_residence_time * self.outs[0].F_vol
        L2D = self.riser_length_to_diameter
        self.riser_diameter = riser_diameter = (riser_volume * 4 / (pi * L2D)) ** (1 / 3)
        self.riser_length = riser_diameter * L2D
        self.riser = bst.AuxiliaryPressureVessel(
            self.feed_pressure, riser_diameter, riser_diameter * L2D,
            pressure_units='Pa', length_units='m',
            orientation='Vertical', material=self.vessel_material,
        )
        reactor_length = self.reactor_vessel_dissengagement_height
        reactor_diameter = sqrt(4 * self.outs[0].F_vol / self.reactor_vessel_exit_velocity / pi)
        self.reactor = bst.AuxiliaryPressureVessel(
            self.feed_pressure, reactor_diameter, reactor_length,
            pressure_units='Pa', length_units='m',
            orientation='Vertical', material=self.vessel_material,
        )
        catalyst_vol = self.catalyst_recirculation / self.chemicals.Catalyst.rho(
            self.outs[0].T, self.outs[0].P
        )
        stripper_volume = self.stripper_catalyst_residence_time * catalyst_vol
        L2D = self.stripper_length_to_diameter
        stripper_diameter = (stripper_volume * 4 / (pi * L2D)) ** (1 / 3)
        self.stripper = bst.AuxiliaryPressureVessel(
            self.feed_pressure, stripper_diameter, stripper_diameter * L2D,
            pressure_units='Pa', length_units='m',
            orientation='Vertical', material=self.vessel_material,
        )
        regenerator_volume = self.regenerator_catalyst_residence_time * catalyst_vol
        L2D = self.regenerator_length_to_diameter
        regenerator_diameter = (regenerator_volume * 4 / (pi * L2D)) ** (1 / 3)
        self.regenerator = bst.AuxiliaryPressureVessel(
            self.regenerator_pressure, regenerator_diameter,
            regenerator_diameter * L2D,
            pressure_units='Pa', length_units='m',
            orientation='Vertical', material=self.vessel_material,
        )
        self.regenerator.design_results["Ideal power"] = 0
        self.air_compressor.design_results["Ideal power"] = 0
        for i in self.auxiliary_units:
            i._design()

    def _cost(self):
        for i in self.auxiliary_units:
            i._cost()


FCC = FluidizedCatalyticCracking


# ============================================================================
# Plasma Reactor
# ============================================================================
class PlasmaReactor(bst.Unit):
    """Non-equilibrium plasma reactor for co-upcycling polyolefins with CO2.

    Yields are mass fractions per kg of feedstock consumed.  Because CO2
    is incorporated into the oxygenated products the yield total exceeds
    1.0; the extra mass is drawn from the inlet CO2 (and O2) streams.

    When ``use_ml=True`` (default), yields are predicted by PyrolysisNet
    with a plasma-specific correction and compound mapping.  When
    ``use_ml=False``, fixed yields from Case G are used.

    Default yields correspond to Case G (CO2 plasma, t_R = 20 s) from
    Radhakrishnan et al., *Green Chem.*, 2024, **26**, 9156-9175.

    Parameters
    ----------
    use_ml : bool
        If True, predict yields dynamically from feed composition via
        PyrolysisNet with plasma correction.  Default True.
    vrt : float
        Vapor residence time in seconds (ML model input).  Default 20.0.
    virtual_temperature : float
        Temperature in °C fed to the ML model (actual plasma T is lower).
        Default 450.
    """
    _N_ins = 1
    _N_outs = 1
    _F_BM_default = {"Plasma Reactor": 1.0}

    DEFAULT_YIELDS = {
        # Liquid products (wt% of PE feedstock, Case G)
        "Alcohol": 0.6111, "Acid": 0.1448, "C14H22O": 0.0904,
        "C8H18": 0.1385, "C18H38": 0.1144, "C30H62": 0.0312,
        # Gas products (~17.7 wt% of PE; ~90% CO, ~5% H2)
        "CO": 0.159, "H2": 0.009,
    }

    def __init__(self, ID="", ins=(), outs=(), power=0, yields=None,
                 feedstock_IDs=None, use_ml=True, vrt=20.0,
                 virtual_temperature=450):
        if yields is None:
            yields = dict(self.DEFAULT_YIELDS)
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self.power_utility = bst.PowerUtility()
        self.power = power
        self.yields = yields
        self.feedstock_IDs = feedstock_IDs if feedstock_IDs is not None else ['Plastic']
        self.use_ml = use_ml
        self.vrt = vrt
        self.virtual_temperature = virtual_temperature

    def _predict_yields(self):
        """Use PyrolysisNet with plasma correction to predict yields."""
        from ..machine_learning.model import predict_plasma

        feed = self.ins[0]
        feedstock_mass = sum(feed.imass[fid] for fid in self.feedstock_IDs)
        if feedstock_mass <= 0:
            return {}

        # Determine HDPE/LDPE/PP wt% from feed
        hdpe_mass = feed.imass['HDPE'] if 'HDPE' in self.feedstock_IDs else 0
        ldpe_mass = feed.imass['LDPE'] if 'LDPE' in self.feedstock_IDs else 0
        pp_mass = feed.imass['PP'] if 'PP' in self.feedstock_IDs else 0

        for fid in self.feedstock_IDs:
            if fid not in ('HDPE', 'LDPE', 'PP'):
                hdpe_mass += feed.imass[fid]

        total_poly = hdpe_mass + ldpe_mass + pp_mass
        if total_poly > 0:
            hdpe_pct = 100.0 * hdpe_mass / total_poly
            ldpe_pct = 100.0 * ldpe_mass / total_poly
            pp_pct = 100.0 * pp_mass / total_poly
        else:
            hdpe_pct, ldpe_pct, pp_pct = 100.0, 0.0, 0.0

        temperature_C = self.ins[0].T - 273.15

        return predict_plasma(
            hdpe_pct, ldpe_pct, pp_pct, temperature_C, self.vrt,
            virtual_temperature=self.virtual_temperature,
        )

    def _setup(self):
        super()._setup()

    def _run(self):
        i = self.ins[0]
        o = self.outs[0]
        o.copy_like(i)

        yields = self._predict_yields() if self.use_ml else self.yields

        feedstock_mass = sum(i.get_flow("kg/hr", fid) for fid in self.feedstock_IDs)
        for product, y in yields.items():
            o.set_flow(feedstock_mass * y, "kg/hr", product)
        for species in [c.ID for c in i.available_chemicals]:
            if species not in yields:
                o.set_flow(i.get_flow("kg/hr", species), "kg/hr", species)
        # CO2 consumed = product mass exceeding feedstock, minus O2 consumed
        co2_consumed = feedstock_mass * (sum(yields.values()) - 1.0) - i.imass["O2"]
        o.imass["CO2"] = max(0, i.imass["CO2"] - max(0, co2_consumed))
        o.imass["O2"] = 0
        for fid in self.feedstock_IDs:
            o.imass[fid] = 0.001 * i.imass[fid]
        o.T = 273.15 + 400

    def _design(self):
        self.add_power_utility(self.power)

    def _cost(self):
        i = self.ins[0]
        base_cost = 20000000
        base_size = 200000
        self.baseline_purchase_costs["Plasma Reactor"] = (
            base_cost * (i.get_total_flow("kg/day") / base_size) ** 0.7
        )


# ============================================================================
# Pyrolyzer for CPY — supports ML-predicted or fixed yields
# ============================================================================
class Pyrolyzer(bst.Unit):
    """Catalytic pyrolyzer with optional ML yield prediction.

    When ``use_ml=True`` (default), yields are predicted at each ``_run()``
    call by a pre-trained PyrolysisNet model based on feedstock composition
    (HDPE/LDPE/PP wt%) and operating conditions (temperature, VRT).

    When ``use_ml=False``, the unit falls back to the fixed ``yields`` dict
    (legacy behaviour).

    Parameters
    ----------
    use_ml : bool
        If True, load the trained PyrolysisNet model and predict yields
        dynamically from feed composition and reactor conditions.
    vrt : float
        Vapor residence time in seconds (used by ML model). Default 1.0.
    yields : dict, optional
        Fixed {compound_ID: mass_fraction} dict.  Only used when
        ``use_ml=False``.
    feedstock_IDs : list of str, optional
        Chemical IDs in the feed that are consumed as feedstock.
        Defaults to ``['HDPE']``.
    """
    _N_ins = 1
    _N_outs = 1

    # Default yields based on typical PS catalytic pyrolysis at 500C
    DEFAULT_YIELDS = {
        'C8H8': 0.25,    # Styrene
        'C6H6': 0.08,    # Benzene
        'C7H8': 0.08,    # Toluene
        'C8H18': 0.05,   # Octane (light naphtha)
        'C8H10': 0.08,   # Xylene
        'C9H12': 0.06,   # Other aromatics
        'C10H22': 0.10,  # Alkanes (non-aromatic liquid)
        'H2': 0.002,     # Hydrogen gas
        'CO2': 0.05,     # Carbon dioxide
        'CH4': 0.01,     # Methane
        'C2H4': 0.03,    # Ethylene
        'C': 0.10,       # Char/carbon
    }

    def __init__(self, ID, ins=(), outs=(), T=500 + 273.15, P=101325,
                 yields=None, feedstock_IDs=None, use_ml=True, vrt=1.0,
                 reactor_type='thermal'):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self.T = T
        self.P = P
        self.use_ml = use_ml
        self.vrt = vrt
        self.reactor_type = reactor_type
        self.yields = yields if yields is not None else dict(self.DEFAULT_YIELDS)
        self.feedstock_IDs = feedstock_IDs if feedstock_IDs is not None else ['HDPE']

    def _predict_yields(self):
        """Use the ML model to predict yields from current feed and conditions."""
        from ..machine_learning.model import predict

        feed = self.ins[0]
        feedstock_mass = sum(feed.imass[fid] for fid in self.feedstock_IDs)
        if feedstock_mass <= 0:
            return {}

        # Determine HDPE/LDPE/PP wt% from feed
        hdpe_mass = feed.imass['HDPE'] if 'HDPE' in self.feedstock_IDs else 0
        ldpe_mass = feed.imass['LDPE'] if 'LDPE' in self.feedstock_IDs else 0
        pp_mass = feed.imass['PP'] if 'PP' in self.feedstock_IDs else 0

        # If feedstock includes generic IDs, assign their mass to HDPE
        for fid in self.feedstock_IDs:
            if fid not in ('HDPE', 'LDPE', 'PP'):
                hdpe_mass += feed.imass[fid]

        total_poly = hdpe_mass + ldpe_mass + pp_mass
        if total_poly > 0:
            hdpe_pct = 100.0 * hdpe_mass / total_poly
            ldpe_pct = 100.0 * ldpe_mass / total_poly
            pp_pct = 100.0 * pp_mass / total_poly
        else:
            hdpe_pct, ldpe_pct, pp_pct = 100.0, 0.0, 0.0

        temperature_C = self.T - 273.15

        return predict(hdpe_pct, ldpe_pct, pp_pct, temperature_C, self.vrt,
                       reactor_type=self.reactor_type)

    def _setup(self):
        super()._setup()

    def _run(self):
        feed = self.ins[0]
        products = self.outs[0]
        products.copy_like(feed)
        feedstock_mass = sum(feed.imass[fid] for fid in self.feedstock_IDs)
        for fid in self.feedstock_IDs:
            products.imass[fid] = 0

        yields = self._predict_yields() if self.use_ml else self.yields
        for chem_id, frac in yields.items():
            products.imass[chem_id] += feedstock_mass * frac
        products.T = self.T
        products.P = self.P

    def _design(self):
        pass

    def _cost(self):
        self.purchase_costs["Reactor"] = (
            2 * 3818000 * (self.ins[0].get_total_flow("lb/hr") / 2526000) ** 0.5
        )
        self.installed_costs["Reactor"] = self.purchase_costs["Reactor"] * 2.3


# ============================================================================
# Turbogenerator — combusts waste gas and generates electricity
# ============================================================================
class Turbogenerator(bst.Unit):
    """Combusts combined waste/flue gas streams and generates electricity."""
    _N_ins = 1
    _N_outs = 1
    _F_BM_default = {"Turbogenerator": 1.5}
    _units = {'Power': 'kW'}

    # LHV values in kJ/kg for common combustible species
    _LHV = {
        'H2': 120000, 'CH4': 50000, 'C2H4': 47200, 'C2H6': 47500,
        'C3H6': 45800, 'C3H8': 46400, 'C4H8': 45300, 'C4H6': 44600,
        'CO': 10100, 'C8H8': 40500, 'C6H6': 40200, 'C7H8': 40600,
    }

    def __init__(self, ID='', ins=(), outs=(), eta=0.35):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self.eta = eta

    def _setup(self):
        super()._setup()

    def _run(self):
        self.outs[0].copy_like(self.ins[0])
        self.outs[0].T = 273.15 + 150
        self.outs[0].P = 101325

    def _design(self):
        feed = self.ins[0]
        heat_kW = sum(
            feed.imass[chem] * lhv / 3600
            for chem, lhv in self._LHV.items()
            if feed.imass[chem] > 0
        )
        power = heat_kW * self.eta
        self.design_results['Power'] = power
        self.add_power_utility(-power)  # negative = generation

    def _cost(self):
        power = self.design_results.get('Power', 0)
        if power > 0:
            self.baseline_purchase_costs["Turbogenerator"] = 600 * power
