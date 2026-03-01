"""
Feasible-space Pareto scatter plot.

Monte Carlo sampling of the 4 split variables produces a cloud of
(MSP, GWP) feasible solutions.  Non-dominated solutions (Pareto front)
are highlighted in orange.

Both objectives are minimised:
    Objective 1 = MSP  ($/kg feed)  — lower breakeven price is more profitable
    Objective 2 = GWP  (kg CO2-eq/kg feed)  — lower emissions is better

After evaluation all values are normalised to [0, 1] per scenario.

Run from the project root:
    python3.12 -m system.pareto_scatter
"""

import os
import sys
import warnings

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

warnings.filterwarnings("ignore")

import numpy as np                          # noqa: E402
import matplotlib.pyplot as plt             # noqa: E402

from system.SUPERSTRUCTURE import evaluate  # noqa: E402
from system._prices import SCENARIOS        # noqa: E402
from system._plot_style import (            # noqa: E402
    apply_style, COLORS, savefig, figsize, label_panels,
)

apply_style()

# ============================================================================
# Configuration
# ============================================================================
CAPACITY_TPD = 250
N_SAMPLES    = 1500   # random draws per scenario (increase for smoother cloud)
SEED         = 42
X0           = [0.34, 0.50, 0.50, 0.50]   # known-good reset point

SCENARIO_LABELS = {
    'baseline':      'Baseline',
    'high_fuel':     'High fuel prices',
    'high_chem':     'High chemical prices',
    'high_organics': 'High organics prices',
}

rng    = np.random.default_rng(SEED)
splits = rng.uniform(0.05, 0.95, size=(N_SAMPLES, 4))   # shape (N, 4)


# ============================================================================
# Non-dominated front (minimise both objectives)
# ============================================================================
def non_dominated_mask(costs: np.ndarray) -> np.ndarray:
    """Return boolean mask selecting non-dominated rows of *costs* (N×2).

    Point *i* is dominated if there exists *j* such that
        costs[j] ≤ costs[i]  element-wise  AND
        costs[j] <  costs[i]  for at least one element.
    """
    n          = len(costs)
    is_nd      = np.ones(n, dtype=bool)
    for i in range(n):
        if not is_nd[i]:
            continue
        # indices of candidates still considered non-dominated
        idx       = np.where(is_nd)[0]
        dominated = (
            np.all(costs[idx] <= costs[i], axis=1) &
            np.any(costs[idx] <  costs[i], axis=1)
        )
        # points that dominate i  →  keep them; mark i dominated
        if dominated.any():
            is_nd[i] = False
        else:
            # i survives: remove any candidates that i dominates
            dominates_i = (
                np.all(costs[i] <= costs[idx], axis=1) &
                np.any(costs[i] <  costs[idx], axis=1)
            )
            dominated_by_i        = idx[dominates_i]
            dominated_by_i        = dominated_by_i[dominated_by_i != i]
            is_nd[dominated_by_i] = False
    return is_nd


# ============================================================================
# Evaluate all scenarios
# ============================================================================
all_data: dict[str, dict | None] = {}

def _reset_system(scenario: str) -> bool:
    """Empty recycles and run one warmup evaluation.

    Returns True if the system is in a usable state afterwards.
    """
    _cache = evaluate.__defaults__[-1]  # mutable default dict
    if 'system' in _cache:
        try:
            _cache['system'].empty_recycles()
        except Exception:
            _cache.clear()
    try:
        evaluate(*X0, capacity_tpd=CAPACITY_TPD, scenario=scenario)
        return True
    except Exception:
        _cache.clear()   # force full rebuild on next call
        try:
            evaluate(*X0, capacity_tpd=CAPACITY_TPD, scenario=scenario)
            return True
        except Exception:
            return False


