"""
Integrated superstructure system builder.

Builds ONE unified system where a common HDPE feed is split among four
upstream technologies (TOD, CP, CPY, PLASMA), with downstream separation
shared where applicable.

Architecture
------------
    HDPE Feed (250 tpd)
        |
    Splitter1 (fraction to CP+TOD vs rest)
       /              \
    Splitter3        Splitter2 (fraction to CPY vs PLASMA)
    (TOD vs CP)        /         \
     /     \         CPY        PLASMA
   TOD     CP       (full)     (full)
     \     /
    Mixer -> DISTILLATION
                |
          Wax -> WaxSplitter -> HC + FCC

Splitter fractions are optimization variables for Pyomo.
"""

import biosteam as bst

# Import compounds (sets up thermo globally)
from . import _compounds
from . import TOD, DISTILLATION, HC, FCC, CPY, PLASMA, CP
from .units import Turbogenerator
from ._tea import TEA, labor_costs as BASE_LABOR_COST
from ._lca import get_total_gwp
from ._prices import SCENARIOS, get_prices, PRICE_DATA

# Default product prices (baseline scenario)
PRODUCT_PRICES = get_prices('baseline')

# Feedstock cost ($/kg waste plastic)
FEEDSTOCK_PRICE = 0.02  # $/kg

# Base labor cost is for a 2000 tpd plant (from _tea.py)
BASE_CAPACITY_TPD = 2000

# ============================================================================
# US average waste plastic composition (weight fractions)
# ============================================================================
#
# Based on US MSW plastic waste characterisation studies:
#
# [1] Milbrandt, A., Coney, K., Badgett, A. & Beckham, G.T. (2022).
#     "Quantification and evaluation of plastic waste in the United States."
#     Resources, Conservation and Recycling, 183, 106363.
#     https://doi.org/10.1016/j.resconrec.2022.106363
#     — 44 Mt US plastic waste in 2019; LDPE/LLDPE ≈ 34% of total.
#
# [2] National Academies / American Chemistry Council (2021).
#     "Reckoning with the U.S. Role in Global Ocean Plastic Waste," Ch. 2.
#     https://www.nationalacademies.org/read/26132/chapter/4
#     — North American resin production (2020, MMT): HDPE 10.4, LLDPE 10.4,
#       PP 7.8, PVC 6.9, LDPE 3.5, PET 2.8, PS 1.6, EPS 0.4.
#
# [3] Geyer, R., Jambeck, J.R. & Law, K.L. (2017).
#     "Production, use, and fate of all plastics ever made."
#     Science Advances, 3(7), e1700782.
#     — Global nonfiber production: PE 36%, PP 21%, PVC 12%, PET/PS <10%.
#
# Raw US MSW plastic waste composition (wt%, from [1]-[3]):
#   LDPE/LLDPE  34%  |  HDPE 17%  |  PP 18%  |  PET 12%  |  PS 8%  |
#   PVC 5%  |  Other 6%
#
# Adjustments for pyrolysis feed:
#   - PET excluded: different decomposition chemistry (oxygenated products);
#     typically pre-sorted for mechanical recycling.
#   - PVC excluded: produces corrosive HCl; pre-sorted before pyrolysis.
#   - Other excluded: heterogeneous mix (multilayer films, ABS, nylon, etc.).
#   - Remaining resins (77 wt%) normalised to 100%:
#
FEED_COMPOSITION = {
    'LDPE': 0.442,   # 34/77 — LDPE/LLDPE (bags, film, flexible packaging)
    'PP':   0.234,   # 18/77 — polypropylene (containers, automotive)
    'HDPE': 0.220,   # 17/77 — high-density polyethylene (bottles, jugs)
    'PS':   0.104,   # 8/77  — polystyrene (foam, disposables)
}

# Feedstock IDs recognised by all pathway reactors
POLYOLEFIN_IDS = ['HDPE', 'LDPE', 'PP']
ALL_FEED_IDS = ['HDPE', 'LDPE', 'PP', 'PS']


