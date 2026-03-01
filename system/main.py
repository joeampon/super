# %% Imports
import warnings
warnings.filterwarnings("ignore")

import pyomo.environ as pyo
from scipy.optimize import minimize as scipy_minimize

from system.SUPERSTRUCTURE import (
    evaluate,
    build_superstructure,
    build_pathway,
    PATHWAY_BUILDERS,
)
from system._prices import (
    SCENARIOS, get_prices, FUEL_PRODUCTS, CHEMICAL_PRODUCTS, ORGANIC_PRODUCTS,
)

PRODUCT_GROUPS = {
    'Fuels': FUEL_PRODUCTS,
    'Chemicals': CHEMICAL_PRODUCTS,
    'Organics': ORGANIC_PRODUCTS,
    'Hydrogen': {'Hydrogen'},
}

# %% Configuration
capacity_tpd = 250
maxiter = 50
weight_MSP = 0.5  # 1.0 = pure economics, 0.0 = pure GWP minimization
weight_GWP = 1.0 - weight_MSP

# Pyomo model (for variable bounds and documentation)
m = pyo.ConcreteModel('Superstructure_MultiObjective')

m.split_TOD = pyo.Var(
    bounds=(0.05, 0.95), initialize=0.34,
    doc='Fraction of feed to CP+TOD (rest to CPY+PLASMA)',
)
m.split_CP = pyo.Var(
    bounds=(0.05, 0.95), initialize=0.50,
    doc='Fraction of CP+TOD feed to TOD (rest to CP)',
)
m.split_CPY = pyo.Var(
    bounds=(0.05, 0.95), initialize=0.50,
    doc='Fraction of non-TOD feed to CPY (rest to PLASMA)',
)
m.split_HC = pyo.Var(
    bounds=(0.05, 0.95), initialize=0.50,
    doc='Fraction of wax to HC (rest to FCC)',
)

m.MSP = pyo.Var(initialize=0, doc='Minimum selling price ($/kg feed)')
m.GWP = pyo.Var(initialize=0, doc='Global warming potential (kg CO2-eq/kg feed)')
m.score = pyo.Var(initialize=0, doc='Weighted multi-objective score')
m.obj = pyo.Objective(expr=m.score, sense=pyo.maximize)

bounds = [
    (pyo.value(m.split_TOD.lb), pyo.value(m.split_TOD.ub)),
    (pyo.value(m.split_CP.lb), pyo.value(m.split_CP.ub)),
    (pyo.value(m.split_CPY.lb), pyo.value(m.split_CPY.ub)),
    (pyo.value(m.split_HC.lb), pyo.value(m.split_HC.ub)),
]
x0 = [pyo.value(m.split_TOD), pyo.value(m.split_CP),
      pyo.value(m.split_CPY), pyo.value(m.split_HC)]

# %% Single evaluation (test, baseline)
res = evaluate(split_TOD=0.34, split_CP=0.50, split_CPY=0.50, split_HC=0.50,
               capacity_tpd=capacity_tpd)
print(f"MSP: ${res['MSP']:.4f}/kg feed")
print(f"GWP: {res['GWP']:.4f} kg CO2-eq/kg feed")
for name, flow in sorted(res['product_flows'].items()):
    if flow > 0.01:
        print(f"  {name:15s}: {flow:10.1f} kg/hr")

# %% Multi-scenario optimization
all_results = {}

