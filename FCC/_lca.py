#%%
import sys 
sys.path.insert(0, '/Users/markmw/Library/CloudStorage/OneDrive-IowaStateUniversity/General - SESA Home/Scripts/sesalca')

from sesalca import * 
import pandas as pd
import math
import matplotlib.pyplot as plt
# %%
def get_impact_factors():
    init()
    resources = [
        "Butane",
        "Naphtha",
        "Diesel",
        "Ethylene",
        "Propylene",
        "Electricity, medium voltage",
        "Natural gas",
        "Wax",
        "Hydrogen"
    ]
    processes = {
        p: get_processes("market for " + p)[0]
        for p in resources
    }
    efs = {
        p: get_total_impacts(processes[p])
        for p in resources
    }

    # add the process name to each impact factor
    for p in resources:
        efs[p]['Process'] = processes[p]

    df = pd.DataFrame(efs).T
    df.to_csv("resource_efs.csv")
    return df

# get_impact_factors()
# %%
# Feeds
# [<Stream: HDPE_Feed>,
#  <Stream: pyrolysis_oxygen>,
#  <Stream: fluidizing_gas>,
#  <Stream: comb_nat_gas>,
#  <Stream: sand>,
#  <Stream: cracking_catalyst>,
#  <Stream: air>,
#  <Stream: steam>]

# Products
# [<Stream: Propylene>,
#  <Stream: FCCOffGas>,
#  <Stream: ExcessH2>,
#  <Stream: ExcessH2O>,
#  <Stream: Naphtha>,
#  <Stream: Diesel>,
#  <Stream: Wax>,
#  <Stream: Butene>,
#  <Stream: Ethylene>]
#%%
streamMaps = {
    "comb_nat_gas": "Natural gas",
    "Propylene": "Propylene",
    "Naphtha": "Naphtha",
    "Diesel": "Diesel",
    "Ethylene": "Ethylene",
    "Butene": "Butane",
    "Wax": "Wax",
    "ExcessH2": "Hydrogen"
}

factors = {
    "comb_nat_gas": 0.8, # m3 to kg conversion factor
    "Propylene": -1.0,
    "Naphtha": -1.0,
    "Diesel": -1.0,
    "Ethylene": -1.0,
    "Butene": -1.0,
    "Wax": -1.0,
    "ExcessH2": -1.0
    
}
#%%
ef = pd.read_csv("resource_efs.csv", index_col=0)
def get_lca(s):
    impacts = {}
    for p in s.feeds + s.products:
        if p.ID in streamMaps.keys():
            res = streamMaps[p.ID]
            impacts[res] = {}
            for impact in ef.columns[0:-4]:
                if impact not in impacts[res]:
                    impacts[res][impact] = 0
                impacts[res][impact] += p.F_mass * ef.loc[res, impact]*factors[p.ID]
            impacts[res]["Amount"] = p.F_mass * factors[p.ID]
    
    impacts["Electricity"] = {
        c: s.power_utility.consumption*3.6 * ef.loc["Electricity, medium voltage", c]
        for c in ef.columns[0:-4]
    }
    impacts["Electricity"]["Amount"] = s.power_utility.consumption*3.6  # kWh to MJ

    net_duty = sum([u.duty for u in s.heat_utilities if u.duty < 0])
    impacts["Heat"] = {
        c: net_duty * ef.loc["Natural gas", c] / 1000 / 3600  # ef in MJ, duty in kJ/hr
        for c in ef.columns[0:-4]
    }
    impacts["Heat"]["Amount"] = net_duty / 1000 / 3600  # kJ/hr to MJ/s

    impacts["FCCOffGas"] = {
        c:  0
        for c in ef.columns[0:-4]
    }
    impacts["FCCOffGas"]["Amount"] = s.flowsheet.stream["FCCOffGas"].F_mass
    impacts["FCCOffGas"]['Global warming (kg CO2 eq)'] = s.flowsheet.stream["FCCOffGas"].imass["CO2"] + s.flowsheet.stream["FCCOffGas"].imass["CH4"]*32 # kg CO2e/kg FCC off-gas
    return impacts

#%%
# %%