def _register_utility_agents():
    """Register custom utility agents for heating/cooling."""
    cooling = bst.HeatUtility.cooling_agents
    heating = bst.HeatUtility.heating_agents
    if _compounds.NH3_utility not in cooling:
        cooling.append(_compounds.NH3_utility)
    if _compounds.Liq_utility not in heating:
        heating.append(_compounds.Liq_utility)
    if _compounds.Gas_utility not in heating:
        heating.append(_compounds.Gas_utility)


def build_superstructure(capacity_tpd=250):
    """
    Build the integrated superstructure system.

    Parameters
    ----------
    capacity_tpd : float
        Total plant capacity in tonnes per day of HDPE.

    Returns
    -------
    system : bst.System
        The outer system (with rec_NCG recycle).
    split_fractions : dict
        Splitter objects whose split values are Pyomo optimization variables.
    product_streams : dict
        All product streams keyed by pathway-prefixed name.
    tea : TEA
        Techno-economic analysis object.
    feed : bst.Stream
        The feed stream (for solve_price).
    """
    _register_utility_agents()
    bst.main_flowsheet.set_flowsheet('superstructure')

    # === Common feed (US average MSW plastic composition) ===
    feed = bst.Stream('feed', T=298, units='kg/hr', price=FEEDSTOCK_PRICE,
                       **FEED_COMPOSITION)
    feed.set_total_flow(capacity_tpd, 'tonnes/day')

    # === 4-way feed split via three chained splitters ===
    # Splitter1: fraction to CP+TOD vs (CPY + PLASMA)
    splitter1 = bst.units.Splitter(
        'SS_Splitter1', ins=feed,
        outs=('SS_to_CP_TOD', 'SS_to_CPY_PLASMA'),
        split=0.34,  # initial: ~1/3 to CP+TOD
    )

    # Splitter3: fraction to TOD vs CP (within the pyrolysis branch)
    splitter3_pyro = bst.units.Splitter(
        'SS_Splitter3', ins=splitter1 - 0,
        outs=('SS_to_TOD', 'SS_to_CP'),
        split=0.50,  # initial: 50/50
    )

    # Splitter2: fraction to CPY vs PLASMA
    splitter2 = bst.units.Splitter(
        'SS_Splitter2', ins=splitter1 - 1,
        outs=('SS_to_CPY', 'SS_to_PLASMA'),
        split=0.50,  # initial: 50/50
    )

    # === TOD + CP pathways -> merge -> DISTILLATION -> Wax split -> HC + FCC ===
    sys_tod, tod_product = TOD.create_system(splitter3_pyro - 0)
    sys_cp, cp_product = CP.create_system(splitter3_pyro - 1, feedstock_IDs=ALL_FEED_IDS)

    # Merge TOD and CP outputs before DISTILLATION
    mx_pyro = bst.Mixer('SS_mx_pyro', ins=(tod_product, cp_product), outs='SS_pyro_combined')

    sys_dist, dist_products, _rec_NCG = DISTILLATION.create_system(
        mx_pyro - 0, prefix='DIST',
    )

    # Split wax between HC and FCC
    wax_splitter = bst.units.Splitter(
        'SS_WaxSplitter', ins=dist_products['Wax'],
        outs=('SS_wax_to_HC', 'SS_wax_to_FCC'),
        split=0.50,  # initial: 50/50
    )

    # HC pathway
    hc_hydrogen = bst.Stream('HC_hydrogen', H2=1, units='kg/hr', T=298)
    hc_hydrogen.set_total_flow(capacity_tpd * 0.02, 'tonnes/day')
    sys_hc, hc_products = HC.create_system(wax_splitter - 0, hc_hydrogen)

    # FCC pathway
    sys_fcc, fcc_products = FCC.create_system(wax_splitter - 1)

    # === CPY pathway ===
    sys_cpy, cpy_products = CPY.create_system(
        splitter2 - 0, feedstock_IDs=ALL_FEED_IDS,
    )

    # === PLASMA pathway ===
    sys_plasma, plasma_products = PLASMA.create_system(
        splitter2 - 1, feedstock_IDs=ALL_FEED_IDS,
    )

    # === Combine like product streams ===
    # Naphtha: DIST + HC + FCC
    mx_naphtha = bst.Mixer(
        'SS_mx_Naphtha',
        ins=(dist_products['Naphtha'], hc_products['Naphtha'], fcc_products['Naphtha']),
        outs='SS_Naphtha',
    )
    # Diesel: DIST + HC + FCC
    mx_diesel = bst.Mixer(
        'SS_mx_Diesel',
        ins=(dist_products['Diesel'], hc_products['Diesel'], fcc_products['Diesel']),
        outs='SS_Diesel',
    )
    # Wax: HC + FCC
    mx_wax = bst.Mixer(
        'SS_mx_Wax',
        ins=(hc_products['Wax'], fcc_products['Wax']),
        outs='SS_Wax',
    )
    # BTX: CPY Benzene + Toluene + Xylene
    mx_btx = bst.Mixer(
        'SS_mx_BTX',
        ins=(cpy_products['Benzene'], cpy_products['Toluene'], cpy_products['Xylene']),
        outs='SS_BTX',
    )
    # Hydrogen: HC + FCC excess H2
    mx_h2 = bst.Mixer(
        'SS_mx_H2',
        ins=(hc_products['ExcessH2'], fcc_products['ExcessH2']),
        outs='SS_Hydrogen',
    )

    # === Turbogenerator subsystem ===
    mx_fluegas = bst.Mixer(
        'TG_mx_FlueGas',
        ins=(cpy_products['FlueGas'], plasma_products['FlueGas'], fcc_products['FlueGas']),
        outs='TG_combined_flue',
    )
    turbogen = Turbogenerator(
        'TG_Turbogenerator',
        ins=mx_fluegas - 0,
        outs='TG_exhaust',
    )
    sys_turbogen = bst.System(
        'sys_turbogenerator',
        path=[mx_fluegas, turbogen],
    )

    # === Assemble outer system ===
    system = bst.System(
        'sys_superstructure',
        path=[
            splitter1, splitter3_pyro, splitter2,
            sys_tod, sys_cp, mx_pyro, sys_dist,
            wax_splitter, sys_hc, sys_fcc,
            mx_naphtha, mx_diesel, mx_wax, mx_h2,
            sys_cpy,
            sys_plasma,
            mx_btx,
            sys_turbogen,
        ],
    )

    # === Collect outputs ===
    split_fractions = {
        'CP_TOD_vs_rest': splitter1,
        'TOD_vs_CP': splitter3_pyro,
        'CPY_vs_PLASMA': splitter2,
        'HC_vs_FCC': wax_splitter,
    }

    product_streams = {
        # TOD -> DISTILLATION light products
        'Ethylene': dist_products['Ethylene'],
        'Propylene': dist_products['Propylene'],
        'Butene': dist_products['Butene'],
        # Combined fuel-range products (DIST + HC + FCC)
        'Naphtha': mx_naphtha.outs[0],
        'Diesel': mx_diesel.outs[0],
        'Wax': mx_wax.outs[0],
        # Combined hydrogen (HC + FCC)
        'Hydrogen': mx_h2.outs[0],
        # CPY products
        'BTX': mx_btx.outs[0],
        'Aromatics': cpy_products['Aromatics'],
        # PLASMA products
        'Paraffins': plasma_products['Paraffins'],
        'Carbonyls': plasma_products['Carbonyls'],
        'Olefins': plasma_products['Olefins'],
        'Alcohols': plasma_products['Alcohols'],
        'Acids': plasma_products['Acids'],
        'C30': plasma_products['C30'],
    }

    # === Set product prices for TEA ===
    for name, stream in product_streams.items():
        if name in PRODUCT_PRICES:
            stream.price = PRODUCT_PRICES[name]

    # === TEA (labor scaled linearly from 2000 tpd baseline) ===
    scaled_labor = BASE_LABOR_COST * (capacity_tpd / BASE_CAPACITY_TPD)
    tea = TEA(
        system=system,
        IRR=0.1,
        duration=(2020, 2040),
        depreciation='MACRS7',
        income_tax=0.21,
        operating_days=333,
        lang_factor=5.05,
        construction_schedule=(0.4, 0.6),
        WC_over_FCI=0.05,
        labor_cost=scaled_labor,
        fringe_benefits=0.4,
        property_tax=0.001,
        property_insurance=0.005,
        supplies=0.20,
        maintenance=0.003,
        administration=0.005,
        finance_fraction=0.4,
        finance_years=10,
        finance_interest=0.07,
    )

    return system, split_fractions, product_streams, tea, feed


