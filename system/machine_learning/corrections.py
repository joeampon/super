"""
Linear correction factors for reactor-type-specific yield adjustments.

The base PyrolysisNet model is trained on conventional (thermal, inert)
pyrolysis data.  These corrections shift the 8 predicted wt% outputs to
account for different reactor chemistries:

    corrected_i(T) = base_i + (α_i + β_i × T)

where T is the reaction temperature in °C, and (α_i, β_i) are reactor-
type-specific coefficients for each output *i*.

Sources
-------
TOD (thermal oxo-degradation):
    Olafasakin et al., Energy Fuels 2023, 37, 15832–15842.
    Single data point at 600 °C, 100 % HDPE, 93:7 HDPE/O₂.
    Correction anchored to zero at 400 °C (below which minimal vapour
    is available for oxidation) and extrapolated linearly.

Catalytic (zeolite / HZSM-5):
    Derived from the aston.xlsx literature database (566 experiments).
    Polyolefin rows split at >10 wt% total aromatics (catalytic, N≈70)
    vs ≤5 wt% (thermal, N≈120).  Additive deltas computed in two
    temperature bins (550-650 °C and 650-800 °C) and fit to a line.
"""

import numpy as np

# Output order (must match model.OUTPUT_NAMES indices)
#   0: Liquid
#   1: Gas
#   2: Solid
#   3: Gasoline range hydrocarbons
#   4: Diesel range hydrocarbons
#   5: Total aromatics (w%)
#   6: BTX (w%)
#   7: Wax (>C21)

# ============================================================================
# TOD correction  (additive wt%)
#   delta_i(T) = α_i + β_i × T
#   Anchored so delta(400 °C) = 0 for all outputs.
#   Measured at 600 °C from Olafasakin et al. 2023 Table S2.
# ============================================================================

_TOD_INTERCEPT = np.array([
    +7.00,    # Liquid
    -16.40,   # Gas
    -0.54,    # Solid
    -11.00,   # Gasoline
    -5.96,    # Diesel
    0.0,      # Aromatics
    0.0,      # BTX
    +24.00,   # Wax
], dtype=np.float64)

_TOD_SLOPE = np.array([
    -0.0175,   # Liquid
    +0.0410,   # Gas
    +0.00135,  # Solid
    +0.0275,   # Gasoline
    +0.0149,   # Diesel
    0.0,       # Aromatics
    0.0,       # BTX
    -0.0600,   # Wax
], dtype=np.float64)


# ============================================================================
# Catalytic correction  (additive wt%)
#   delta_i(T) = α_i + β_i × T
#   Fit to two temperature-bin midpoints (600 °C and 725 °C)
#   derived from aston.xlsx catalytic-vs-thermal comparison.
# ============================================================================

_CAT_INTERCEPT = np.array([
    +61.7,    # Liquid
    +76.7,    # Gas
    -36.1,    # Solid
    -13.5,    # Gasoline
    -6.8,     # Diesel
    +142.3,   # Aromatics
    -8.5,     # BTX
    -146.0,   # Wax
], dtype=np.float64)

_CAT_SLOPE = np.array([
    -0.1064,  # Liquid
    -0.0952,  # Gas
    +0.0512,  # Solid
    +0.0128,  # Gasoline
    -0.0048,  # Diesel
    -0.1672,  # Aromatics
    +0.0264,  # BTX
    +0.1816,  # Wax
], dtype=np.float64)


# ============================================================================
# Plasma correction
#   Calibrated so that at virtual_temperature=450 °C with HDPE=100 the
#   corrected categories reproduce Case G (CO2 plasma, tR=20 s) from
#   Radhakrishnan et al., Green Chem., 2024, 26, 9156-9175.
#
#   Phase totals (Liquid, Gas, Solid) and suppression categories
#   (Aromatics, BTX) use additive corrections:  corr = raw + α + β*T
#
#   Liquid sub-categories (Gasoline, Diesel, Wax) use multiplicative
#   scaling:  corr = raw × scale_factor.  This prevents negative values
#   when the ML model predicts different raw distributions for non-HDPE
#   feeds (LDPE, PP, PS).
#
#   Phase totals are NOT normalised to 100 % because CO2 mass
#   incorporation inflates the liquid fraction (total yields ≈130 %).
# ============================================================================

# Additive correction for phases and aromatics (indices 0,1,2,5,6)
_PLASMA_INTERCEPT = np.array([
    +29.61,   # Liquid  (boosted by CO2 incorporation → oxygenated products)
    +8.05,    # Gas     (CO-dominated)
    -1.61,    # Solid   (eliminated under plasma conditions)
    0.0,      # Gasoline (multiplicative, see _PLASMA_SCALES)
    0.0,      # Diesel   (multiplicative, see _PLASMA_SCALES)
    -2.15,    # Aromatics (suppressed — no catalyst, no aromatic selectivity)
    -1.59,    # BTX       (suppressed)
    0.0,      # Wax       (multiplicative, see _PLASMA_SCALES)
], dtype=np.float64)

