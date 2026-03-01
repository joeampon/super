# %%
import thermosteam as tmo
from thermosteam import Chemical, Chemicals
from thermosteam.functional import rho_to_V
import sys

# %%
_cal2joule = 4.184  # auom('cal').conversion_factor('J')
chems = Chemicals([])


def add_chemical(ID, ref=None, **data):
    chemical = Chemical(ID, **data) if ref is None else ref.copy(ID, **data)
    chems.append(chemical)
    return chemical


##### Gases #####
O2 = add_chemical("O2", phase="g", Hf=0)
O2.Hf = 0
add_chemical("N2", phase="g", Hf=0)
add_chemical("C2H4",phase ="g")
add_chemical("C3H8",phase ="g")
add_chemical("H2", phase="g", Hf=0)
add_chemical("CH4", phase="g")
add_chemical("CO", search_ID="CarbonMonoxide", phase="g", Hf=-26400 * _cal2joule)
add_chemical("CO2", phase="g")
add_chemical("NO", search_ID="NitricOxide", phase="g")
add_chemical("NO2", phase="g")
NaOH = add_chemical("NaOH", phase='s')
# NaOH.Cn.g.add_method(55.57, Tmin=-20000, Tmax=50)

NaCl = add_chemical("NaCl")
# NaCl.Cn.g.add_method(55.57, Tmin=-20000, Tmax=50)

Glucose = add_chemical("Glucose", phase="s")
Glucose.default()
# Glucose.Cn.add_method(194.61181281968177, Tmin=-20000,Tmax=10)

Yeast = add_chemical(
    "Yeast",
    search_db=False,
    phase="s",
    formula="CH1.57O0.31N0.29S0.007",
    Hf=-17618 * _cal2joule,
)
Yeast.default()
# Yeast.Cn.add_method(0.0, Tmin=-20000, Tmax=10)

Tryptone = add_chemical(
    "Tryptone",
    search_db=False,
    phase="s",
    formula="CH1.57O0.31N0.29S0.007",
    Hf=-17618 * _cal2joule,
)
Tryptone.default()
# Tryptone.Cn.add_method(0.0, Tmin=-20000, Tmax=10)

Innoculum = add_chemical(
    "Innoculum",
    search_db=False,
    phase="s",
    formula="CH1.57O0.31N0.29S0.007",
    Hf=-17618 * _cal2joule,
)
Innoculum.default()
# Innoculum.Cn.add_method(0.0, Tmin=-20000, Tmax=10)
# Protein.default()
# Enzyme = add_chemical('Enzyme', search_db=False, phase='l',
#                         formula='CH1.59O0.42N0.24S0.01', Hf=-17618*_cal2joule)
# Enzyme.default()

# Properties of fermentation microbes copied from Z_mobilis as in ref [1]
# FermMicrobe = add_chemical('FermMicrobe', search_db=False, phase='l', formula='CH1.8O0.5N0.2', Hf=-31169.39*_cal2joule)
# FermMicrobe.default()

Water = add_chemical("Water")
# Water.Cn.g.add_method(33.26, Tmin=-20000, Tmax=50)
LacticAcid = add_chemical("LacticAcid", Hfus=11340, phase="l", Hf=0)

# Polymer = add_chemical('Polymer', search_db=False, phase='s', MW=1, Hf=0, HHV=0, LHV=0)
# Polymer.Cn.add_model(evaluate=0, name='Constant')
# Polymer.default()

##### Oil Products #####
olefins = add_chemical("C8H18")
paraffins = add_chemical("C18H38")
alcohols = add_chemical("Alcohol", search_ID="112-53-8")
acids = add_chemical("Acid", search_ID="68603-87-2")
carbonyl = add_chemical("C14H22O")  # C10 to C18
C11H24 = add_chemical("C11H24")
C30H62 = add_chemical("C30H62")

