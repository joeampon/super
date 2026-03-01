"""
Unified chemical compounds for the superstructure optimization.

Merges all chemicals needed by TOD, PLASMA, CPY, HC, FCC, and DISTILLATION
into a single Chemicals object so all subsystems share one thermo context.
"""

import math
import biosteam as bst
import thermosteam as tmo
from thermosteam import Chemical, Chemicals

_cal2joule = 4.184

compounds = Chemicals([])


def add_chemical(ID, ref=None, **data):
    chemical = Chemical(ID, **data) if ref is None else ref.copy(ID, **data)
    compounds.append(chemical)
    return chemical


# ============================================================================
# Gases
# ============================================================================
add_chemical('O2', phase='g')
add_chemical('NO', phase='g')
add_chemical('N2', phase='g')

# ============================================================================
# Non-condensable gas (NCG) compounds
# ============================================================================
add_chemical('CO')
add_chemical('H2', phase='g')
add_chemical('CH4', phase='g')
add_chemical('C2H4')
add_chemical('C3H8')
add_chemical('C4H8')
# FCC additional NCG
add_chemical('C4H6')
add_chemical('C5H12')
add_chemical('C6H14')
add_chemical('C6H12')
add_chemical('C4H10')
add_chemical('C7H14')
add_chemical('C5H10')

# ============================================================================
# Naphtha-range compounds
# ============================================================================
add_chemical('C9H18')
add_chemical('C11H24')
add_chemical('C12H26')
add_chemical('C10H22')
add_chemical('C8H18')
add_chemical('C7H16')
add_chemical('C8H16', search_ID='1-octene')
add_chemical('C10H20')
add_chemical('C12H24')

# ============================================================================
# Diesel-range compounds
# ============================================================================
add_chemical('C14H28')
add_chemical('C14H30')
add_chemical('C16H32')
add_chemical('C15H30')
add_chemical('C20H42')
add_chemical('C20H40')

# ============================================================================
# Aromatics (FCC pathway)
# ============================================================================
add_chemical('C7H8')    # Toluene
add_chemical('C8H10')   # Ethylbenzene / Xylene
c6h6 = add_chemical('C6H6')    # Benzene
add_chemical('C8H8')    # Styrene
add_chemical('C9H10')   # Methylstyrene
c9h12 = add_chemical('C9H12')  # isoPropylBenzene
c9h12.copy_models_from(compounds['C7H8'])
add_chemical('C10H8')   # Naphthalene
c12h16 = add_chemical('C12H16')
c12h16.copy_models_from(compounds['C10H8'])
c12h16.Tb = 493

# ============================================================================
# Wax-range compounds
# ============================================================================
add_chemical('C24H50')
add_chemical('C40H82')

# ============================================================================
# Plasma-specific oil products
# ============================================================================
c18h38 = add_chemical('C18H38')
c30h62 = add_chemical('C30H62')
alcohols = add_chemical('Alcohol', search_ID='112-53-8')
acids = add_chemical('Acid', search_ID='68603-87-2')
add_chemical('C14H22O')

# ============================================================================
# Other compounds
# ============================================================================
add_chemical('water')
add_chemical('NH3')
add_chemical('HF')
add_chemical('C7H14O2')
add_chemical('CO2', phase='g')
add_chemical('NO2', phase='g')
add_chemical('SO2', phase='g')
add_chemical('HCl', phase='g')
add_chemical('H2S')
add_chemical('S')

# ============================================================================
# Solids / Feed materials
# ============================================================================
HDPE = add_chemical('HDPE', search_ID='heptacontane', phase='s')
LDPE = add_chemical('LDPE', search_ID='hexatriacontane', phase='s')  # C36H74 surrogate
PP = add_chemical('PP', search_ID='dotriacontane', phase='s')        # C32H66 surrogate
PS = add_chemical('PS', search_ID='C8H8')
Plastic = add_chemical(
    'Plastic', search_ID='9002-88-4', phase='s',
    Hf=c30h62.Hf, HHV=c30h62.HHV, LHV=c30h62.LHV,
)
add_chemical('Ash', search_ID='CaO', phase='s')
add_chemical('Char', search_ID='C', phase='s')
add_chemical('C', search_ID='C', phase='s')   # CPY carbon solid
add_chemical('Sand', search_ID='SiO2', phase='s')
add_chemical('Lime', phase='s')
add_chemical('CaSO4', phase='s')

