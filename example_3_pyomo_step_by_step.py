#%%
"""
BioSTEAM-Pyomo Integration: Step by Step

This example shows how to optimize a superstructure using Pyomo.
We will implement it step by step to understand each part.

Author: David Lorenzo
Date: 2026-01-13
"""

import matplotlib
import biosteam as bst
from superstructure_node import SuperstructureNode, ConvergenceMixer, get_active_system_units
import pyomo.environ as pyo

import matplotlib.pyplot as plt

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

plant_capacity = 250 # tonnes per day

#%%
# ============================================================================
# Step 1: Define the superstructure (same as before)
# ============================================================================

print("="*80)
print("STEP 1: DEFINE SUPERSTRUCTURE")
print("="*80)

# Chemicals and feed

bst.main_flowsheet.clear()
bst.main_flowsheet.set_flowsheet('PS_flowsheet')
capacity = plant_capacity  # tonnes per day

chemicals = bst.Chemicals(['PS', 'C6H6', 'C7H8', 'H2O'])
bst.settings.set_thermo(chemicals)

feed = bst.Stream('PS_Feed',
                        PS=1,
                        units='kg/hr',
                        T=298)

feed.set_total_flow(capacity, 'tonnes/day')

feed = bst.Stream('feed', C6H6=1000, T=298, P=101325)
pump = bst.units.Pump("P1", ins=feed, outs="pressurized", P=5*101325)

# Decision node
node = SuperstructureNode(
    ID='NODE1',
    ins=pump.outs[0],
    outs=('to_mixer_A', 'to_mixer_B', 'to_mixer_C'),
    active_outlet=0
)

# Three mixers with different costs (simulated)
mixer_A = bst.units.Mixer('MX_A', ins=node.outs[0], outs='mixed_stream_A')
mixer_B = bst.units.Mixer('MX_B', ins=node.outs[1], outs='mixed_stream_B')
mixer_C = bst.units.Mixer('MX_C', ins=node.outs[2], outs='mixed_stream_C')

# Manually assign costs as custom attribute for demonstration
# In practice, BioSTEAM calculates purchase_cost automatically
mixer_A.custom_cost = 10000  # Cheapest
mixer_B.custom_cost = 15000  # Medium
mixer_C.custom_cost = 25000  # Most expensive

convergence_mixer = ConvergenceMixer(
    'CONVERGENCE',
    ins=(mixer_A.outs[0], mixer_B.outs[0], mixer_C.outs[0]),
    outs='converged_stream'
)

pump2 = bst.units.Pump("P2", ins=convergence_mixer.outs[0], outs="final_product", P=10*101325)

all_units = [pump, node, mixer_A, mixer_B, mixer_C, convergence_mixer, pump2]

print("\nSuperstructure defined")
print(f"  Node: {node.ID} with {node.n_outlets} outlets")
print(f"  Costs: MX_A=${mixer_A.custom_cost:,}, MX_B=${mixer_B.custom_cost:,}, MX_C=${mixer_C.custom_cost:,}")

#%%
# ============================================================================
# Step 2: Create the Pyomo model
# ============================================================================

print("\n" + "="*80)
print("STEP 2: CREATE PYOMO MODEL")
print("="*80)

# Create a concrete model
# A concrete model has all data defined from the beginning
model = pyo.ConcreteModel(name="Superstructure_Optimization")

print("\nModel created")
print(f"  Type: {type(model)}")
print(f"  Name: {model.name}")

#%%
# ============================================================================
# Step 3: Define binary variables
# ============================================================================

print("\n" + "="*80)
print("STEP 3: DEFINE BINARY VARIABLES")
print("="*80)

# In Pyomo, binary variables are defined with domain=pyo.Binary
# We will create a variable for each alternative

# Option 1: Create individual variables
model.y_A = pyo.Var(domain=pyo.Binary, initialize=0)
model.y_B = pyo.Var(domain=pyo.Binary, initialize=0)
model.y_C = pyo.Var(domain=pyo.Binary, initialize=0)