paraffins.Cn.g.add_method(paraffins.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
olefins.Cn.g.add_method(olefins.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
alcohols.Cn.g.add_method(alcohols.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
acids.Cn.g.add_method(acids.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
carbonyl.Cn.g.add_method(carbonyl.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
C11H24.Cn.g.add_method(C11H24.Cn.g(T=273.15), Tmin=-20000, Tmax=10)
C30H62.Cn.g.add_method(C30H62.Cn.g(T=273.15), Tmin=-20000, Tmax=10)

# C6H4Cl2 = add_chemical('C6H4Cl2', search_ID='106-46-7')
# Benzene = add_chemical('Benzene', search_ID='71-43-2')
# Toluene = add_chemical('Toluene', search_ID='108-88-3')
# oXylene = add_chemical('oXylene', search_ID='95-47-6')
# pXylene = add_chemical('pXylene', search_ID='106-42-3')
# EthylBenzene = add_chemical('EthylBenzene', search_ID='100-41-4')
# C11H24 = add_chemical('C11H24')
# Propylene = add_chemical('Propylene', search_ID='108-32-7')
# Ethanol = add_chemical('Ethanol', search_ID='64-17-5')
# AceticAcid = add_chemical('AceticAcid', search_ID='64-19-7')
# Aldehyde = add_chemical('Aldehyde', search_db=False, phase='s', MW=30.07, Hf=0, HHV=0, LHV=0)
# Aldehyde.Cn.add_model(evaluate=0, name='Constant')
# Aldehyde.default()


##### Solids #####

PLA = add_chemical("PLA", search_ID="26100-51-6", phase="s")
PHA = add_chemical("PHA", search_ID="26100-51-6", phase="s")
Cell = add_chemical("Cell", search_ID="26100-51-6", phase="s")

# PLA.Cn.add_method(PLA.Cn(T=273.15), Tmin=-20000, Tmax=10)
# PHA.Cn.add_method(PHA.Cn(T=273.15), Tmin=-20000, Tmax=10)
# Cell.Cn.add_method(PHA.Cn(T=273.15), Tmin=-20000, Tmax=10)

# PHA.copy_models_from(PLA)

Plastic = add_chemical(
    "Plastic",
    search_ID="9002-88-4",
    phase="s",
    Hf=C30H62.Hf,
    HHV=C30H62.HHV,
    LHV=C30H62.LHV,
)
Ash = add_chemical("Ash", search_ID="SiO", phase="s")
Ash.default()
ZnO = add_chemical("ZnO", phase="s")
ZnO.default()
# ZnO.Cn.add_method(ZnO.Cn(T=273.15), Tmin=-20000, Tmax=10)
# ZnO.V.l.add_method(1.4537142857142902e-05)
HCl = add_chemical("HCl", phase="g")
SO2 = add_chemical("SO2", phase="g")
Lime = add_chemical("Lime", phase="s")
CaSO4 = add_chemical("CaSO4", phase="s")

for c in chems:
    if c.Sfus == None:
        c.Sfus = 0
        
tmo.settings.set_thermo(chems)

# return chems

# create_chemicals()
h3op = Water.copy("H3Op")
# %%
sys.path
# # %%
# boiling_points = {}
# for c in chems:
#     if c.Tb:
#         boiling_points[c.ID] = c.Tb
# sorted_bps = sorted(boiling_points.items(), key=lambda x: x[1])
# for k,v in reversed(sorted_bps):
#     print(k,v)
# %%
# Boiling points
# NaCl 1738.15
# NaOH 1661.15
# Glucose 844.68
# C30H62 724.15
# C18H38 589.15
# C14H22O 552.15
# Acid 546.15
# Alcohol 537.25
# Cell 505.49
# PHA 505.49
# PLA 505.49
# LacticAcid 505.49
# C11H24 448.0
# C8H18 391.35
# Water 373.124295848
# NO2 251.8
# C3H8 231.03624791
# CO2 194.67
# Plastic 169.378648434
# C2H4 169.378648434
# NO 121.41
# CH4 111.667205474
# O2 90.1878078805
# CO 81.6381829183
# N2 77.3549950205
# H2 20.3689085101   