for scenario in SCENARIOS:
    print(f"\n{'─' * 55}")
    print(f"Scenario: {scenario}  ({N_SAMPLES} samples)")
    print(f"{'─' * 55}")

    # Reset between scenarios to avoid corrupted state carrying over
    if not _reset_system(scenario):
        print(f"  [CRITICAL] Cannot initialise system for '{scenario}'. Skipping.")
        all_data[scenario] = None
        continue

    msps: list[float] = []
    gwps: list[float] = []
    _first_err_printed = False
    _needs_reset       = False

    for k, x in enumerate(splits):
        if k % 250 == 0:
            print(f"  {k:>5}/{N_SAMPLES} evaluated …", flush=True)

        # If previous sample corrupted the state, reset before continuing
        if _needs_reset:
            _needs_reset = not _reset_system(scenario)

        try:
            r   = evaluate(*x, capacity_tpd=CAPACITY_TPD, scenario=scenario)
            msp = float(r['MSP'])
            gwp = float(r['GWP'])
            msps.append(msp)
            gwps.append(gwp)
        except Exception as exc:
            if not _first_err_printed:
                print(f"  [WARNING] First exception at sample {k}: {type(exc).__name__}: {exc}")
                _first_err_printed = True
            msps.append(np.nan)
            gwps.append(np.nan)
            _needs_reset = True   # trigger reset before next sample

    msps_arr = np.array(msps)
    gwps_arr = np.array(gwps)

    valid           = np.isfinite(msps_arr) & np.isfinite(gwps_arr)
    msps_v, gwps_v  = msps_arr[valid], gwps_arr[valid]

    print(f"  Valid points: {valid.sum()}/{N_SAMPLES}")

    if valid.sum() == 0:
        print(f"  [ERROR] No valid samples for scenario '{scenario}'. Skipping.")
        all_data[scenario] = None
        continue

    print(f"  MSP range: [{msps_v.min():.4f}, {msps_v.max():.4f}] $/kg")
    print(f"  GWP range: [{gwps_v.min():.4f}, {gwps_v.max():.4f}] kg CO2-eq/kg")

    # Normalise to [0, 1]
    def _norm(v: np.ndarray) -> np.ndarray:
        lo, hi = v.min(), v.max()
        return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)

    obj1_n = _norm(msps_v)   # MSP  (minimise)
    obj2_n = _norm(gwps_v)   # GWP  (minimise)

    nd = non_dominated_mask(np.column_stack([obj1_n, obj2_n]))
    print(f"  Non-dominated points: {nd.sum()}")

    all_data[scenario] = dict(
        obj1_n=obj1_n, obj2_n=obj2_n,
        msps=msps_v, gwps=gwps_v,
        pareto=nd,
    )


# ============================================================================
# Figure 1 – 2×2 panel (one Pareto scatter per scenario)
# ============================================================================
fig1, axes = plt.subplots(2, 2, figsize=figsize('double'))

for i, (scenario, d) in enumerate(all_data.items()):
    ax = axes.ravel()[i]
    ax.set_title(SCENARIO_LABELS[scenario])

    if d is None:
        ax.text(0.5, 0.5, 'No valid data', ha='center', va='center',
                transform=ax.transAxes, color='gray')
        continue

    mask = d['pareto']

    ax.scatter(
        d['obj1_n'][~mask], d['obj2_n'][~mask],
        color=COLORS[0], s=8, alpha=0.4,
        label='Feasible space',
    )
    ax.scatter(
        d['obj1_n'][mask], d['obj2_n'][mask],
        color=COLORS[1], s=22, alpha=0.9,
        edgecolors='k', linewidths=0.3, zorder=3,
        label='Non-dominated solution',
    )

    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel('Objective 1 – MSP (Minimize, normalized)')
    ax.set_ylabel('Objective 2 – GWP (Minimize, normalized)')

    if i == 0:
        ax.legend(loc='upper right', markerscale=1.3)

label_panels(axes.ravel())
fig1.subplots_adjust(hspace=0.55, wspace=0.42)

_out1 = os.path.join(_PROJECT_ROOT, 'system', 'pareto_scatter_by_scenario')
savefig(fig1, _out1)
print(f"\nSaved: {_out1}.pdf / .png")


# ============================================================================
# Figure 2 – baseline scenario, single panel (for main manuscript)
# ============================================================================
fig2, ax2 = plt.subplots(figsize=figsize('single'))

d = all_data.get('baseline')
if d is None:
    raise RuntimeError("Baseline scenario produced no valid samples — check evaluate().")

mask = d['pareto']

ax2.scatter(
    d['obj1_n'][~mask], d['obj2_n'][~mask],
    color=COLORS[0], s=10, alpha=0.45,
    label='Feasible space',
)
ax2.scatter(
    d['obj1_n'][mask], d['obj2_n'][mask],
    color=COLORS[1], s=25, alpha=0.9,
    edgecolors='k', linewidths=0.3, zorder=3,
    label='Non-dominated solution',
)

ax2.set_xlim(-0.02, 1.05)
ax2.set_ylim(-0.02, 1.05)
ax2.set_xlabel('Objective 1 – MSP (Minimize, normalized)')
ax2.set_ylabel('Objective 2 – GWP (Minimize, normalized)')
ax2.legend(loc='upper right')

_out2 = os.path.join(_PROJECT_ROOT, 'system', 'pareto_scatter_baseline')
savefig(fig2, _out2)
print(f"Saved: {_out2}.pdf / .png")

plt.show()
