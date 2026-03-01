"""System builder for the Polystyrene pyrolysis configuration.

import uuid
from typing import Dict, Optional, Sequence

import biosteam as bst

# Import side-effects (chemicals, property packages, unit subclasses, etc.)
from ._compounds import *  # noqa: F401,F403  pylint: disable=wildcard-import,unused-wildcard-import
from ._pyrolyzer import *  # noqa: F401,F403
from ._feed_handling import *  # noqa: F401,F403
from ._grinder import *  # noqa: F401,F403
from ._chscreen import *  # noqa: F401,F403
from ._cyclone import *  # noqa: F401,F403
from ._compressor import *  # noqa: F401,F403
from ._conveyor import *  # noqa: F401,F403
from ._hydrogen_production import *  # noqa: F401,F403
from ._utilityagents import *  # noqa: F401,F403


bst.nbtutorial()
bst.settings.CEPCI = 596.2
bst.settings.electricity_price = 0.065
bst.preferences.update(flow='kg/hr', T='degK', P='Pa', N=100, composition=True)

# Extend utility agent roster so cooling/heating duties match other builders
bst.HeatUtility().cooling_agents.append(NH3_utility)
bst.HeatUtility().heating_agents.append(Liq_utility)
bst.HeatUtility().heating_agents.append(Gas_utility)

DEFAULT_PRICES: Dict[str, float] = {
    "PS": 0.0,
    "Benzene": 0.86,
    "Toluene": 0.82,
    "Xylene": 0.80,
    "Aromatics": 0.78,
    "Hydrogen": 2.83,
    "NG": 7.40 * 1000 * 1.525 / 28316.8,
    "BTX": 0.83,
}


def _get_price(prices: Dict[str, float], key: str, fallback_keys: Optional[Sequence[str]] = None,
               default: float = 0.0) -> float:
    """Helper to fetch a price with optional fallbacks."""
    if key in prices:
        return prices[key]
    if fallback_keys:
        for candidate in fallback_keys:
            if candidate in prices:
                return prices[candidate]
    return default


def build_system(
    capacity: float,
    prices: Optional[Dict[str, float]] = None,
    reactor_temperature: float = 500 + 273.15,
    oxygen_equivalence_ratio: float = 0.07,
    fluidizing_gas_mass: float = 15.0,
    hydrotreat_hydrogen_mass: float = 15.0,
) -> bst.System:
    """Construct and return the BioSTEAM System for PS pyrolysis."""
    price_table = DEFAULT_PRICES if prices is None else prices
    previous_flowsheet = bst.main_flowsheet
    flowsheet = bst.Flowsheet(f"ps_flowsheet_{uuid.uuid4().hex[:6]}")
    bst.main_flowsheet = flowsheet

    try:
        ps_price = _get_price(price_table, "PS")
        benzene_price = _get_price(price_table, "Benzene", fallback_keys=["BTX"])
        toluene_price = _get_price(price_table, "Toluene", fallback_keys=["BTX"])
        xylene_price = _get_price(price_table, "Xylene", fallback_keys=["BTX"])
        aromatics_price = _get_price(price_table, "Aromatics", fallback_keys=["Xylene", "BTX"], default=xylene_price)
        hydrogen_price = _get_price(price_table, "Hydrogen")
        ng_price = _get_price(price_table, "NG")

        feed = bst.Stream('PS_Feed', PS=1, units='kg/hr', T=298, price=ps_price)
        feed.set_total_flow(capacity, 'tonnes/day')

        pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen', O2=1, units='kg/hr', T=298, price=0.0)
        oxygen_mass = oxygen_equivalence_ratio * capacity * 100 / 93
        pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

        fluidizing_gas = bst.Stream('fluidizing_gas', N2=1, units='kg/hr', T=298, price=0.0)
        fluidizing_gas.set_total_flow(fluidizing_gas_mass, 'kg/hr')

        hydrotreat_hydrogen = bst.Stream('Hydrogen', H2=1, units='kg/hr', T=298, price=hydrogen_price)
        hydrotreat_hydrogen.set_total_flow(hydrotreat_hydrogen_mass, 'kg/hr')

        recycle = bst.Stream('recycle')
        CRPS = bst.Stream('CRPS')
        char_sand = bst.Stream('CharSand')

        handling = Feed_handling('Handling', ins=[feed, recycle], outs=('FeedHandling',))
        mixer_1 = bst.units.Mixer('Mixer_1', ins=[handling-0])
        grinder = Grinder('Grinder', ins=[mixer_1-0], outs=('grinderout',))
        ch_screen = Screen('CHScreen', ins=[grinder-0], outs=[CRPS])

        mixer_pyrolyzer = bst.units.Mixer('Mixer_pyrolyzer', ins=[CRPS, fluidizing_gas, pyrolysis_oxygen])

        reactor = bst.units.Pyrolyzer('Pyrolyzer', ins=[mixer_pyrolyzer-0], outs=('PyrolyzerO',),
                                      T=reactor_temperature, P=101325)
        cyclone = bst.units.Cyclone('Cyclone0', ins=(reactor-0,), outs=['oil_Gas', char_sand], efficiency=0.99)
        cooler1 = bst.units.HXutility('cooler', ins=[cyclone-0], outs=('coolerOil',), T=273.15 + 10, rigorous=False)
        flash0 = bst.units.Flash('F0', ins=cooler1-0, T=273.15 + 10, P=101325, outs=('F0gas', 'F0oil'))
        flash0.reset_cache()

        pump1 = bst.units.Pump('Pump1', ins=[flash0-1], P=25 * 101325)
        flash1 = bst.units.Flash('F1o', ins=pump1-0, T=285, P=101325, outs=('F1ogas', 'F1ooil'))
        flash1.reset_cache()

        dist1 = bst.units.BinaryDistillation(
            'D1', ins=flash1.outs[1], outs=['BenzeneD1', 'TolueneD1'],
            LHK=('C6H6', 'C7H8'), y_top=0.90, x_bot=0.10, k=2.2, P=101325,
        )

        dist2 = bst.units.BinaryDistillation(
            'D2', ins=dist1-1, outs=['TolueneD2', 'XyleneD2'],
            LHK=('C7H8', 'C8H18'), product_specification_format='Recovery',
            Lr=0.95, Hr=0.95, k=2.2, P=101325,
        )

        dist3 = bst.units.BinaryDistillation(
            'D3', ins=dist2-1, outs=['Aromatics', 'XyleneD3'],
            LHK=('C8H18', 'C8H10'), y_top=0.95, x_bot=0.05, k=2.2, P=101325,
        )

        dist4 = bst.units.BinaryDistillation(
            'D4', ins=dist3-1, outs=['XyleneD4', ''],
            LHK=('C8H10', 'PS'), product_specification_format='Recovery',
            Lr=0.95, Hr=0.95, k=2.2, P=101325,
        )
        dist4._design = lambda: None
        dist4._cost = lambda: None
        dist4.purchase_costs = {'Distillation column': 320257.691}

        cooler2 = bst.units.HXutility('coolerD1', ins=dist1-0, outs=('BenzeneO',), T=298.15, rigorous=True)
        cooler2.outs[0].price = benzene_price

        cooler3 = bst.units.HXutility('coolerD2', ins=dist2-0, outs=('TolueneO',), T=298.15, rigorous=True)
        cooler3.outs[0].price = toluene_price

        cooler4 = bst.units.HXutility('coolerD3', ins=dist3-0, outs=('AromaticsO',), T=298.15, rigorous=True)
        cooler4.outs[0].price = aromatics_price

        cooler5 = bst.units.HXutility('coolerD4', ins=dist4-0, outs=('XyleneO',), T=298.15, rigorous=True)
        cooler5.outs[0].price = xylene_price

        cooler6 = bst.units.HXutility('coolerD5', ins=dist4-1, outs=('PSO',), T=298.15, rigorous=True)
        cooler6.outs[0].price = ps_price

        turbo_mixer = bst.units.Mixer('Turbogenerator_mixer', ins=[flash0-0, flash1-0])

        btg_fuel = bst.Stream('boiler_turbogenerator_fuel', NG=1, T=298.15, P=101325, price=ng_price)
        btg_water = bst.Stream('boiler_turbogenerator_water', T=298.15, P=101325)
        btg_ng = bst.Stream('boiler_turbogenerator_ng', NG=1, T=298.15, P=101325, price=ng_price)
        btg_lime = bst.Stream('boiler_turbogenerator_lime', T=298.15, P=101325)
        btg_chemicals = bst.Stream('boiler_turbogenerator_chemicals', T=298.15, P=101325)

        bst.BoilerTurbogenerator(
            'Turbogenerator',
            ins=(btg_fuel, turbo_mixer-0, btg_water, btg_ng, btg_lime, btg_chemicals),
        )

        system = flowsheet.create_system(f'PS_sys_{uuid.uuid4().hex[:6]}')

        for stream in system.products:
            # Preserve explicit prices (e.g., already set on coolers) and only fill gaps
            if not stream.price:
                try:
                    stream.price = price_table[str(stream)]
                except KeyError:
                    pass
    finally:
        bst.main_flowsheet = previous_flowsheet

    return system
