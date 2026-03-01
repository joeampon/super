# %% Import necessary modules
import time
import math
import pandas as pd
import numpy as np

import biosteam as bst 
import thermosteam as tmo
from thermo import SRK
#  import compounds and set thermo  
from ._compounds import *
from ._Hydrocracking_Unit import *
from ._Hydrogen_production import *



from ._Grinder import *
from ._CHScreen import *
from ._RYield import *
from ._Cyclone import *
from ._Sand_Furnace import *
from ._UtilityAgents import *    # Created heat utilities that can heat to high temperatures and cool to sub zero temperatures 
from ._process_yields import *
from ._Compressor import *
from ._feed_handling import *
from ._teapyrolysis import *
from ._tea_wax_mfsp import *


# %%
#--------------------------------------------------------------------------------------------------------------
# Economic Analysis
#----------------------------------------------------------------------------------------------------------------
employee_costs = {
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
    employee_costs[v][0]* employee_costs[v][1]  for v in employee_costs
            ])
print(f"Labor cost: {labor_costs}")
# %%
# %% TEA component

#--------------------------------------------------------------------------------------------------------------
# Economic Analysis: TEA code for MSP
#----------------------------------------------------------------------------------------------------------------

facility_outputs = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]

all_systems = []
for scen_label, scenario in enumerate(scenarios):
    print(f"Running scenario {scen_label+1}: {scenarios_labels[scen_label]} of {len(scenarios)} scenarios")
    system = run_scenario(scenario)
    system.save_report(f"Scenario_{scenarios_labels[scen_label]}_report.xlsx")
    all_systems.append(system)

tea_msp = TEA_MFSP(
    system=all_systems[0],
    IRR=0.1,
    duration=(2020, 2040),
    depreciation="MACRS7",
    income_tax=0.21,
    operating_days=333,
    lang_factor=5.05,  # ratio of total fixed capital cost to equipment cost
    construction_schedule=(0.4, 0.6),
    WC_over_FCI=0.05,  # working capital / fixed capital investment
    labor_cost=labor_costs,
    fringe_benefits=0.4,  # percent of salary for misc things
    property_tax=0.001,
    property_insurance=0.005,
    supplies=0.20,
    maintenance=0.003,
    administration=0.005,
    finance_fraction=0.4,
    finance_years=10,
    finance_interest=0.07,
)
# # %%
# msp = tea_msp.solve_price(all_systems[0].flowsheet.unit.data["Mixer4"].outs[0])
# msp
# print(f"Minimum selling price of Wax for Conventional Pyrolysis: {msp:.3f} USD/kg")
# # %%
# print(tea_msp.installed_equipment_cost)
# %% Conventional pyrolysis and hydrocracking 
msp_cpy = tea_msp.solve_price(all_systems[0].flowsheet.stream.data["Wax"])
msp_cpy
print(f"Minimum selling price of Wax for Conventional Pyrolysis: {msp_cpy:.3f} USD/kg")

#  Conventional pyrolysis and hydrocracking
msp_cpy_hc = tea_msp.solve_price(all_systems[1].flowsheet.stream.data["Naphtha"])
msp_cpy_hc
print(f"Minimum selling price of Naphtha for Conventional Pyrolysis: {msp_cpy_hc:.3f} USD/kg")
#  Thermal-oxodegradation 
msp_oxo = tea_msp.solve_price(all_systems[2].flowsheet.stream.data["Wax"])
msp_oxo
print(f"Minimum selling price of Wax for Thermal-oxodegradation: {msp_oxo:.3f} USD/kg")
#  Thermal-oxodegradation and hydrocracking
msp_oxo_hc = tea_msp.solve_price(all_systems[3].flowsheet.stream.data["Naphtha"])
msp_oxo_hc  
print(f"Minimum selling price of Naphtha for Thermal-oxodegradation: {msp_oxo_hc:.3f} USD/kg")

#  High residence time
msp_hrt = tea_msp.solve_price(all_systems[4].flowsheet.stream.data["Naphtha"])
msp_hrt
print(f"Minimum selling price of Naphtha for High residence time: {msp_hrt:.3f} USD/kg")

#  High residence time and hydrocracking
msp_hrt_hc = tea_msp.solve_price(all_systems[5].flowsheet.stream.data["Naphtha"])
msp_hrt_hc
print(f"Minimum selling price of Naphtha for High residence time: {msp_hrt_hc:.3f} USD/kg")

# %% plot the minimum selling price of the different scenarios against the same products from fossil products

labels = ["CPY\nWax", "TOD\nwax", "CPY-HC\nNaphtha", "TOD-HC\nNaphtha", "HRT\nNaphtha", "HRT-HC\nNaphtha", "Fossil\nNaphtha"]
values = [msp_cpy, msp_oxo, msp_cpy_hc, msp_oxo_hc, msp_hrt, msp_hrt_hc,actual_prices['Naphtha']]
# %%
df_msp = pd.DataFrame({"labels":labels,"values":values})
df_msp.to_excel("Results/Minimum selling price.xlsx")

# %%
colors = ['blue'] * (len(labels) - 1) + ['red']  # Set last bar to red

# Create a bar chart
plt.figure(figsize=(9, 7))
plt.bar(labels, values, color=colors)

# Add labels and title
plt.xlabel("Products")
plt.ylabel("Prices($/kg)")
plt.title("Minimum selling price of products from different scenarios")

# Show the plot
plt.xticks(rotation= 0)  # Rotate x-axis labels for better readability
plt.tight_layout()

plt.savefig("Results/Images/MSP_all_scenarios.png",dpi=300,bbox_inches="tight")

plt.show()
# %%

# **********************************************************************************************************************
# Economic Analysis: TEA code for NPV
# **********************************************************************************************************************


facility_outputs = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]
products_streams ={ "Ethylene": "Ethylene",
                    "Propylene": "Propylene",
                    "Butene": "Butene",
                    "Naphtha": "Naphtha",
                    "Diesel": "Diesel",
                    "Wax": "Wax",
}

