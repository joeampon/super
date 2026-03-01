"""
Shared product fractionation / distillation module.

Standard separation train used after pyrolysis (primarily with TOD).
Separates cooled crude pyrolysis vapor into light gases and fuel-range products.

Products: Ethylene, Propylene, Butene, Naphtha, Diesel, Wax
Also produces an NCG recycle stream for the upstream reactor.

Notes
-----
D1 (de-ethanizer) and D2 (depropanizer) use rigorous BinaryDistillation
because their LHK (C2H4/C3H8, C3H8/C4H8) are always present in the
compressed-gas path.

D3 (debutanizer), D4 (NaphthaSplitter), and D5 (DieselSplitter) use
boiling-point-based component splitting for robustness.  The F3 flash
at 0 °C condenses most of the crude product; only a small fraction
passes through the gas-phase distillation train.  The condensed liquid
(F3 liquid) is routed to D4 so that naphtha, diesel, and wax are all
properly separated by Tb cutoff.
"""

import biosteam as bst
from ._compounds import compounds as _chems


def _bp_split(Tb_heavy_key_id):
    """Build a per-component split dict: Tb < heavy key → outs[0]."""
    Tb_cut = _chems[Tb_heavy_key_id].Tb
    split = {}
    for chem in _chems:
        tb = getattr(chem, 'Tb', None)
        split[chem.ID] = 1.0 if (tb is not None and tb < Tb_cut) else 0.0
    return split