def evaluate(split_TOD=0.34, split_CP=0.50, split_CPY=0.50, split_HC=0.50,
             capacity_tpd=250, scenario='baseline', _cache={}):
    """
    Evaluate the superstructure at given split fractions.

    Builds the system on the first call, then re-uses it on subsequent
    calls (only updating splits and re-simulating).  Designed to be
    called repeatedly by Pyomo or any optimizer.

    Parameters
    ----------
    split_TOD : float
        Fraction of total feed sent to CP+TOD (rest goes to CPY + PLASMA).
    split_CP : float
        Fraction of CP+TOD stream sent to TOD (rest goes to CP).
    split_CPY : float
        Fraction of non-TOD feed sent to CPY (rest goes to PLASMA).
    split_HC : float
        Fraction of wax sent to HC (rest goes to FCC).
    capacity_tpd : float
        Plant capacity in tonnes per day (only used on first build).
    scenario : str
        Price scenario: 'baseline', 'high_fuel', 'high_chem', or
        'high_organics'.  See ``system._prices`` for details and sources.

    Returns
    -------
    results : dict
        'product_flows'          : dict {name: kg/hr}
        'product_streams'        : dict {name: bst.Stream}
        'split_fractions'        : dict {name: bst.Splitter}
        'system'                 : bst.System
        'tea'                    : TEA object
        'feed'                   : bst.Stream, the feed stream
        'MSP'                    : float, minimum selling price of feed ($/kg)
        'GWP'                    : float, GWP per kg feed (kg CO2-eq/kg)
        'carbon_abatement_cost'  : float, $/kg CO2-eq reduced
        'scenario'               : str, the price scenario used
    """
    # Build once, cache the system objects
    if 'system' not in _cache:
        system, splits, products, tea, feed = build_superstructure(capacity_tpd)
        _cache['system'] = system
        _cache['splits'] = splits
        _cache['products'] = products
        _cache['tea'] = tea
        _cache['feed'] = feed

    system = _cache['system']
    splits = _cache['splits']
    products = _cache['products']
    tea = _cache['tea']
    feed = _cache['feed']

    # Update split fractions
    splits['CP_TOD_vs_rest'].split[:] = split_TOD
    splits['TOD_vs_CP'].split[:] = split_CP
    splits['CPY_vs_PLASMA'].split[:] = split_CPY
    splits['HC_vs_FCC'].split[:] = split_HC

    # Apply scenario prices
    prices = get_prices(scenario)
    for name, stream in products.items():
        if name in prices:
            stream.price = prices[name]

    # Simulate (skip reconfiguration on re-runs since topology is unchanged)
    try:
        system.simulate(update_configuration=False)
    except Exception:
        system.empty_recycles()
        system.simulate(update_configuration=False)

    # Collect results
    product_flows = {
        name: stream.F_mass for name, stream in products.items()
    }

    feed_kg_hr = feed.F_mass
    feed_kg_yr = feed_kg_hr * tea.operating_hours

    # MSP: breakeven feedstock price ($/kg)
    original_price = feed.price
    msp = tea.solve_price(feed)
    feed.price = original_price  # restore to not pollute cached TEA state

    # GWP per kg feed
    gwp_total = get_total_gwp(system)       # kg CO2-eq/hr
    gwp_per_kg = gwp_total / feed_kg_hr     # kg CO2-eq/kg feed

    # Carbon abatement cost ($/kg CO2-eq reduced)
    production_cost_per_kg = tea.AOC / feed_kg_yr
    revenue_per_kg = tea.sales / feed_kg_yr
    net_cost_per_kg = production_cost_per_kg - revenue_per_kg
    co2_reduced_per_kg = -gwp_per_kg  # positive when GWP is negative
    if abs(co2_reduced_per_kg) > 1e-10:
        carbon_abatement_cost = net_cost_per_kg / co2_reduced_per_kg
    else:
        carbon_abatement_cost = float('inf')

    return {
        'product_flows': product_flows,
        'product_streams': products,
        'split_fractions': splits,
        'system': system,
        'tea': tea,
        'feed': feed,
        'MSP': msp,                                     # $/kg feed
        'GWP': gwp_per_kg,                              # kg CO2-eq/kg feed
        'carbon_abatement_cost': carbon_abatement_cost,  # $/kg CO2-eq
        'scenario': scenario,
    }


