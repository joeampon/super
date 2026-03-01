import os
import pandas as pd

# sesalca is only needed for regenerating impact factors (get_impact_factors)
try:
    import sys as _sys
    _sys.path.insert(0, '/Users/markmw/Library/CloudStorage/OneDrive-IowaStateUniversity/General - SESA Home/Scripts/sesalca')
    from sesalca import init, get_processes, get_total_impacts
except ImportError:
    pass


def get_impact_factors():
    init()
    resources = [
        "Benzene",
        "Acetic acid",
        "Acetaldehyde",
        "Heavy fuel oil",
        "Lubricating oil",
        "Steam",
        "Treatment of waste platic",
        "Oxygen",
        "Methanol",
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
    df.to_csv(os.path.join(_project_root, "resource_efs.csv"))
    return df


# Load precomputed impact factors (CSV lives in project root)
_module_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_module_dir)
ef = pd.read_csv(os.path.join(_project_root, "resource_efs.csv"), index_col=0)

# Maps BioSTEAM stream IDs to LCA resource names
streamMaps = {
    "comb_nat_gas": "Natural gas",
    "CPY_residue": "Heavy fuel oil",
    "CPY_AromaticsO": "Benzene",
    "SS_BTX": "Benzene",
    "PLASMA_Carbonyls": "Acetaldehyde",
    "PLASMA_Acids": "Acetic acid",
    "PLASMA_Alcohols": "Methanol",
    "PLASMA_C30": "Lubricating oil",
    "PLASMA_Olefins": "Butane",
    "PLASMA_Paraffins": "Naphtha",
    "SS_Diesel": "Diesel",
    "SS_Wax": "Wax",
    "SS_Hydrogen": "Hydrogen",
    "SS_Naphtha": "Naphtha",
    "SS_Butene": "Butane",
    "DIST_Ethylene": "Ethylene",
    "DIST_Propylene": "Propylene",
    "DIST_Butene": "Butane",
}

# Multipliers: negative = product credit, positive = feed burden
factors = {
    "comb_nat_gas": 0.8,  # m3 to kg conversion factor
    "CPY_residue": -1.0,
    "CPY_AromaticsO": -1.0,
    "SS_BTX": -1.0,
    "PLASMA_Carbonyls": -1.0,
    "PLASMA_Acids": -1.0,
    "PLASMA_Alcohols": -1.0,
    "PLASMA_C30": -1.0,
    "PLASMA_Olefins": -1.0,
    "PLASMA_Paraffins": -1.0,
    "SS_Diesel": -1.0,
    "SS_Wax": -1.0,
    "SS_Hydrogen": -1.0,
    "SS_Naphtha": -1.0,
    "SS_Butene": -1.0,
    "DIST_Ethylene": -1.0,
    "DIST_Propylene": -1.0,
    "DIST_Butene": -1.0,
}

# Impact categories (exclude metadata columns)
_impact_cols = [c for c in ef.columns if c not in ('Amount', 'Unit', 'Location', 'Process')]


def get_lca(s):
    """
    Compute life-cycle environmental impacts for the system.

    Parameters
    ----------
    s : bst.System

    Returns
    -------
    impacts : dict of dict
        {source: {impact_category: value, ..., 'Amount': kg/hr or MJ}}
    """
    impacts = {}
    for p in s.feeds + s.products:
        if p.ID in streamMaps:
            res = streamMaps[p.ID]
            if res not in ef.index:
                continue  # skip resources not present in the precomputed CSV
            impacts[res] = {}
            for impact in _impact_cols:
                if impact not in impacts[res]:
                    impacts[res][impact] = 0
                impacts[res][impact] += p.F_mass * ef.loc[res, impact] * factors[p.ID]
            impacts[res]["Amount"] = p.F_mass * factors[p.ID]

    impacts["Electricity"] = {
        c: s.power_utility.consumption * 3.6 * ef.loc["Electricity, medium voltage", c]
        for c in _impact_cols
    }
    impacts["Electricity"]["Amount"] = s.power_utility.consumption * 3.6  # kWh to MJ

    net_duty = sum([u.duty for u in s.heat_utilities if u.duty < 0])
    impacts["Heat"] = {
        c: net_duty * ef.loc["Natural gas", c] / 1000 / 3600  # ef in MJ, duty in kJ/hr
        for c in _impact_cols
    }
    impacts["Heat"]["Amount"] = net_duty / 1000 / 3600  # kJ/hr to MJ/s

    # FCC off-gas direct emissions (CO2 + CH4 as CO2-eq)
    try:
        fcc_stream = s.flowsheet.stream["FCCOffGas"]
        impacts["FCCOffGas"] = {c: 0 for c in _impact_cols}
        impacts["FCCOffGas"]["Amount"] = fcc_stream.F_mass
        impacts["FCCOffGas"]['Global warming (kg CO2 eq)'] = (
            fcc_stream.imass["CO2"] + fcc_stream.imass["CH4"] * 32
        )
    except (KeyError, AttributeError):
        pass  # stream not present in this system configuration

    return impacts


def get_total_gwp(s):
    """
    Convenience: return total Global Warming Potential (kg CO2-eq/hr).

    Parameters
    ----------
    s : bst.System

    Returns
    -------
    float
        Total GWP in kg CO2-eq per hour.
    """
    impacts = get_lca(s)
    return sum(
        entry.get('Global warming (kg CO2 eq)', 0)
        for entry in impacts.values()
    )