def create_system(crude_stream, rec_NCG=None, prefix='DIST'):
    """
    Build the standard product fractionation subsystem.

    Parameters
    ----------
    crude_stream : bst.Stream
        Cooled crude pyrolysis product.
    rec_NCG : bst.Stream or None
        Non-condensable gas recycle stream to feed back upstream.
        If None, a new stream is created.
    prefix : str
        Unit ID prefix (default 'DIST').

    Returns
    -------
    sys : bst.System
    product_streams : dict
    rec_NCG : bst.Stream
    """
    if rec_NCG is None:
        rec_NCG = bst.Stream(f'{prefix}_rec_NCG')

    # --- Initial condensation ---
    F1 = bst.units.Flash(
        f'{prefix}_Condenser', ins=crude_stream,
        outs=(f'{prefix}_S201', f'{prefix}_S239'),
        P=101325, T=283.15,
    )
    H7 = bst.HXutility(
        f'{prefix}_Heater7', ins=F1 - 1, outs=f'{prefix}_S232',
        T=273.15 + 150, rigorous=False,
    )
    F3 = bst.units.Flash(
        f'{prefix}_FlashSep', ins=H7 - 0,
        outs=(f'{prefix}_S233', f'{prefix}_S234'),
        P=1.01 * 101325, T=273.15,
    )

    # --- Compression and deep cooling ---
    K1 = bst.units.IsentropicCompressor(
        f'{prefix}_Compressor1', ins=F1 - 0, outs=f'{prefix}_S202',
        P=2 * 101325, eta=0.8,
    )
    H2 = bst.units.HXutility(
        f'{prefix}_Heater2', ins=K1 - 0, outs=f'{prefix}_S203',
        T=273.15 + 30, rigorous=False,
    )
    K2 = bst.units.IsentropicCompressor(
        f'{prefix}_Compressor2', ins=H2 - 0, outs=f'{prefix}_S205',
        P=7 * 101325, eta=0.8,
    )
    F2 = bst.units.Flash(
        f'{prefix}_Condenser2', ins=K2 - 0,
        outs=(f'{prefix}_S210', f'{prefix}_S209'),
        P=7 * 101325, T=273.15 - 110,
    )
    P1 = bst.units.Pump(
        f'{prefix}_Pump', ins=F2 - 1, outs=f'{prefix}_S211',
        P=25 * 101325,
    )
    H6 = bst.HXutility(
        f'{prefix}_Heater6', ins=P1 - 0, outs=f'{prefix}_S212',
        T=273.15 + 2, rigorous=False,
    )

    # --- De-ethanizer ---
    D1 = bst.units.BinaryDistillation(
        f'{prefix}_De_ethanizer', ins=H6 - 0,
        outs=(f'{prefix}_S213', f'{prefix}_S214'),
        LHK=('C2H4', 'C3H8'), y_top=0.99, x_bot=0.01, k=2, is_divided=True,
    )
    D1.check_LHK = False
    D1_spl = bst.units.Splitter(
        f'{prefix}_EthyleneFrac', ins=D1 - 0,
        outs=(f'{prefix}_S215', f'{prefix}_S216'),
        split={'C2H4': 0.99, 'CO2': 0.10, 'C3H8': 0.05, 'O2': 1, 'CO': 1, 'H2': 1},
    )
    D1_mx = bst.Mixer(f'{prefix}_D1_MX', ins=D1_spl - 0, outs=f'{prefix}_Ethylene')

    # --- Depropanizer ---
    H8 = bst.HXutility(
        f'{prefix}_Heater8', ins=D1 - 1, outs=f'{prefix}_S217',
        T=273.15 + 100, rigorous=False,
    )
    D2 = bst.units.BinaryDistillation(
        f'{prefix}_Depropanizer', ins=H8 - 0,
        outs=(f'{prefix}_S218', f'{prefix}_S219'),
        LHK=('C3H8', 'C4H8'), y_top=0.99, x_bot=0.01, k=2, is_divided=True,
    )
    D2.check_LHK = False
    H9 = bst.HXutility(
        f'{prefix}_Heater9', ins=D2 - 0, outs=f'{prefix}_S220',
        T=273.15 + 70, rigorous=False,
    )
    KD2 = bst.units.IsentropicCompressor(
        f'{prefix}_CompressorD2', ins=H9 - 0, outs=f'{prefix}_S221',
        P=22 * 101325, eta=0.8,
    )
    D2_spl = bst.units.Splitter(
        f'{prefix}_PropyleneFrac', ins=KD2 - 0,
        outs=(f'{prefix}_S222', f'{prefix}_S223'),
        split={'C3H8': 0.05, 'C2H4': 1, 'O2': 1, 'CO': 1, 'H2': 1},
    )
    D2_mx = bst.Mixer(f'{prefix}_D2_MX', ins=D2_spl - 0, outs=f'{prefix}_Propylene')

    # --- NCG recycle ---
    Mrec = bst.Mixer(
        f'{prefix}_Mixer_rec', ins=[D2_spl - 1, F2 - 0, D1_spl - 1],
        outs=rec_NCG,
    )

    # --- Debutanizer (Tb < Tb_C10H22 → butene) ---
    M3 = bst.Mixer(f'{prefix}_Mixer3', ins=[F3 - 0, D2 - 1], outs=f'{prefix}_S224')
    D3 = bst.units.Splitter(
        f'{prefix}_Debutanizer', ins=M3 - 0,
        outs=(f'{prefix}_S225', f'{prefix}_S226'),
        split=_bp_split('C10H22'),
    )
    D3_mx = bst.Mixer(f'{prefix}_D3_MX', ins=D3 - 0, outs=f'{prefix}_Butene')

    # --- Naphtha splitter (Tb < Tb_C14H30 → naphtha) ---
    # F3 liquid (heavy condensate) joins D3 bottoms so that all
    # naphtha/diesel/wax components are properly classified.
    M_D4in = bst.Mixer(
        f'{prefix}_MixerD4', ins=[D3 - 1, F3 - 1], outs=f'{prefix}_D4in',
    )
    D4 = bst.units.Splitter(
        f'{prefix}_NaphthaSplitter', ins=M_D4in - 0,
        outs=(f'{prefix}_S227', f'{prefix}_S228'),
        split=_bp_split('C14H30'),
    )
    D4_mx = bst.Mixer(f'{prefix}_D4_MX', ins=D4 - 0, outs=f'{prefix}_Naphtha')

    # --- Diesel splitter (Tb < Tb_C24H50 → diesel) ---
    D5 = bst.units.Splitter(
        f'{prefix}_DieselSplitter', ins=D4 - 1,
        outs=(f'{prefix}_S229', f'{prefix}_S230'),
        split=_bp_split('C24H50'),
    )
    D5_mx = bst.Mixer(f'{prefix}_D5_MX', ins=D5 - 0, outs=f'{prefix}_Diesel')

    # --- Wax (heavy residue from D5 bottoms) ---
    M4_mx = bst.Mixer(f'{prefix}_M4_MX', ins=D5 - 1, outs=f'{prefix}_Wax')

    sys = bst.System(
        f'sys_{prefix}',
        path=[
            F1, H7, F3,
            K1, H2, K2, F2, P1, H6,
            D1, D1_spl, D1_mx,
            H8, D2, H9, KD2, D2_spl, D2_mx,
            Mrec,
            M3, D3, D3_mx,
            M_D4in, D4, D4_mx,
            D5, D5_mx,
            M4_mx,
        ],
    )

    product_streams = {
        'Ethylene': D1_mx.outs[0],
        'Propylene': D2_mx.outs[0],
        'Butene': D3_mx.outs[0],
        'Naphtha': D4_mx.outs[0],
        'Diesel': D5_mx.outs[0],
        'Wax': M4_mx.outs[0],
    }
    return sys, product_streams, rec_NCG
