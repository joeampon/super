# %%

import biosteam as bst
import thermosteam as tmo
from thermosteam import Chemical, Chemicals
from thermosteam.functional import rho_to_V
import math

_cal2joule = 4.184 # auom('cal').conversion_factor('J')
compounds = Chemicals([])


def add_chemical(ID, ref=None, **data):
    chemical = Chemical(ID, **data) if ref is None else ref.copy(ID, **data)
    compounds.append(chemical)
    return chemical

chemical_groups = dict(
    InsolubleSolids = ['Ash', 'Char', 'Sand'],
    gases = ['O2','NO','N2'],
    NCG_compounds = ['CO', 'H2', 'CH4', 'C2H4','C3H8','C4H8','C4H6','C5H12','C6H14','C6H12','C4H10','C7H14','C5H10'], 
    napthaRange_compounds = ['C9H18','C11H24','C12H26','C10H22','C8H18','C7H16','C8H16','C10H20','C12H24'],
    dieselRange_compounds = [ 'C14H28','C14H30','C16H32','C15H30','C20H42','C20H40'],
    waxRange_compounds = ['C24H50', 'C40H82'],
    others = ['water','NH3', 'HF','C7H14O2'],
    aromatics = ['C7H8', 'C8H10','C6H6','C8H8','C9H10','C9H12','C10H8','C12H16']
  
)

# test = tmo.Chemical('heptacontane')
# test

####Add all  Gases #####

for gas in chemical_groups['gases']:
    c = add_chemical(gas, phase='g')
    
for gas in chemical_groups['NCG_compounds']:
    add_chemical(gas)
    
#### Add all naptha_range compounds ####
for comp in chemical_groups['napthaRange_compounds']:
    add_chemical(comp)

#### Add all naptha_range compounds ####
for comp in chemical_groups['dieselRange_compounds']:
    add_chemical(comp)
    
### Add all aromatics ####
for comp in chemical_groups['aromatics']:
    add_chemical(comp)
#### Add all wax range compounds ####
for comp in chemical_groups['waxRange_compounds']:
    add_chemical(comp)
    
for comp in chemical_groups['others']:
    add_chemical(comp)
#### Add solids ####
add_chemical("HDPE", search_ID="heptacontane", phase="s")    #Assumption: Represent plastics with heptacontane C70H144

add_chemical('Ash', search_ID='CaO', phase='s')   #Work on the details later 
add_chemical('Char', search_ID='C', phase='s')  #Work on the details later
add_chemical('Sand', search_ID='SiO2', phase='s')  #Work on the details later
add_chemical ('CO2', search_ID='CO2', phase='g')  #Work on the details later

### Add catalysts ####
zeolite = add_chemical('Zeolite', search_ID='Al2O5Si', phase='s',HHV = 0, Hf = 0)  #Work on the details later
nickel = add_chemical('Nickel_catalyst', search_ID='Nickel', phase='s',HHV = 0, Hf = 0)  #Using H2 because its cost is calculated based on the H2 production capacity
zinc_ox = add_chemical('ZnO', search_ID='ZnO', phase='s',HHV = 0, Hf = 0)  #Work on the details later
zeolite.copy_models_from(zinc_ox)

Catalyst = add_chemical('Catalyst', search_ID='Al2O5Si', phase='s',HHV = 0, Hf = 0)  #Work on the details later
Catalyst.copy_models_from(zeolite)

### Add refrigerants ###
Tetrafluoroethane = add_chemical('Tetrafluoroethane', search_ID="Tetrafluoroethane")  #Work on the details later
ethane_ref = add_chemical('Ethane', search_ID="Ethane")  #Work on the details later
propene_ref = add_chemical('Propene', search_ID="Propene")  #Work on the details later
propane_ref = add_chemical('Propane', search_ID="Propane")  #Work on the details later
methane_ref = add_chemical('Methane', search_ID="Methane")  #Work on the details later




