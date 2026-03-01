"""
Fluid Catalytic Cracking (FCC) downstream module.

Takes a heavy hydrocarbon feed (wax/heavy oil from pyrolysis)
and catalytically cracks it into lighter products.

Post-FCC separation uses boiling-point-based Splitters (same
approach as HC.py) for robustness against complex feed mixtures.
"""

import biosteam as bst
import thermosteam as tmo
from .units import FluidizedCatalyticCracking
from ._compounds import compounds as _chems


def _bp_split(Tb_heavy_key_id):
    """Build a per-component split dict: Tb < heavy key → outs[0]."""
    Tb_cut = _chems[Tb_heavy_key_id].Tb
    split = {}
    for chem in _chems:
        tb = getattr(chem, 'Tb', None)
        split[chem.ID] = 1.0 if (tb is not None and tb < Tb_cut) else 0.0
    return split


def create_system(heavy_feed):
    """
    Build the FCC downstream subsystem.

    Parameters
    ----------
    heavy_feed : bst.Stream
        Heavy hydrocarbon feed (e.g., wax fraction from pyrolysis flash).

    Returns
    -------
    sys : bst.System
    product_streams : dict
    """
    # FCC catalytic cracking reactions
    catalytic_cracking_reaction = tmo.ParallelReaction([
        tmo.Reaction('C11H24 -> C2H6 + C9H18', reactant='C11H24', X=0.85, correct_mass_balance=True),
        tmo.Reaction('C8H16 -> C2H4 + C6H12', reactant='C8H16', X=0.85, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C3H8 + C8H16', reactant='C11H24', X=0., correct_mass_balance=True),
        tmo.Reaction('C9H18 -> C3H6 + C6H12', reactant='C9H18', X=1.0, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C4H10 + C7H14', reactant='C11H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C12H24 -> C4H8 + C8H16', reactant='C12H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C12H26 -> C4H8 + C8H18', reactant='C12H26', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C4H8 -> C4H6 + H2', reactant='C4H8', X=1.0, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C5H12 + C6H12', reactant='C11H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C6H14 + C5H10', reactant='C11H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C7H14O2 -> C6H14 + CO2', reactant='C7H14O2', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C7H16 + C4H8', reactant='C11H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C16H32 -> 2C8H16', reactant='C16H32', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C11H24 -> C8H18 + C3H6', reactant='C11H24', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C15H30 -> C9H18 + C6H12', reactant='C15H30', X=0.7, correct_mass_balance=True),
        tmo.Reaction('C24H50 -> C12H26 + C12H24', reactant='C24H50', X=0.999, correct_mass_balance=True),
        tmo.Reaction('C40H82 -> C20H42 + C20H40', reactant='C40H82', X=0.999, correct_mass_balance=True),
        tmo.Reaction('C20H42 -> C10H22 + C10H20', reactant='C20H42', X=0.999, correct_mass_balance=True),
        tmo.Reaction('C8H16 -> C8H8 + 4H2', reactant='C8H16', X=0.3, correct_mass_balance=True),
        tmo.Reaction('C8H16 -> C8H10 + 3H2', reactant='C8H16', X=0.3, correct_mass_balance=True),
        tmo.Reaction('C9H18 -> C9H10 + 4H2', reactant='C9H18', X=0.3, correct_mass_balance=True),
        tmo.Reaction('C10H22 -> C10H8 + 7H2', reactant='C10H22', X=0.2, correct_mass_balance=True),
        tmo.Reaction('C10H20 -> C10H8 + 6H2', reactant='C10H20', X=0.2, correct_mass_balance=True),
        tmo.Reaction('C20H40 -> 2C10H20', reactant='C20H40', X=1.0, correct_mass_balance=True),
    ])

    # Catalyst and utility streams
    cracking_catalyst = bst.Stream('FCC_catalyst', Zeolite=1, units='lb/hr')
    cracking_catalyst.set_total_flow(200, "kg/hr")
    cracking_catalyst.price = 15.5 * 2.20462262  # $/kg

    air = bst.Stream('FCC_air', phase='g')
    steam = bst.Stream('FCC_steam', phase='g')

    # FCC reactor
    fcc_reactor = FluidizedCatalyticCracking(
        "FCC_Cat_cracking",
        ins=(heavy_feed, cracking_catalyst, air, steam),
        reaction=catalytic_cracking_reaction,
    )

    cat_crack = bst.units.MixTank(
        'FCC_Cat_cracking_Unit', ins=(fcc_reactor - 0, fcc_reactor - 1), outs=(),
    )
    splitter_H2 = bst.units.Splitter(
        "FCC_H2split", ins=(cat_crack - 0), outs=("FCC_ExcessH2"),
        split={'H2': 0.99},
    )
    splitter_H2O = bst.units.Splitter(
        "FCC_water_split", ins=(splitter_H2 - 1), outs=("FCC_ExcessH2O"),
        split={'water': 0.99},
    )

    # Post-FCC separation (boiling-point Splitters for robustness)
    D6 = bst.units.Splitter(
        'FCC_NaphthaSplitter2', ins=splitter_H2O - 1,
        outs=("FCC_S302", "FCC_heavies"),
        split=_bp_split('C14H30'),
    )
    D7 = bst.units.Splitter(
        'FCC_DieselSplitter2', ins=D6 - 1,
        outs=("FCC_S303", "FCC_S304"),
        split=_bp_split('C24H50'),
    )
    D7_mx = bst.Mixer('FCC_D7_MX', ins=D7 - 1, outs=("FCC_Wax"))

    M_naphtha = bst.units.Mixer('FCC_mix_Naphtha', ins=(D6 - 0,), outs=("FCC_Naphtha"))
    M_diesel = bst.units.Mixer('FCC_mix_Diesel', ins=(D7 - 0,), outs=("FCC_Diesel"))

    sys = bst.System(
        'sys_FCC',
        path=[
            fcc_reactor, cat_crack, splitter_H2, splitter_H2O,
            D6, D7, D7_mx, M_naphtha, M_diesel,
        ],
    )

    product_streams = {
        'Naphtha': M_naphtha.outs[0],
        'Diesel': M_diesel.outs[0],
        'Wax': D7_mx.outs[0],
        'ExcessH2': splitter_H2.outs[0],
        'FlueGas': fcc_reactor.outs[2],
    }
    return sys, product_streams
