"""
Pareto front analysis for the superstructure multi-objective optimisation.

Sweeps weight_MSP from 0.0 (pure GWP minimisation) to 1.0 (pure MSP
maximisation) in N_WEIGHTS steps.  For each weight the weighted-sum
problem is solved with Nelder-Mead and the optimal (MSP, GWP) is stored.
The resulting Pareto fronts are plotted for all price scenarios.

"""

import os
import sys
import warnings

# Ensure the project root (parent of 'system/') is on sys.path so that
# 'system.*' imports work when running from a notebook or any directory
# other than the project root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from scipy.optimize import minimize as scipy_minimize  # noqa: E402

from system.SUPERSTRUCTURE import evaluate  # noqa: E402
from system._prices import SCENARIOS  # noqa: E402
from system._plot_style import (  # noqa: E402
    apply_style, COLORS, CMAP_SEQ, savefig, figsize, label_panels,
)

apply_style()

# ============================================================================
# Configuration
# ============================================================================
CAPACITY_TPD = 250
MAXITER      = 50
N_WEIGHTS    = 11          # 0.0, 0.1, …, 1.0

weight_values = np.linspace(0.0, 1.0, N_WEIGHTS)

BOUNDS = [(0.05, 0.95)] * 4
X0     = [0.34, 0.50, 0.50, 0.50]

SCENARIO_LABELS = {
    'baseline':      'Baseline',
    'high_fuel':     'High fuel prices',
    'high_chem':     'High chemical prices',
    'high_organics': 'High organics prices',
}


# ============================================================================
# Pareto sweep function
# ============================================================================
def run_pareto_sweep(scenario: str) -> list:
    """Run one optimisation per weight value for *scenario*.

    Returns
    -------
    list of dict with keys: weight_MSP, MSP, GWP, x
    """
    ref     = evaluate(*X0, capacity_tpd=CAPACITY_TPD, scenario=scenario)
    MSP_ref = abs(ref['MSP']) if abs(ref['MSP']) > 1e-6 else 1.0
    GWP_ref = abs(ref['GWP']) if abs(ref['GWP']) > 1e-6 else 1.0

    results = []
    for w_msp in weight_values:
        w_gwp = 1.0 - w_msp
        best  = {'score': -1e15, 'MSP': None, 'GWP': None, 'x': None}

        def neg_score(x, _b=best, _wm=w_msp, _wg=w_gwp):
            try:
                r     = evaluate(x[0], x[1], x[2], x[3],
                                 capacity_tpd=CAPACITY_TPD, scenario=scenario)
                msp   = r['MSP']
                gwp   = r['GWP']
                score = _wm * (msp / MSP_ref) + _wg * (-gwp / GWP_ref)
                if score > _b['score']:
                    _b.update(score=score, MSP=msp, GWP=gwp, x=list(x))
                return -score
            except Exception:
                return 1e15

        print(f"  w_MSP={w_msp:.2f} ...", end=" ", flush=True)
        scipy_minimize(
            neg_score, X0, method='Nelder-Mead',
            bounds=BOUNDS,
            options={'maxiter': MAXITER, 'xatol': 0.01, 'fatol': 0.001,
                     'adaptive': True},
        )
        print(f"MSP=${best['MSP']:.4f}/kg  GWP={best['GWP']:.4f} kg CO2-eq/kg")
        results.append({
            'weight_MSP': w_msp,
            'MSP':        best['MSP'],
            'GWP':        best['GWP'],
            'x':          best['x'],
        })
    return results


# ============================================================================
# Run sweeps for every scenario
# ============================================================================
all_pareto: dict[str, list] = {}
for scenario in SCENARIOS:
    print(f"\n{'=' * 60}")
    print(f"Scenario: {scenario}")
    print(f"{'=' * 60}")
    all_pareto[scenario] = run_pareto_sweep(scenario)


# ============================================================================
# Figure 1 – 2×2 panel: one Pareto front per scenario
# ============================================================================
fig1, axes = plt.subplots(2, 2, figsize=figsize('double'))
axes_flat  = axes.ravel()

norm = Normalize(vmin=0.0, vmax=1.0)

for i, (scenario, results) in enumerate(all_pareto.items()):
    ax      = axes_flat[i]
    msps    = np.array([r['MSP']        for r in results])
    gwps    = np.array([r['GWP']        for r in results])
    weights = np.array([r['weight_MSP'] for r in results])

    # Sort by MSP to draw a smooth Pareto curve
    order   = np.argsort(msps)
    ax.plot(msps[order], gwps[order],
            color='gray', ls='--', lw=0.8, zorder=2)

    sc = ax.scatter(
        msps, gwps,
        c=weights, cmap=CMAP_SEQ, norm=norm,
        s=25, edgecolors='k', linewidths=0.3, alpha=0.9, zorder=3,
    )

    ax.set_xlabel('MSP (\$/kg feed)')
    ax.set_ylabel('GWP (kg CO$_2$-eq/kg feed)')
    ax.set_title(SCENARIO_LABELS[scenario])

label_panels(axes_flat)

fig1.subplots_adjust(right=0.87, hspace=0.50, wspace=0.38)
cbar_ax = fig1.add_axes([0.90, 0.15, 0.02, 0.70])
cb = fig1.colorbar(ScalarMappable(norm=norm, cmap=CMAP_SEQ), cax=cbar_ax)
cb.set_label('$w_{\\mathrm{MSP}}$ (economic weight, —)')
cb.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])

_out1 = os.path.join(_PROJECT_ROOT, 'system', 'pareto_by_scenario')
savefig(fig1, _out1)
print(f"\nSaved: {_out1}.pdf / .png")


# ============================================================================
# Figure 2 – all scenarios overlaid on a single panel
# ============================================================================
fig2, ax2 = plt.subplots(figsize=figsize('single'))

for i, (scenario, results) in enumerate(all_pareto.items()):
    msps  = np.array([r['MSP'] for r in results])
    gwps  = np.array([r['GWP'] for r in results])
    order = np.argsort(msps)

    ax2.plot(msps[order], gwps[order],
             color=COLORS[i], ls='-', lw=1.0, zorder=2,
             label=SCENARIO_LABELS[scenario])
    ax2.scatter(msps, gwps,
                color=COLORS[i], s=20,
                edgecolors='k', linewidths=0.3, alpha=0.85, zorder=3)

ax2.set_xlabel('MSP (\$/kg feed)')
ax2.set_ylabel('GWP (kg CO$_2$-eq/kg feed)')
ax2.legend(loc='best')

_out2 = os.path.join(_PROJECT_ROOT, 'system', 'pareto_all_scenarios')
savefig(fig2, _out2)
print(f"Saved: {_out2}.pdf / .png")

plt.show()