# ============================================================================
# Catalysts
# ============================================================================
zeolite = add_chemical('Zeolite', search_ID='Al2O5Si', phase='s', HHV=0, Hf=0)
nickel = add_chemical('Nickel_catalyst', search_ID='Nickel', phase='s', HHV=0, Hf=0)
zinc_ox = add_chemical('ZnO', search_ID='ZnO', phase='s', HHV=0, Hf=0)
zeolite.copy_models_from(zinc_ox)
Catalyst = add_chemical('Catalyst', search_ID='Al2O5Si', phase='s', HHV=0, Hf=0)
Catalyst.copy_models_from(zeolite)

# ============================================================================
# Refrigerants
# ============================================================================
add_chemical('Tetrafluoroethane')
add_chemical('Ethane')
add_chemical('Propene')
add_chemical('Propane')
add_chemical('Methane')

# ============================================================================
# CPY-specific
# ============================================================================
add_chemical('Polyethylene', search_ID='C2H4')

# ============================================================================
# Finalise: set defaults and thermo
# ============================================================================
for c in compounds:
    c.default()

# --- Pre-compilation property fixes ---

# Catalyst boiling points (prevent VLE issues)
compounds['Zeolite'].Tb = 2000
compounds['ZnO'].Tb = 2000
compounds['Catalyst'].Tb = 2000

# Fix incorrect Tb for wax surrogate C24H50 (n-tetracosane).
# BioSTEAM's default Tb ≈ 481 K is too low (correct: 391 °C = 664 K).
# Without this fix, the diesel/wax distillation LHK pair is inverted
# because C24H50 Tb < C14H30 Tb, causing separation failures.
compounds['C24H50'].Tb = 664.0

# Global Sfus fix (must be before compilation)
for c in compounds:
    if c.Sfus is None:
        c.Sfus = 0

tmo.settings.set_thermo(compounds)

# --- Post-compilation fixes ---

# Fix Sfus inside compiled entropy functors (gas and liquid)
for c in compounds:
    if hasattr(c, 'S'):
        for phase_attr in ('g', 'l'):
            phase_model = getattr(c.S, phase_attr, None)
            if phase_model is not None and hasattr(phase_model, '__dict__'):
                if 'Sfus' in phase_model.__dict__ and phase_model.__dict__['Sfus'] is None:
                    phase_model.__dict__['Sfus'] = 0.0

# --- Post-thermo Cn model extensions ---

# C6H6 Cn low-T model extensions
c6h6.Cn.l.add_method(c6h6.Cn('l', T=278, P=101325))
c6h6.Cn.g.add_method(c6h6.Cn('g', T=278, P=101325), Tmin=-1000)

# PS Cn low-T model extensions
PS.Cn.l.add_method(PS.Cn('l', T=278, P=101325))
PS.Cn.g.add_method(PS.Cn('g', T=278, P=101325), Tmin=-1000)

# Light-gas Cn low-T extensions (prevent solver divergence in mixers)
for chem_id in ['CO', 'H2', 'CH4', 'C2H4', 'C3H8', 'C4H8', 'CO2', 'N2', 'O2']:
    c = compounds[chem_id]
    try:
        val = c.Cn.g(T=68.2)
        c.Cn.g.add_method(val, Tmin=-200000, Tmax=68)
    except Exception:
        pass

# Plasma oil products Cn low-T extensions
for chem_id in ['C18H38', 'C30H62', 'C11H24', 'C8H18']:
    c = compounds[chem_id]
    c.Cn.g.add_method(c.Cn.g(T=273.15), Tmin=-20000, Tmax=10)

for chem_id in ['Alcohol', 'Acid', 'C14H22O']:
    c = compounds[chem_id]
    c.Cn.g.add_method(c.Cn.g(T=273.15), Tmin=-20000, Tmax=10)

# ============================================================================
# Utility Agents (high-T heating, sub-zero cooling)
# ============================================================================
Gas_utility = bst.UtilityAgent(
    ID='steam_high_T', phase='g', T=1000, P=101325.0,
    T_limit=1200, heat_transfer_price=1.32e-05,
    regeneration_price=0, heat_transfer_efficiency=0.9,
    water=1,
)

Liq_utility = bst.UtilityAgent(
    ID='super_hot_water', phase='l', T=75, P=101325.0 * 3,
    T_limit=1200, heat_transfer_price=1.32e-05,
    regeneration_price=0, heat_transfer_efficiency=0.9,
    water=1,
)

NH3_utility = bst.UtilityAgent(
    ID='ammonia', phase='l', T=0, P=101325.0 * 3,
    T_limit=1200, heat_transfer_price=1.32e-05,
    regeneration_price=0, heat_transfer_efficiency=0.9,
    water=1,
)
