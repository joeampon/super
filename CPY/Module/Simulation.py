#%%
import biosteam as bst 
import sys 
import numpy as np
import pandas as pd
sys.path.append('./Module/')

from _pyrolyzer import *
from _compounds import *
from _feed_handling import *
from _grinder import *
from _chscreen import *
from _cyclone import *
from _compressor import *
from _utilityagents import *
from _tea import *

from _sankeys import sankeys, sankeys_energy

import matplotlib.pyplot as plt
import matplotlib
plt.style.use("seaborn-v0_8")
matplotlib.rcParams.update({'font.size': 14})

bst.nbtutorial()
bst.settings.CEPCI = 800 # CEPCI 2024

bst.preferences.update(flow='t/d', T='degK', P='Pa', N=100, composition=False)


# prices
prices ={
    "PS": 1.50, # $/kg   https://businessanalytiq.com/procurementanalytics/index/polystyrene-ps-price-index/
    "styrene": 1.33, # $/kg https://businessanalytiq.com/procurementanalytics/index/styrene-price-index/
    "toluene": 0.97*0.8, # $/kg https://businessanalytiq.com/procurementanalytics/index/toluene-price-index/
    "benzene": 0.96*0.8, # $/kg https://businessanalytiq.com/procurementanalytics/index/benzene-price-index/
    "ethylbenzene": 1.08*0.8, # $/kg https://medium.com/intratec-products-blog/ethylbenzene-prices-latest-historical-data-in-several-countries-429afa8ae173
    "xylene": 0.76, # $/kg TR Brown et al. 2012. DOI: 10.1002/bbb.344
    "Ethylene": 0.61, # Gracida Al
    "Propylene": 0.97*0.8, # $/kg
    "NG": 7.40 * 1000 * 1.525/28316.8, 
    "Fresh catalyst": 15.5 * 2.20462262,
    "Hydrogen plant catalyst": 3.6/885.7,      #3.6 /1000scf/28.317m3/885.71kg 2007 quote from Jones et al. 2009 PNNL report SRI international 2007
    "Hydrogen": 2.83,      #2.83 USD/kg from Gracida Alvarez et al. 2.1 from Borja Hernandez et al. 2019
    "Hydrotreating catalyst": 15.5 * 2.20462262,      #15.5 $/lb from Li et al. 2017 PNNL report SRI international 2007
    "Fluid catalytic cracking catalyst": 15.5 * 2.20462262, # 15.5 $/lb from Li et al. 2016
}
bst.settings.electricity_price = 0.062 # Li et al. 2
#%%
cpy = {"Technology":"CPY", "catalytic": "No", "Hydrotreating": "No", "Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"high"}
cpy_ht = {"Technology":"CPY", "catalytic":"No", "Hydrotreating": "Yes", "Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" : "high"}
tcp = {"Technology":"TCP", "catalytic": "Yes","Hydrotreating": "No",  "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"high"}
tcp_ht = {"Technology":"TCP", "catalytic": "Yes","Hydrotreating": "Yes", "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"high"}

scenarios = [cpy,cpy_ht,tcp,tcp_ht]
scenarios_labels = ["CPY","CPY-HT","TCP","TCP-HT"]
plant_capacity = 250 # tonnes per day
capacity = plant_capacity
scenario = scenarios[3]
irr = 0.1
#%%
#%%
def create_sys(reactorT):
    bst.main_flowsheet.clear()
    bst.main_flowsheet.set_flowsheet('PS_flowsheet')
    capacity = 250
    feed = bst.Stream('PS_Feed',
                        PS=1,
                        units='kg/hr',
                        T=298)
    feed.set_total_flow(capacity, 'tonnes/day')
    feed.price = prices["PS"]


    pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen',O2=1,units='kg/hr',T=298,price=0.000)
    oxygen_mass = 0.07 * capacity * 100/93   # 7% equivalence ratio from Polin et al. 2019
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    fluidizing_gas = bst.Stream('fluidizing_gas',N2=1,units='kg/hr',T=298,price=0.000)
    fluidizing_gas_mass = 15   # fluidizing gas is 20kg/hr for now
    fluidizing_gas.set_total_flow(fluidizing_gas_mass, 'kg/hr')

    hydrotreat_hydrogen = bst.Stream('Hydrogen',H2=1,units='kg/hr',T=298, price=prices["Hydrogen"])
    hydrotreat_hydrogen_mass = 15
    hydrotreat_hydrogen.set_total_flow(hydrotreat_hydrogen_mass, 'kg/hr')

    recycle = bst.Stream('recycle')
    CRPS = bst.Stream('CRPS')
    char_sand = bst.Stream('CharSand')
    HT_Oil = bst.Stream('HT_Oil')

    ### pretreatment unit
    handling = Feed_handling('Handling', ins=[feed, recycle], outs=("FeedHandling"))
    # handling = bst.units.Mixer('Handling', ins=[feed], outs=["HandlingO"])
    M1 = bst.units.Mixer('Mixer_1', ins =[handling-0])
    grinder = Grinder('Grinder', ins=[M1-0], outs =("grinderout"))
    CHscreen = Screen("CHScreen", ins=[grinder-0], outs=[CRPS])

    mixer_pyrolyzer = bst.Mixer('Mixer_pyrolyzer',ins=[CRPS,fluidizing_gas,pyrolysis_oxygen])


    reactor = bst.units.Pyrolyzer('Pyrolyzer', ins=[mixer_pyrolyzer-0], outs= ('PyrolyzerO'), T=reactorT, P=101325)
    Cyclone = bst.units.Cyclone('Cyclone0', ins= (reactor-0), outs= ['oil_Gas', char_sand], efficiency=0.99)
    cooler1 = bst.units.HXutility('cooler', ins=[Cyclone-0], outs=('coolerOil'), T=273.15 +10, rigorous=False)
    F0 = bst.units.Flash('F0', ins=cooler1-0, T=273.15 +10, P=101325, outs=('F0gas', 'F0oil')) #Check flash temperature
    F0.reset_cache()

    Pump1 = bst.units.Pump('Pump1', ins=[F0-1], P=25 * 101325)

    ### Products Separation
    F1 = bst.units.Flash('F1o', ins=Pump1-0, T=285, P=101325, outs=('F1ogas', 'F1ooil'))
    F1.reset_cache()


    D1 = bst.units.BinaryDistillation(
        'D1', 
        ins=F1.outs[1], 
        outs=['BenzeneD1', 'TolueneD1'],
        LHK=('C6H6', 'C7H8'), 
        y_top=0.90, 
        x_bot=0.10,
        k=2.2,
        P=101325
    )

    D2 = bst.units.BinaryDistillation(
        'D2', 
        ins=D1-1, 
        outs=['TolueneD2', 'XyleneD2'],
        LHK=('C7H8','C8H18'), 
        product_specification_format='Recovery',
        Lr=0.95, 
        Hr=0.95,
        k=2.2, 
        P=101325
    )
    # D2.outs[1].price = prices["xylene"]
    # D2.check_LHK = False 

    D3 = bst.units.BinaryDistillation(
        'D3', 
        ins=D2-1, 
        outs=['Aromatics', 'XyleneD3'],
        LHK=('C8H18','C8H10'), 
        y_top=0.95, 
        x_bot=0.05,
        k=2.2, 
        P=101325
    )
    D3.outs[0].price = prices["ethylbenzene"]

    D4 = bst.units.BinaryDistillation(
        'D4',
        ins=D3-1,
        outs=['XyleneD4', ''],
        LHK=('C8H10', 'PS'),
        product_specification_format='Recovery',
        Lr=0.95,
        Hr=0.95,
        k=2.2,
        P=101325
    )
    D4._design = lambda: None
    D4._cost = lambda: None
    D4.outs[0].price = prices["xylene"]
    D4.outs[1].price = prices["PS"]
    
    D4.purchase_costs = {}
    D4.purchase_costs['Distillation column']=320257.691

    cooler2 = bst.units.HXutility('coolerD1', 
        ins=D1-0, 
        outs=('BenzeneO'), 
        T=298.15,
        rigorous=True
    )
    cooler2.outs[0].price = prices["benzene"]

    cooler3 = bst.units.HXutility('coolerD2',
        ins=D2-0,
        outs=('TolueneO'),
        T=298.15,
        rigorous=True
    )
    cooler3.outs[0].price = prices["toluene"]

    cooler4 = bst.units.HXutility('coolerD3',
        ins=D3-0,
        outs=('AromaticsO'),
        T=298.15,
        rigorous=True
    )
    cooler4.outs[0].price = prices["benzene"]

    cooler5 = bst.units.HXutility('coolerD4',
        ins=D4-0,
        outs=('XyleneO'),
        T=298.15,
        rigorous=True
    )
    cooler5.outs[0].price = prices["xylene"]

    cooler6 = bst.units.HXutility('coolerD5',
        ins=D4-1,
        outs=('PSO'),
        T=298.15,
        rigorous=True
    )
    cooler6.outs[0].price = prices["PS"]

    turbogenerator_mixer = bst.units.Mixer('Turbogenerator_mixer', ins=[F0-0, F1-0])

#     [1] Gas feed that will be burned.
# [2] Make-up water.
# [3] Natural gas to satisfy steam and power requirement.
# [4] Lime for flue gas desulfurization.
# [5] Boiler chemicals.

    btg_fuel = bst.Stream('boiler_turbogenerator_fuel', NG=1, T=298.15, P=101325)
    btg_water = bst.Stream('boiler_turbogenerator_water', T=298.15, P=101325)
    btg_ng = bst.Stream('boiler_turbogenerator_ng', NG=1, T=298.15, P=101325)
    btg_lime = bst.Stream('boiler_turbogenerator_lime', T=298.15, P=101325)
    btg_chemicals = bst.Stream('boiler_turbogenerator_chemicals', T=298.15, P=101325)

    turbogenerator = bst.BoilerTurbogenerator('Turbogenerator', ins=(
        btg_fuel,
        turbogenerator_mixer-0,
        btg_water,
        btg_ng,
        btg_lime,
        btg_chemicals))

    sys = bst.main_flowsheet.create_system('PS_sys')
    return sys
#%%
# sys.save_report
# sys.diagram(2, filename="diagram.png")
#%%
# sys.N_runs = 1
sys = create_sys(500 + 273.15)
sys.reset_cache()
sys.empty_recycles()
# sys.maxiter = 500
try:
    sys.converge()
except:
    sys.converge()
bst.main_flowsheet.diagram(format='png')
# reactor.show(composition=False,flow='kmol/hr')
#%%
# sys.diagram()
# sankeys(sys, filename="sankey.png")
#%%

# sankeys_energy(sys, filename="sankey_energy.png")
#%%
streams = [
    "PS_Feed",
    "PyrolyzerO",
    "Aromatics",
    "PSO", 
    "F0gas",
    "CharSand",
    "BenzeneD1",
    "TolueneD2",
    "XyleneD4"
]

chemicals = [
    "PS",
    "C6H6",
    "C7H8",
    "C8H10",
    "C8H18",
    "H2",
    "CO2",
    "CH4",
    "C"
]

data = {}
for stream in streams:
    data[stream] = {}
    for chemical in chemicals:
        data[stream][chemical] = sys.flowsheet.stream[stream].imass[chemical]/sys.flowsheet.stream["PS_Feed"].F_mass

compositionDF = pd.DataFrame(data)
compositionDF.T.plot(kind="bar", stacked=True)
plt.ylabel("Key Stream Composition\n(kg/kg polystyrene feed)")
plt.legend(title="Chemical", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.grid(True, axis="y")

# plt.savefig("product_yields.png", dpi=300, bbox_inches="tight")
plot_product_yields = plt.gcf()
plt.close()

#%%
# Pyrolysis Reactor Temperature Sensitivity
streams = [
    "PS_Feed",
    "PyrolyzerO",
    "Aromatics",
    "PSO",
    "F0gas",
    "CharSand",
    "BenzeneD1",
    "TolueneD2",
    "XyleneD4"
]
T0 = 500 + 273.15
dataByT = {}
for T1 in [T0 - 50, T0, T0 + 50]:
    try:
        sys2 = create_sys(T1)
        sys2.converge()
        data2 = {}
        for stream in streams:
            data2[stream] = {}
            for chemical in chemicals:
                data2[stream][chemical] = sys2.flowsheet.stream[stream].imass[chemical]/ sys2.flowsheet.stream["PS_Feed"].F_mass
        dataByT[T1] = pd.DataFrame(data2)
    except Exception as e:
        # # print(T1)
        # # print(e)

        continue

# reactor.T = T0
dataByT
#%%
plt.figure(figsize=(20, 6))
for i, T in enumerate(dataByT):
    ax = plt.subplot(1, 3, i+1)
    dataByT[T].T.plot(kind="bar", stacked=True, ax=ax, position=i, legend=False)
    plt.ylim(0, 1)
    plt.xticks(rotation=45)
    plt.title(f"Reactor Temperature: {T-273.15:.0f}°C")
    if i == 0:
        plt.ylabel("Key Stream Composition\n(kg/kg polystyrene feed)")
    if i != 0:
        plt.ylabel("")
        plt.yticks([])
    if i == 2:
        plt.legend(title="Chemical", loc="center left", bbox_to_anchor=(1.05, 0.5))

# plt.savefig("product_yields_sensitivity.png", dpi=300, bbox_inches="tight")
plot_product_yields_sensitivity = plt.gcf()
plt.close()
# %%

sys = create_sys(400+273.15)
 #Economic Analysis
#----------------------------------------------------------------------------------------------------------------
employee_costs ={
    "Plant Manager":[ 159000,  1],
    "Plant Engineer":[ 94000,  1],
    "Maintenance Supr":[ 87000,  1],
    "Maintenance Tech":[ 62000,  6],
    "Lab Manager":[ 80000,  1],
    "Lab Technician":[ 58000,  1],
    "Shift Supervisor":[ 80000,  3],
    "Shift Operators":[ 62000,  12],
    "Yard Employees":[ 36000,  4],
    "Clerks & Secretaries":[ 43000,  1],
    "General Manager":[188000, 0]
} # Labor cost taken from Dutta 2002 and adjusted using the U.S. Bureau of Labor Statistics. Number of staff required gotten from Yadav et al.  
#  US BLS (http://data.bls.gov/cgi-bin/srgateCEU3232500008)
labor_costs = sum([
    employee_costs[v][0]* employee_costs[v][1] * sys.flowsheet.stream["PS_Feed"].F_mass/(2000*1000/24)  for v in employee_costs
            ])
# # print(f"Labor cost: {labor_costs}")
# %%
# Economic Analysis: TEA code for MSP
#----------------------------------------------------------------------------------------------------------------

#facility_outputs = ["Ethylene","Propylene","Benzene","ethylbenzene","Toluene","styrene"]
def get_tea(sys):
    return TEA_PS(
        system=sys,
        IRR=0.1,
        duration=(2020, 2040),
        depreciation="MACRS7",
        income_tax=0.21,
        operating_days=350,
        lang_factor=5.05,  # ratio of total fixed capital cost to equipment cost
        construction_schedule=(0.4, 0.6),
        WC_over_FCI=0.05,  # working capital / fixed capital investment
        labor_cost=labor_costs,
        fringe_benefits=0.4,  # percent of salary for misc things
        property_tax=0.001,
        property_insurance=0.005,
        supplies=0.20,
        maintenance=0.004,
        administration=0.005,
        finance_fraction=0.4,
        finance_years=10,
        finance_interest=0.07,
    ) 

tea_msp = get_tea(sys)
tea_msp.system.simulate()

# Calculate MSP for each product in the facility outputs
msp_results = {}
feedprices = [0.0, 0.1, 1.5] # $30/tonne tipping fee to $30/tonne cost, https://www.statista.com/statistics/1171105/price-polystyrene-forecast-globally/
products = ["BenzeneO", "TolueneO", "AromaticsO", "XyleneO", "PSO"]

for fp in feedprices:
    tea_msp.system.flowsheet.stream["PS_Feed"].price = fp
    msp_results[f"Waste Plastic Cost:\n${1000*fp}/MT"] = {}
    for p in products:
        try:
            msp = tea_msp.solve_price(tea_msp.system.flowsheet.stream[p])*1000
            msp_results[f"Waste Plastic Cost:\n${1000*fp}/MT"][p] = msp
        except:
            msp_results[f"Waste Plastic Cost: ${1000*fp}/MT"][p] = None

tea_msp.system.flowsheet.stream["PS_Feed"].price = prices["PS"]

#%%
df = pd.DataFrame(msp_results).sort_values(by=f"Waste Plastic Cost:\n${1000*0.0}/MT").T
df.plot(kind="bar", stacked=False)
plt.ylabel("Product Minimum Selling Price ($/MT of single product)")
plt.xticks(rotation=45)
plt.legend(title="Product", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.grid(True, axis="y")

# plt.savefig("msp_results.png", dpi=300, bbox_inches="tight")
plot_msp = plt.gcf()
plt.close()

#%%

MSPSTables = {}
msps = {}
T0 = 800
for T1 in [T0 - 50, T0, T0 + 50]:
    sys = create_sys(T1)
    sys.simulate()
    tea = get_tea(sys)
    tea.system.flowsheet.stream["PS_Feed"].price = prices["PS"]

    products = ["BenzeneO", "TolueneO", "AromaticsO", "XyleneO", "PSO"]
    productsAnnualFlowRate = sum([tea.system.flowsheet.stream[p].get_total_flow('t/year') for p in products])

    msp_table = {k: v/productsAnnualFlowRate for (k,v) in  tea.mfsp_table(tea.system.flowsheet.stream["BenzeneO"]).items()}
    MSPSTables[f"Pyrolysis Temperature\n{T1-273.15} °C"] = msp_table
    msps[f"Pyrolysis Temperature\n{T1-273.15} °C"] = sum(msp_table.values())

#%%
df = pd.DataFrame(MSPSTables).T
df.plot(kind="bar", stacked=True)
plt.ylabel("Mean Minimum Selling Price ($/MT of liquid products)")
plt.xticks(rotation=45)
plt.legend(title="Product", loc="center left", bbox_to_anchor=(1.05, 0.5))
# plt.ylim(-90, 120)

for i, T1 in enumerate(msps):
    plt.text(i, 100, f"${msps[T1]:.2f}", ha="center", va="bottom")

# plt.savefig("msp_temperature_sensitivity.png", dpi=300, bbox_inches="tight")

plot_msp_temperature_sensitivity = plt.gcf()
plt.close()
#%%
equipment_costs = pd.DataFrame(dict((k.ID, k.installed_cost/1**6) for k in sys.units), index=[0]).T
major_equipment_costs = equipment_costs[equipment_costs[0]>250000]
major_equipment_costs = major_equipment_costs.sort_values(by=0)
other_equipment_costs = equipment_costs.drop(major_equipment_costs.index)
other_equipment_costs = other_equipment_costs.sum()
major_equipment_costs.loc["Other"] = other_equipment_costs

major_equipment_costs.T.plot.bar( stacked=True, figsize=(7, 12))
plt.legend(title="Equipment", loc="center left", bbox_to_anchor=(1, 0.8))
plt.ylabel("Installed Cost (MM$)")
plt.xticks([])
# plt.savefig("equipment_installed_costs.png", dpi=300, bbox_inches="tight")

plot_equipment_costs = plt.gcf()
plt.close()

#%% LCA
ef = pd.read_csv('impact_factors.csv', index_col=0)

# %%
impacts = {}
for p in sys.feeds + sys.products:
    if p.ID not in ef.index:
        continue
    impacts[p.ID] = {}
    for c in ef.columns[0:-3]:
        try:
            if p.ID == "PS_Feed":
                factor =  -ef.loc[p.ID, c] # Avoided emissions
            elif p.ID == "boiler_turbo_generator_ng": # natural gas has heating value of 55 MJ/kg
                factor =  ef.loc[p.ID, c] / 55 
            elif p in sys.products:
                factor =  -ef.loc[p.ID, c]
            else:
                factor =  ef.loc[p.ID, c]
            impacts[p.ID][c] = p.F_mass *factor
        except:
            pass 

impacts["Electricity"] = {c:sys.flowsheet.unit["Turbogenerator"].power_utility.rate*3.6 * ef.loc["Electricity", c] for c in ef.columns[0:-3]}

impacts["Direct CO2"] = {c:0 for c in ef.columns[0:-3]}
impacts["Direct CO2"]["Climate change (kg CO2 eq)"] = sum([s.imass["CO2"] + s.imass["CH4"]*25  for s in sys.products])
impacts["Direct CO2"]["Climate change - Fossil (kg CO2 eq)"] += sum([s.imass["CO2"] + s.imass["CH4"]*25  for s in sys.feeds])
#%%
impactsDF = pd.DataFrame(impacts)
#%% normalize the impacts by dividing by the total impact 
impactsNorm = impactsDF.T/impactsDF.abs().sum(axis=1)
# %%
impactsNorm.T.plot(kind="bar", stacked=True)
plt.ylim(-1,0.25)
plt.legend(title="Impact Category", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.ylabel("Normalized Impact")
lca_fig = plt.gcf()
plt.close()
#%%
lca_fig
# %%
impactsDF.T.sum()/sys.flowsheet.stream["PS_Feed"].F_mass
# %%
print(f"The GWP impact of PS Recycling is {impactsDF.T.sum()['Climate change (kg CO2 eq)']/sys.flowsheet.stream['PS_Feed'].F_mass:.2f} kg CO2 eq/kg PS")
# %%
#%%
(impactsDF.loc[["Climate change (kg CO2 eq)"], :]/sys.flowsheet.stream["PS_Feed"].F_mass).plot(kind="bar", stacked=True, figsize=(8,9))
plt.legend(title="Impact Category", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.xticks([])
plt.ylabel("Global Warming Potential (kg CO2 eq/kg product)")

# %%
