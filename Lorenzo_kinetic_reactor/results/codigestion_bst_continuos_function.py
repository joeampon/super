#%%
import kinetic_reactors as kr
import biosteam as bst
import thermosteam as tmo
import pandas as pd
import matplotlib.pyplot as plt
from biosteam.units.decorators import cost
from aria_class import IsentropicCompressor
from _tea import TEA
from _tea import *
from warnings import filterwarnings; filterwarnings('ignore')
import sesalca_v2 as lm
from dryer import Dryer
from RYield import RYield
import numpy as np
import sys
sys.path.append('/Users/davidlorenzo/Library/CloudStorage/OneDrive-IowaStateUniversity/KINCOD/cassadi_aplication/')


# ========================================================================
# LCA CONFIGURATION - Centralized mapping definitions
# ========================================================================
# These mappings are defined once and reused in both setup and reuse modes
# Format: {stream_name: (process_id_or_description, amount)}
#
# process_id_or_description:
#   - UUID: 'e8eae2c1-7dd3-3677-a387-240bcf6b634f' (exact, fast)
#   - Description: 'slaughterhouse waste treatment' (AI search)
#
# amount (impact sign):
#   +1  = Burden (consumption, waste generation)
#   -1  = Credit (avoided impact, displacement)
# ========================================================================

INPUT_LCA_MAPPING = {
    'slaughterhouse': ('e8eae2c1-7dd3-3677-a387-240bcf6b634f', -1),  # Avoided slaughterhouse waste
    'DW_feed': ('309afced-4607-47ea-9103-241d1c3db871', -1),         # Avoided municipal waste
    'I_feed': ('c76f512c-e028-3a7d-a3dc-6ec9fb4b7396', -1),          # Avoided inoculum waste
    'MEA': ('653be2a8-0e37-34a8-a85b-32cb53ace19c', 1),              # MEA production
}

OUTPUT_LCA_MAPPING = {
    'mea_loss': ('6ea9bdbe-5d07-3b75-9dd3-4a413c14d7e3', 1),        # MEA waste treatment
    'wastewater2': ('1f941187-cbc5-3d57-8286-5e066bc5720f', 1),     # Wastewater treatment
    'CH4_leak': ('methane', 1),                                      # CH4 leaks
    'SoilAmendment': ('biochar soil amendment', -1),                 # Biochar credit
}

UTILITY_LCA_MAPPING = {
    'electricity': 'dbe13af2-56fb-391b-a0b8-be36fc16e2ac',
    'steam': 'ef27af67-cecc-3589-9872-1cbfbf7b6c29',
}


def _assign_lca_impacts_to_streams(lca_manager, stream_mapping, streams_dict, verbose=False, stream_type=""):
    """
    Helper function to assign LCA impacts to multiple streams.
    Reduces code duplication between setup and reuse modes.
    """
    for stream_name, (activity_id, amount) in stream_mapping.items():
        if stream_name in streams_dict:
            try:
                lca_manager.assign_impacts_to_stream(streams_dict[stream_name], activity_id, amount)
                if verbose:
                    impact_type = "burden" if amount > 0 else "credit"
                    print(f"  ✓ {stream_name} → {activity_id} (amount={amount:+.0f}, {impact_type})")
            except Exception as e:
                if verbose:
                    print(f"  ✗ Error assigning {stream_name}: {e}")
        else:
            if verbose:
                print(f"  ⚠ Warning: Stream '{stream_name}' not found in system {stream_type}")


