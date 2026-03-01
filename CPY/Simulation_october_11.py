#%%
from matplotlib.pyplot import xticks
import biosteam as bst 
import sys 
import numpy as np
import pandas as pd
from torch import cat
sys.path.append('./Module/')

#from Pyrolyzer import *
from _pyrolyzer import *
from _compounds import *
from _feed_handling import *
from _grinder import *
from _chscreen import *
from _cyclone import *
from _compressor import *
from _utilityagents import *
from _tea import *
#from _ANN_model_recent import *
from _sankeys import sankeys, sankeys_energy
#from biosteam.units.distillation import DSTWU
from thermosteam import Chemical
import matplotlib.pyplot as plt
import matplotlib
# plt.style.use("seaborn-v0_8")
# use a journal quality plot style
plt.style.use('seaborn-v0_8-whitegrid')
matplotlib.rcParams.update({'font.size': 14})

bst.nbtutorial()
bst.settings.CEPCI = 800 # CEPCI 2024

bst.preferences.update(flow='t/d', T='degK', P='Pa', N=100, composition=False)
# %% 
# prices
prices ={
    "PS": 0.90, # $/kg  https://businessanalytiq.com/procurementanalytics/index/polystyrene-ps-price-index/
    "Styrene": 0.96, # $/kg https://businessanalytiq.com/procurementanalytics/index/styrene-price-index/
    "BTX": 0.97*0.8, # $/kg https://businessanalytiq.com/procurementanalytics/index/toluene-price-index/
    "Benzene": 0.96*0.8, # $/kg https://businessanalytiq.com/procurementanalytics/index/benzene-price-index/
    "Aromatics": 1.08*0.8, # $/kg https://medium.com/intratec-products-blog/ethylbenzene-prices-latest-historical-data-in-several-countries-429afa8ae173
    "Xylene": 0.76, # $/kg TR Brown et al. 2012. DOI: 10.1002/bbb.344
    "Ethylene": 0.61, # Gracida Al
    "Propylene": 0.97*0.8, # $/kg
    "NG": 7.40 * 1000 * 1.525/28316.8, 
    "Fresh catalyst": 1.09, # $/kg https://www.intratec.us/solutions/primary-commodity-prices/commodity/zinc-oxide-prices
    "Hydrogen plant catalyst": 3.6/885.7,      #3.6 /1000scf/28.317m3/885.71kg 2007 quote from Jones et al. 2009 PNNL report SRI international 2007
    "Hydrogen": 2.83,      #2.83 USD/kg from Gracida Alvarez et al. 2.1 from Borja Hernandez et al. 2019
    "Hydrotreating catalyst": 15.5 * 2.20462262,      #15.5 $/lb from Li et al. 2017 PNNL report SRI international 2007
    "Fluid catalytic cracking catalyst": 15.5 * 2.20462262, # 15.5 $/lb from Li et al. 2016
}
bst.settings.electricity_price = 0.062 # Li et al. 2
# %%
cpy = {"Technology":"CPY", "catalytic": "Yes",  "Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"low"}
cpy_ht = {"Technology":"CPY", "catalytic":"No",  "Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" : "high"}
tcp = {"Technology":"TCP", "catalytic": "Yes",  "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"high"}
tcp_ht = {"Technology":"TCP", "catalytic": "No", "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"low"}

scenarios = [cpy,cpy_ht,tcp,tcp_ht]
scenarios_labels = ["CPY","CPY-HT","TCP","TCP-HT"]
plant_capacity = 250 # tonnes per day
capacity = plant_capacity
scenario = scenarios[3]
irr = 0.1
# %%
# --- Catalyst policy (ZnO) ---
CATALYST_PRICE_USD_PER_KG = prices["Fresh catalyst"]  # you already defined this
CATALYST_INVENTORY_KG     = 5_000.0                   # set your design inventory (kg total in system)
CATALYST_FEED_MASS_FRAC   = 0.05                      # 1:0.05 feed:catalyst (5 wt%)
CATALYST_REPLENISH_PER_DAY = 0.02                     # 2%/day planned replacement
CATALYST_ATTRITION_PER_DAY = 0.016                    # 1.6%/day attrition
CATALYST_TOTAL_REPLENISH_PER_DAY = (
    CATALYST_REPLENISH_PER_DAY + CATALYST_ATTRITION_PER_DAY
)  # 0.036/day
#%%
# --- Helper: size N2 from reactor diameter & superficial velocity (bed conditions) ---
import math


#%%
reactorT = 600 + 273.15  # Reactor temperature in Kelvin
def create_ps_sys():
    bst.main_flowsheet.clear()
    bst.main_flowsheet.set_flowsheet('PS_flowsheet')
    capacity = 250
    feed = bst.Stream('PS_Feed',
                        PS=1,
                        units='kg/hr',
                        T=298)
    feed.set_total_flow(capacity, 'tonnes/day')
    #feed.price = prices["PS"]
    catalyst_ratio = 0.05  # 5 wt% catalyst on PS basis
    ZnO_mass = capacity * catalyst_ratio
    
        ### Catalyst Handling ###
        # 5% of feed mass
    catalyst_inventory_fraction = 0.02  # 2% of feed mass
    attrition_rate = 0.016            # 1.6% of inventory per day

    catalyst_inventory = catalyst_inventory_fraction * ZnO_mass   # in tonnes/day
    catalyst_makeup = catalyst_inventory * attrition_rate  
    catalyst_unit_cost = prices["Fresh catalyst"]
    feed_price = 0.013 + (attrition_rate + catalyst_inventory_fraction) * catalyst_unit_cost / 5  # 5:1 biomass:catalyst
    feed.price = prices["PS"]

    catalyst = bst.Stream('catalyst',
                      ZnO=catalyst_makeup + catalyst_inventory,  # daily input
                      units='tonnes/day',
                      phase='s')
    catalyst.price = prices["Fresh catalyst"]
    
    # pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen',O2=1,units='kg/hr',T=298,price=0.000)
    reactor_diameter_m = 0.50         # <— tune
    target_U0 = 0.30                   # m/s at bed conditions  <— tune
    T_bed = reactorT                   # keep bed gas at reactor setpoint
    P_bed = 101325.0

    co2_makeup_rate = 0.1
    fluid_gas = bst.Stream("fluid_gas", CO2=feed.F_mass*2*co2_makeup_rate, T=298.15, P=101325, units='kg/hr')
    

    # Preheat N2 to bed temperature (utility duty will be supplied by BoilerTurbogenerator)
    fluid_gas_heater = bst.units.HXutility('Fluid_gas_heater',
                                    ins=fluid_gas,
                                    outs=('N2_hot',),
                                    T=T_bed,
                                    rigorous=True)
    
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
    CHscreen = Screen("CHScreen", ins=[grinder-0], outs=[CRPS,recycle])
    
    mixer_pyrolyzer = bst.Mixer('Mixer_pyrolyzer',ins=[CRPS, catalyst, fluid_gas_heater-0], outs=('mixer_pyrolyzer_out'))

    
    # Dummy stream to represent spent catalyst from reactor (assumed for logic)
    spent_catalyst = bst.Stream('spent_catalyst', ZnO=ZnO_mass - catalyst_makeup, units='tonnes/day', phase='s')

# Regenerator unit
    regenerator = bst.units.MixerSettler('Catalyst_Regenerator',
    ins=(spent_catalyst, catalyst),
    outs=('regenerated_catalyst', 'purged_catalyst')
    )

# Recycle regenerated catalyst back to mixer_pyrolyzer
    mixer_pyrolyzer.ins.append(regenerator-0)

    #reactor = bst.units.Pyrolyzer('Pyrolyzer', ins=[mixer_pyrolyzer-0], outs= ('PyrolyzerO'), T=reactorT, P=101325, tau=1.5)
    reactor = Pyrolyzer('Pyrolyzer', 
                   ins=[mixer_pyrolyzer-0], 
                   outs=('PyrolyzerO'), 
                   T=reactorT, 
                   P=101325,
                   tau=1)

    def pyrolyzer_spec():
        reactor.T = reactorT
        reactor._run()
    reactor.add_specification(pyrolyzer_spec)

    Cyclone = bst.units.Cyclone('Cyclone0', ins= (reactor-0), outs= ['oil_Gas', spent_catalyst], efficiency=0.99)
    cooler1 = bst.units.HXutility('cooler', ins=[Cyclone-0], outs=('coolerOil'), T=273.15 +10, rigorous=False)
    F0 = bst.units.Flash('Condenser', ins=cooler1-0, T=273.15 +10, P=101325, outs=('F0gas', 'F0oil')) #Check flash temperature
    F0.reset_cache()

    Pump1 = bst.units.Pump('Pump1', ins=[F0-1], P=25 * 101325)

    ### Products Separation
    F1 = bst.units.Flash('F1o', ins=Pump1-0, T=285, P=101325, outs=('F1ogas', 'F1ooil'))
    F1.reset_cache()
    
    preflash = bst.units.Flash('preflash', ins=F1-1, T=285, P=101325, outs=('preflash_gas', 'preflash_liquid'))
    
    PF_bleed = bst.Splitter('PF_bleed', ins=preflash-1, outs=('PF_to_BTX', 'PF_to_bleed'), split=0.99)
    D1 = bst.units.BinaryDistillation(
        'DBTX',
        ins=PF_bleed-0,
        outs=('BTX', ''),
        LHK=('C8H10', 'PS'),
        product_specification_format='Recovery',
        Lr=0.95, Hr=0.95, k=2.0, P=101325,
    )
    D1.outs[0].price = prices["BTX"]

    
    D2 = bst.units.BinaryDistillation(
        'DStyrene',
        ins= D1-1,
        outs=('Styrene', ''),
        LHK=('PS', 'C9H12'),
        product_specification_format='Recovery',
        Lr=0.90, Hr=0.9, k=2.0, P=101325,
    )
    D2.outs[0].price = prices["Styrene"]

    # bp = D2.outs[1].bubble_point_at_P()

    d3hx = bst.units.HXutility('D3hx', ins=D2-1, outs=(''), T=433.61, rigorous=False)

    D3 = bst.units.Flash('DAromatics',
        ins=d3hx-0,
        T=433.61+10, P=101325,
        outs=('Aromatics', 'Bottoms')
    )
    D3.outs[0].price = prices["Aromatics"]

    # D3 = bst.units.BinaryDistillation(
    #     'DAromatics',
    #     ins=d3hx-0,
    #     outs=('AromaticsO', 'Bottoms'),
    #     LHK=('C9H12', 'PS'),
    #     product_specification_format='Recovery',
    #     Lr=0.90, Hr=0.9, k=2.0, P=101325,
    # )

    
    turbogenerator_mixer = bst.units.Mixer('Turbogenerator_mixer', ins=[F0-0, F1-0])
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
        btg_chemicals),
        boiler_efficiency=0.85,
        turbogenerator_efficiency=0.85)
    
    sys = bst.main_flowsheet.create_system('PS_sys')
    return sys
#%%
reactorT = 600 + 273.15  # Reactor temperature in Kelvin
sys = create_ps_sys()
sys.reset_cache()
sys.empty_recycles()
sys.simulate()
bst.main_flowsheet.diagram(format='png')
#%%

sankeys(sys, filename="sankey.png")
fig = plt.gcf()
ax = plt.gca()
for stream in sys.streams:
    if not stream.isempty() and hasattr(stream, 'sankey_data'):
        flow = stream.F_mass  # or stream.F_mol
        # Find midpoint of stream line
        x, y = stream.sankey_data['x'], stream.sankey_data['y']
        mid_index = len(x)//2
        ax.text(
            x[mid_index], y[mid_index], 
            f"{flow:.2f} kg/hr", 
            fontsize=8, color='black', ha='center', va='center'
        )

# Save or display
fig.savefig('sankey_with_flowrates.png', dpi=300, bbox_inches='tight')
fig.show()
sankeys_energy(sys, filename="sankey_energy.png")
#%%
# Wastewater treatment
# WW_mixer = bst.units.Mixer('Wastewater_mixer', ins=[], outs=('Wastewater_out'))

Streams = [
    'PS_Feed',
    # 'catalyst',
    # 'pyrolysis_oxygen',
    # 'N2_hot',
    # 'Hydrogen',
    #'Handling-0',
    #'Mixer_1-0',
    # 'grinderout',
    #'CHScreen-0',
    #'CHScreen-1',
    # 'mixer_pyrolyzer_out',
    # 'spent_catalyst',
    # 'regenerated_catalyst',
    # 'purged_catalyst',
    'PyrolyzerO',
    'oil_Gas',
    'coolerOil',
    # 'F0gas',
    'F0oil',
    #'Pump1-0',
    # 'F1ogas',
    'F1ooil',
    # 'preflash_gas',
    'preflash_liquid',
    'PF_to_BTX',
    # 'PF_to_bleed',
    
    #'StyreneO-0',
    #'StyreneO-1', 
    'Styrene', 
   'Aromatics', 
   'Bottoms',
    'BTX'
]

ChemicalList= [
    'PS',
    'C8H8',
    'C6H6',
    'C7H8',
    'C8H10',
    'C9H12',
    'C10H22',
    'CO',
    'CO2',
    'CH4',
    'C2H6',
    'C2H4',
    'C3H8',
    'C3H6',
    'H2O',
    'N2',
    'O2',
    'H2',
    'ZnO'
]

data = {}
for stream in Streams:
    data[stream] = {}
    for c in sys.flowsheet.stream[stream].available_chemicals:
        if c.ID == "CO2":
            continue
        chemical = c.ID
        data[stream][chemical] = (sys.flowsheet.stream[stream].imass[chemical])/sys.flowsheet.stream["PS_Feed"].F_mass


# matplotlib colorscheme with 20 distinct colors
colors = plt.cm.get_cmap('tab20', 20).colors
# make default color cycle use these colors
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)

