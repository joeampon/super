"""
Thermal Oxodegradation (TOD) upstream pyrolysis module.

Decomposes HDPE plastic feed via autothermal pyrolysis (no furnace).
Produces a cooled crude pyrolysis vapor for downstream separation.
"""

import biosteam as bst
from .units import Feed_handling, Grinder, Screen, RYield, Cyclone

# TOD product yields (mass fractions of HDPE feed)
_yields_comp = [
    "HDPE", "Ash", "Char", "O2", "CO", "CO2", "H2",
    "CH4", "C2H4", "C3H8", "C4H8",
    "C10H22", "C14H30", "C24H50", "C40H82",
]
_TOD_comp = [
    0, 0.003, 0, 0.002568044, 0.008331545, 0.065173325, 0.000269637,
    0.004444155, 0.006684276 + 0.01964527, 0.016659066, 0.016224682,
    0.0769, 0.0431, 0.3735, 0.3364,
]
TOD_YIELDS = dict(zip(_yields_comp, _TOD_comp))


def create_system(feed):
    """
    Build the TOD pyrolysis subsystem.

    Parameters
    ----------
    feed : bst.Stream
        HDPE feed stream.

    Returns
    -------
    sys : bst.System
    cooled_product : bst.Stream
    """
    capacity_tpd = feed.get_total_flow('tonnes/day')
    oxygen_mass = 0.07 * capacity_tpd * 100 / 93

    pyrolysis_oxygen = bst.Stream('TOD_oxygen', O2=1, units='kg/hr', T=298, price=0.0)
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    fluidizing_gas = bst.Stream('TOD_fluidizing_gas', N2=1, units='kg/hr', T=298, price=0.0)
    fluidizing_gas.set_total_flow(15, 'kg/hr')

    recycle = bst.Stream('TOD_recycle')
    CRHDPE = bst.Stream('TOD_CRHDPE')

    handling = Feed_handling('TOD_Handling', ins=feed, outs=("TOD_S102"))
    M1 = bst.units.Mixer('TOD_Mixer', ins=[handling - 0, recycle])
    grinder = Grinder('TOD_Grinder', ins=[M1 - 0], outs="TOD_S103")
    ch_screen = Screen("TOD_CHScreen", ins=grinder - 0, outs=[CRHDPE, recycle])

    M2 = bst.units.Mixer('TOD_Mixer2', ins=[CRHDPE, pyrolysis_oxygen, fluidizing_gas])
    reactor = RYield(
        'TOD_CFB_Reactor', ins=M2 - 0, outs=("TOD_S106"),
        yields=TOD_YIELDS, factor=0.4, wt_closure=90.4,
    )
    cyclone = Cyclone('TOD_Cyclone1', ins=reactor - 0,
                       outs=['TOD_S107', "TOD_char_sand"], efficiency=0.99)
    cooler = bst.units.HXutility('TOD_cooler', ins=cyclone - 0, outs='TOD_cooled',
                                  T=273.15 + 10, rigorous=False)

    sys = bst.System(
        'sys_TOD',
        path=[
            bst.System('sys_TOD_pretreatment',
                        path=[handling, M1, grinder, ch_screen],
                        recycle=recycle),
            M2, reactor, cyclone, cooler,
        ],
    )
    return sys, cooler.outs[0]
