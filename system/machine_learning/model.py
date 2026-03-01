"""
PyrolysisNet: Neural network for predicting pyrolysis product yields.

Predicts 8 product categories from feedstock composition and operating conditions.
Outputs are mapped to specific BioSTEAM compound IDs for reactor integration.

Reactor-type corrections (TOD, catalytic) are applied via linear additive
adjustments defined in ``corrections.py``.
"""

import os
import torch
import torch.nn as nn
import numpy as np

try:
    from .corrections import apply_correction, apply_plasma_correction, REACTOR_TYPES
except ImportError:
    from corrections import apply_correction, apply_plasma_correction, REACTOR_TYPES

# ============================================================================
# Model Architecture
# ============================================================================

class PyrolysisNet(nn.Module):
    """Feedforward neural network for pyrolysis yield prediction.

    Input (5): HDPE, LDPE, PP (wt%), Temperature (°C), VRT (s)
    Output (8): Liquid, Gas, Solid, Gasoline, Diesel, Total aromatics, BTX, Wax (wt%)
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 8),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x) * 100.0  # Scale to [0, 100] wt%


# ============================================================================
# Output column names (order matches model output indices)
# ============================================================================

OUTPUT_NAMES = [
    'Liquid',                       # y[0]
    'Gas',                          # y[1]
    'Solid',                        # y[2]
    'Gasoline range hydrocarbons',  # y[3]
    'Diesel range hydrocarbons',    # y[4]
    'Total aromatics (w%)',         # y[5]
    'BTX (w%)',                     # y[6]
    'Wax (>C21)',                   # y[7]
]


# ============================================================================
# Compound Mapping: ML Output → BioSTEAM Compound IDs
# ============================================================================

# Sub-distributions for each product category (must sum to 1.0 within each)
GAS_COMPOUNDS = {
    'H2': 0.02, 'CH4': 0.20, 'C2H4': 0.25,
    'C3H8': 0.25, 'C4H8': 0.15, 'CO': 0.05, 'CO2': 0.08,
}

GASOLINE_COMPOUNDS = {
    'C8H18': 0.35, 'C10H22': 0.35, 'C7H16': 0.15, 'C11H24': 0.15,
}

DIESEL_COMPOUNDS = {
    'C14H30': 0.40, 'C16H32': 0.35, 'C20H42': 0.25,
}

BTX_COMPOUNDS = {
    'C6H6': 0.30, 'C7H8': 0.40, 'C8H10': 0.30,
}

OTHER_AROMATICS_COMPOUNDS = {
    'C8H8': 0.40, 'C9H10': 0.30, 'C10H8': 0.30,
}

WAX_COMPOUNDS = {
    'C24H50': 0.60, 'C40H82': 0.40,
}


# ============================================================================
# Plasma-specific compound mapping
# ============================================================================

# CO2-derived reactive species shift gas composition to CO-dominated
PLASMA_GAS_COMPOUNDS = {
    'CO': 0.90, 'H2': 0.05, 'CH4': 0.03, 'C2H4': 0.02,
}

# Residual Liquid (liquid minus sub-categories) → oxygenated products
# Ratios from Case G: Alcohol 61.1, Acid 14.5, C14H22O 9.0
PLASMA_OXYGENATED_COMPOUNDS = {
    'Alcohol': 0.722, 'Acid': 0.171, 'C14H22O': 0.107,
}

# Non-oxidized liquid sub-categories use single surrogates
PLASMA_GASOLINE_COMPOUND = 'C8H18'
PLASMA_DIESEL_COMPOUND = 'C18H38'
PLASMA_WAX_COMPOUND = 'C30H62'

# Total yields ≈130% of feedstock mass due to CO2 incorporation
PLASMA_CO2_FACTOR = 1.298


# ============================================================================
# Model loading (cached)
# ============================================================================

_MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
_cached_model = None
_cached_scaler = None


def _ensure_loaded():
    """Load the trained model and scaler once, cache for reuse."""
    global _cached_model, _cached_scaler
    if _cached_model is not None:
        return _cached_model, _cached_scaler

    model_path = os.path.join(_MODEL_DIR, 'pyrolysis_model.pt')
    scaler_path = os.path.join(_MODEL_DIR, 'scaler_params.pt')

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"Model files not found. Run train.py first.\n"
            f"  Expected: {model_path}\n"
            f"  Expected: {scaler_path}"
        )

    _cached_scaler = torch.load(scaler_path, weights_only=True)
    _cached_model = PyrolysisNet()
    _cached_model.load_state_dict(torch.load(model_path, weights_only=True))
    _cached_model.eval()
    return _cached_model, _cached_scaler


# ============================================================================
# Raw prediction (8 wt% categories)
# ============================================================================

def predict_raw(hdpe, ldpe, pp, temperature, vrt, reactor_type='thermal'):
    """Predict the 8 product-category wt% values.

    Parameters
    ----------
    hdpe, ldpe, pp : float
        Feedstock weight percentages (0-100).
    temperature : float
        Reaction temperature in °C.
    vrt : float
        Vapor residence time in seconds.
    reactor_type : str
        ``'thermal'`` (base), ``'TOD'``, or ``'catalytic'``.

    Returns
    -------
    ndarray, shape (8,)
        [Liquid, Gas, Solid, Gasoline, Diesel, Aromatics, BTX, Wax] in wt%.
    """
    model, scaler = _ensure_loaded()

    raw = np.array([[hdpe, ldpe, pp, temperature, vrt]], dtype=np.float32)
    mean = scaler['mean'].numpy()
    scale = scaler['scale'].numpy()
    normalised = (raw - mean) / scale

    with torch.no_grad():
        x = torch.tensor(normalised, dtype=torch.float32)
        pred = model(x).squeeze().numpy()

    pred = np.clip(pred, 0.0, 100.0)

    if reactor_type != 'thermal':
        pred = apply_correction(pred, temperature, reactor_type)

    return pred


# ============================================================================
# Compound-level prediction
# ============================================================================

def _categories_to_compounds(pred):
    """Convert 8 category wt% to {compound_ID: mass_fraction} dict."""
    liquid_pct = pred[0]
    gas_pct = pred[1]
    solid_pct = pred[2]
    gasoline_pct = pred[3]
    diesel_pct = pred[4]
    total_aromatics_pct = pred[5]
    btx_pct = pred[6]
    wax_pct = pred[7]

    btx_pct = min(btx_pct, total_aromatics_pct)
    other_aromatics_pct = total_aromatics_pct - btx_pct

    compounds = {}

    # Gas → NCG compounds
    for cid, frac in GAS_COMPOUNDS.items():
        compounds[cid] = gas_pct * frac

    # Solid → Char
    compounds['Char'] = solid_pct

    # Sub-categories of liquid
    sub_total = gasoline_pct + diesel_pct + total_aromatics_pct + wax_pct

    if sub_total > liquid_pct and sub_total > 0:
        sf = liquid_pct / sub_total
        gasoline_pct *= sf
        diesel_pct *= sf
        btx_pct *= sf
        other_aromatics_pct *= sf
        wax_pct *= sf
    elif liquid_pct > sub_total:
        gasoline_pct += (liquid_pct - sub_total)

    for cid, frac in GASOLINE_COMPOUNDS.items():
        compounds[cid] = compounds.get(cid, 0) + gasoline_pct * frac
    for cid, frac in DIESEL_COMPOUNDS.items():
        compounds[cid] = compounds.get(cid, 0) + diesel_pct * frac
    for cid, frac in BTX_COMPOUNDS.items():
        compounds[cid] = compounds.get(cid, 0) + btx_pct * frac
    for cid, frac in OTHER_AROMATICS_COMPOUNDS.items():
        compounds[cid] = compounds.get(cid, 0) + other_aromatics_pct * frac
    for cid, frac in WAX_COMPOUNDS.items():
        compounds[cid] = compounds.get(cid, 0) + wax_pct * frac

    # Normalise to mass fractions summing to 1.0
    total = sum(compounds.values())
    if total > 0:
        compounds = {k: v / total for k, v in compounds.items()}
    else:
        compounds = dict(GAS_COMPOUNDS)

    return {k: v for k, v in compounds.items() if v > 1e-10}


def _plasma_categories_to_compounds(pred):
    """Convert 8 plasma-corrected category wt% to {compound_ID: mass_fraction}.

    The residual liquid (total Liquid minus Gasoline/Diesel/Aromatics/Wax)
    represents hydrocarbons oxidised by CO2-derived reactive species and is
    mapped to oxygenated products (Alcohol, Acid, C14H22O).

    Final mass fractions sum to ~PLASMA_CO2_FACTOR (≈1.30) because the
    extra mass comes from CO2.
    """
    liquid_pct = pred[0]
    gas_pct = pred[1]
    gasoline_pct = pred[3]
    diesel_pct = pred[4]
    aromatics_pct = pred[5]
    wax_pct = pred[7]

    compounds = {}

    # Gas → CO-dominated distribution
    for cid, frac in PLASMA_GAS_COMPOUNDS.items():
        compounds[cid] = gas_pct * frac

    # Non-oxidised liquid sub-categories → single surrogates
    compounds[PLASMA_GASOLINE_COMPOUND] = gasoline_pct
    compounds[PLASMA_DIESEL_COMPOUND] = diesel_pct
    compounds[PLASMA_WAX_COMPOUND] = wax_pct

    # Residual liquid → oxygenated products
    sub_total = gasoline_pct + diesel_pct + aromatics_pct + wax_pct
    residual = max(0.0, liquid_pct - sub_total)
    for cid, frac in PLASMA_OXYGENATED_COMPOUNDS.items():
        compounds[cid] = residual * frac

    # Normalise to sum=1.0, then scale by CO2 factor
    total = sum(compounds.values())
    if total > 0:
        compounds = {k: v / total * PLASMA_CO2_FACTOR
                     for k, v in compounds.items()}

    return {k: v for k, v in compounds.items() if v > 1e-10}


def predict_plasma(hdpe, ldpe, pp, temperature_C, vrt,
                   virtual_temperature=450):
    """Predict plasma reactor yields from feedstock and conditions.

    The ML model is queried at ``virtual_temperature`` (within its training
    range) rather than the actual reactor temperature.  A plasma-specific
    correction then shifts the predictions to match experimental data.

    Parameters
    ----------
    hdpe, ldpe, pp : float
        Feedstock weight percentages (0-100).
    temperature_C : float
        Actual reactor temperature in °C (unused for ML query, kept for API).
    vrt : float
        Vapor residence time in seconds.
    virtual_temperature : float
        Temperature fed to the ML model (default 450 °C).

    Returns
    -------
    dict[str, float]
        {compound_ID: mass_fraction} where fractions sum to ~1.30.
    """
    # Query ML model at virtual temperature (no correction — 'thermal')
    pred = predict_raw(hdpe, ldpe, pp, virtual_temperature, vrt, 'thermal')
    # Apply plasma-specific correction (no phase normalisation)
    pred = apply_plasma_correction(pred, virtual_temperature)
    return _plasma_categories_to_compounds(pred)


def predict(hdpe, ldpe, pp, temperature, vrt, reactor_type='thermal'):
    """Predict pyrolysis product yields from feedstock and conditions.

    Parameters
    ----------
    hdpe, ldpe, pp : float
        Feedstock weight percentages (0-100).
    temperature : float
        Reaction temperature in °C.
    vrt : float
        Vapor residence time in seconds.
    reactor_type : str
        ``'thermal'``, ``'TOD'``, ``'catalytic'``, or ``'plasma'``.

    Returns
    -------
    dict[str, float]
        {compound_ID: mass_fraction} where fractions sum to ~1.0
        (or ~1.30 for plasma due to CO2 incorporation).
    """
    if reactor_type == 'plasma':
        return predict_plasma(hdpe, ldpe, pp, temperature, vrt)
    pred = predict_raw(hdpe, ldpe, pp, temperature, vrt, reactor_type)
    return _categories_to_compounds(pred)