def run_TEA(system,products = facility_outputs,irr = 0.1, lf = 5.05,prices= actual_prices, duration = (2020, 2040)):
    tea = TEA(system=system,
                IRR= irr,
                duration= duration,
                depreciation='MACRS7',
                income_tax=0.21,
                operating_days=333,
                lang_factor= lf, # ratio of total fixed capital cost to equipment cost
                construction_schedule=(0.4, 0.6),
                WC_over_FCI=0.05, #working capital / fixed capital investment
                labor_cost=labor_costs,
                fringe_benefits=0.4,# percent of salary for misc things
                property_tax=0.001,
                property_insurance=0.005,
                supplies=0.20,
                maintenance=0.003,
                administration=0.005,
                finance_fraction = 0.4,
                finance_years=10,
                finance_interest=0.07)

    sorted_equipment = sorted(system.units, key=lambda x: x.installed_cost)

    equipment_costs = []
    purchase_costs = []
    for unit in sorted_equipment:
        
        equipment_costs.append([unit.ID, unit.installed_cost])
        purchase_costs.append([unit.ID, unit.purchase_cost])
    
    annual_yield = [system.flowsheet.stream[prod].get_total_flow("kg/year") for prod in products]
    annual_revenue = [system.flowsheet.stream[prod].get_total_flow("kg/year") * prices[prod] for prod in products]
    npv = tea.NPV
    mfsp_table = tea.mfsp_table()
    return (purchase_costs,equipment_costs,mfsp_table,tea,annual_revenue,annual_yield)
# **********************************************************************************************************************
# LCA
# **********************************************************************************************************************

EF = {'Diesel' :4423.19681,    # for 1 cubic meter of diesel
'Electricity':0.65228,
'Gasoline':2339.06178,         # for 1 cubic meter of gasoline
'Natural Gas':0.241,
'Heat_NG': 0.069,
'Steam Production':0.12,
'Transport':0.165,
'Water for cooling':0.00018,
'Hydrogen': 9.34445 #EF for 1 kg H2 used for hydrocracking
}

def run_GWP(syst,df_emi = EF):
    sys_labels = ["Feedstock Collection","Pretreatment & Pyrolysis","Product Fractionation", "Hydrocracking"]
    system_emissions = dict(zip(sys_labels,np.zeros(len(sys_labels))))

    waste_coll_diesel =  248.48/(500/24)/850 # 1. waste collection fuel = 248.48/500 kg/tonne REF Gracida Alvarez et al. 2019; EF is in m3, divide by 850 to convert kg to m3
    MRF_electricity = 286.67/(500/24) # 2. HDPE MRF electricity = 286.67/500 kwh per tonne REF Gracida Alvarez et al. 2019 
    MRF_heat = 541.67/(500/24) # 3. HDPE MRF heat = 541.67/500 MJ/tonne REF Gracida Alvarez et al. 2019
    MRF_diesel = 12.38/(500/24)/850 # 4. HDPE MRF diesel = 12.38/500 kg/tonne REF Gracida Alvarez et al. 2019
    MRF_gasoline = 2.02/(500/24)/748.9 # 5. HDPE MRF gasoline = 2.02/500 kg/tonne REF Gracida Alvarez et al. 2019 
    HDPE_transportation= 1041.67/(500/24) # 6. HDPE transport to facility = 1041.67/500tkm REF Gracida Alvarez et al. 2019
    feed_hr = syst.flowsheet.stream.data["HDPE_Feed"].get_total_flow("tonnes/hr")
    system_emissions["Feedstock Collection"] = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"] + HDPE_transportation*df_emi["Transport"]) * feed_hr # tonnes per day
    
    waste_processing = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"]) * feed_hr
    #  Hydrogen production (per MMscfd H2 produced) and Hydrocracking (per bbl feed)
    
    if scenario['Hydrocracking'] == "No":
        system_emissions["Hydrocracking"] = 0
        H2_prod = 0
        # HP_nat_gas = 0
        HC_diesel = 0
        HC_electricity = 0
        # HP_electricity = 0
        # HP_electricity_hr = HP_electricity*H2_prod # electricity required per hour

    else:
        HC_feed = syst.flowsheet.unit.data["Hydrocracking"].ins[0].get_total_flow("bbl/hr")
        hydrogen_feed = syst.flowsheet.unit.data["Hydrocracking"].ins[1].get_total_flow("kg/hr")
        HC_diesel = 5.3 * HC_feed #Fuel oil, kg 5.3 kg per barrel feed REF Refining Processes 2004 pg 94
        HC_electricity = 6.9 * HC_feed # HC_electricity = 6.9kWh per barrel
        # HC_cooling_water = 0.64 # HC_cooling_water = 0.64 m3 per barrel
        system_emissions["Hydrocracking"] = HC_diesel/850 * df_emi["Diesel"] + HC_electricity * df_emi["Electricity"] + hydrogen_feed * df_emi["Hydrogen"] #+ HC_cooling_water * df_emi["Water for cooling"]

    #  Pyrolysis and pretreatment
    PY_elect = sum([unit.net_power for unit in syst.flowsheet.system.data["sys_pretreatment"].units])
    
    if scenario['Technology'] == "CPY":
        sand_heat = syst.flowsheet.unit.data["furnace"].ins[0].get_total_flow("kg/hr") 
    else:
        sand_heat = 0
    purge_comb = syst.flowsheet.unit.data["Condenser2"].outs[0].get_total_flow("kg/hr")
    system_emissions["Pretreatment & Pyrolysis"] =  PY_elect*df_emi["Electricity"] + sand_heat*df_emi["Heat_NG"] + purge_comb*df_emi["Heat_NG"]
    
    # Product fractionation
    PF_elect = sum([unit.net_power for unit in syst.flowsheet.system.data["sys_Product_Fractionation"].units])
    system_emissions["Product Fractionation"] = PF_elect*df_emi["Electricity"]

# Sensitivity analysis
    waste_processing = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"])
    purge = (purge_comb*df_emi["Heat_NG"])/feed_hr
    other_emission = waste_processing + purge
    #  Hydrogen production (per MMscfd H2 produced) and Hydrocracking (per bbl feed)

    waste_transport = HDPE_transportation 
    electricity_req = (PY_elect + PF_elect)/feed_hr    # + HP_electricity_hr 
    diesel_req = (HC_diesel)/feed_hr
    # natural_gas_req = HP_nat_gas/feed_hr
    nat_gas_for_sand = sand_heat/feed_hr


    sensitivity_factors = {"Waste Transport":waste_transport,"Electricity":electricity_req,"Diesel":diesel_req,"Natural Gas for Sand":nat_gas_for_sand} 
    return (system_emissions, sensitivity_factors,other_emission)
# **********************************************************************************************************************
# Sensitivity Analysis
# **********************************************************************************************************************

sensitivity_analysis_variables = [ "Fixed Capital Investment","Internal rate of return","Feedstock cost","Hydrocracking catalyst cost",
                                    "Electricity cost","Facility capacity","Ethylene price","Propylene price",
                                    "Butene price","Diesel price","Naphtha price","Wax price","hydrogen price"
                                    ]