for scenario in SCENARIOS:
    print(f"\n{'=' * 60}")
    print(f"Scenario: {scenario}")
    print(f"{'=' * 60}")

    # Reference evaluation for normalization (per-scenario)
    ref = evaluate(0.34, 0.50, 0.50, 0.50,
                   capacity_tpd=capacity_tpd, scenario=scenario)
    MSP_ref = abs(ref['MSP']) if abs(ref['MSP']) > 1e-6 else 1.0
    GWP_ref = abs(ref['GWP']) if abs(ref['GWP']) > 1e-6 else 1.0
    print(f"  Reference MSP: ${ref['MSP']:.4f}/kg feed")
    print(f"  Reference GWP: {ref['GWP']:.4f} kg CO2-eq/kg feed")

    best = {'score': -1e15, 'MSP': None, 'GWP': None, 'CAC': None,
            'x': None, 'result': None, 'n_eval': 0}

    def neg_score(x, _best=best, _MSP_ref=MSP_ref, _GWP_ref=GWP_ref,
                  _scenario=scenario):
        _best['n_eval'] += 1
        n = _best['n_eval']
        try:
            res = evaluate(x[0], x[1], x[2], x[3],
                           capacity_tpd=capacity_tpd, scenario=_scenario)
            msp = res['MSP']
            gwp = res['GWP']
            cac = res['carbon_abatement_cost']
            score = weight_MSP * (msp / _MSP_ref) + weight_GWP * (-gwp / _GWP_ref)

            improved = score > _best['score']
            if improved:
                _best['score'] = score
                _best['MSP'] = msp
                _best['GWP'] = gwp
                _best['CAC'] = cac
                _best['x'] = list(x)
                _best['result'] = res

            print(
                f"  [{n:3d}] TOD={x[0]:.3f}  CP={x[1]:.3f}  CPY={x[2]:.3f}  HC={x[3]:.3f}"
                f"  MSP=${msp:.4f}/kg  GWP={gwp:.4f} kg/kg"
                f"  score={score:.4f}{'  *' if improved else ''}"
            )
            return -score
        except Exception as e:
            print(
                f"  [{n:3d}] TOD={x[0]:.3f}  CP={x[1]:.3f}  CPY={x[2]:.3f}  HC={x[3]:.3f}"
                f"  FAILED: {e}"
            )
            return 1e15

    print(f"\nOptimizing ({capacity_tpd} tpd, weights: MSP={weight_MSP:.2f},"
          f" GWP={weight_GWP:.2f})...\n")

    scipy_minimize(
        neg_score, x0, method='Nelder-Mead',
        bounds=bounds,
        options={'maxiter': maxiter, 'xatol': 0.01, 'fatol': 0.001,
                 'adaptive': True},
    )

    # Per-scenario summary
    final = best['result']
    tea = final['tea']
    prices = get_prices(scenario)

    print(f"\n--- {scenario} results ({best['n_eval']} evaluations) ---")
    print(f"Optimal splits:")
    print(f"  CP+TOD vs rest: {best['x'][0]:.4f}")
    print(f"  TOD vs CP:      {best['x'][1]:.4f}")
    print(f"  CPY vs PLASMA:  {best['x'][2]:.4f}")
    print(f"  HC vs FCC:      {best['x'][3]:.4f}")
    print(f"TEA:")
    print(f"  MSP:              ${best['MSP']:.4f}/kg feed")
    print(f"  Utility cost:     ${tea.utility_cost:,.0f}/yr")
    print(f"  Annual sales:     ${tea.sales:,.0f}/yr")
    print(f"  Installed cost:   ${tea.installed_equipment_cost:,.0f}")
    print(f"LCA:")
    print(f"  GWP:              {best['GWP']:.4f} kg CO2-eq/kg feed")
    print(f"  Carbon abatement: ${best['CAC']:.2f}/kg CO2-eq")
    print(f"Product flows (kg/hr):")
    for name, flow in sorted(final['product_flows'].items()):
        if flow > 0.01:
            price = prices.get(name, 0)
            print(f"  {name:15s}: {flow:10.1f} kg/hr  (${flow * price:,.0f}/hr)")

    # Subgroup sales ($/yr)
    op_hrs = tea.operating_hours
    group_sales = {}
    for group, members in PRODUCT_GROUPS.items():
        group_sales[group] = sum(
            final['product_flows'].get(p, 0) * prices.get(p, 0) * op_hrs
            for p in members
        )
    print(f"Sales by product group ($/yr):")
    for group, sales_yr in group_sales.items():
        print(f"  {group:12s}: ${sales_yr:>14,.0f}/yr")
    print(f"  {'Total':12s}: ${sum(group_sales.values()):>14,.0f}/yr")

    # Per-product organic revenues ($/yr)
    organic_sales = {
        p: final['product_flows'].get(p, 0) * prices.get(p, 0) * op_hrs
        for p in sorted(ORGANIC_PRODUCTS)
    }

    best['sales'] = tea.sales
    best['utility_cost'] = tea.utility_cost
    best['installed_cost'] = tea.installed_equipment_cost
    best['group_sales'] = group_sales
    best['organic_sales'] = organic_sales
    all_results[scenario] = best

# %% Update Pyomo model with baseline optimal values
bl = all_results['baseline']
m.split_TOD.set_value(bl['x'][0])
m.split_CP.set_value(bl['x'][1])
m.split_CPY.set_value(bl['x'][2])
m.split_HC.set_value(bl['x'][3])
m.MSP.set_value(bl['MSP'])
m.GWP.set_value(bl['GWP'])
m.score.set_value(bl['score'])

# %% Cross-scenario comparison
print(f"\n{'=' * 120}")
print(f"Cross-Scenario Comparison (weights: MSP={weight_MSP:.2f}, GWP={weight_GWP:.2f})")
print(f"{'=' * 120}")
hdr_groups = ''.join(f" {g:>12s}" for g in PRODUCT_GROUPS)
print(f"{'Scenario':16s} {'TOD':>5s} {'CP':>5s} {'CPY':>5s} {'HC':>5s}"
      f"  {'MSP':>8s} {'GWP':>8s} {'CAC':>8s}"
      f" |{hdr_groups} {'Total':>13s}")
print(f"{'-' * 120}")
for scenario, best in all_results.items():
    x = best['x']
    gs = best['group_sales']
    grp_cols = ''.join(f" {gs[g]/1e6:>11.2f}M" for g in PRODUCT_GROUPS)
    total = sum(gs.values())
    print(f"{scenario:16s} {x[0]:5.3f} {x[1]:5.3f} {x[2]:5.3f} {x[3]:5.3f}"
          f"  {best['MSP']:>8.4f} {best['GWP']:>8.4f} {best['CAC']:>8.2f}"
          f" |{grp_cols} {total/1e6:>12.2f}M")

# %% Organics revenue breakdown
organic_names = sorted(ORGANIC_PRODUCTS)
hdr_org = ''.join(f" {n:>12s}" for n in organic_names)
print(f"\n{'=' * 100}")
print(f"Organics Revenue Breakdown ($/yr)")
print(f"{'=' * 100}")
print(f"{'Scenario':16s} |{hdr_org} {'Total':>13s}")
print(f"{'-' * 100}")
for scenario, best in all_results.items():
    os_ = best['organic_sales']
    cols = ''.join(f" {os_[p]/1e6:>11.2f}M" for p in organic_names)
    total = sum(os_.values())
    print(f"{scenario:16s} |{cols} {total/1e6:>12.2f}M")

# %% Diagrams (baseline)
system = all_results['baseline']['result']['system']
for k in ["surface", "thorough", "cluster"]:
    system.diagram(k, file=f"/Users/markmw/Github/superStructure/system/system_diagram_{k}",
                   format="png", display=False)
