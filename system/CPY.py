"""
Catalytic Pyrolysis (CPY) upstream module.

Based on Adejare's Polystyrene pyrolysis system.
Uses a simplified Pyrolyzer (fixed yields, no ML model dependency).
"""

import biosteam as bst
from .units import Feed_handling, Grinder, Screen, Pyrolyzer


def create_system(feed, feedstock_IDs=None, reactor_type='catalytic'):
    """
    Build the CPY (Polystyrene catalytic pyrolysis) subsystem.

    Parameters
    ----------
    feed : bst.Stream
        PS (Polystyrene) feed stream.
    feedstock_IDs : list of str, optional
        Chemical IDs treated as feedstock by the Pyrolyzer.
        Defaults to ['PS'] (original behavior).
    reactor_type : str
        Reactor type for ML yield correction: 'thermal', 'TOD', or 'catalytic'.

    Returns
    -------
    sys : bst.System
    product_streams : dict
        Dictionary of product stream objects keyed by name.
    """
    reactor_temperature = 500 + 273.15
    oxygen_equivalence_ratio = 0.07
    capacity_tpd = feed.get_total_flow('tonnes/day')

    pyrolysis_oxygen = bst.Stream('CPY_oxygen', O2=1, units='kg/hr', T=298, price=0.0)
    oxygen_mass = oxygen_equivalence_ratio * capacity_tpd * 100 / 93
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    fluidizing_gas = bst.Stream('CPY_fluidizing_gas', N2=1, units='kg/hr', T=298, price=0.0)
    fluidizing_gas.set_total_flow(15, 'kg/hr')

    recycle = bst.Stream('CPY_recycle')
    CRPS = bst.Stream('CPY_CRPS')
    char_sand = bst.Stream('CPY_CharSand')

    # Pretreatment
    handling = Feed_handling('CPY_Handling', ins=feed, outs=('CPY_handled',))
    M1 = bst.units.Mixer('CPY_Mixer_1', ins=[handling - 0, recycle])
    grinder = Grinder('CPY_Grinder', ins=[M1 - 0], outs=('CPY_ground',))
    ch_screen = Screen('CPY_CHScreen', ins=[grinder - 0], outs=[CRPS, recycle])

    # Pyrolysis
    mixer_pyro = bst.units.Mixer('CPY_Mixer_pyro', ins=[CRPS, fluidizing_gas, pyrolysis_oxygen])
    pyro_kwargs = dict(T=reactor_temperature, P=101325, reactor_type=reactor_type)
    if feedstock_IDs is not None:
        pyro_kwargs['feedstock_IDs'] = feedstock_IDs
    reactor = Pyrolyzer('CPY_Pyrolyzer', ins=[mixer_pyro - 0], outs=('CPY_pyro_out',),
                         **pyro_kwargs)
    cyclone = bst.units.Cyclone('CPY_Cyclone', ins=(reactor - 0,),
                                 outs=['CPY_oil_gas', char_sand], efficiency=0.99)
    cooler = bst.units.HXutility('CPY_cooler', ins=[cyclone - 0], outs=('CPY_cooled',),
                                  T=273.15 + 10, rigorous=False)

    # Flash separation
    flash0 = bst.units.Flash('CPY_F0', ins=cooler - 0, T=273.15 + 10, P=101325,
                              outs=('CPY_F0gas', 'CPY_F0oil'))

    pump1 = bst.units.Pump('CPY_Pump1', ins=[flash0 - 1], P=25 * 101325)
    flash1 = bst.units.Flash('CPY_F1', ins=pump1 - 0, T=285, P=101325,
                              outs=('CPY_F1gas', 'CPY_F1oil'))

    # Distillation train for aromatics separation
    D1 = bst.units.BinaryDistillation(
        'CPY_D1', ins=flash1.outs[1], outs=['CPY_BenzeneD1', 'CPY_TolueneD1'],
        LHK=('C6H6', 'C7H8'), y_top=0.90, x_bot=0.10, k=2.2, P=101325,
    )
    D1.check_LHK = False
    D1._design = lambda: None
    D1._cost = lambda: None
    D1.purchase_costs = {'Distillation column': 320257.691}
    D2 = bst.units.BinaryDistillation(
        'CPY_D2', ins=D1 - 1, outs=['CPY_TolueneD2', 'CPY_XyleneD2'],
        LHK=('C7H8', 'C8H18'), product_specification_format='Recovery',
        Lr=0.95, Hr=0.95, k=2.2, P=101325,
    )
    D2.check_LHK = False
    D2._design = lambda: None
    D2._cost = lambda: None
    D2.purchase_costs = {'Distillation column': 320257.691}
    D3 = bst.units.BinaryDistillation(
        'CPY_D3', ins=D2 - 1, outs=['CPY_Aromatics', 'CPY_XyleneD3'],
        LHK=('C8H18', 'C8H10'), y_top=0.95, x_bot=0.05, k=2.2, P=101325,
    )
    D3.check_LHK = False
    D3._design = lambda: None
    D3._cost = lambda: None
    D3.purchase_costs = {'Distillation column': 320257.691}
    D4 = bst.units.BinaryDistillation(
        'CPY_D4', ins=D3 - 1, outs=['CPY_XyleneD4', 'CPY_residue'],
        LHK=('C8H10', 'PS'), product_specification_format='Recovery',
        Lr=0.95, Hr=0.95, k=2.2, P=101325,
    )
    D4.check_LHK = False
    D4._design = lambda: None
    D4._cost = lambda: None
    D4.purchase_costs = {'Distillation column': 320257.691}

    # Product coolers
    cooler_D1 = bst.units.HXutility('CPY_coolerD1', ins=D1 - 0, outs=('CPY_BenzeneO',),
                                     T=298.15, rigorous=True)
    cooler_D2 = bst.units.HXutility('CPY_coolerD2', ins=D2 - 0, outs=('CPY_TolueneO',),
                                     T=298.15, rigorous=True)
    cooler_D3 = bst.units.HXutility('CPY_coolerD3', ins=D3 - 0, outs=('CPY_AromaticsO',),
                                     T=298.15, rigorous=True)
    cooler_D4 = bst.units.HXutility('CPY_coolerD4', ins=D4 - 0, outs=('CPY_XyleneO',),
                                     T=298.15, rigorous=True)

    sys = bst.System(
        'sys_CPY',
        path=[
            bst.System('sys_CPY_pretreatment',
                        path=[handling, M1, grinder, ch_screen],
                        recycle=recycle),
            mixer_pyro, reactor, cyclone, cooler,
            flash0, pump1, flash1,
            D1, D2, D3, D4,
            cooler_D1, cooler_D2, cooler_D3, cooler_D4,
        ],
    )

    product_streams = {
        'Benzene': cooler_D1.outs[0],
        'Toluene': cooler_D2.outs[0],
        'Aromatics': cooler_D3.outs[0],
        'Xylene': cooler_D4.outs[0],
        'FlueGas': flash0.outs[0],
    }
    return sys, product_streams