def get_NPV(lang_factor,IRR,feedstock_cost,hydrocracking_catalyst,
            electricity_cost,facility_capacity,ethylene_price,propylene_price,
            butene_price,diesel_price,naphtha_price,wax_price,hydrogen_price):
    new_price = {"HDPE": feedstock_cost,
            "Ethylene": ethylene_price,
            "Propylene": propylene_price,
            "Butene": butene_price,
            "Naphtha": naphtha_price,
            "Diesel": diesel_price,
            "Wax": wax_price,
            "NG": 7.40 * 1000 * 1.525/28316.8,
            "Hydrocracking catalyst": hydrocracking_catalyst,
            "Hydrogen": hydrogen_price
            }
    capacity = facility_capacity
    bst.settings.electricity_price = electricity_cost
    sys = run_scenario(scenario,capacity=capacity,prices=new_price)
    tonnes = sys.flowsheet.stream.data['HDPE_Feed'].get_total_flow('tonnes/day')
    purchase_cost,equipment_cost,mfsp_table,tea,annual_revenue,annual_yield=run_TEA(sys, lf= lang_factor,irr=IRR,prices=new_price)
    return tea.NPV

def create_df(label, l1, l2, l3, cols):
    data = {'Column 1': l1, 'Column 2': l2, 'Column 3': l3}
    df = pd.DataFrame(data, index=label)
    df.columns = cols
    return df
# %%
actual_IRR = 0.1
actual_lf = 5.05
electricity_cost = 0.069
base = np.array([actual_lf,actual_IRR,actual_prices['HDPE'],actual_prices["Hydrocracking catalyst"],
                electricity_cost,plant_capacity,actual_prices["Ethylene"],actual_prices["Propylene"],
                actual_prices["Butene"],actual_prices["Diesel"],actual_prices["Naphtha"],actual_prices["Wax"],
                actual_prices["Hydrogen"]
                ])                
lower_b = 0.8 * base
upper_b = 1.2 * base

# Extract the annual yield of each product and save in a dataframe
sys_labels = ["Feedstock Collection","Pretreatment & Pyrolysis","Product Fractionation","Hydrocracking"]
system_emissions = dict(zip(sys_labels,np.zeros(len(sys_labels))))

products = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]
df_annual_yield = pd.DataFrame(columns=products)
df_annual_revenue = pd.DataFrame(columns=products)
all_systems = []
all_operating_cost = []
all_capital_cost = []
all_purchase_cost = []
all_FCIs = []
all_NPV = []
all_30_years_NPV = []
all_utility_cost = []
all_teas = []
all_GWP = []

for scen_label, scenario in enumerate(scenarios):
    print(f"Running scenario {scen_label+1}: {scenarios_labels[scen_label]} of {len(scenarios)} scenarios")
    system = run_scenario(scenario)
    system.save_report("Results/Reports/"+ scenarios_labels[scen_label] + ".xlsx")
    all_systems.append(system)
    purchase_cost,equipment_cost,mfsp_table,tea,annual_revenue,annual_yield = run_TEA(system)
    all_capital_cost.append(equipment_cost)
    all_purchase_cost.append(purchase_cost)
    all_operating_cost.append(mfsp_table)
    all_FCIs.append(tea.FCI)
    all_NPV.append(tea.NPV)
    df_annual_yield.loc[scenarios_labels[scen_label]] = annual_yield
    df_annual_revenue.loc[scenarios_labels[scen_label]] = annual_revenue
    all_utility_cost.append(tea.utility_cost)
    all_teas.append(tea)

    tea_30 = run_TEA(system, duration= (2020,2050))[3]
    all_30_years_NPV.append(tea_30.NPV)

    GWP = run_GWP(system)
    all_GWP.append(GWP[0])

# Plots and tables
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")

x = np.arange(len(scenarios_labels))
width = 0.4
fig, ax = plt.subplots(figsize=(8, 6))
rects1 = ax.bar(x - width/2, [x/1e6 for x in all_NPV], width, label='20 years Facility Lifetime')
rects2 = ax.bar(x + width/2, [x/1e6 for x in all_30_years_NPV], width, label='30 years Facility Lifetime')
ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("Net Present Value (MM USD)", color="black")
ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels)
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.)
plt.title("(C) Net Present Value of all Scenarios \n (20 & 30 Years Facility Lifetime)")
plt.savefig("Results/Images/Net Present Value 20 30 years.png",dpi=300,bbox_inches="tight")
plt.show()

df_NPV = pd.DataFrame({'20-years NPV': [x/1e6 for x in all_NPV],'30-years NPV': [x/1e6 for x in all_30_years_NPV] })
df_NPV.index = scenarios_labels
df_NPV.to_excel("Results/NPV table.xlsx")

fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")
plt.title("(C) Net Present Value of all Scenarios")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")

groups = {"Pretreatment & Pyrolysis":['Handling','Mixer','Grinder',
                                    'CHScreen','Mixer2','CFB_Reactor',
                                    'Cyclone1','furnace','cooler'],
        "Product Fractionation Unit": ['Condenser','Heater7','FlashSeparator','Compressor1',
                                        'Heater2','evaporator_ref','compressor_ref','condenser_ref',
                                        'expansion_device','Compressor2','evaporator_ref2',
                                        'compressor_ref2','condenser_ref2','expansion_device2',
                                        'evaporator_ref3','compressor_ref3','condenser_ref3','evaporator_ref4',
                                        'expansion_device3','Condenser2','Pump','Heater6',
                                        'De_ethanizer','EthyleneFractionator','Depropanizer','PropyleneFractionator',
                                        'Heater8','CompressorD2', 'Heater9','Mixer3','Debutanizer','NaphthaSplitter',
                                        'DieselSplitter','Mixer4','NaphthaSplitter2','DieselSplitter2'],
        "Hydrocracking Unit": ['Compressor3','Hydrocracking','Hydrocracking_Unit','H2split'],
        "Others":[]
}

def find_group(equipment):
    for k in groups.keys():
        if equipment in groups[k]:
            return k
    return "Others"

equipment_costs = []
equipment_purchase = []
for i in all_capital_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_costs.append(costs.values())

for i in all_purchase_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_purchase.append(costs.values())

df_cap_cost = pd.DataFrame(equipment_costs, index=scenarios_labels, columns=groups.keys())
df_purchase_cost = pd.DataFrame(equipment_purchase, index=scenarios_labels, columns=groups.keys())
df_cap_cost = df_cap_cost/1e6
df_purchase_cost = df_purchase_cost/1e6

