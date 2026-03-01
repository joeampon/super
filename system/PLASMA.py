"""
Plasma Pyrolysis upstream module.

Converts waste plastic via plasma reactor, includes integrated
heavy/light separation, steam methane reforming, and hydrocracking.
"""

import biosteam as bst
from .units import PlasmaReactor


def create_system(feed, feedstock_IDs=None, use_ml=True,
                  virtual_temperature=450):
    """
    Build the Plasma pyrolysis subsystem (with integrated separation).

    Parameters
    ----------
    feed : bst.Stream
        Plastic feed stream.
    feedstock_IDs : list of str, optional
        Chemical IDs treated as feedstock by the PlasmaReactor.
        Defaults to ['Plastic'] (original behavior).
    use_ml : bool
        If True, use ML-predicted yields (default). If False, use fixed
        Case G yields.
    virtual_temperature : float
        Temperature (°C) fed to the ML model. Default 450.

    Returns
    -------
    sys : bst.System
    product_streams : dict
        Product stream objects keyed by name.
    """
    plasma_yields = {
        # Liquid products (wt% of PE feedstock, Case G)
        "Alcohol": 0.6111, "Acid": 0.1448, "C14H22O": 0.0904,
        "C8H18": 0.1385, "C18H38": 0.1144, "C30H62": 0.0312,
        # Gas products (~17.7 wt% of PE; ~90% CO, ~5% H2)
        "CO": 0.159, "H2": 0.009,
    }

    # CO2 and O2 feed ratios (kg per kg plastic feed)
    co2_r = 0.30   # make-up CO2 (~0.25 consumed + excess for recycle)
    o2in_r = 0.05  # supplementary O2

    co2in = bst.Stream("PLASMA_CO2", CO2=1, price=0.10)
    o2in = bst.Stream("PLASMA_O2", O2=1)

    # Initial flows (updated dynamically by mxFeed spec below)
    plant_size = feed.get_total_flow('tonnes/day')
    co2in.set_total_flow(plant_size * co2_r, "tonnes/day")
    o2in.set_total_flow(plant_size * o2in_r, "tonnes/day")

    recycle_stream = bst.Stream("PLASMA_recycle")

    # --- Plasma reactor ---
    mxFeed = bst.units.Mixer('PLASMA_mxFeed', ins=(feed, co2in, o2in, recycle_stream))

    # Scale CO2 and O2 flows with current feed (changes during optimization)
    def _update_gas_feeds():
        feed_kg_hr = feed.F_mass
        co2in.imass['CO2'] = max(0.001, feed_kg_hr * co2_r)
        o2in.imass['O2'] = max(0.001, feed_kg_hr * o2in_r)
        mxFeed._run()
    mxFeed.add_specification(_update_gas_feeds)

    plasma_kwargs = dict(yields=plasma_yields, power=0.111,
                         use_ml=use_ml,
                         virtual_temperature=virtual_temperature)
    if feedstock_IDs is not None:
        plasma_kwargs['feedstock_IDs'] = feedstock_IDs
    rxplasma = PlasmaReactor(
        "PLASMA_rxPlasma", ins=mxFeed - 0, outs="PLASMA_rxOut",
        **plasma_kwargs,
    )
    hxcond = bst.units.HXutility(
        "PLASMA_hxcond", ins=rxplasma - 0, outs=("PLASMA_hxcond_out"),
        T=32 + 273.15, rigorous=False,
    )

    # --- Heavy separations ---
    gasSplit = bst.units.Flash(
        "PLASMA_spGasSplit", ins=hxcond - 0, outs=("", ""),
        P=101325, T=273.15 + 200,
    )
    hxLiquids = bst.units.HXutility(
        "PLASMA_hxLiquids", ins=gasSplit - 1, outs=(""), T=32 + 273.15,
    )
    clHeavy = bst.units.ShortcutColumn(
        "PLASMA_clHeavy", ins=(hxLiquids - 0), outs=("", ""),
        LHK=("C18H38", "C30H62"), k=1.5, Lr=0.98, Hr=0.98,
    )
    
    clHeavy.check_LHK = False

    # --- Light separations ---
    de_propanizer_bottom = bst.Stream("PLASMA_deprop_bot")
    mxHeavy = bst.units.Mixer("PLASMA_mxHeavy", ins=(clHeavy - 0, de_propanizer_bottom))
    deButanizer = bst.units.ShortcutColumn(
        "PLASMA_deButanizer", ins=(mxHeavy - 0), outs=("", ""),
        LHK=("C8H18", "Alcohol"), k=1.5, Lr=0.95, Hr=0.95,
    )
    deButanizer.check_LHK = False

    _deButanizer_run = deButanizer._run
    def _robust_deButanizer_run():
        try:
            _deButanizer_run()
        except Exception:
            for c in deButanizer.ins[0].available_chemicals:
                if c.Tb < 468:  # midpoint C8H18 (399K) / Alcohol (537K)
                    deButanizer.outs[0].imass[c.ID] = deButanizer.ins[0].imass[c.ID] * 0.95
                    deButanizer.outs[1].imass[c.ID] = deButanizer.ins[0].imass[c.ID] * 0.05
                else:
                    deButanizer.outs[0].imass[c.ID] = deButanizer.ins[0].imass[c.ID] * 0.05
                    deButanizer.outs[1].imass[c.ID] = deButanizer.ins[0].imass[c.ID] * 0.95
    deButanizer._run = _robust_deButanizer_run
    deButanizer._design = lambda: None
    deButanizer._cost = lambda: None

    hxLights = bst.units.HXutility(
        "PLASMA_hxLights", ins=deButanizer - 0, outs=("PLASMA_FlueGases2"),
        T=32 + 273.15,
    )
    clC14 = bst.units.ShortcutColumn(
        "PLASMA_clCarbonyls", ins=(deButanizer - 1), outs=("", ""),
        LHK=("C14H22O", "C18H38"), k=1.5, Lr=0.95, Hr=0.95,
    )
    clC14.check_LHK = False

    def carbonyls():
        try:
            clC14._run()
        except Exception:
            for c in clC14.ins[0].available_chemicals:
                if c.Tb < 552.15:
                    clC14.outs[0].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.95
                    clC14.outs[1].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.05
                else:
                    clC14.outs[0].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.05
                    clC14.outs[1].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.95
    clC14.add_specification(carbonyls)

    # Separate Alcohol (Tb=537K) from C14H22O (Tb=563K) in clC14 tops
    clAlcoholSep = bst.units.ShortcutColumn(
        "PLASMA_clAlcoholSep", ins=(clC14 - 0), outs=("", ""),
        LHK=("Alcohol", "C14H22O"), k=1.5, Lr=0.95, Hr=0.95,
    )
    clAlcoholSep.check_LHK = False

    def alcohol_sep_spec():
        try:
            clAlcoholSep._run()
        except Exception:
            for c in clAlcoholSep.ins[0].available_chemicals:
                if c.Tb < 550:  # midpoint Alcohol(537K) / C14H22O(563K)
                    clAlcoholSep.outs[0].imass[c.ID] = clAlcoholSep.ins[0].imass[c.ID] * 0.95
                    clAlcoholSep.outs[1].imass[c.ID] = clAlcoholSep.ins[0].imass[c.ID] * 0.05
                else:
                    clAlcoholSep.outs[0].imass[c.ID] = clAlcoholSep.ins[0].imass[c.ID] * 0.05
                    clAlcoholSep.outs[1].imass[c.ID] = clAlcoholSep.ins[0].imass[c.ID] * 0.95
    clAlcoholSep.add_specification(alcohol_sep_spec)

    hxCarbonyls = bst.units.HXutility(
        "PLASMA_hxCarbonyls", ins=clAlcoholSep - 1, outs=("PLASMA_Carbonyls"),
        T=32 + 273.15, rigorous=False,
    )

    # --- Heavy cracking ---
    heavyColumn = bst.units.ShortcutColumn(
        "PLASMA_clHeavy2", ins=(clC14 - 1), outs=("", ""),
        LHK=("C18H38", "C30H62"), k=1.5, Lr=0.98, Hr=0.98,
    )
    heavyColumn.check_LHK = False

    def heavy_column_spec():
        try:
            heavyColumn._run()
        except Exception:
            for c in heavyColumn.ins[0].available_chemicals:
                if c.Tb < 625:  # lighter than C30H62
                    heavyColumn.outs[0].imass[c.ID] = heavyColumn.ins[0].imass[c.ID] * 0.98
                    heavyColumn.outs[1].imass[c.ID] = heavyColumn.ins[0].imass[c.ID] * 0.02
                else:
                    heavyColumn.outs[0].imass[c.ID] = heavyColumn.ins[0].imass[c.ID] * 0.02
                    heavyColumn.outs[1].imass[c.ID] = heavyColumn.ins[0].imass[c.ID] * 0.98
    heavyColumn.add_specification(heavy_column_spec)
    heavyColumn._design = lambda: None
    heavyColumn._cost = lambda: None
    hxC30 = bst.units.HXutility(
        "PLASMA_hxC30", ins=heavyColumn - 1, outs=("PLASMA_C30"),
        T=32 + 273.15,
    )
    ppHeavy = bst.units.Pump("PLASMA_ppHeavy", ins=clHeavy - 1, outs="PLASMA_HeavyOil")

    ngIn = bst.Stream("PLASMA_ngIn", CH4=1)
    cpReformer = bst.units.IsentropicCompressor(
        "PLASMA_cpReformer", ins=ngIn, outs=(""), P=20 * 101325, vle=True,
    )
    waterIn = bst.Stream("PLASMA_waterIn", water=1)
    ppReformer = bst.units.Pump("PLASMA_ppReformer", ins=waterIn, outs=(""), P=20 * 101325)
    rxReformer = bst.units.MixTank(
        "PLASMA_rxReformer", ins=(cpReformer - 0, ppReformer - 0), outs=(""), tau=0.5,
    )

    def reforming():
        rxReformer._run()
        ngIn.F_mass = ppHeavy.outs[0].F_mass * 0.02 * 16 / 4 / 0.9 / 0.8
        waterIn.F_mol = ngIn.F_mol * 2
        rxn = bst.Reaction("CH4+H2O->CO+3H2 ", reactant="CH4", X=0.9)
        rxn(rxReformer.outs[0])
    rxReformer.add_specification(reforming)

    psa = bst.units.Splitter("PLASMA_psa", ins=rxReformer - 0, split={"H2": 0.8})
    hcReactor = bst.units.MixTank(
        "PLASMA_Hydrocracker", ins=(ppHeavy - 0, psa - 0),
        outs=("PLASMA_HydrocrackedOil"), tau=0.5,
    )

    def hydrocracking():
        hcReactor._run()
        rxn = bst.Reaction("3C30H62+2H2->5C18H38 ", reactant="C30H62", X=0.95)
        rxn(hcReactor.outs[0])
    hcReactor.add_specification(hydrocracking)

    hcFlash = bst.units.Flash(
        "PLASMA_hcFlash", ins=hcReactor - 0, outs=("PLASMA_FlueGas3", ""),
        T=273.15 + 40, P=101325,
    )
    mxDiesel = bst.units.Mixer("PLASMA_mxParaffins", ins=(hcFlash - 1, heavyColumn - 0))
    hxParaffins = bst.units.HXutility(
        "PLASMA_hxParaffins", ins=mxDiesel - 0, outs=("PLASMA_Paraffins"),
        T=32 + 273.15,
    )

    # --- Light recovery ---
    cpOlefins = bst.units.IsentropicCompressor(
        "PLASMA_cpOlefins", ins=gasSplit - 0, P=2 * 101325,
    )
    HX1 = bst.HXutility("PLASMA_evap1", ins=(cpOlefins - 0), T=273.15 - 42)
    HX2 = bst.HXutility("PLASMA_evap2", ins=(HX1 - 0), T=273.15 - 88)
    C2 = bst.units.IsentropicCompressor(
        "PLASMA_cp2", ins=HX2 - 0, outs=(""), P=2 * 101325, eta=0.7, vle=True,
    )
    HXc2 = bst.units.HXutility("PLASMA_cond2", ins=C2 - 0, T=273.15 - 45)
    HX2c2 = bst.units.HXutility("PLASMA_cond3", ins=HXc2 - 0, T=273.15 - 50)
    HX3c2 = bst.units.HXutility("PLASMA_cond4", ins=HX2c2 - 0, T=273.15 - 60)

    flash1 = bst.units.Flash(
        "PLASMA_Flash", ins=HX3c2 - 0, outs=("PLASMA_RecycleCO2",),
        T=273.15 - 78, P=(HX3c2 - 0).P,
    )
    P1 = bst.units.Pump("PLASMA_pump", ins=flash1 - 1, P=25 * 101325)
    HX3 = bst.units.HXutility("PLASMA_heater", ins=P1 - 0, T=273.15 + 2)

    dist1 = bst.units.ShortcutColumn(
        "PLASMA_clEthanizer", ins=(HX3 - 0), outs=("", ""),
        LHK=("C8H18", "Alcohol"), k=1.5, Lr=0.99, Hr=0.98,
    )

    _dist1_run = dist1._run
    def _robust_dist1_run():
        try:
            _dist1_run()
        except Exception:
            for c in dist1.ins[0].available_chemicals:
                if c.Tb < 468:  # midpoint C8H18 (399K) / Alcohol (537K)
                    dist1.outs[0].imass[c.ID] = dist1.ins[0].imass[c.ID] * 0.99
                    dist1.outs[1].imass[c.ID] = dist1.ins[0].imass[c.ID] * 0.01
                else:
                    dist1.outs[0].imass[c.ID] = dist1.ins[0].imass[c.ID] * 0.02
                    dist1.outs[1].imass[c.ID] = dist1.ins[0].imass[c.ID] * 0.98
    dist1._run = _robust_dist1_run
    dist1._design = lambda: None
    dist1._cost = lambda: None

    ethylene_frac = bst.units.ShortcutColumn(
        "PLASMA_clEthylene", ins=(dist1 - 0), outs=("PLASMA_Olefins", ""),
        LHK=("C8H18", "Alcohol"), k=1.5, Lr=0.99, Hr=0.99,
    )
    ethylene_frac.check_LHK = False

    HX4 = bst.units.HXutility(
        "PLASMA_heater2", ins=dist1 - 1, outs="PLASMA_S8", T=273.15 + 50, rigorous=False,
    )
    dist2 = bst.units.ShortcutColumn(
        "PLASMA_Depropanizer", ins=(HX4 - 0),
        LHK=("Alcohol", "C14H22O"), outs=("", de_propanizer_bottom),
        k=1.5, Lr=0.98, Hr=0.98,
    )
    dist2.check_LHK = False

    HX5 = bst.units.HXutility("PLASMA_heater3", ins=dist2 - 0, T=273.15 + 30, rigorous=False)
    C3 = bst.units.IsentropicCompressor("PLASMA_cp3", ins=HX5 - 0, P=25 * 101325, eta=0.7)
    clAlcohol = bst.units.ShortcutColumn(
        "PLASMA_clAlcohol", ins=(C3 - 0), outs=("", ""),
        LHK=("Alcohol", "Acid"), P=25 * 101325, k=1.5, Lr=0.95, Hr=0.95,
    )
    clAlcohol.check_LHK = False
    clAcid = bst.units.ShortcutColumn(
        "PLASMA_clAcid", ins=(clAlcohol - 1), outs=("", "PLASMA_Acids"),
        LHK=("Alcohol", "Acid"), P=25 * 101325, k=1.5, Lr=0.98, Hr=0.98,
    )

    # Merge alcohol recovered from carbonyls column with main alcohol product
    mxAlcohols = bst.units.Mixer(
        "PLASMA_mxAlcohols",
        ins=(clAlcohol - 0, clAlcoholSep - 0),
        outs=("PLASMA_Alcohols"),
    )

    recycle_mixer = bst.units.Mixer(
        "PLASMA_recycle_mixer",
        ins=(clAcid - 0, ethylene_frac - 1, flash1 - 0),
    )
    recycle_splitter = bst.units.Splitter(
        "PLASMA_recycle_splitter", ins=recycle_mixer - 0,
        outs=(recycle_stream, ""), split=0.9,
    )
    fluegas_mixer = bst.units.Mixer(
        "PLASMA_flueGasMixer",
        ins=(recycle_splitter - 1, hcFlash - 0, hxLights - 0, psa - 1),
        outs="PLASMA_FlueGases",
    )

    sys = bst.System(
        "sys_PLASMA",
        path=[
            mxFeed, rxplasma, hxcond, gasSplit, hxLiquids, clHeavy,
            ppHeavy, cpReformer, ppReformer, rxReformer, psa,
            hcReactor, hcFlash,
            cpOlefins, HX1, HX2, C2, HXc2, HX2c2, HX3c2,
            flash1, P1, HX3, dist1, ethylene_frac,
            HX4, dist2, HX5, C3, clAlcohol, clAcid,
            mxHeavy, deButanizer, hxLights, clC14, clAlcoholSep, hxCarbonyls,
            heavyColumn, hxC30,
            mxDiesel, hxParaffins,
            mxAlcohols,
            recycle_mixer, recycle_splitter, fluegas_mixer,
        ],
        recycle=recycle_stream,
    )

    # Apply custom cost overrides
    def column_costs(unit):
        unit.installed_costs = {}
        unit.installed_costs["Column"] = (
            1264000 * (unit.ins[0].get_total_flow("tonne/hr") / 4.37) ** 0.6
        )

    def hydrocracker_costs(unit):
        unit.installed_costs = {}
        unit.installed_costs["Hydrocracker"] = (
            556 / 585.7 * 1.43 * 6046000
            * (unit.ins[0].get_total_flow("lb/hr") / 55000) ** 0.7
        )

    clAlcohol._design = lambda: 0
    clAlcohol._cost = lambda: column_costs(clAlcohol)
    clAcid._design = lambda: 0
    clAcid._cost = lambda: column_costs(clAcid)
    clC14._design = lambda: 0
    clC14._cost = lambda: column_costs(clC14)
    clAlcoholSep._design = lambda: 0
    clAlcoholSep._cost = lambda: column_costs(clAlcoholSep)
    hcReactor._design = lambda: 0
    hcReactor._cost = lambda: hydrocracker_costs(hcReactor)

    product_streams = {
        'Paraffins': hxParaffins.outs[0],
        'Carbonyls': hxCarbonyls.outs[0],
        'Olefins': ethylene_frac.outs[0],
        'Alcohols': mxAlcohols.outs[0],
        'Acids': clAcid.outs[1],
        'C30': hxC30.outs[0],
        'FlueGas': fluegas_mixer.outs[0],
    }
    return sys, product_streams