def create_and_simulate_system(
    ISR=2.0,
    S0=300000,
    F_TOTAL=100000,
    feedStock_ratio=0.5,
    X10_ratio=0.6,
    reactor_tau=2*24,
    reactor_T=330,
    IRR=0.10,
    lang_factor=2.7,#2.7,
    WC_over_FCI=0.15, #0.05,
    operating_days=330,
    I_feed_price = 0.01,
    SW_feed_price = 0.03,
    DW_feed_price = 0.01,
    mea_fresh_price = 1.2,
    biochar_price = 0.2,
    setup_lca=False,
    lca_method_id="d2c781ce-21b4-3218-8fca-78133f2c8d4d",
    lca_manager_reuse=None
):
    """
    Creates and simulates the complete codigestion system.

    Parameters
    ----------
    ISR : float
        Inoculum to substrate ratio
    S0 : float
        Initial volatile solids concentration (mg/L)
    F_TOTAL : float
        Total feed flow rate (kg/hr)
    feedStock_ratio : float
        Fraction of SW in the feedstock (0-1)
    X10_ratio : float
        Fraction of X1 biomass in inoculum (0-1)
    reactor_tau : float
        Reactor residence time (hours)
    reactor_T : float
        Reactor temperature (K)
    IRR : float
        Internal rate of return (fraction)
    lang_factor : float
        Lang factor for capital cost estimation
    operating_days : int
        Operating days per year
    setup_lca : bool, optional
        If True, automatically setup LCA impacts for all streams. Default is False.
    lca_method_id : str, optional
        LCA method ID to use. Default is EF 3.1 method.
    lca_manager_reuse : LCAManager, optional
        Pre-configured LCA manager to reuse (avoids reassigning impacts each time).
        If provided, setup_lca is ignored and this manager is used directly.
        This is for Monte Carlo simulations to avoid repeating LCA assignment.

    Returns
    -------
    system : bst.System
        Simulated system
    tea : TEA
        TEA object
    streams : dict
        Dictionary with key streams
    lca_manager : LCAManager or None
        LCA manager if setup_lca=True, otherwise None
    """

    # Clear previous flowsheet
    bst.main_flowsheet.clear()

    propanoic_acid = tmo.Chemical('Propanoic Acid', cache=True)
    LP = tmo.Chemical('L-proline', cache=True)
    Water = tmo.Chemical('Water', cache=True)
    C = tmo.Chemical('C', cache=True)
    CO2 = tmo.Chemical('CO2', cache=True)
    CH4 = tmo.Chemical('CH4', cache=True)

    SW = Water.copy('SW')
    DW = Water.copy('DW')
    VFA = propanoic_acid.copy('VFA')
    X1 = LP.copy('X1')
    X2 = LP.copy('X2')
    X1d = LP.copy('X1d')
    X2d = LP.copy('X2d')
    Biochar = C.copy('Biochar')
    Monoethanolamine = tmo.Chemical('Monoethanolamine', cache=True)

    chemicals = tmo.Chemicals([CH4, CO2, X1, X2, SW, VFA, DW, X1d, X2d, Water, Monoethanolamine, Biochar], cache=True)
    tmo.settings.set_thermo(chemicals)
    
    
    p = {
    "kd1": 0.24273086311948674,
    "kd2": 0.003697283546804762,
    "ks_1": 1000.007100737135,
    "ks_2": 5000.240277007153,
    "ksi_2": 250025.05254529344,
    "ks_3": 34954.592262124024,
    "mu_max_1": 0.05613830379662277,
    "mu_max_2": 0.030325622210543267,
    "b1": 4.999991342621719,
    "b2": 24.907990423694837,
    "b3": 2.0184920981400865,
    "c1": 6.109109109478715,
    "c2": 2.044471191448219,
    "c3": 9.999975062821896,
    "mu_max_3": 0.3480740353332263
}


    #p = pd.read_pickle('parametros_optimos_fin.pkl')
    kd1 = p['kd1']
    kd2 = p['kd2']
    ks_1 = p['ks_1']
    ks_2 = p['ks_2']
    ksi_2 = p['ksi_2']
    ks_3 = p['ks_3']
    mu_max_1 = p['mu_max_1']
    mu_max_2 = p['mu_max_2']
    mu_max_3 = p['mu_max_3']
    b1 = p['b1']
    b2 = p['b2']
    b3 = p['b3']
    c1 = p['c1']
    c2 = p['c2']
    c3 = p['c3']
    
    print('Kinetic parameters loaded successfully.')
    print(p)

    def a_calculate_a(b, c):
        return 1 + b + c

    a1 = a_calculate_a(b1, c1)
    a2 = a_calculate_a(b2, c2)
    a3 = a_calculate_a(b3, c3)


    reacciones = {
        'R1': tmo.Reaction(f'{a1/SW.MW}SW,l -> {1/X1.MW}X1,l + {b1/VFA.MW}VFA,l + {c1/CO2.MW}CO2,l'),
        'R2': tmo.Reaction(f'{a2/VFA.MW}VFA,l -> {1/X2.MW}X2,l + {b2/CH4.MW}CH4,l + {c2/CO2.MW}CO2,l'),
        'R3': tmo.Reaction(f'{a3/DW.MW}DW,l -> {1/X1.MW}X1,l + {b3/VFA.MW}VFA,l + {c3/CO2.MW}CO2,l'),
        'R4': tmo.Reaction(f'X1,l -> X1d,l'),
        'R5': tmo.Reaction(f'X2,l -> X2d,l')
    }

    for r in reacciones.values():
        r.basis = 'wt'


    def monod(S1, mu_max1, Ks1):
        return mu_max1 * (S1 / (Ks1 + S1))

    def monod_2(S, mu_max, Ks2, Ksi2):
        return mu_max * S/(S+Ks2+ S**2/Ksi2)

    modelo_cinetico = {
        'R1': kr.KineticExpression(lambda SW, X1, **kwargs: monod(SW, mu_max_1, ks_1) * X1),
        'R2': kr.KineticExpression(lambda VFA, X2, **kwargs: monod_2(VFA, mu_max_2, ks_2, ksi_2) * X2),
        'R3': kr.KineticExpression(lambda DW, X1, **kwargs: monod(DW, mu_max_3, ks_3) * X1),
        'R4': kr.KineticExpression(lambda X1, **kwargs: kd1 * X1),
        'R5': kr.KineticExpression(lambda X2, **kwargs: kd2 * X2)
    }

    RM = kr.ReactionModel(reacciones, modelo_cinetico)
    RM.set_units(time_units='h', conc_units='mg/L')


    def feed_configuration(ISR, S0, X10_ratio, FeedStock_ratio, F_TOTAL, SW_feed, DW_feed, I_feed):
        S = S0 / (1+ ISR)
        I_SV = S0 - S
        X20_ratio = 1-X10_ratio

        SW_SW_C = S*FeedStock_ratio /1e6
        WATER_SW_C = 1 - SW_SW_C

        DW_DW_C = S*(1-FeedStock_ratio)/1e6
        WATER_DW_C = 1 - DW_DW_C

        VFA_BM_C = 1500 / 1e6
        BM_BM_C = I_SV /1e6 - VFA_BM_C
        WATER_BM_C = 1 - VFA_BM_C - BM_BM_C
        X1_BM_C = X10_ratio * BM_BM_C
        X2_BM_C = X20_ratio * BM_BM_C

        SW_RAtio = S * FeedStock_ratio / S0
        DW_RAtio = S * (1-FeedStock_ratio) / S0
        BM_RATIO = I_SV / S0

        SW_flow = F_TOTAL * SW_RAtio
        DW_flow = F_TOTAL * DW_RAtio
        I_flow = F_TOTAL * BM_RATIO

        SW_feed.imass['SW'] = SW_SW_C* SW_flow
        SW_feed.imass['Water'] = WATER_SW_C * SW_flow

        DW_feed.imass['DW'] = DW_DW_C * DW_flow
        DW_feed.imass['Water'] = WATER_DW_C * DW_flow

        I_feed.imass['X1'] = X1_BM_C * I_flow
        I_feed.imass['X2'] = X2_BM_C * I_flow
        I_feed.imass['VFA'] = VFA_BM_C * I_flow
        I_feed.imass['Water'] = WATER_BM_C * I_flow

        SW_feed.F_mass = SW_flow
        DW_feed.F_mass = DW_flow
        I_feed.F_mass = I_flow

    SW_feed = bst.Stream('slaughterhouse', units='kg/hr')
    DW_feed = bst.Stream('DW_feed', units='kg/hr')
    I_feed = bst.Stream('I_feed', units='kg/hr')

    feed_configuration(ISR, S0, X10_ratio, feedStock_ratio, F_TOTAL, SW_feed, DW_feed, I_feed)


    Mixer_feed = bst.Mixer('Mixer_feed', ins=[SW_feed, DW_feed, I_feed], outs='Feed')
    Mixer_feed.simulate()

    R1 = kr.KineticCSTR('R1',
                         ins=Mixer_feed-0,
                         outs='out',
                         ReactionModel=RM,
                         adiabatic=False,
                         batch=False,
                         T=reactor_T,
                         tau=reactor_tau,
                         Plot_profiles=False)

    R1.modo_termico = 'isotermo'

    Biogas_crudo = bst.Stream('Biogas_crudo', phase = 'g', units='kg/hr')
    Digestate = bst.Stream('digestate', phase = 'l', units='kg/hr')
    SP_biogas = bst.Splitter('SP_biogas', ins=R1-0, outs=[Biogas_crudo, Digestate],
                              split={'CO2': 0.999, 'CH4': 0.9999})

    Biogas_crudo.vle(T=Biogas_crudo.T, P=Biogas_crudo.P)

    rng_compressor = IsentropicCompressor(
            "CPRNG",
            ins=(Biogas_crudo),
            outs=("compressed_biogas"),
            P=101325 * 2,
            eta=0.72,
            driver='Electric motor'
        )

    rng_cooler_out = bst.Stream("rng_cooler_out")
    rng_cooler = bst.units.HXutility(
            ID="HXGasCooling",
            ins=(rng_compressor - 0,),
            outs=(rng_cooler_out,),
            T=273.15 + 40,
            rigorous=True,
        )

    digestate_drier = Dryer(
            "DRDryer",
            ins=(Digestate),
            outs=("dry", "wastewater2"),
            moisture_content=0.1,
        )

    dry_digestate = digestate_drier-0

    pyrolyzer = RYield(
        "RXPyrolysis",
        ins=(dry_digestate),
        outs=("soil_amend_out")
    )

    @pyrolyzer.add_specification(run=True)
    def pyrolysis_yields():
        if dry_digestate.get_total_flow("kg/hr") > 0 and pyrolyzer:
            pyrolyzer.yields = {
                "Biochar": 0.8
                * (
                    1
                    - dry_digestate.get_flow("kg/hr", "Water")
                    / dry_digestate.get_total_flow("kg/hr")
                ),
                "Water": dry_digestate.get_flow("kg/hr", "Water")
                / dry_digestate.get_total_flow("kg/hr"),
                "CO2": 0.2
                * (
                    1
                    - dry_digestate.get_flow("kg/hr", "Water")
                    / dry_digestate.get_total_flow("kg/hr")
                ),
            }

    biochar_splitter = bst.units.Splitter(
        "SPBiochar",
        ins=pyrolyzer - 0,
        split={"Biochar": 0.99},
        outs=("SoilAmendment", "FlueGas"),
    )
    
    
    cooler_biochar = bst.units.HXutility("HXBiocharCooling",
        ins=biochar_splitter - 0,
        T=298.15,
        rigorous=False)
    
    biochar = cooler_biochar - 0

    r_m = bst.System('r_m', path=[Mixer_feed, R1, SP_biogas, rng_compressor, rng_cooler, digestate_drier, pyrolyzer, biochar_splitter, cooler_biochar])
    r_m.simulate()


    mea_fresh = bst.Stream("MEA", Monoethanolamine=20, units="kmol/hr")
    mea_LEAN = bst.Stream("MEARecycle", Monoethanolamine=5, units="kmol/hr")
    meaRNG = bst.MultiStream("MEARNG")
    biogas = rng_cooler_out

    co2_absorber_mixer = bst.MixTank("CO2_Absorber_Mixer", ins=[biogas, mea_fresh, mea_LEAN], outs=meaRNG)

    @co2_absorber_mixer.add_specification(run=True, args=[1.5])
    def adjust_mea_flow(co2_mea_ratio):
        mea_needed = co2_mea_ratio * biogas.get_flow("kmol/hr", "CO2")
        mea_flow = mea_needed - mea_LEAN.get_flow("kmol/hr", "Monoethanolamine")
        if mea_flow < 0:
            mea_flow = 0
        mea_fresh.set_flow(mea_flow, "kmol/hr", "Monoethanolamine")

    MEA_rich = bst.Stream("MEA_rich")
    ch4_rich = bst.Stream("ch4_rich")

    @cost('Flow rate', units='m3/hr',  cost=78e6, CE=550.8,
          n=0.6, S=2360705)
    class absorber_JC(bst.Splitter): pass

    co2_absorber = absorber_JC("Absorber_A1",
        ins=[meaRNG],
        order =("CO2", "CH4"),
        split=(0.25, 0.95),
        outs=[ch4_rich, MEA_rich],
    )

    co2_flash0 = bst.units.SplitFlash(
            "CLCO2BottomFlash",
            ins=co2_absorber- 1,
            outs=("co2_top", "co2_bottom"),
            T=273.15 + 30,
            P=101325*2,
            vessel_type="Vertical",
            split={"CH4": 0.999, "CO2": 0.001, "Water": 0.001, "Monoethanolamine": 0.001},
        )

    co2_pump = bst.units.Pump(
        "Pump_C4",
        ins=co2_flash0 - 1,
        outs=("S28"),
        P=101325 * 2.7,
    )

    co2_stripper_out = bst.Stream("CO2StripperOut")
    co2_hx = bst.units.HXprocess(
            "HXCO2", ins=(co2_pump - 0, co2_stripper_out), outs=("co2hx0", "co2hx1"))

    co2_stripper = bst.units.ShortcutColumn(
            "CLCO2Stripper",
            ins=co2_hx - 0,
            outs=(co2_stripper_out, "stripper_bottom"),
            P=101325 * 2,
            LHK=("CO2", "Monoethanolamine"),
            product_specification_format="Recovery",
            Lr=0.75,
            Hr=0.95,
            k=1.2,
            is_divided=False,)

    co2_stripper.check_LHK = False

    def stripper_design():
        co2_stripper.design_results = {'Theoretical feed stage': 3.0,
            'Theoretical stages': 3.0,
            'Minimum reflux': 0.3,
            'Reflux': 0.36,
            'Actual stages': 169.0,
            'Height': 260.5,
            'Diameter': 10.5,
            'Wall thickness': 1.375,
            'Weight': 505927}
        return

    co2_stripper._design = stripper_design

    def co2_stripper_spec():
        if co2_stripper.ins[0].F_mass > 0:
            for _ in range(0, 2):
                try:
                    co2_stripper._run()
                except Exception:
                    pass

    co2_stripper.add_specification(co2_stripper_spec)
    mea_loss = bst.Stream("mea_loss")

    mea_recovery = bst.units.Splitter(
            "CLMEARecovery",
            ins=(co2_stripper - 1),
            outs=(mea_LEAN, "mea_loss"),
            split={"Monoethanolamine": 0.99, "Water": 0.01},
        )

    def mea_recovery_spec():
        if mea_recovery.ins[0].F_mass > 0:
            mea_recovery._run()

    mea_recovery.add_specification(mea_recovery_spec)

    def mea_recovery_cost():
        flow = mea_recovery.ins[0].F_mass
        mea_recovery.purchase_costs['Splitter'] = 75_000 * (flow / 10_000) ** 0.6

    mea_recovery._cost = mea_recovery_cost

    co2_recovery = bst.System('co2_recovery', path=[co2_absorber_mixer, co2_absorber, co2_flash0, co2_pump, co2_hx, co2_stripper, mea_recovery])
    co2_recovery.simulate()

    co2_flash_mix = bst.units.Mixer(
            "MXAbsorber", ins=(co2_absorber - 0, co2_flash0 - 0), outs=("mx_out")
        )

    
    rng_out = bst.Stream("RNG_out")
    
    rng_flash = bst.units.SplitFlash(
            "CLRNGFlash",
            T=40 + 273.15,
            P=101325*2,
            ins=co2_flash_mix - 0,
            outs=(rng_out, "co2_waste"),
            vessel_type="Vertical",
            split={"CH4": 0.999, "CO2": 0.001, "Water": 0.001, "Monoethanolamine": 0.001},
        )
    rng_flash._cost = lambda: None
    rng_flash._design = lambda: None
    
    RNG = bst.Stream("RNG")
    CH4_leak = bst.Stream("CH4_leak")
    
    ch4_splitter_leaks = bst.units.Splitter(
        "SPCH4Leaks",
        ins=rng_out,
        split={"CH4": 0.97},
        outs=(RNG, CH4_leak),
    )

    rng_clean = bst.System('rng_clean', path=[co2_flash_mix, rng_flash, ch4_splitter_leaks])
    rng_clean.simulate()

    class Pipeline(bst.Unit):
        def _run(self):
            pass
        def _design(self):
            pass
        def _cost(self):
            self.purchase_costs['Pipeline'] = (24198 + 55313 + 26396 + 7199) * 5 * 2

    pipeline = Pipeline('Pipeline')


    system = bst.System('system', path=[R1, r_m, co2_recovery, rng_clean, pipeline])
    system.simulate()


    I_feed.price = I_feed_price
    SW_feed.price = SW_feed_price
    DW_feed.price = DW_feed_price
    mea_fresh.price = mea_fresh_price
    biochar.price = biochar_price

    tea = TEA(
            system=system,
            IRR=IRR,
            duration=(2025, 2045),
            depreciation="MACRS7",
            income_tax=0.21,
            operating_days=operating_days,
            lang_factor=lang_factor,
            construction_schedule=(0.4, 0.6),
            WC_over_FCI=WC_over_FCI,
            labor_cost= 45 * 2 * 8760 * (330 / 365)/2,
            fringe_benefits=0.4,
            property_tax=0.001,
            property_insurance=0.005,
            supplies=0.20,
            maintenance=0.003,
            administration=0.005,
            finance_interest=0.07,
            finance_years=20,
            finance_fraction=0.4
        )

    # Get key streams
    rng = RNG

    streams = {
        'rng': rng,
        'RNG': RNG,
        'RNGleaks': CH4_leak,
        'biochar': biochar,
        'SW_feed': SW_feed,
        'DW_feed': DW_feed,
        'I_feed': I_feed,
        'mea_fresh': mea_fresh,
        'biogas': biogas,
        'R1': R1
    }

    # Setup LCA - either reuse existing manager or create new one
    lca_manager = None

    if lca_manager_reuse is not None:
        # ========================================================================
        # REUSE MODE - Reassign impacts to new stream objects (critical for Monte Carlo!)
        # ========================================================================
        lca_manager = lca_manager_reuse

        inputs_dict = {stream.ID: stream for stream in system.feeds}
        outputs_dict = {stream.ID: stream for stream in system.products}

        # Assign impacts (silently - no prints in Monte Carlo)
        _assign_lca_impacts_to_streams(lca_manager, INPUT_LCA_MAPPING, inputs_dict, verbose=False)
        _assign_lca_impacts_to_streams(lca_manager, OUTPUT_LCA_MAPPING, outputs_dict, verbose=False)

        # Assign utilities (silently - no errors in Monte Carlo)
        try:
            lca_manager.assign_impacts_to_electricity(UTILITY_LCA_MAPPING['electricity'], operating_hours=8760)  # type: ignore
            lca_manager.assign_impacts_to_steam(UTILITY_LCA_MAPPING['steam'])  # type: ignore
        except Exception:
            pass

    elif setup_lca:
        # ========================================================================
        # SETUP MODE - Create new LCA manager and assign impacts
        # ========================================================================
        lca_manager = lm.LCAManager(default_method_id=lca_method_id)

        inputs_dict = {stream.ID: stream for stream in system.feeds}
        outputs_dict = {stream.ID: stream for stream in system.products}

        # Print available streams for reference
        print("\n=== Available Input Streams ===")
        for name, stream in inputs_dict.items():
            print(f"  {name}: {stream.F_mass:.2f} kg/hr")

        print("\n=== Available Output Streams ===")
        for name, stream in outputs_dict.items():
            print(f"  {name}: {stream.F_mass:.2f} kg/hr")

        # Assign impacts (with verbose output)
        _assign_lca_impacts_to_streams(lca_manager, INPUT_LCA_MAPPING, inputs_dict, verbose=True, stream_type="inputs")
        _assign_lca_impacts_to_streams(lca_manager, OUTPUT_LCA_MAPPING, outputs_dict, verbose=True, stream_type="outputs")

        # Assign utilities
        print("\n=== Assigning LCA Impacts to Utilities ===")
        lca_manager.assign_impacts_to_electricity(UTILITY_LCA_MAPPING['electricity'], operating_hours=8760)  # type: ignore
        print(f"  ✓ Electricity → {UTILITY_LCA_MAPPING['electricity']}")

        lca_manager.assign_impacts_to_steam(UTILITY_LCA_MAPPING['steam'])  # type: ignore
        print(f"  ✓ Steam → {UTILITY_LCA_MAPPING['steam']}")
        print("\n✓ LCA impacts assigned successfully\n")

    return system, tea, streams, lca_manager