# Individual pathway builders for standalone testing
def build_TOD_DIST(capacity_tpd=250):
    """Build the TOD -> DISTILLATION pathway."""
    _register_utility_agents()
    bst.main_flowsheet.set_flowsheet('TOD_DIST')
    feed = bst.Stream('feed', T=298, units='kg/hr', **FEED_COMPOSITION)
    feed.set_total_flow(capacity_tpd, 'tonnes/day')
    sys_tod, tod_product = TOD.create_system(feed)
    sys_dist, dist_products, _rec_NCG = DISTILLATION.create_system(
        tod_product, prefix='DIST',
    )
    main_sys = bst.System(
        'sys_TOD_DIST', path=[sys_tod, sys_dist],
    )
    return main_sys, dist_products


def build_PLASMA(capacity_tpd=250):
    """Build the PLASMA pathway (self-contained separation)."""
    _register_utility_agents()
    bst.main_flowsheet.set_flowsheet('PLASMA_pathway')
    feed = bst.Stream('feed', T=298, units='kg/hr', **FEED_COMPOSITION)
    feed.set_total_flow(capacity_tpd, 'tonnes/day')
    sys_plasma, plasma_products = PLASMA.create_system(feed, feedstock_IDs=ALL_FEED_IDS)
    return sys_plasma, plasma_products


def build_CPY(capacity_tpd=250):
    """Build the CPY (catalytic pyrolysis) pathway (self-contained)."""
    _register_utility_agents()
    bst.main_flowsheet.set_flowsheet('CPY_pathway')
    feed = bst.Stream('feed', T=298, units='kg/hr', **FEED_COMPOSITION)
    feed.set_total_flow(capacity_tpd, 'tonnes/day')
    sys_cpy, cpy_products = CPY.create_system(feed, feedstock_IDs=ALL_FEED_IDS)
    return sys_cpy, cpy_products


PATHWAY_BUILDERS = {
    'TOD_DIST': build_TOD_DIST,
    'PLASMA': build_PLASMA,
    'CPY': build_CPY,
    'SUPERSTRUCTURE': build_superstructure,
}


def build_pathway(name, capacity_tpd=250):
    """
    Build a single pathway by name.

    Parameters
    ----------
    name : str
        One of 'TOD_DIST', 'PLASMA', 'CPY', 'SUPERSTRUCTURE'.
    capacity_tpd : float
        Plant capacity in tonnes per day.
    """
    builder = PATHWAY_BUILDERS[name]
    return builder(capacity_tpd)