df_cap_cost = df_cap_cost.drop(columns=["Others"]) 
df_cap_cost.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.)
plt.xlabel("Scenarios")
plt.ylabel("Capital Cost (MM USD)")
plt.title("(A) Breakdown of Capital Costs of all Scenarios")
plt.xticks(rotation=0)
plt.savefig("Results/Images/Capital Cost.png",dpi=300,bbox_inches="tight")

df_cap_cost['Total'] = df_cap_cost.sum(axis=1)
df_cap_cost.T.to_excel("Results/cap_cost.xlsx")

df_ope_cost = pd.DataFrame(all_operating_cost, index=scenarios_labels)
df_ope_cost = df_ope_cost.fillna(0)
df_ope_cost = df_ope_cost/1e6

df_ope_summary = pd.DataFrame()
df_ope_summary["Feedstock Cost"] = df_ope_cost["HDPE_Feed"]
df_ope_summary["Utilities"] = df_ope_cost["Utilities"]
df_ope_summary["Depreciaton"] = df_ope_cost["Depreciation"]
df_ope_summary["Operations & Maintenance"] = df_ope_cost["O&M"]
df_ope_summary["Natural Gas"] = df_ope_cost['comb_nat_gas']
df_ope_summary["Hydrogen"] = df_ope_cost["Hydrogen"]
df_ope_summary["Others"] = df_ope_cost["Other"] + df_ope_cost["hydrocracking_catalyst"]

df_plot = df_ope_summary
df_plot.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
plt.xlabel("Scenarios", fontsize="large", color="black")
plt.ylabel("Annual Operating Cost (MM USD)", fontsize="large", color="black")
plt.title("(B) Breakdown of Annual Operating Costs of all Scenarios")
plt.xticks(rotation=0)
plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.)
plt.savefig("Results/Images/Operating Cost.png",dpi=300,bbox_inches="tight")

fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")

df_annual_revenue2 = df_annual_revenue/1e6 
df_annual_revenue2.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")
plt.xticks(rotation='horizontal')
plt.ylabel("Annual Revenue (MM USD)",fontsize="large",color = "black")
plt.legend(bbox_to_anchor=(1.02, 0.7), loc='upper left', borderaxespad=0.)
plt.savefig("Results/Images/Annual Revenue.png",dpi=300,bbox_inches="tight")
df_annual_revenue_3 = (df_annual_revenue/1e6).copy()
df_annual_revenue_3['Total'] = df_annual_revenue_3.sum(axis=1)
df_annual_revenue_3.T.to_excel("Results/annual_revenue.xlsx")

df_plot = df_annual_yield/1e6
df_plot.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")
plt.xticks(rotation='horizontal')
plt.ylabel("Annual Output (kilotonnes/year)",fontsize="large",color = "black")
plt.legend(bbox_to_anchor=(1.15, 0.7), loc='upper center', borderaxespad=0.)
plt.savefig("Results/Images/Annual Yield.png",dpi=300,bbox_inches="tight")
df_plot["Total"] = df_plot.sum(axis=1)
df_annual_yield2 = df_plot.copy()
df_plot.T.to_excel("Results/annual_yield.xlsx")

df_GWP_perhr = pd.DataFrame(all_GWP, index=scenarios_labels)
df_GWP_perhr.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.ylabel("GWP (kg CO2-eq/hour of operation)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per hour of all Scenarios")
plt.savefig("Results/Images/GWP per hr.png",dpi=300,bbox_inches="tight")
df_GWP_perhr.to_excel("Results/GWP per hr.xlsx")

df_GWP_tonne = df_GWP_perhr/(plant_capacity/24)
df_GWP_tonne.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.xticks(rotation='horizontal')
plt.ylabel("GWP (kg CO2-eq/tonne of waste HDPE)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per tonne of all Scenarios")
plt.savefig("Results/Images/GWP per tonne.png",dpi=300,bbox_inches="tight")
df_GWP_tonne.to_excel("Results/GWP per tonne of waste HDPE.xlsx")

df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)

Total = df_GWP_tonne.sum(axis= 1)
percentage_df = df_GWP_tonne.divide(Total, axis=0) * 100
percentage_df.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xticks(rotation='horizontal')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
plt.ylabel("Percentage contribution to GWP (%)")
plt.xlabel("Scenarios")
plt.title("(B) Percentage contribution to GWP of all Scenarios")
plt.savefig("Results/Images/Percentage contribution to GWP.png",dpi=300,bbox_inches="tight")

df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)
df_GWP_tonne_2.T.to_excel("Results/GWP per tonne of waste HDPE.xlsx")

avoided_emission_factors = {"Ethylene": 1.37893,
                            "Propylene": 1.41647,
                            "Butene": 1.50706,  
                            "Naphtha": 0.43911,
                            "Diesel": 0.49756,
                            "Wax": 0.75109}
                
primary_product = {"CPY": "Wax",
                    "CPY-HC": "Naphtha",
                    "TOD": "Wax",
                    "TOD-HC": "Naphtha",
                    "HRT": "Naphtha",
                    "HRT-HC": "Naphtha"
                    }

df_yield_per_kg = df_annual_yield.copy()
row_sums = df_yield_per_kg.sum(axis=1)
df_yield_per_kg = df_yield_per_kg.div(row_sums, axis=0)
df_avoided_emission = df_yield_per_kg.apply(lambda row: row * avoided_emission_factors[row.name],axis =0)

for key,value in primary_product.items():
    df_avoided_emission[value][key] = 0

df_avoided_emission["Total"] = df_avoided_emission.sum(axis=1)

df_avoided_emission["Study emissions"] = df_GWP_tonne_2["Total"]/1000
df_avoided_emission["Primary product emission"] = df_avoided_emission["Study emissions"] - df_avoided_emission["Total"] 

df_avoided_emission["Primary product emission per kg"] = np.zeros(len(df_avoided_emission))
df_avoided_emission["Virgin product emission"] = np.zeros(len(df_avoided_emission))
for key,value in primary_product.items():
    df_avoided_emission["Primary product emission per kg"][key] = df_avoided_emission['Primary product emission'][key]/ df_yield_per_kg[value][key]
    df_avoided_emission["Virgin product emission"][key] = avoided_emission_factors[primary_product[key]]

x = np.arange(len(scenarios_labels))
width = 0.4
fig, ax = plt.subplots(figsize=(8, 6))
rects1 = ax.bar(x - width/2, df_avoided_emission["Primary product emission per kg"], width, label='Study emissions')
rects2 = ax.bar(x + width/2, df_avoided_emission["Virgin product emission"], width, label='Virgin product')
ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("GWP", color="black")
ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels)
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.)
plt.show()