_PLASMA_SLOPE = np.zeros(8, dtype=np.float64)

# Multiplicative scale factors for sub-categories (indices 3,4,7)
# Calibrated at HDPE=100, T=450: target / raw
_PLASMA_SCALES = np.array([
    1.0,      # Liquid  (additive)
    1.0,      # Gas     (additive)
    1.0,      # Solid   (additive)
    0.850,    # Gasoline: 13.1 / 15.42
    0.329,    # Diesel:   11.4 / 34.70
    1.0,      # Aromatics (additive)
    1.0,      # BTX       (additive)
    0.058,    # Wax:       3.1 / 53.23
], dtype=np.float64)


# ============================================================================
# Registry
# ============================================================================

_CORRECTIONS = {
    'thermal': None,       # No correction (base model)
    'TOD':     (_TOD_INTERCEPT, _TOD_SLOPE),
    'catalytic': (_CAT_INTERCEPT, _CAT_SLOPE),
}

REACTOR_TYPES = tuple(_CORRECTIONS.keys()) + ('plasma',)


def apply_correction(raw_wt_pct, temperature_C, reactor_type='thermal'):
    """Apply a reactor-type correction to the 8 raw ML outputs.

    Parameters
    ----------
    raw_wt_pct : array-like, shape (8,)
        Base ML predictions in wt% (Liquid, Gas, Solid, Gasoline,
        Diesel, Aromatics, BTX, Wax).
    temperature_C : float
        Reaction temperature in °C.
    reactor_type : str
        One of 'thermal', 'TOD', or 'catalytic'.

    Returns
    -------
    corrected : ndarray, shape (8,)
        Corrected wt% predictions, clamped to [0, 100].
    """
    raw = np.asarray(raw_wt_pct, dtype=np.float64)

    if reactor_type not in _CORRECTIONS:
        raise ValueError(
            f"Unknown reactor_type {reactor_type!r}. "
            f"Choose from {REACTOR_TYPES}"
        )

    coefs = _CORRECTIONS[reactor_type]
    if coefs is None:
        return np.clip(raw, 0.0, 100.0)

    intercept, slope = coefs
    delta = intercept + slope * temperature_C
    corrected = raw + delta

    # Clamp individual outputs to [0, 100]
    corrected = np.clip(corrected, 0.0, 100.0)

    # Renormalise phase totals (Gas + Liquid + Solid) to ~100 %
    phase_sum = corrected[0] + corrected[1] + corrected[2]
    if phase_sum > 0 and abs(phase_sum - 100.0) > 1.0:
        scale = 100.0 / phase_sum
        corrected[0] *= scale  # Liquid
        corrected[1] *= scale  # Gas
        corrected[2] *= scale  # Solid

    # Ensure sub-categories fit inside Liquid
    sub_total = corrected[3] + corrected[4] + corrected[5] + corrected[7]
    if sub_total > corrected[0] and sub_total > 0:
        sf = corrected[0] / sub_total
        corrected[3] *= sf   # Gasoline
        corrected[4] *= sf   # Diesel
        corrected[5] *= sf   # Aromatics
        corrected[6] *= sf   # BTX (scales with aromatics)
        corrected[7] *= sf   # Wax

    # Enforce BTX ≤ Aromatics
    corrected[6] = min(corrected[6], corrected[5])

    return np.clip(corrected, 0.0, 100.0)


def apply_plasma_correction(raw_wt_pct, temperature_C):
    """Apply plasma-specific correction to the 8 raw ML outputs.

    Phase totals (Liquid, Gas, Solid) and suppression categories
    (Aromatics, BTX) are shifted additively.  Liquid sub-categories
    (Gasoline, Diesel, Wax) are scaled multiplicatively so they remain
    positive for any feedstock composition.

    Unlike :func:`apply_correction`, this does **not** normalise
    Liquid + Gas + Solid to 100 %, because CO2 mass incorporation
    causes total yields to exceed 100 % of feedstock mass.

    Parameters
    ----------
    raw_wt_pct : array-like, shape (8,)
        Base ML predictions in wt%.
    temperature_C : float
        Virtual temperature in °C (the value fed to the ML model).

    Returns
    -------
    corrected : ndarray, shape (8,)
        Corrected wt% predictions, clamped to >= 0.
    """
    raw = np.asarray(raw_wt_pct, dtype=np.float64)

    # Additive correction for phases and aromatics
    delta = _PLASMA_INTERCEPT + _PLASMA_SLOPE * temperature_C
    corrected = raw + delta

    # Multiplicative correction for sub-categories (Gasoline, Diesel, Wax)
    for idx in (3, 4, 7):
        corrected[idx] = raw[idx] * _PLASMA_SCALES[idx]

    return np.clip(corrected, 0.0, None)