def plot_equipment_costs(system, cutoff=1.5e4, save_path='results/equipment_costs.png'):
    """
    Plots major equipment costs as a stacked bar chart.

    Parameters
    ----------
    system : bst.System
        BioSTEAM system
    cutoff : float
        Minimum cost to be included as major equipment
    save_path : str
        Path to save the figure
    """
    equipment_costs = {i.ID: i.purchase_cost for i in system.units}

    # Consolidar costos antes de crear DataFrame
    equipment_costs["Absorber_A1"] = equipment_costs['CLCO2BottomFlash'] + equipment_costs["Absorber_A1"]
    equipment_costs['CLCO2BottomFlash'] = 0
    equipment_costs['CLCO2Stripper'] = equipment_costs['CLMEARecovery'] + equipment_costs['CLCO2Stripper']
    equipment_costs['CLMEARecovery'] = 0

    # Mapeo de nombres técnicos a nombres descriptivos
    mapeo = {'R1':                   'AD reactor \n(C-101)',
            'DRDryer':               'Dryer \n(T-302)',
            'CO2_Absorber_Mixer':    'MEA mixer \n(T-202)',
            'CLCO2Stripper':         'CO2 Stripper\n (C-202)',
            'Pipeline':              'Pipeline',
            'Absorber_A1':           'Absorber A1 \n(C-205)',
            'CLCO2BottomFlash':      'CO2 Bottom Flash',
            'CLMEARecovery':         'MEA Recovery',
            'HXGasCooling':          'Cooling \n(X-101)',
            'CPRNG':                 'Compressor \n(S-101)',
            'Pump_C4':               'MEA pump \n(P-202)',
            'HXCO2':                 'MEA heat exchanger \n(X-201)',
            'RXPyrolysis':           'Pyrolyzer \n(C-301)',
            'SPBiochar':             'Biochar separator',
            'Mixer_feed':            'Feed mixer',
            'SP_biogas':             'Biogas separator',
            'MXAbsorber':            'Absorber mixer',
            'CLRNGFlash':            'RNG Flash'}

    # Crear DataFrame y aplicar mapeo de nombres
    df = pd.DataFrame.from_dict(equipment_costs, orient='index', columns=['Cost (USD)'])
    df.index = df.index.map(lambda x: mapeo.get(x, x))  # Aplicar mapeo, mantener original si no existe
    df = df.sort_values(by='Cost (USD)', ascending=False)

    major = df[df['Cost (USD)'] > cutoff]
    minor = df[df['Cost (USD)'] <= cutoff]
    major.loc["Other"] = minor.sum()

    # Definir paleta de colores distintivos
    import matplotlib.cm as cm
    n_colors = len(major)
    colors = cm.tab20c(np.linspace(0, 1, n_colors))  # Paleta con 20 colores distintivos

    # Crear figura con espacio adicional para la leyenda
    fig, ax = plt.subplots(figsize=(8, 7))
    major.T.plot(kind='bar', stacked=True, fontsize=14, legend=False, color=colors, ax=ax)

    ax.set_ylabel(r'Cost, $\$$', fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.set_xticklabels([])
    ax.grid(True, axis='y', alpha=0.5)

    # Colocar leyenda fuera del gráfico (a la derecha)
    ax.legend(title='Equipment ID', bbox_to_anchor=(1.02, 1), loc='upper left',
              fontsize=14, title_fontsize=14, frameon=True, shadow=True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

    return df


def plot_operating_costs(tea, biogas_stream, save_path='results/operating_costs.png'):
    """
    Plots operating costs breakdown as a stacked bar chart.

    Parameters
    ----------
    tea : TEA
        TEA object
    biogas_stream : bst.Stream
        Biogas stream for normalization
    save_path : str
        Path to save the figure
    """
    opex = pd.DataFrame.from_dict(
        {k: v/(biogas_stream.F_mass*tea.operating_hours) for (k, v) in tea.mfsp_table(biogas_stream).items()},
        orient='index',
        columns=['Cost (USD)']
    ).sort_values(by='Cost (USD)', ascending=False)

    # Mapeo de nombres de costos operativos
    mapeo = {
        'I_feed': 'BM cost',
        'slaughterhouse': 'SHW cost',
        'Utilities': 'Utilities',
        'ROI': 'ROI',
        'Capital': 'Capital',
        'Income Tax': 'Income Tax',
        'O&M': 'O&M',
        'DW_feed': 'DW cost',
        'MEA': 'MEA cost',
        'Other': 'Other',
        'SoilAmendment': 'Biochar sell'
    }

    # Aplicar mapeo de nombres
    opex.index = opex.index.map(lambda x: mapeo.get(x, x))

    # Definir paleta de colores distintivos
    import matplotlib.cm as cm
    n_colors = len(opex)
    colors = cm.tab20c(np.linspace(0, 1, n_colors))

    # Crear figura con espacio adicional para la leyenda
    fig, ax = plt.subplots(figsize=(8, 7))
    opex.T.plot(kind='bar', stacked=True, fontsize=14, legend=False, color=colors, ax=ax)

    ax.set_xlabel('')
    ax.set_ylabel(r'Cost, $\$ \cdot kg^{-1}_{RNG}$', fontsize=14, fontweight='bold')
    ax.tick_params(axis='both', labelsize=14)
    ax.set_xticklabels([])

    # Colocar leyenda fuera del gráfico (a la derecha)
    ax.legend(title='Operating Cost', bbox_to_anchor=(1.02, 1), loc='upper left',
              fontsize=14, title_fontsize=14, frameon=True, shadow=True)
    ax.grid(True, axis='y', alpha=0.5)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

    return opex


def plot_mass_inventory(system, tea, rng_stream, save_path='results/process_diagram.png'):
    """
    Plots process mass inventory diagram with inputs and outputs.

    Parameters
    ----------
    system : bst.System
        BioSTEAM system
    tea : TEA
        TEA object
    rng_stream : bst.Stream
        RNG product stream
    save_path : str
        Path to save the figure
    """
    salidas = {i.ID: i.F_mass for i in system.products}
    entradas = {i.ID: i.F_mass for i in system.feeds}

    salidas['co2_waste'] = salidas['co2_waste']  + salidas['co2hx1']
    salidas['co2hx1'] = 0

    ins = {k: v for k, v in entradas.items() if v > 0}
    outs = {k: v for k, v in salidas.items() if v > 0}
    
    outs['co2_waste']

    n_in = len(ins)
    n_out = len(outs)
    n_max = max(n_in, n_out)
    box_height = n_max * 0.7

    fig, ax = plt.subplots(figsize=(8, 2 + n_max))

    # Process box
    y_bottom = 1
    y_top = y_bottom + box_height
    ax.plot([2, 2, 4, 4, 2], [y_bottom, y_top, y_top, y_bottom, y_bottom], color='black')
    ax.text(3, y_bottom + box_height/2,
            f'MSP: {tea.solve_price(rng_stream):.1f} ' + r'$\$ \cdot kg^{-1}$' +
            f'\nProd: {rng_stream.F_mass * 53*8000/1000/1000:.0f} ' + r'$GJ \cdot year^{-1}$',
            ha='center', va='center', fontsize=18,
            bbox=dict(facecolor='white', edgecolor='black'))

    
    mapeo = {
        'slaughterhouse': 'SHW feed (s. 1)',
        'DW_feed': 'DW feed (s. 2)',
        'I_feed': 'BM feed (s. 3)',
        'rng_out': 'RNG (s. 10)',
        'co2_waste': 'CO2 captured (s. 17)',
        'FlueGas': 'Flue Gas (s. 20)',
        'mea_loss': 'MEA waste (s. 23)',
        'MEA': 'MEA-F feed (s. 26)',
        'wastewater2': 'Wastewater (s. 30)',
        'SoilAmendment': 'Biochar (s. 32)',
        'co2hx1': 'CO2 HX (s. 15)',
        "RNG": 'RNG product (s. 10)',
        "CH4_leak" : 'CH4 leaks (ns)',
        's1': 'Biochar (s. 32)',
    }
    
    # Inputs (left)
    for i, (nombre, caudal) in enumerate(ins.items()):
        y = y_top - (i + 0.5) * (box_height / n_in)
        ax.arrow(1, y, 1, 0, head_width=0.2, head_length=0.2, fc='blue', ec='blue', length_includes_head=True)
        ax.text(0.7, y, f"{mapeo[nombre]}\n{caudal:.0f} "+r"$kg \cdot h^{-1}$", ha='right', va='center', color='blue', fontsize=16)
        print(nombre, caudal)
    # Outputs (right)
    for i, (nombre, caudal) in enumerate(outs.items()):
        y = y_top - (i + 0.5) * (box_height / n_out)
        ax.arrow(4, y, 1, 0, head_width=0.2, head_length=0.2, fc='green', ec='green', length_includes_head=True)
        ax.text(5.3, y, f"{mapeo[nombre]}\n{caudal:.0f} "+r"$kg \cdot h^{-1}$", ha='left', va='center', color='green', fontsize=16)
        print(nombre, caudal)
    ax.axis('off')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
  

    return ins, outs

def plot_lca_by_stream(total_impacts_rng, stream_impacts_contribution, save_path='results/lca_by_stream.png'):
    """
    Gráfico de barras apiladas mostrando contribución de cada corriente al impacto total por kg de RNG.

    Parameters
    ----------
    total_impacts_rng : dict
        {categoria: valor_total} impactos totales por kg de RNG
    stream_impacts_contribution : dict
        {categoria: {corriente: fraccion_normalizada}} contribución de cada corriente (0-1)
    save_path : str
        Ruta para guardar la figura
    """
    # Crear DataFrame para RNG (unidad funcional)
    df_rng = pd.DataFrame(stream_impacts_contribution).fillna(0)

    if df_rng.empty:
        print("No hay datos para RNG")
        return None

    categories = list(df_rng.columns)
    n_cat = len(categories)


    # Figura
    fig, ax = plt.subplots(figsize=(10, 10))
    x = np.arange(n_cat)
    width = 0.4

    # Todas las corrientes
    all_streams = df_rng.index
    print(f"Corrientes: {list(all_streams)}")

    # Mapeo de nombres de corrientes para la leyenda
    stream_names = {
        'slaughterhouse': 'SHW',
        'DW_feed': 'DW',
        'I_feed': 'BM',
        'MEA': 'MEA',
        'rng_out': 'RNG avoided',
        'co2_waste': 'CO₂ captured',
        'FlueGas': 'Flue gas',
        'mea_loss': 'MEA waste',
        'wastewater2': 'Wastewater',
        'SoilAmendment': 'Biochar avoided',
        'electricity': 'Electricity',
        'utilities': 'Utilities',
        'CH4_leak': 'CH4 leaks',
    }

    # Colores por corriente
    colors = plt.cm.tab20(np.linspace(0, 1, len(all_streams)))
    stream_colors = dict(zip(all_streams, colors))

    # Barras apiladas
    bottom_pos = np.zeros(n_cat)
    bottom_neg = np.zeros(n_cat)

    for stream in all_streams:
        values = np.array([df_rng.loc[stream, cat] for cat in categories])

        pos_vals = np.where(values > 0, values, 0)
        neg_vals = np.where(values < 0, values, 0)

        legend_name = stream_names.get(stream, stream)

        if pos_vals.any():
            ax.bar(x, pos_vals, width, bottom=bottom_pos,
                   label=legend_name,
                   color=stream_colors[stream],
                   alpha=0.85,
                   edgecolor='black',
                   linewidth=0.5)
            bottom_pos += pos_vals

        if neg_vals.any():
            ax.bar(x, neg_vals, width, bottom=bottom_neg,
                   label=legend_name if not pos_vals.any() else "",
                   color=stream_colors[stream],
                   alpha=0.85,
                   edgecolor='black',
                   linewidth=0.5)
            bottom_neg += neg_vals

    # Añadir valores totales justo encima de cada barra (en vertical)
    total_values = [total_impacts_rng[cat] for cat in categories]
    for i, (cat, total) in enumerate(zip(categories, total_values)):
        # Posición: justo encima del tope de las barras normalizadas (entre -1 y 1)
        # Si hay barras positivas, usar su altura; si solo hay negativas, ponerlo arriba igual
        if bottom_pos[i] > 0.01:
            y_pos = bottom_pos[i] + 0.03
        else:
            y_pos = 0.03

        ax.text(i, y_pos, f'{total:.2e}',
                ha='center', va='bottom',
                fontsize=9, fontweight='bold',
                rotation=90,  # Texto vertical
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

    ax.set_ylabel('Normalized impact per kg RNG', fontsize=14, fontweight='bold')
    ax.set_xlabel('Impact Categories', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(' (', '\n(') for c in categories],
                        rotation=45, ha='right', fontsize=11)

    
    ax.set_ylim(-1, 1)

    ax.axhline(0, color='black', linewidth=1.5)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Leyenda mejorada
    ax.legend(ncol=3, loc='upper left', fontsize=11, framealpha=0.95)

    # Título informativo
    ax.text(0.98, 0.98, 'Functional unit: 1 kg RNG',
            transform=ax.transAxes,
            fontsize=12, verticalalignment='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8, pad=0.5))

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

    return df_rng


def run_complete_analysis(system, tea, streams, output_dir='results'):
    """
    Runs complete TEA analysis and generates all plots and tables.

    Parameters
    ----------
    system : bst.System
        BioSTEAM system
    tea : TEA
        TEA object
    streams : dict
        Dictionary with key streams
    output_dir : str
        Output directory for results

    Returns
    -------
    results : dict
        Dictionary with analysis results
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    rng = streams['rng']
    biogas = streams['biogas']

    # Calculate MSP
    msp = tea.solve_price(rng)

    print("="*80)
    print(f"The minimum selling price for RNG is ${msp:.3f}/kg.")
    print("="*80)

    # Generate plots
    print("\nGenerating plots...")
    df_equipment = plot_equipment_costs(system, save_path=f'{output_dir}/equipment_costs.png')
    
    
    opex = plot_operating_costs(tea, biogas, save_path=f'{output_dir}/operating_costs.png')
    
    print(opex)
    
    ins, outs = plot_mass_inventory(system, tea, rng, save_path=f'{output_dir}/process_diagram.png')


    # Mass balance check
    assert verify_mass_balance(ins, outs), "Mass balance check"

    sal_F = sum(outs.values())
    ent_F = sum(ins.values())

    print(f"\nMass flow in: {ent_F:.2f} kg/h")
    print(f"Total mass flow out: {sal_F:.2f} kg/h")
    print(f"Total mass flow balance: {ent_F - sal_F:.2f} kg/h")

    results = {
        'msp': msp,
        'equipment_costs': df_equipment,
        'operating_costs': opex,
        'mass_balance': {'inputs': ins, 'outputs': outs, 'error': ent_F - sal_F},
        'FCI': tea.FCI
    }

    return results


def verify_mass_balance(ins, outs, tolerance=0.01, verbose=True):
    """
    Verify mass balance closure.
    
    Args:
        ins (dict): Input streams {name: flow_kg/h}
        outs (dict): Output streams {name: flow_kg/h}
        tolerance (float): Relative error tolerance (%)
        verbose (bool): Print detailed results
    
    Returns:
        bool: True if balance is satisfied
    """
    ent_F = sum(ins.values())
    sal_F = sum(outs.values())
    balance_error = ent_F - sal_F
    relative_error = abs(balance_error / ent_F * 100) if ent_F > 0 else 0
    
    is_balanced = relative_error < tolerance
    
    if verbose:
        print("\n" + "="*80)
        print("MASS BALANCE VERIFICATION")
        print("="*80)
        print(f"Total inlet:        {ent_F:>12.2f} kg/h")
        print(f"Total outlet:       {sal_F:>12.2f} kg/h")
        print(f"Absolute error:     {balance_error:>12.2f} kg/h")
        print(f"Relative error:     {relative_error:>12.4f} %")
        print(f"Tolerance:          {tolerance:>12.4f} %")
        
        if is_balanced:
            print(f"\n✓ Mass balance SATISFIED")
        else:
            print(f"\n✗ Mass balance FAILED")
            print(f"  Error exceeds tolerance by {relative_error - tolerance:.4f}%")
        
        print("="*80)
    
    return is_balanced


def run_lca_analysis(system,  streams, lca_manager, output_dir=None):
    """
    Runs LCA analysis and generates plots.

    Parameters
    ----------
    system : bst.System
        BioSTEAM system
    tea : TEA
        TEA object
    streams : dict
        Dictionary with key streams
    lca_manager : LCAManager
        LCA manager with assigned impacts
    output_dir : str
        Output directory for results

    Returns
    -------
    df_impacts : pd.DataFrame
        DataFrame with impact contributions by stream and category
    """
    
    rng = streams['rng']
    biochar = streams['biochar']
    
    mass_allocation = rng.F_mass / (biochar.F_mass + rng.F_mass)

    
    cat = lca_manager.get_indicators_category

    individual_impacts = {}

    total_impacts = {i: system.get_net_impact(key=i)/system.operating_hours for i in cat}

    total_impacts_rng = {i: v*mass_allocation/rng.F_mass for i, v in total_impacts.items()}

    total_absoluto = {}
    distribution_streams = {}
    
  
    for c in cat:
        individual_impacts[c] = {s.ID: s.get_impact(c) * mass_allocation / rng.F_mass for s in system.feeds + system.products}
        individual_impacts[c]['electricity'] = system.get_net_electricity_impact(c) * mass_allocation / rng.F_mass
        individual_impacts[c]['utilities'] = system.get_net_utility_impact(c) * mass_allocation / rng.F_mass

        total_absoluto[c] = sum(abs(v) for v in individual_impacts[c].values())

        distribution_streams[c] = {s: v / total_absoluto[c] for s, v in individual_impacts[c].items() if total_absoluto[c] > 1e-10}

    stream_impacts_contribution = distribution_streams

    return total_impacts_rng, stream_impacts_contribution


def energy_balance(tea):  
    energy_data = []
    for unit in tea.system.units:
        # Get inlet and outlet enthalpies
        H_in = sum([s.H for s in unit.ins if s.H is not None])  # Total inlet enthalpy (kJ/hr)
        H_out = sum([s.H for s in unit.outs if s.H is not None])  # Total outlet enthalpy (kJ/hr)
        
        # Net duty (positive = heating, negative = cooling)
        net_duty = (H_out - H_in) / 1000  # Convert to kW
        
        # Get power consumption
        power = unit.power_utility.consumption if hasattr(unit, 'power_utility') and unit.power_utility else 0
        
        energy_info = {
            'Unit': unit.ID,
            'H_in (kW)': H_in / 1000,
            'H_out (kW)': H_out / 1000,
            'Net Duty (kW)': net_duty,
            'Power (kW)': power,
            'Type': 'Heating' if net_duty > 0 else 'Cooling' if net_duty < 0 else 'Neutral'
        }
        energy_data.append(energy_info)

    
    return energy_data    


def equipment_costs(tea):
    unit_data = []
    for unit in tea.system.units:
    # Handle None values gracefully
        installed = getattr(unit, 'installed_cost', 0) or 0.0
        utility_hr = getattr(unit, 'utility_cost', 0) or 0.0
        purchase = getattr(unit, 'purchase_cost', 0) or 0.0
        design = getattr(unit, 'design_results', {}) or {}

        unit_info = {
            'Unit': unit.ID,
            'Design Results': design,
            'Purchase Cost': purchase,
            'Installed Cost': installed,
            'Utility ($/hr)': utility_hr,
            'Annual Utility': utility_hr * tea.operating_hours
        }
        unit_data.append(unit_info)
        
    return unit_data
        


# Ejecutar análisis completo (plots + tablas)
if __name__ == "__main__":
    # Create and simulate with default parameters
    system, tea, streams, lca_manager = create_and_simulate_system(setup_lca=True)

    # Get MSP
    rng = streams['rng']
    biochar = streams['biochar']
    msp = tea.solve_price(rng)

    print("="*80)
    print(f"Minimum Selling Price (MSP): ${msp:.3f}/kg RNG")
    print("="*80)

    # Show system diagram
    system.diagram(kind='cluster', number=True, format='png')

    # Show product stream
    rng.show(N=1000, flow="kg/hr")


    results = run_complete_analysis(system, tea, streams, output_dir='results')

    total_impacts_rng, stream_impacts_contribution = run_lca_analysis(system, streams, lca_manager, output_dir=None)

    plot_lca_by_stream(total_impacts_rng, stream_impacts_contribution, save_path='results/lca_by_stream.png')

    
    system.results()
    
    

    

    # %%
    