wax_label = ["CPY","TOD","Virgin"]
naphtha_label = ["CPY-HC","TOD-HC","HRT","HRT-HC","Virgin"]
wax_list = [df_avoided_emission["Primary product emission per kg"]["CPY"],
            df_avoided_emission["Primary product emission per kg"]["TOD"],
            df_avoided_emission["Virgin product emission"]["CPY"]]
naphtha_list = [df_avoided_emission["Primary product emission per kg"]["CPY-HC"],
                df_avoided_emission["Primary product emission per kg"]["TOD-HC"],
                df_avoided_emission["Primary product emission per kg"]["HRT"],
                df_avoided_emission["Primary product emission per kg"]["HRT-HC"],
                df_avoided_emission["Virgin product emission"]["CPY-HC"]
                ]

width = 0.18
colors = ["blue","blue","blue","blue","blue"]
colors2 = ["grey","grey","grey"]
fig, ax = plt.subplots(figsize=(8, 6))
x_positions = [0.1,0.3,0.5,0.7,0.9]
x2_positions = [1.2,1.4,1.6]
rects1 = ax.bar(x_positions,naphtha_list, width,color = colors, label = "Naphtha")
rects2 = ax.bar(x2_positions,wax_list,width,color=colors2, label = "Wax")
ax.set_ylabel("GWP (kg CO2-eq)")
ax.set_xticks(x_positions + x2_positions)
ax.set_xticklabels(naphtha_label + wax_label)
ax.legend()
ax.axhline(0, color='black', linewidth=0.5)
ax.set_title("(C) Primary Products Emissons per kg of all Scenarios vs Virgin Products Emissions")
plt.tight_layout()
plt.show()
# %%
actual_IRR = 0.1
actual_lf = 5.05
electricity_cost = 0.069
base = np.array([actual_lf,actual_IRR,actual_prices['HDPE'],actual_prices["Hydrocracking catalyst"],
            electricity_cost,plant_capacity,actual_prices["Ethylene"],actual_prices["Propylene"],
            actual_prices["Butene"],actual_prices["Diesel"],actual_prices["Naphtha"],actual_prices["Wax"],
            actual_prices["Hydrogen"]
            ])                
lower_b = 0.8 * base
upper_b = 1.2 * base
# upper_b = np.array([actual_lf * 1.2,
#                 actual_IRR * 1.2,
#                 actual_prices['HDPE'] * 1.2,
#                 actual_prices["Hydrocracking catalyst"] * 1.2,
#                 electricity_cost *1.2,
#                 295,  #300 capacity is throwing error. using 297 instead 
#                 actual_prices["Ethylene"] * 1.2,
#                 actual_prices["Propylene"]* 1.2,
#                 actual_prices["Butene"]* 1.2,
#                 actual_prices["Diesel"]* 1.2,
#                 actual_prices["Naphtha"]* 1.2,
#                 actual_prices["Wax"]* 1.2,
#                 actual_prices["Hydrogen"]* 1.2
#                 ])

# **********************************************************************************************************************
#  
# **********************************************************************************************************************

# Extract the annual yield of each product and save in a dataframe
sys_labels = ["Feedstock Collection","Pretreatment & Pyrolysis","Product Fractionation","Hydrocracking"]
system_emissions = dict(zip(sys_labels,np.zeros(len(sys_labels))))

products = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]
df_annual_yield = pd.DataFrame(columns=products)
df_annual_revenue = pd.DataFrame(columns=products)
all_systems = []
all_operating_cost = []
all_capital_cost = []
all_purchase_cost = []
all_FCIs = []
all_NPV = []
all_30_years_NPV = []
all_utility_cost = []
all_teas = []
all_GWP = []



# %% 
# olu = 0
for scen_label, scenario in enumerate(scenarios):
print(f"Running scenario {scen_label+1}: {scenarios_labels[scen_label]} of {len(scenarios)} scenarios")
system = run_scenario(scenario)
system.save_report("Results/Reports/"+ scenarios_labels[scen_label] + ".xlsx")
all_systems.append(system)
purchase_cost,equipment_cost,mfsp_table,tea,annual_revenue,annual_yield = run_TEA(system)
all_capital_cost.append(equipment_cost)
all_purchase_cost.append(purchase_cost)
all_operating_cost.append(mfsp_table)
all_FCIs.append(tea.FCI)
all_NPV.append(tea.NPV)
df_annual_yield.loc[scenarios_labels[scen_label]] = annual_yield
df_annual_revenue.loc[scenarios_labels[scen_label]] = annual_revenue
all_utility_cost.append(tea.utility_cost)
all_teas.append(tea)

tea_30 = run_TEA(system, duration= (2020,2050))[3]
all_30_years_NPV.append(tea_30.NPV)

GWP = run_GWP(system)
all_GWP.append(GWP[0])

# **********************************************************************************************************************
# Conduct NPV Sensitivity Analysis for all scenarios
# **********************************************************************************************************************

npv_mean_case = get_NPV(*(tuple(base)))/1e6
print(f"npv baseline: ${npv_mean_case:,.2f} MM")
npv_actual = npv_mean_case * np.ones(len(sensitivity_analysis_variables))

npv_lowerb = []
npv_upperb = []
for i in range(len(sensitivity_analysis_variables)):
    print(f"Working on {sensitivity_analysis_variables[i]}")
    new = base.copy() 
    new[i] = upper_b[i]
    npv_u = get_NPV(*tuple(new))/1e6
    npv_upperb.append(npv_u)

    new = base.copy() 
    new[i] = lower_b[i]
    npv_l = get_NPV(*tuple(new))/1e6
    npv_lowerb.append(npv_l)
    print(f"Worked on {sensitivity_analysis_variables[i]} with upper NPV = {npv_u:,.2f} MM and lower NPV = {npv_l:,.2f} MM and actual NPV = {npv_mean_case:,.2f} MM")
    print("****************************************************************************************")
    print("****************************************************************************************")

npv_lowerb = np.array(npv_lowerb)
npv_upperb = np.array(npv_upperb)
df_sen = create_df(sensitivity_analysis_variables,npv_lowerb,npv_actual,npv_upperb,["Lower","actual","Upper"])
df_title = "Results/Sensitivity Tables/NPV_sensitivity"+ scenarios_labels[scen_label] + ".xlsx"
df_sen.to_excel(df_title)

pairs = zip(np.abs(npv_upperb-npv_actual),npv_lowerb,npv_upperb,npv_actual,sensitivity_analysis_variables)
sorted_pairs = sorted(pairs)

tuples = zip(*sorted_pairs)
l1,l2,l3,l4,l5 = [ list(tuple) for tuple in  tuples]

