"""
Hydrocracking (HC) downstream module.

Takes a heavy hydrocarbon feed and hydrogen, cracks heavy fractions
into naphtha and diesel range products.

Separation uses boiling-point-based component splitting rather than
rigorous BinaryDistillation.  The HC wax feed can contain aromatics
and naphtha-range compounds that condense in the upstream DISTILLATION
flash (F3 at 0 °C).  BinaryDistillation fails to converge with these
intermediate volatiles, so sharp Tb-cutoff splitters are used instead.
This is consistent with the Hydrocrack reactor's pass-through model.
"""

import biosteam as bst
import thermosteam as tmo
from .units import Compressor, Hydrocrack
from ._compounds import compounds as _chems


def _bp_split(Tb_heavy_key_id):
    """Build a per-component split dict: Tb < heavy key → outs[0]."""
    Tb_cut = _chems[Tb_heavy_key_id].Tb
    split = {}
    for chem in _chems:
        tb = getattr(chem, 'Tb', None)
        split[chem.ID] = 1.0 if (tb is not None and tb < Tb_cut) else 0.0
    return split


def create_system(heavy_feed, hydrogen):
    """
    Build the Hydrocracking downstream subsystem.

    Parameters
    ----------
    heavy_feed : bst.Stream
        Heavy hydrocarbon feed (wax/heavy oil from upstream pyrolysis).
    hydrogen : bst.Stream
        Hydrogen feed stream.

    Returns
    -------
    sys : bst.System
    product_streams : dict
    """
    HC_catalyst_price = 15.5 * 2.20462262  # $/kg

    # Hydrocracking reactions: wax + H2 → naphtha + diesel
    # Based on Jones et al. (PNNL 2009) / Dutta et al. (NREL 2015) referenced
    # in Olafasakin et al. (2023): >90 wt% conversion of wax to lighter cuts.
    hydrocracking_rxn = tmo.ParallelReaction([
        tmo.Reaction('C40H82 + 2H2 -> C18H38 + C14H30 + C8H18',
                     reactant='C40H82', X=0.99),
        tmo.Reaction('C30H62 + H2 -> C18H38 + C12H26',
                     reactant='C30H62', X=0.95),
        tmo.Reaction('C24H50 + H2 -> C14H30 + C10H22',
                     reactant='C24H50', X=0.95),
        tmo.Reaction('C20H42 + H2 -> C12H26 + C8H18',
                     reactant='C20H42', X=0.90),
        tmo.Reaction('C20H40 + 2H2 -> C12H26 + C8H18',
                     reactant='C20H40', X=0.90),
    ])

    K3 = Compressor('HC_Compressor3', ins=hydrogen, outs=("HC_S301"),
                     P=89.7 * 101325, eta=0.8)
    hydrocracking_catalyst = bst.Stream('HC_catalyst', Zeolite=1, units='lb/hr')
    hydrocracking_catalyst.set_total_flow(200, "kg/hr")
    hydrocracking_catalyst.price = HC_catalyst_price

    hydro_crack = Hydrocrack(
        "HC_Hydrocracking", ins=(heavy_feed, K3 - 0, hydrocracking_catalyst),
        reaction=hydrocracking_rxn,
    )
    hydrocrack_unit = bst.units.MixTank(
        'HC_Hydrocracking_Unit', ins=(hydro_crack - 0, hydro_crack - 1), outs=(),
    )
    splitter1 = bst.units.Splitter(
        "HC_H2split", ins=(hydrocrack_unit - 0), outs=("HC_ExcessH2"),
        split={'H2': 0.99},
    )

    # Naphtha cut: Tb < Tb(C14H30) → naphtha
    D6 = bst.units.Splitter(
        'HC_NaphthaSplitter2', ins=splitter1 - 1,
        outs=("HC_S302", "HC_heavies"),
        split=_bp_split('C14H30'),
    )
    # Diesel cut: Tb < Tb(C24H50) → diesel (remainder = wax)
    D7 = bst.units.Splitter(
        'HC_DieselSplitter2', ins=D6 - 1,
        outs=("HC_S303", "HC_S304"),
        split=_bp_split('C24H50'),
    )
    D7_mx = bst.Mixer('HC_D7_MX', ins=D7 - 1, outs=("HC_Wax"))

    M_naphtha = bst.units.Mixer('HC_mix_Naphtha', ins=(D6 - 0,), outs=("HC_Naphtha"))
    M_diesel = bst.units.Mixer('HC_mix_Diesel', ins=(D7 - 0,), outs=("HC_Diesel"))

    sys = bst.System(
        'sys_HC',
        path=[
            K3, hydro_crack, hydrocrack_unit, splitter1,
            D6, D7, D7_mx, M_naphtha, M_diesel,
        ],
    )

    product_streams = {
        'Naphtha': M_naphtha.outs[0],
        'Diesel': M_diesel.outs[0],
        'Wax': D7_mx.outs[0],
        'ExcessH2': splitter1.outs[0],
    }
    return sys, product_streams
