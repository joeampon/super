"""
Conventional Pyrolysis (CP) upstream module.

Thermal pyrolysis of HDPE under inert N2 atmosphere (no oxygen feed).
Uses the Pyrolyzer unit with reactor_type='thermal' for ML-predicted yields.
Output feeds into the shared DISTILLATION system alongside TOD.
"""

import biosteam as bst
from .units import Feed_handling, Grinder, Screen, Pyrolyzer, Cyclone


def create_system(feed, feedstock_IDs=None):
    """
    Build the CP (conventional pyrolysis) subsystem.

    Parameters
    ----------
    feed : bst.Stream
        HDPE feed stream.
    feedstock_IDs : list of str, optional
        Chemical IDs treated as feedstock by the Pyrolyzer.
        Defaults to ['HDPE'].

    Returns
    -------
    sys : bst.System
    cooled_product : bst.Stream
    """
    if feedstock_IDs is None:
        feedstock_IDs = ['HDPE', 'LDPE', 'PP', 'PS']

    fluidizing_gas = bst.Stream('CP_fluidizing_gas', N2=1, units='kg/hr', T=298, price=0.0)
    fluidizing_gas.set_total_flow(15, 'kg/hr')

    recycle = bst.Stream('CP_recycle')
    CRHDPE = bst.Stream('CP_CRHDPE')

    # Pretreatment
    handling = Feed_handling('CP_Handling', ins=feed, outs=('CP_S102',))
    M1 = bst.units.Mixer('CP_Mixer', ins=[handling - 0, recycle])
    grinder = Grinder('CP_Grinder', ins=[M1 - 0], outs='CP_S103')
    ch_screen = Screen('CP_CHScreen', ins=grinder - 0, outs=[CRHDPE, recycle])

    # Pyrolysis (no oxygen — inert N2 only)
    M2 = bst.units.Mixer('CP_Mixer2', ins=[CRHDPE, fluidizing_gas])
    reactor = Pyrolyzer(
        'CP_Pyrolyzer', ins=M2 - 0, outs=('CP_S106',),
        T=500 + 273.15, P=101325,
        reactor_type='thermal',
        feedstock_IDs=feedstock_IDs,
    )
    cyclone = Cyclone(
        'CP_Cyclone1', ins=reactor - 0,
        outs=['CP_S107', 'CP_char_sand'], efficiency=0.99,
    )
    cooler = bst.units.HXutility(
        'CP_cooler', ins=cyclone - 0, outs='CP_cooled',
        T=273.15 + 10, rigorous=False,
    )

    sys = bst.System(
        'sys_CP',
        path=[
            bst.System('sys_CP_pretreatment',
                        path=[handling, M1, grinder, ch_screen],
                        recycle=recycle),
            M2, reactor, cyclone, cooler,
        ],
    )
    return sys, cooler.outs[0]