print("\nBinary variables created:")
print(f"  y_A: {model.y_A} (domain: Binary)")
print(f"  y_B: {model.y_B} (domain: Binary)")
print(f"  y_C: {model.y_C} (domain: Binary)")
print("\nThese variables represent whether each mixer is active (1) or inactive (0)")

#%%
# ============================================================================
# Step 4: Define constraints
# ============================================================================

print("\n" + "="*80)
print("STEP 4: DEFINE CONSTRAINTS")
print("="*80)

# Main constraint: Only one alternative can be active
# Mathematically: y_A + y_B + y_C = 1

# In Pyomo, constraints are defined with functions
def single_choice_rule(m):
    """Only one alternative can be active"""
    return m.y_A + m.y_B + m.y_C == 1

# Add the constraint to the model
model.single_choice = pyo.Constraint(rule=single_choice_rule)

print("\nConstraint added:")
print(f"  Name: single_choice")
print(f"  Rule: y_A + y_B + y_C == 1")
print(f"  Meaning: Exactly one alternative must be active")

#%%
# ============================================================================
# Step 5: Pre-compute costs for each configuration
# ============================================================================

print("\n" + "="*80)
print("STEP 5: PRE-COMPUTE COSTS")
print("="*80)

# For each configuration, we need to simulate and calculate the cost
# This is necessary because BioSTEAM is not differentiable

costs = {}

print("\nSimulating each configuration...\n")

for config_name, config_idx, mixer in [('A', 0, mixer_A), ('B', 1, mixer_B), ('C', 2, mixer_C)]:
    print(f"Configuration {config_name}:")

    # Activate the corresponding outlet
    node.set_active_outlet(config_idx)

    # Get active units
    active_units = get_active_system_units([node], all_units)

    # Create and simulate system
    system = bst.System(f'System_{config_name}', path=active_units)
    system.simulate()

    # Calculate total cost (sum of costs of all active units)
    # We use custom_cost for mixers, purchase_cost for the rest
    total_cost = sum(getattr(u, 'custom_cost', getattr(u, 'purchase_cost', 0)) for u in active_units)

    costs[config_name] = total_cost

    print(f"  Active units: {[u.ID for u in active_units]}")
    print(f"  Total cost: ${total_cost:,.2f}")
    print()

print("\nPre-computed costs:")
for config, cost in costs.items():
    print(f"  Config {config}: ${cost:,.2f}")

#%%
# ============================================================================
# Step 6: Define objective function
# ============================================================================

print("\n" + "="*80)
print("STEP 6: DEFINE OBJECTIVE FUNCTION")
print("="*80)

# The objective function is a linear combination of binary variables
# and costs: total_cost = cost_A * y_A + cost_B * y_B + cost_C * y_C

def objective_rule(m):
    """Minimize total cost"""
    return costs['A'] * m.y_A + costs['B'] * m.y_B + costs['C'] * m.y_C

# Add objective function to the model
model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

print("\nObjective function defined:")
print(f"  Minimize: {costs['A']:,.2f}*y_A + {costs['B']:,.2f}*y_B + {costs['C']:,.2f}*y_C")
print(f"  Sense: minimize (we seek the minimum cost)")

#%%
# ============================================================================
# Step 7: Solve the problem
# ============================================================================

print("\n" + "="*80)
print("STEP 7: SOLVE THE PROBLEM")
print("="*80)

# To solve, we need a solver
# Pyomo comes with 'glpk' (free solver for MILP)
# If not installed, use 'cbc' or install glpk

print("\nUsing Gurobi solver (direct gurobipy interface)...")