plt.figure(figsize=(7,5))
plt.rcParams['font.size'] = 12
for row in zip(l2, l3, l4, l5, range(len(sensitivity_analysis_variables))):
    plt.broken_barh([
        (row[0], row[2]-row[0]), 
        (row[2], row[1]-row[2])], 
        (row[4]*6+1, 5), 
        facecolors=('blue','red'))
plt.xlabel("NPV(MM USD)")
plt.yticks(ticks = [3.5 + 6*i for i in range(len(l5))],labels = l5)
plt.title(scenarios_labels[scen_label] + " NPV Sensitivity to Key Parameters")
plt.grid(True)

title = "Results/Sensitivity Images/Sensitivity Analysis NPV " + scenarios_labels[scen_label] + ".png" 
plt.savefig(title,dpi=300,bbox_inches="tight")
plt.show()

# **********************************************************************************************************************
# Conduct LCA Sensitivity Analysis for all scenarios
# **********************************************************************************************************************
# sensitivity_factors = {"Waste Transport":waste_transport,"Electricity":electricity_req,"Diesel":diesel_req,"Gasoline":gasoline_req,"Natural Gas":natural_gas_req} 

# waste_transport = HDPE_transportation 
# electricity_req = HP_electricity_hr + (PY_elect + PF_elect)/feed_hr
# diesel_req = (HC_diesel)/feed_hr
# gasoline_req = MRF_gasoline/feed_hr
# natural_gas_req = HP_nat_gas/feed_hr
# nat_gas_for_sand = sand_heat/feed_hr


sensitivity_var = ["MRF Distance to refinery", "Electricity", "Diesel for product upgrading","Natural gas for process heat"]
sensitivity_factors = GWP[1]
base_g = np.array([x for x in sensitivity_factors.values()])
upper_bg = 0.8 * base_g
lower_bg = 1.2 * base_g
other_emissions = GWP[2]
def sens_GWP(factors,EF):
    return other_emissions + factors[0] * EF["Transport"] + factors[1] * EF["Electricity"]+ factors[2] * EF["Diesel"]/850  + factors[3] *  EF["Heat_NG"]


GWP_mean_case = sens_GWP(base_g,EF)
print(f"GWP baseline: {GWP_mean_case:,.2f} kg CO2-eq")
GWP_actual = GWP_mean_case * np.ones(len(sensitivity_var))

GWP_lowerb = []
GWP_upperb = []

for i in range(len(sensitivity_var)):
    print(f"Worked on {sensitivity_var[i]}")

    new_g = base_g.copy() 
    new_g[i] = upper_bg[i]
    GWP_u = sens_GWP(new_g,EF)
    GWP_upperb.append(GWP_u)

    new_g = base_g.copy() 
    new_g[i] = lower_bg[i]
    GWP_l = sens_GWP(new_g,EF)
    GWP_lowerb.append(GWP_l)
    print(f"Worked on {sensitivity_var[i]} with upper GWP = {GWP_u:,.2f} kg CO2-eq and lower GWP = {GWP_l:,.2f} kg CO2-eq and actual GWP = {GWP_mean_case:,.2f} kg CO2-eq")
    print("****************************************************************************************")
    print("****************************************************************************************")

GWPlowerb = np.array(GWP_lowerb)
GWPupperb = np.array(GWP_upperb)
df_sen_g = create_df(sensitivity_var,GWPlowerb,GWP_actual,GWPupperb,["Lower","actual","Upper"])
df_title = "Results/Sensitivity Tables/GWP_sensitivity"+ scenarios_labels[scen_label] + ".xlsx"
df_sen_g.to_excel(df_title)

pairs = zip(np.abs(GWPupperb-GWP_actual),GWP_lowerb,GWP_upperb,GWP_actual,sensitivity_var)
sorted_pairs = sorted(pairs)

tuples = zip(*sorted_pairs)
l1,l2,l3,l4,l5 = [ list(tuple) for tuple in  tuples]
plt.figure(figsize=(7,5))
plt.rcParams['font.size'] = 12
for row in zip(l2, l3, l4, l5, range(len(sensitivity_var))):
    plt.broken_barh([
        (row[0], row[2]-row[0]), 
        (row[2], row[1]-row[2])], 
        (row[4]*6+1, 5), 
        facecolors=('blue','red'))
plt.xlabel("GWP(kg CO2-eq)")
plt.yticks(ticks = [3.5 + 6*i for i in range(len(l5))],labels = l5)
plt.title(scenarios_labels[scen_label] + " GWP Sensitivity to Key Parameters")
plt.grid(True)

title = "Results/Sensitivity Images/SensitivitySensitivity Analysis GWP " + scenarios_labels[scen_label] + ".png"
plt.savefig(title,dpi=300,bbox_inches="tight")
plt.show()
# olu += 1
# if olu == 2:
#     break
# **********************************************************************************************************************

# **********************************************************************************************************************

# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")


# %%
x = np.arange(len(scenarios_labels))
width = 0.4  # Width of the bars

fig, ax = plt.subplots(figsize=(8, 6))

rects1 = ax.bar(x - width/2, [x/1e6 for x in all_NPV], width, label='20 years Facility Lifetime')
rects2 = ax.bar(x + width/2, [x/1e6 for x in all_30_years_NPV], width, label='30 years Facility Lifetime')

ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("Net Present Value (MM USD)", color="black")

ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels) #, rotation='horizontal')
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) # (title="Legend")

plt.title("(C) Net Present Value of all Scenarios \n (20 & 30 Years Facility Lifetime)")
plt.savefig("Results/Images/Net Present Value 20 30 years.png",dpi=300,bbox_inches="tight")

plt.show()
# %%
df_NPV = pd.DataFrame({'20-years NPV': [x/1e6 for x in all_NPV],'30-years NPV': [x/1e6 for x in all_30_years_NPV] })
df_NPV.index = scenarios_labels
df_NPV.to_excel("Results/NPV table.xlsx")



# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.title("(C) Net Present Value of all Scenarios")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")


# %%

groups = {"Pretreatment & Pyrolysis":['Handling','Mixer','Grinder',
                                    'CHScreen','Mixer2','CFB_Reactor',
                                    'Cyclone1','furnace','cooler'],
        "Product Fractionation Unit": ['Condenser','Heater7','FlashSeparator','Compressor1',
                                        'Heater2','evaporator_ref','compressor_ref','condenser_ref',
                                        'expansion_device','Compressor2','evaporator_ref2',
                                        'compressor_ref2','condenser_ref2','expansion_device2',
                                        'evaporator_ref3','compressor_ref3','condenser_ref3','evaporator_ref4',
                                        'expansion_device3','Condenser2','Pump','Heater6',
                                        'De_ethanizer','EthyleneFractionator','Depropanizer','PropyleneFractionator',
                                        'Heater8','CompressorD2', 'Heater9','Mixer3','Debutanizer','NaphthaSplitter',
                                        'DieselSplitter','Mixer4','NaphthaSplitter2','DieselSplitter2'],
        "Hydrocracking Unit": ['Compressor3','Hydrocracking','Hydrocracking_Unit','H2split'],
        "Others":[]
}