compounds["Zeolite"].Tb = 2000
compounds["ZnO"].Tb = 2000
compounds["C24H50"].Sfus = 0

# compounds["C12H16"].Tb = 2000

# --- Yaw correlation parameters ---
# Valid for 380.39 K to 521.39 K (107.24 °C to 248.24 °C)
yaw_A = 1.57050e+01
yaw_B = -4.49734e+03
yaw_C = -8.86800e+01

# Lambda function for Psat (N/m^2 or Pa) using Yaw correlation
# T must be in Kelvin
# Conversion: kPa to N/m^2 (Pa) is * 1000
psat_yaw = lambda T: math.exp(yaw_A + yaw_B / (T + yaw_C)) * 1000

# --- KDB Vap correlation parameters ---
# Valid for 280.14 K to 744.00 K (6.99 °C to 470.85 °C)
kdb_A = 1.08191e+02
kdb_B = -1.15507e+04
kdb_C = -1.31757e+01
kdb_D = 4.30979e-06

# Lambda function for Psat (N/m^2 or Pa) using KDB Vap correlation
# T must be in Kelvin
# Conversion: kPa to N/m^2 (Pa) is * 1000
psat_kdb = lambda T: (math.exp(kdb_A + kdb_B / (T + kdb_C) + kdb_D * T)) * 1000

compounds["C12H16"].copy_models_from(compounds["C10H8"])  # Copying models from naphthalene
compounds["C12H16"].Tb = 493



tmo.settings.set_thermo(compounds)

for c in compounds:
    if c.Sfus is None:
        c.Sfus = 0


'''
import thermosteam as tmo
from thermosteam import Chemical, Chemicals
from thermosteam.functional import rho_to_V
from thermo import SRK
_cal2joule = 4.184 # auom('cal').conversion_factor('J')


chemical_groups = dict(
    InsolubleSolids = ['Ash', 'Char', 'Sand'],
    NCG_compounds = ['CO', 'CO2', 'H2', 'CH4', 'C2H6', 'C2H4', 'C3H8', 'C3H6'], 
    napthaRange_compounds = ['C4H8', 'C6H6', 'C8H18', 'C10H8'],
    dieselRange_compounds = ['C10H22', 'C14H30', 'C17H36'],
    waxRange_compounds = ['C22H46', 'C24H50', 'C40H82']
)

chemical_groups['InsolubleSolids']

def add_chemical(ID,ref=None,**data):
    chemical = Chemical(ID,**data) if ref is None else ref.copy(ID,**data)
    compounds.append(chemical)
    return chemical
    


solids = (chemical_groups['InsolubleSolids'])

# Learn to model HDPE and char

compounds = Chemicals([Chemical("O2"),Chemical("N2"),Chemical("CO"),
                        Chemical("CO2"),Chemical("H2"), Chemical("CH4"),
                        Chemical("C2H6"),Chemical("C2H4"),Chemical("C3H8"),
                        Chemical("C3H6"),Chemical("C4H8"),Chemical("C6H6"),
                        Chemical("C8H18"),Chemical("C10H8"),Chemical("C10H22"),
                        Chemical("C14H30"),Chemical("C17H36"),Chemical("C17H36"),
                        Chemical("C22H46"),Chemical("C24H50"),Chemical("C40H82"),
                        Chemical("H2O")
                        ])


# USe Heptacontae C70H142 as HDPE and Carbon for char for a start

add_chemical('HDPE', search_ID='heptacontane')

##### Insoluble organics #####
# Holmes, Trans. Faraday Soc. 1962, 58 (0), 1916–1925, abstract
# This is for auto-population of combustion reactions
add_chemical('Ash', search_ID='CaO', phase='s', Hf=-151688*_cal2joule, HHV=0, LHV=0)
add_chemical('Char', search_ID='CaO', phase='s', Hf=-151688*_cal2joule, HHV=0, LHV=0)
add_chemical('Sand', search_ID='CaO', phase='s', Hf=-151688*_cal2joule, HHV=0, LHV=0)
'''







# %%