# Use gurobipy directly (more efficient than Pyomo SolverFactory)
try:
    import gurobipy as gp
    from gurobipy import GRB

    print("\nGurobipy imported successfully")

    # Create Gurobi model
    gurobi_model = gp.Model("Superstructure_Optimization")
    gurobi_model.setParam('OutputFlag', 0)  # Silence output (equivalent to tee=False)

    # Create binary variables
    y_A = gurobi_model.addVar(vtype=GRB.BINARY, name="y_A")
    y_B = gurobi_model.addVar(vtype=GRB.BINARY, name="y_B")
    y_C = gurobi_model.addVar(vtype=GRB.BINARY, name="y_C")

    # Constraint: exactly one alternative active
    gurobi_model.addConstr(y_A + y_B + y_C == 1, name="single_choice")

    # Objective function: minimize cost
    gurobi_model.setObjective(
        costs['A'] * y_A + costs['B'] * y_B + costs['C'] * y_C,
        GRB.MINIMIZE
    )

    # Solve
    print("\nSolving with Gurobi...")
    gurobi_model.optimize()

    # Check solution status
    if gurobi_model.status == GRB.OPTIMAL:
        print("\nProblem solved")
        print(f"  Status: OPTIMAL")
        print(f"  Objective value: ${gurobi_model.ObjVal:,.2f}")

        # Extract solution
        print("\n--- OPTIMAL SOLUTION ---")
        print(f"  y_A = {y_A.X}")
        print(f"  y_B = {y_B.X}")
        print(f"  y_C = {y_C.X}")
        print(f"  Optimal cost: ${gurobi_model.ObjVal:,.2f}")

        # Determine which configuration was selected
        if y_A.X == 1:
            optimal_config = 'A'
            optimal_idx = 0
        elif y_B.X == 1:
            optimal_config = 'B'
            optimal_idx = 1
        else:
            optimal_config = 'C'
            optimal_idx = 2

        print(f"\n  -> Optimal configuration: {optimal_config}")
    else:
        print(f"\nProblem not solved optimally. Status: {gurobi_model.status}")
        optimal_config = 'A'  # Default fallback
        optimal_idx = 0

except ImportError:
    print("\nError: gurobipy is not installed")
    print("  Install with: pip install gurobipy")
    print("  And make sure you have a valid license")
    optimal_config = 'A'  # Default fallback
    optimal_idx = 0
except Exception as e:
    print(f"\nError solving: {e}")
    optimal_config = 'A'  # Default fallback
    optimal_idx = 0

#%%
# ============================================================================
# Step 8: Apply optimal solution and simulate
# ============================================================================

print("\n" + "="*80)
print("STEP 8: APPLY SOLUTION AND SIMULATE")
print("="*80)

# Apply the optimal configuration
node.set_active_outlet(optimal_idx)
active_units = get_active_system_units([node], all_units)
optimal_system = bst.System('Optimal_System', path=active_units)
optimal_system.simulate()

print(f"\nOptimal configuration applied: {optimal_config}")
print(f"  Active units: {[u.ID for u in active_units]}")
print(f"  Total cost: ${sum(getattr(u, 'purchase_cost', 0) for u in active_units):,.2f}")

print("\n--- Optimal System ---")
optimal_system.show()

#%%
# ============================================================================
# SUMMARY: What have we learned?
# ============================================================================

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print("""
BioSTEAM-Pyomo integration completed:

1. PYOMO MODEL:
   - Binary variables (y_A, y_B, y_C) represent decisions
   - Constraint: sum(y_i) = 1 (only one active)
   - Objective function: minimize cost

2. PROCESS:
   - Pre-compute costs with BioSTEAM (simulate each config)
   - Formulate MILP problem in Pyomo
   - Solver finds optimum automatically

3. ADVANTAGES:
   - Scalable to large problems
   - Guarantees global optimum
   - Can include additional constraints

4. NEXT STEP:
   - Extend to multiple decision nodes
   - Add continuous variables (T, P, flows)
   - Integrate with BioSTEAM TEA/LCA
""")
# %%