# groups = {"Pretreatment & Pyrolysis":['Handling','Mixer','Grinder',
#                                     'CHScreen','Mixer2','CFB_Reactor',
#                                     'Cyclone1','furnace','cooler','Condenser'],
#         "Product Fractionation Unit": ['Heater7','FlashSeparator','Compressor1',
#                                         'Heater2','evaporator_ref','compressor_ref','condenser_ref',
#                                         'expansion_device','Compressor2','evaporator_ref2',
#                                         'compressor_ref2','condenser_ref2','expansion_device2',
#                                         'evaporator_ref3','compressor_ref3','condenser_ref3',
#                                         'expansion_device3','Condenser2','Pump','Heater6',
#                                         'De_ethanizer','Depropanizer','PropyleneFractionator',
#                                         'EthyleneFractionator','Mixer3','Debutanizer','NaphthaSplitter',
#                                         'DieselSplitter','Mixer4'],
#         "Hydrogen Production Unit": ['Steam_Reformer', 'Mixer5', 'Hydrogen_production', 'PSA'],
#         "Hydrocracking Unit": ['Compressor3','Hydrocracking','Hydrocracking_Unit','H2split','NaphthaSplitter2',
#                                 'DieselSplitter2'],
#         "Other":[]
# }
# %%

def find_group(equipment):
    for k in groups.keys():
        if equipment in groups[k]:
            return k
    return "Others"


# %%
# equipment_ids = [i[0] for i in all_capital_cost[1]]
equipment_costs = []
equipment_purchase = []
for i in all_capital_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_costs.append(costs.values())

for i in all_purchase_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_purchase.append(costs.values())
df_cap_cost = pd.DataFrame(equipment_costs, index=scenarios_labels, columns=groups.keys())
df_purchase_cost = pd.DataFrame(equipment_purchase, index=scenarios_labels, columns=groups.keys())
df_cap_cost = df_cap_cost/1e6
df_purchase_cost = df_purchase_cost/1e6

df_cap_cost = df_cap_cost.drop(columns=["Others"]) 
df_cap_cost.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) #loc='upper center', ncols=3, 
# plt.legend(bbox_to_anchor=(0.5, 1.20), loc='upper center', borderaxespad=0., ncol=3)
plt.xlabel("Scenarios")
plt.ylabel("Capital Cost (MM USD)")
plt.title("(A) Breakdown of Capital Costs of all Scenarios")
plt.xticks(rotation=0)
plt.savefig("Results/Images/Capital Cost.png",dpi=300,bbox_inches="tight")

df_cap_cost['Total'] = df_cap_cost.sum(axis=1)
df_cap_cost.T.to_excel("Results/cap_cost.xlsx")
# %%
df_ope_cost = pd.DataFrame(all_operating_cost, index=scenarios_labels)
df_ope_cost = df_ope_cost.fillna(0)
df_ope_cost = df_ope_cost/1e6


#  %%
df_ope_summary = pd.DataFrame()
df_ope_summary["Feedstock Cost"] = df_ope_cost["HDPE_Feed"]
df_ope_summary["Utilities"] = df_ope_cost["Utilities"]
df_ope_summary["Depreciaton"] = df_ope_cost["Depreciation"]
df_ope_summary["Operations & Maintenance"] = df_ope_cost["O&M"]
df_ope_summary["Natural Gas"] = df_ope_cost['comb_nat_gas']
df_ope_summary["Hydrogen"] = df_ope_cost["Hydrogen"]
df_ope_summary["Others"] = df_ope_cost["Other"] + df_ope_cost["hydrocracking_catalyst"]

df_plot = df_ope_summary
df_plot.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
# plt.xlabel("Scenarios")
plt.xlabel("Scenarios", fontsize="large", color="black")
plt.ylabel("Annual Operating Cost (MM USD)", fontsize="large", color="black")
plt.title("(B) Breakdown of Annual Operating Costs of all Scenarios")
plt.xticks(rotation=0)

plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) #loc='upper center', ncols=3, 
plt.savefig("Results/Images/Operating Cost.png",dpi=300,bbox_inches="tight")
# df_ope_cost.to_excel("Results/ope_cost.xlsx")
# df_ope_summary.to_excel("Results/ope_summary.xlsx")


# %%
# equipment_costs
# %%
# equipment_ids2 = [i[0] for i in all_operating_cost[1]]
# equipment_costs2 = []
# for i in all_operating_cost:
#     costs = {k:0 for k in groups.keys()}
#     for j in range(len(i)):
#         group = find_group(equipment_ids2[j])
#         costs[group] += i[j][1]
#     equipment_costs2.append(costs.values())
# df = pd.DataFrame(equipment_costs2, index=scenarios_labels, columns=groups.keys())
# df.plot.bar(stacked=True, figsize=(14,10))
# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
# %%
# equipment_ids = [i[0] for i in all_purchase_cost[1]]
# equipment_costs = []
# for i in all_purchase_cost:
#     costs = {k:0 for k in groups.keys()}
#     for j in range(len(i)):
#         group = find_group(i[j][0])
#         costs[group] += i[j][1]
#     equipment_costs.append(costs.values())
# df_cap_cost2 = pd.DataFrame(equipment_costs, index=scenarios_labels, columns=groups.keys())
# df_cap_cost2.plot.bar(stacked=True, figsize=(9,7))
# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)


# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
# plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")

# %%
df_annual_revenue2 = df_annual_revenue/1e6 
df_annual_revenue2.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.xticks(rotation='horizontal')