compositionDF = pd.DataFrame(data)
compositionDF.T.plot(kind="bar", stacked=True)
plt.ylabel("Key Stream Composition\n(kg/kg polystyrene feed)")
plt.legend(title="Chemical", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.grid(True, axis="y")

# plt.savefig("product_yields.png", dpi=300, bbox_inches="tight")
plot_product_yields = plt.gcf()
# plt.close()
# %%
#sys.save_report("pyrolysis_BTX_Styrene_aromatic_1.xlsx", sheets=['Reactions',' Itemized costs', 'Cash  flow', 'Design requirements', 'Stream table', 'Flowsheet'])
# %%
#reactorT = 550 + 273.15  # Reactor temperature in Kelvin
#sys = create_ps_sys()
#sys.feeds.append(sys.flowsheet.stream["PS_Feed"])
#economic analysis
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
labor_costs = sum([
    employee_costs[v][0]* employee_costs[v][1] * sys.flowsheet.stream["PS_Feed"].F_mass/(2000*1000/24)  for v in employee_costs
            ])

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
mspBTX = tea_msp.solve_price(tea_msp.system.flowsheet.stream["BTX"])*1000
mspAromatics = tea_msp.solve_price(tea_msp.system.flowsheet.stream["Aromatics"])*1000
mspStyrene = tea_msp.solve_price(tea_msp.system.flowsheet.stream["Styrene"])*1000
print(f"Minimum selling price of BTX: ${mspBTX:,.2f}")
print(f"Minimum selling price of Aromatics: ${mspAromatics:,.2f}")
print(f"Minimum selling price of Styrene: ${mspStyrene:,.2f}")
#%%
mfsp_table = {k: v/ sum([tea_msp.system.flowsheet.stream[p].get_total_flow('t/year') for p in ["BTX", "Aromatics", "Styrene"]]) for (k,v) in  tea_msp.mfsp_table(tea_msp.system.flowsheet.stream["BTX"]).items()}
df = pd.DataFrame.from_dict(mfsp_table, orient='index', columns=['MFSP ($/MT of liquids)'])
df.T.plot(kind="bar", stacked=True, figsize=(6,10))
plt.ylabel("Mean Liquids Minimum Selling Price ($/MT)")
plt.xticks([])
plt.legend(title="Cost", loc="center left", bbox_to_anchor=(1.05, 0.8))
plt.grid(True, axis="y")

# %%
msp_results = {}
feedprices = [0.23,0.59,0.64] #0onne tipping fee to $30/tonne cost, https://www.statista.com/statistics/1171105/price-polystyrene-forecast-globally/
products = ["BTX", "Aromatics", "Styrene"]

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



df = pd.DataFrame(msp_results).sort_values(by=f"Waste Plastic Cost:\n${1000*0.23}/MT").T
df.plot(kind="bar", stacked=False)

# add lines for btx, aromatics, styrene prices
plt.hlines([
    prices["BTX"]*1000, 
    prices["Aromatics"]*1000, 
    prices["Styrene"]*1000], 
    xmin=-1, xmax=len(feedprices), colors=['C0','C1','C2'], linestyles='dashed')

# add text labels for the lines
plt.text(-0.5, prices["BTX"]*1000 - 300, 'BTX Price', color='C0')
plt.text(-0.5, prices["Styrene"]*1000 + 250, 'Styrene Price', color='C2')


plt.text(2.4, -3540, "Negative MSPs indicate\nprofitable products", color='black', fontsize=10, ha='right',
         bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

plt.ylabel("Product Minimum Selling Price ($/MT)")
plt.xticks(rotation=45)
plt.legend(title="Product", loc="center left", bbox_to_anchor=(1.05, 0.5))
plt.grid(True, axis="y")
plt.savefig("msp_sensitivity.png", dpi=300, bbox_inches="tight")
#%%
print("\nMinimum Selling Prices (MSPs) of products at different PS feedstock costs:")
for feed_cost_label, product_msps in msp_results.items():
    print(f"\n{feed_cost_label}")
    for product, msp in product_msps.items():
        if msp is not None:
            print(f"  {product}: ${msp:,.2f} per MT")
        else:
            print(f"  {product}: Calculation failed or not available")

# %%
MSPSTables = {}
msps = {}
T0 = 500 + 273.15
for T1 in [T0 - 100, T0, T0 + 100]:
    reactorT = T1
    sys = create_ps_sys()
    sys.simulate()
    tea = get_tea(sys)
    tea.system.flowsheet.stream["PS_Feed"].price = prices["PS"]

    products = ["BTX", "Aromatics", "Styrene"]
    productsAnnualFlowRate = sum([tea.system.flowsheet.stream[p].get_total_flow('t/year') for p in products])

    msp_table = {k: v/productsAnnualFlowRate for (k,v) in  tea.mfsp_table(tea.system.flowsheet.stream["BTX"]).items()}
    MSPSTables[f"Pyrolysis Temperature\n{T1-273.15} °C"] = msp_table
    msps[f"Pyrolysis Temperature\n{T1-273.15} °C"] = sum(msp_table.values())

df = pd.DataFrame(MSPSTables).T

# If any blank/None column labels slipped in, rename them
rename_map = {}
for c in df.columns:
    if c is None or (isinstance(c, str) and c.strip() == ''):
        rename_map[c] = 'Unlabeled'
if rename_map:
    df = df.rename(columns=rename_map)


ax = df.plot(kind="bar", stacked=True)


ax = plt.gca()
ax.text(1.48, -0.15, f"PS Feed Price: ${prices['PS']}/kg", transform=ax.transAxes,
    color='black', fontsize=14, ha='right', va='bottom')

plt.ylabel("Mean Liquids Minimum Selling Price ($/MT)")
plt.xticks(rotation=45)
plt.legend(title="Cost", loc="center left", bbox_to_anchor=(1.05, 0.5))

# Annotate MSP values on the bars (keep your original logic)
for i, T1 in enumerate(msps):
    plt.text(i, 100, f"${msps[T1]:.2f}", ha="center", va="bottom", fontsize=10, weight='bold')

plot_msp_temperature_sensitivity = plt.gcf()
plt.savefig("msp_temperature_sensitivity.png", dpi=300, bbox_inches="tight")
# %%
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
plot_equipment_costs = plt.gcf()
plt.savefig("equipment_costs.png", dpi=300, bbox_inches="tight")
# %%
#LCA
ef = pd.read_csv('impact_factors.csv', index_col=0)

def get_impacts(sys):
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
                print(f"Impact factor for {p.ID} and {c} not found.")
                pass 

    impacts["Electricity"] = {c:sys.flowsheet.unit["Turbogenerator"].power_utility.rate*3.6 * ef.loc["Electricity", c] for c in ef.columns[0:-3]}

    impacts["Direct CO2"] = {c:0 for c in ef.columns[0:-3]}
    impacts["Direct CO2"]["Climate change (kg CO2 eq)"] = sum([s.imass["CO2"] + s.imass["CH4"]*25  for s in sys.products])
    impacts["Direct CO2"]["Climate change - Fossil (kg CO2 eq)"] += sum([s.imass["CO2"] + s.imass["CH4"]*25  for s in sys.feeds])
    return impacts

impacts = get_impacts(sys)

impactDF = pd.DataFrame(impacts)
impactDF = impactDF.T
impactDF = impactDF/ sys.flowsheet.stream["PS_Feed"].F_mass *1000 # per tonne of PS
impactDF = impactDF.sort_values(by="Climate change (kg CO2 eq)")
# impactDF.plot(kind="bar", stacked=True, figsize=(10, 6))
# plt.ylabel("Life Cycle Environmental Impacts\nper tonne of polystyrene feed (kg or MJ/tonne PS)")
# plt.legend(title="Impact category", loc="center left", bbox_to_anchor=(1.05, 0.5))
# plt.grid(True, axis="y")
# plot_lca = plt.gcf()

impactsDF = pd.DataFrame(impacts)
# normalize the impacts by dividing by the total impact 
impactsNorm = impactsDF.T/impactsDF.abs().sum(axis=1)
impactsNorm.T.plot(kind="bar", stacked=True, figsize=(12, 9))
plt.ylim(-1,0.25)
plt.legend(title="Impact Category", loc="center left", bbox_to_anchor=(1.05, 0.5))
# replace the legend label "boiler_turbo_generator_ng" with "Natural gas"
legends = plt.gca().get_legend()
for text in legends.get_texts():
    if text.get_text() == "boiler_turbogenerator_ng":
        text.set_text("Natural gas")

plt.ylabel("Normalized Impact")
lca_fig = plt.gcf()
# plt.close()
lca_fig.savefig("lca_figure.png", dpi=300, bbox_inches="tight")
impactsDF.T.sum()/sys.flowsheet.stream["PS_Feed"].F_mass
print(f"The GWP impact of PS Recycling is {impactsDF.T.sum()['Climate change (kg CO2 eq)']/sys.flowsheet.stream['PS_Feed'].F_mass:.2f} kg CO2 eq/kg PS")
lca_fig

# %%
(impactsDF.loc[["Climate change (kg CO2 eq)"], :]/sys.flowsheet.stream["PS_Feed"].F_mass).plot(kind="bar", stacked=True, figsize=(8,9))
plt.legend(title="Impact Category", loc="center left", bbox_to_anchor=(1.05, 0.5))
legends = plt.gca().get_legend()
for text in legends.get_texts():
    if text.get_text() == "boiler_turbogenerator_ng":
        text.set_text("Natural gas")

plt.text(0.74, 0.75, f"Total GWP: {impactsDF.T.sum()['Climate change (kg CO2 eq)']/sys.flowsheet.stream['PS_Feed'].F_mass:.2f} kg CO2 eq/kg PS", transform=plt.gca().transAxes,
    color='black', fontsize=14, ha='right', va='top', bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))
plt.xticks([])
plt.ylabel("Global Warming Potential (kg CO2 eq/kg product)")
plt.savefig("lca_gwp.png", dpi=300, bbox_inches="tight")
# %%
def get_mean_msp():    
    products = ["BTX", "Aromatics", "Styrene"]
    productsAnnualFlowRate = sum([tea.system.flowsheet.stream[p].get_total_flow('t/year') for p in products])

    msp_table = {k: v/productsAnnualFlowRate for (k,v) in  tea.mfsp_table(tea.system.flowsheet.stream["BTX"]).items()}
    return sum(msp_table.values())

sys = create_ps_sys()
sys.simulate()
tea = get_tea(sys)
tea.system.simulate()
tea.system.flowsheet.stream["PS_Feed"].price = prices["PS"]
baseline_MSP = get_mean_msp()
print(f"Baseline MFSP: ${baseline_MSP:.2f} per MT of liquid products")
# %%
# Sensitivity analysis
# Sensitivity analysis (corrected: ensure +20% is "High", -20% is "Low", always re-simulate and restore baseline)
sensitivity_results = []

# helper to test +20% and -20% for an arbitrary setter/getter pair
def run_pct_sensitivity(get_baseline, set_value):
    base = get_baseline()
    # +20%
    set_value(base * 1.2)
    tea.system.simulate()
    high = get_mean_msp()
    # -20%
    set_value(base * 0.8)
    tea.system.simulate()
    low = get_mean_msp()
    # restore
    set_value(base)
    tea.system.simulate()
    return base, low, high

# 1) PS feed price (per kg)
ps_stream = bst.main_flowsheet.stream["PS_Feed"]
base, low, high = run_pct_sensitivity(lambda: ps_stream.price, lambda v: setattr(ps_stream, "price", v))
sensitivity_results.append({
    "Parameter": f"PS Price (${base:.2f}/kg)",
    "Baseline": base,
    "Parameter Low": base * 0.8,
    "Parameter High": base * 1.2,
    "Baseline MSP": baseline_MSP,
    "High": high,
    "Low": low,
})

#2) Aromatics price (fallback to prices dict or stream)
arom_stream = tea.system.flowsheet.stream["Aromatics"]
base_arom = prices.get("Aromatics", getattr(arom_stream, "price", 0.0)) if arom_stream is not None else prices.get("Aromatics", 0.0)
def set_arom(v):
    if arom_stream is not None:
        arom_stream.price = v
    prices["Aromatics"] = v
base, low, high = run_pct_sensitivity(lambda: base_arom, set_arom)
sensitivity_results.append({
    "Parameter": f"Aromatics Price (${base:.2f}/kg)",
    "Baseline": base,
    "Parameter Low": base * 0.8,
    "Parameter High": base * 1.2,
    "Baseline MSP": baseline_MSP,
    "High": high,
    "Low": low,
})

# 3) Styrene price
sty_stream = tea.system.flowsheet.stream["Styrene"]
base_sty = prices.get("Styrene", getattr(sty_stream, "price", 0.0)) if sty_stream is not None else prices.get("Styrene", 0.0)
def set_sty(v):
    if sty_stream is not None:
        sty_stream.price = v
    prices["Styrene"] = v
base, low, high = run_pct_sensitivity(lambda: base_sty, set_sty)
sensitivity_results.append({
    "Parameter": f"Styrene Price (${base:.2f}/kg)",
    "Baseline": base,
    "Parameter Low": base * 0.8,
    "Parameter High": base * 1.2,
    "Baseline MSP": baseline_MSP,
    "High": high,
    "Low": low,
})

# 4) BTX price
btx_stream = tea.system.flowsheet.stream["BTX"]
base_btx = prices["Benzene"]
def set_btx(v):
    btx_stream.price = v
base, low, high = run_pct_sensitivity(lambda: base_btx, set_btx)
# sensitivity_results.append({
#     "Parameter": f"BTX Price (${base:.2f}/kg)",
#     "Baseline": base,
#     "Parameter Low": base * 0.8,
#     "Parameter High": base * 1.2,
#     "Baseline MSP": baseline_MSP,
#     "High": high,
#     "Low": low,
# })

# # 5) Catalyst price (stream 'catalyst')
cat_stream = tea.system.flowsheet.stream["catalyst"]
if cat_stream is not None:
    base_cat = getattr(cat_stream, "price", prices.get("Fresh catalyst", 0.0))
    def set_cat(v):
        cat_stream.price = v
    base, low, high = run_pct_sensitivity(lambda: base_cat, set_cat)
    sensitivity_results.append({
        "Parameter": f"Catalyst Price (${base:.2f}/kg)",
        "Baseline": base,
        "Parameter Low": base * 0.8,
        "Parameter High": base * 1.2,
        "Baseline MSP": baseline_MSP,
        "High": high,
        "Low": low,
    })

# 6) Lang factor (TEA)
base_lang = tea.lang_factor
def set_lang(v):
    tea.lang_factor = v
base, low, high = run_pct_sensitivity(lambda: base_lang, set_lang)
sensitivity_results.append({
    "Parameter": f"Lang Factor ({base:.2f})",
    "Baseline": base,
    "Parameter Low": base * 0.8,
    "Parameter High": base * 1.2,
    "Baseline MSP": baseline_MSP,
    "High": high,
    "Low": low,
})

# 7) Reactor temperature (Pyrolyzer unit T)
# 7) Reactor temperature (Pyrolyzer unit T)
pyro_unit = tea.system.flowsheet.unit["Pyrolyzer"]
if pyro_unit is not None:
    base_T = pyro_unit.T
    def set_T(v):
        global reactorT
        pyro_unit.T = v
        reactorT = v
    # Run sensitivity at +20% and -20% of reactor temperature
    base, low, high = run_pct_sensitivity(lambda: pyro_unit.T, set_T)
    sensitivity_results.append({
        "Parameter": f"Reactor Temperature ({base - 273.15:.2f} °C)",
        "Baseline": base,
        "Parameter Low": base * 0.8,
        "Parameter High": base * 1.2,
        "Baseline MSP": baseline_MSP,
        "High": high,
        "Low": low,
    })

# # Sort by absolute change magnitude and plot (differences relative to baseline MSP)
sensitivity_results = sorted(sensitivity_results, key=lambda x: abs(x["High"] - x["Baseline MSP"]), reverse=False)

plt.figure(figsize=(10, 6))
labels = [s["Parameter"] for s in sensitivity_results]
high_deltas = [(s["High"] - s["Baseline MSP"]) for s in sensitivity_results]
low_deltas  = [(s["Low"]  - s["Baseline MSP"]) for s in sensitivity_results]

# plot +20% and -20% as bars relative to baseline
plt.barh(labels, high_deltas, color='lightblue', label='+20%')
plt.barh(labels, low_deltas,  color='lightgreen', label='-20%')
plt.axvline(0, color='gray', linestyle='--')
plt.xlabel('MSP ($/MT of liquid products) relative to baseline')
# x tick labels centered at baseline_MSP
xticks = plt.xticks()[0]
plt.xticks(xticks, [f"${(x + baseline_MSP):,.2f}" for x in xticks])
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.legend(title='Impact Level', loc='lower right')
plt.tight_layout()

sensitivity_analysis_fig = plt.gcf()
plt.savefig("sensitivity_analysis.png", dpi=300, bbox_inches="tight")
# %%
def get_gwp(system):
    impacts = get_impacts(system)
    gwp = 0 
    for k in impacts:
        gwp += impacts[k].get('Climate change (kg CO2 eq)', 0)
    products = ["BTX", "Aromatics", "Styrene"]
    productsAnnualFlowRate = sum([tea.system.flowsheet.stream[p].get_total_flow('t/year') for p in products])
    return gwp/productsAnnualFlowRate

reactorT = 600 + 273.15  # Reactor temperature in Kelvin
sys = create_ps_sys()
sys.simulate()
sensitivity_lca_results = []
baseline_gwp = get_gwp(sys)

baselineEF = ef.loc["PS_Feed"]["Climate change (kg CO2 eq)"]
ef.loc["PS_Feed", "Climate change (kg CO2 eq)"] = baselineEF * 1.2
high = get_gwp(sys)
ef.loc["PS_Feed", "Climate change (kg CO2 eq)"] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["PS_Feed", "Climate change (kg CO2 eq)"] = baselineEF
sensitivity_lca_results.append({
    "Parameter": f"PS Feed GWP ({baselineEF:.2f} kg CO2 eq/kg PS)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

baselineEF = ef.loc["boiler_turbogenerator_ng"]["Climate change (kg CO2 eq)"]
ef.loc["boiler_turbogenerator_ng", "Climate change (kg CO2 eq)"] = baselineEF * 1.2
high = get_gwp(sys)
ef.loc["boiler_turbogenerator_ng", "Climate change (kg CO2 eq)"] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["boiler_turbogenerator_ng", "Climate change (kg CO2 eq)"] = baselineEF
sensitivity_lca_results.append({
    "Parameter": f"Boiler NG GWP ({baselineEF:.2f} kg CO2 eq/kg NG)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

baselineEF = ef.loc["Electricity"]["Climate change (kg CO2 eq)"]
ef.loc["Electricity", "Climate change (kg CO2 eq)"] = baselineEF * 1.2
high = get_gwp(sys) 
ef.loc["Electricity", "Climate change (kg CO2 eq)"] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["Electricity", "Climate change (kg CO2 eq)"] = baselineEF
sensitivity_lca_results.append({
    "Parameter": f"Electricity GWP ({baselineEF:.2f} kg CO2 eq/kWh)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

# Ensure Xylene is present in impact factors for LCA sensitivity
# Ensure impact factors exist for Xylene and Aromatics and that the flowsheet streams are counted as products
cc_col = "Climate change (kg CO2 eq)"

baselineEF = ef.loc["Aromatics"]["Climate change (kg CO2 eq)"]
ef.loc["Aromatics", "Climate change (kg CO2 eq)"] = baselineEF * 1.2
high = get_gwp(sys)
ef.loc["Aromatics", "Climate change (kg CO2 eq)"] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["Aromatics", "Climate change (kg CO2 eq)"] = baselineEF
sensitivity_lca_results.append({
    "Parameter": f"Aromatics GWP ({baselineEF:.2f} kg CO2 eq/kg Aromatics)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

# Safely obtain a baseline emission factor for BTX (use fallbacks if "BTX" is missing)
cc_col = "Climate change (kg CO2 eq)"

# Ensure BTXO row exists/gets updated for sensitivity runs
ef.loc["BTX", cc_col] = baselineEF * 1.2
high = get_gwp(sys)
ef.loc["BTX", cc_col] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["BTX", cc_col] = baselineEF

sensitivity_lca_results.append({
    "Parameter": f"BTX GWP ({baselineEF:.2f} kg CO2 eq/kg BTX)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

#baselineEF = ef.loc["Toluene"]["Climate change (kg CO2 eq)"]
#ef.loc["Toluene", "Climate change (kg CO2 eq)"] = baselineEF * 1.2
#high = get_gwp(sys)
#ef.loc["Toluene", "Climate change (kg CO2 eq)"] = baselineEF * 0.8
#low = get_gwp(sys)
#ef.loc["Toluene", "Climate change (kg CO2 eq)"] = baselineEF
#sensitivity_lca_results.append({
#    "Parameter": f"Toluene GWP ({baselineEF:.2f} kg CO2 eq/kg Toluene)",
#    "Baseline": baselineEF,
#    "Parameter Low": baselineEF * 0.8,
#    "Parameter High": baselineEF * 1.2,
#    "Baseline GWP": baseline_gwp,
#    "High": high,
#    "Low": low,
#})


baselineEF = ef.loc["Styrene"][cc_col]
ef.loc["Styrene", cc_col] = baselineEF * 1.2
high = get_gwp(sys)
ef.loc["Styrene", cc_col] = baselineEF * 0.8
low = get_gwp(sys)
ef.loc["Styrene", cc_col] = baselineEF
sensitivity_lca_results.append({
    "Parameter": f"Styrene GWP ({baselineEF:.2f} kg CO2 eq/kg Styrene)",
    "Baseline": baselineEF,
    "Parameter Low": baselineEF * 0.8,
    "Parameter High": baselineEF * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": high,
    "Low": low,
})

# Reactor Temperature
baselineT = 600 + 273.15  # Reactor temperature in Kelvin
reactorT = baselineT * 1.2
sys.simulate()
high = get_gwp(sys)
reactorT = baselineT * 0.6
sys.simulate()
low = get_gwp(sys)
reactorT = baselineT
sys.simulate()
sensitivity_lca_results.append({
    "Parameter": f"Reactor Temperature ({reactorT-273.15:.2f} °C)",
    "Baseline": baselineT,  
    "Parameter Low": baselineT * 0.8,
    "Parameter High": baselineT * 1.2,
    "Baseline GWP": baseline_gwp,
    "High": low,
    "Low": high,
})
#%%
sensitivity_lca_results = sorted(sensitivity_lca_results, key=lambda x: abs(x["High"]))
plt.figure(figsize=(10, 6)) 
plt.barh([s["Parameter"] for s in sensitivity_lca_results], 
        [(s["High"] - s["Baseline GWP"]) for s in sensitivity_lca_results],
        color='lightblue', label='+20%')
plt.barh([s["Parameter"] for s in sensitivity_lca_results], 
        [(s["Low"] - s["Baseline GWP"]) for s in sensitivity_lca_results],
        color='lightgreen', label='-20%')
plt.axvline(0, color='gray', linestyle='--')
xticks = plt.xticks()[0]
plt.xticks(xticks, [f"{x+baseline_gwp:.2f}" for x in xticks])
plt.xlabel('GWP (kg CO2 eq/kg products)')
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.legend(title='Impact Level', loc='lower right')
plt.tight_layout()
sensitivity_lca_analysis_fig = plt.gcf()

plt.savefig("sensitivity_lca_analysis.png", dpi=300, bbox_inches="tight")
# %%