plt.ylabel("Annual Revenue (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.legend(bbox_to_anchor=(1.02, 0.7), loc='upper left', borderaxespad=0.)
# plt.show()
plt.savefig("Results/Images/Annual Revenue.png",dpi=300,bbox_inches="tight")
df_annual_revenue_3 = (df_annual_revenue/1e6).copy()
df_annual_revenue_3['Total'] = df_annual_revenue_3.sum(axis=1)
df_annual_revenue_3.T.to_excel("Results/annual_revenue.xlsx")

# %%

# %%
df_plot = df_annual_yield/1e6
df_plot.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.xticks(rotation='horizontal')
plt.ylabel("Annual Output (kilotonnes/year)",fontsize="large",color = "black")#,fontweight ="bold")
plt.legend(bbox_to_anchor=(1.15, 0.7), loc='upper center', borderaxespad=0.)
plt.savefig("Results/Images/Annual Yield.png",dpi=300,bbox_inches="tight")
df_plot["Total"] = df_plot.sum(axis=1)
df_annual_yield2 = df_plot.copy()
df_plot.T.to_excel("Results/annual_yield.xlsx")
# %%


# %%
df_GWP_perhr = pd.DataFrame(all_GWP, index=scenarios_labels)
df_GWP_perhr.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.ylabel("GWP (kg CO2-eq/hour of operation)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per hour of all Scenarios")
plt.savefig("Results/Images/GWP per hr.png",dpi=300,bbox_inches="tight")
df_GWP_perhr.to_excel("Results/GWP per hr.xlsx")

# %%
df_GWP_tonne = df_GWP_perhr/(plant_capacity/24)
df_GWP_tonne.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.xticks(rotation='horizontal')
plt.ylabel("GWP (kg CO2-eq/tonne of waste HDPE)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per tonne of all Scenarios")
plt.savefig("Results/Images/GWP per tonne.png",dpi=300,bbox_inches="tight")
df_GWP_tonne.to_excel("Results/GWP per tonne of waste HDPE.xlsx")


# %%

df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)
df_GWP_tonne_2

# %%
Total = df_GWP_tonne.sum(axis= 1)
percentage_df = df_GWP_tonne.divide(Total, axis=0) * 100
percentage_df.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xticks(rotation='horizontal')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
plt.ylabel("Percentage contribution to GWP (%)")
plt.xlabel("Scenarios")
plt.title("(B) Percentage contribution to GWP of all Scenarios")
plt.savefig("Results/Images/Percentage contribution to GWP.png",dpi=300,bbox_inches="tight")
percentage_df
# %%
df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)
df_GWP_tonne_2.T.to_excel("Results/GWP per tonne of waste HDPE.xlsx")
# %%
avoided_emission_factors = {"Ethylene": 1.37893,
                            "Propylene": 1.41647,
                            "Butene": 1.50706,  
                            "Naphtha": 0.43911,
                            "Diesel": 0.49756,
                            "Wax": 0.75109}
                
# %%
primary_product = {"CPY": "Wax",
                    "CPY-HC": "Naphtha",
                    "TOD": "Wax",
                    "TOD-HC": "Naphtha",
                    "HRT": "Naphtha",
                    "HRT-HC": "Naphtha"
                    }


# %%
df_yield_per_kg = df_annual_yield.copy()
row_sums = df_yield_per_kg.sum(axis=1)
df_yield_per_kg = df_yield_per_kg.div(row_sums, axis=0)
df_avoided_emission = df_yield_per_kg.apply(lambda row: row * avoided_emission_factors[row.name],axis =0)

# Relace primary products with zero
for key,value in primary_product.items():
    df_avoided_emission[value][key] = 0

# update total avoided emissions per kg
df_avoided_emission["Total"] = df_avoided_emission.sum(axis=1)

# add study emissions to the table 
df_avoided_emission["Study emissions"] = df_GWP_tonne_2["Total"]/1000
df_avoided_emission["Primary product emission"] = df_avoided_emission["Study emissions"] - df_avoided_emission["Total"] 

# %%
df_avoided_emission["Primary product emission per kg"] = np.zeros(len(df_avoided_emission))
df_avoided_emission["Virgin product emission"] = np.zeros(len(df_avoided_emission))
for key,value in primary_product.items():
    df_avoided_emission["Primary product emission per kg"][key] = df_avoided_emission['Primary product emission'][key]/ df_yield_per_kg[value][key]
    df_avoided_emission["Virgin product emission"][key] = avoided_emission_factors[primary_product[key]]
# %%
df_avoided_emission 
# %%

x = np.arange(len(scenarios_labels))
width = 0.4  # Width of the bars

fig, ax = plt.subplots(figsize=(8, 6))

rects1 = ax.bar(x - width/2, df_avoided_emission["Primary product emission per kg"], width, label='Study emissions')
rects2 = ax.bar(x + width/2, df_avoided_emission["Virgin product emission"], width, label='Virgin product')

ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("GWP", color="black")

ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels) #, rotation='horizontal')
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) # (title="Legend")

# plt.title("(C) Net Present Value of all Scenarios \n (20 & 30 Years Facility Lifetime)")
# plt.savefig("Results/Images/Net Present Value 20 30 years.png",dpi=300,bbox_inches="tight")

plt.show()
# %%
wax_label = ["CPY","TOD","Virgin"]
naphtha_label = ["CPY-HC","TOD-HC","HRT","HRT-HC","Virgin"]
wax_list = [df_avoided_emission["Primary product emission per kg"]["CPY"],
            df_avoided_emission["Primary product emission per kg"]["TOD"],
            df_avoided_emission["Virgin product emission"]["CPY"]]
naphtha_list = [df_avoided_emission["Primary product emission per kg"]["CPY-HC"],
                df_avoided_emission["Primary product emission per kg"]["TOD-HC"],
                df_avoided_emission["Primary product emission per kg"]["HRT"],
                df_avoided_emission["Primary product emission per kg"]["HRT-HC"],
                df_avoided_emission["Virgin product emission"]["CPY-HC"]
                ]

width = 0.18  # Width of the bars
colors = ["blue","blue","blue","blue","blue"]
colors2 = ["grey","grey","grey"]
fig, ax = plt.subplots(figsize=(8, 6))
x_positions = [0.1,0.3,0.5,0.7,0.9]
x2_positions = [1.2,1.4,1.6]
rects1 = ax.bar(x_positions,naphtha_list, width,color = colors, label = "Naphtha")
rects2 = ax.bar(x2_positions,wax_list,width,color=colors2, label = "Wax")

# Add labels and title
# ax.set_xlabel("Categories")
ax.set_ylabel("GWP (kg CO2-eq)")
# ax.set_title("Bar Chart with Custom Colors")

ax.set_xticks(x_positions + x2_positions)
ax.set_xticklabels(naphtha_label + wax_label)
# ax.legend(bbox_to_anchor=(1., 0.7), borderaxespad=0.) # (title="Legend")
ax.legend()


# Add a line at zero on the y-axis
ax.axhline(0, color='black', linewidth=0.5)

# Add a legend
ax.set_title("(C) Primary Products Emissons per kg of all Scenarios vs Virgin Products Emissions")

# Show the plot
plt.tight_layout()
plt.show()
# %%
