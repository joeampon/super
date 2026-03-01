# %% Imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, SymLogNorm
from matplotlib.ticker import LogFormatterSciNotation
from system.SUPERSTRUCTURE import evaluate
from system._plot_style import (
    apply_style, CMAP_SEQ, CMAP_DIV, savefig, figsize, label_panels,
)

apply_style()

# %% Configuration
capacity_tpd = 250
n_points = 12  # grid resolution per axis (12x12 = 144 evaluations per pair)
param_range = (0.10, 0.90)

# Fixed values for variables not being swept in a given pair
fixed_TOD = 0.34
fixed_CP = 0.50
fixed_CPY = 0.50
fixed_HC = 0.50
fixed_PLASMA = 1 - fixed_CPY  # PLASMA is complement of CPY


def _to_eval_kwargs(raw):
    """Translate virtual variables to evaluate() parameters.

    ``split_PLASMA`` is not a direct parameter of ``evaluate()``; it maps
    to ``split_CPY = 1 - split_PLASMA``.
    """
    kwargs = {}
    for k, v in raw.items():
        if k == 'split_PLASMA':
            kwargs['split_CPY'] = 1 - v
        else:
            kwargs[k] = v
    return kwargs


# %% Evaluate grid — all pairwise combinations of 5 split variables
# (skip degenerate CPY vs PLASMA since split_PLASMA = 1 - split_CPY)
pairs = [
    ('split_TOD', 'split_CP',      {'split_CPY': fixed_CPY,     'split_HC': fixed_HC}),
    ('split_TOD', 'split_CPY',     {'split_CP': fixed_CP,       'split_HC': fixed_HC}),
    ('split_TOD', 'split_PLASMA',  {'split_CP': fixed_CP,       'split_HC': fixed_HC}),
    ('split_TOD', 'split_HC',      {'split_CP': fixed_CP,       'split_CPY': fixed_CPY}),
    ('split_CP',  'split_CPY',     {'split_TOD': fixed_TOD,     'split_HC': fixed_HC}),
    ('split_CP',  'split_PLASMA',  {'split_TOD': fixed_TOD,     'split_HC': fixed_HC}),
    ('split_CP',  'split_HC',      {'split_TOD': fixed_TOD,     'split_CPY': fixed_CPY}),
    ('split_CPY', 'split_HC',      {'split_TOD': fixed_TOD,     'split_CP': fixed_CP}),
    ('split_PLASMA', 'split_HC',   {'split_TOD': fixed_TOD,     'split_CP': fixed_CP}),
]

results = {}
for x_name, y_name, fixed_kwargs in pairs:
    key = f"{x_name} vs {y_name}"
    fixed_str = ', '.join(f'{k}={v:.2f}' for k, v in fixed_kwargs.items())
    print(f"\nSweeping {key} ({fixed_str})...")

    x_vals = np.linspace(*param_range, n_points)
    y_vals = np.linspace(*param_range, n_points)
    MSP_grid = np.full((n_points, n_points), np.nan)
    GWP_grid = np.full((n_points, n_points), np.nan)
    CAC_grid = np.full((n_points, n_points), np.nan)

    for i, yv in enumerate(y_vals):
        for j, xv in enumerate(x_vals):
            raw = {x_name: xv, y_name: yv, **fixed_kwargs,
                   'capacity_tpd': capacity_tpd}
            kwargs = _to_eval_kwargs(raw)
            try:
                res = evaluate(**kwargs)
                MSP_grid[i, j] = res['MSP']                       # $/kg feed
                GWP_grid[i, j] = res['GWP']                       # kg CO2-eq/kg feed
                cac = res['carbon_abatement_cost']
                CAC_grid[i, j] = cac if np.isfinite(cac) else np.nan
            except Exception as e:
                print(f"  FAILED at {x_name}={xv:.2f}, {y_name}={yv:.2f}: {e}")

        done = (i + 1) * n_points
        total = n_points * n_points
        print(f"  {done}/{total} evaluations complete")

    results[key] = {
        'x_vals': x_vals, 'y_vals': y_vals,
        'x_name': x_name, 'y_name': y_name,
        'fixed_kwargs': fixed_kwargs,
        'MSP': MSP_grid, 'GWP': GWP_grid, 'CAC': CAC_grid,
    }

# save results for later use
import pickle
with open('contour_results.pkl', 'wb') as f:
    pickle.dump(results, f)

# %% Plot contours
labels = {
    'split_TOD': 'CP+TOD fraction',
    'split_CP': 'TOD fraction (of CP+TOD)',
    'split_CPY': 'CPY fraction',
    'split_PLASMA': 'PLASMA fraction',
    'split_HC': 'HC fraction',
}

n_pairs = len(results)
fig, axes = plt.subplots(n_pairs, 3, figsize=(10.5, 2.4 * n_pairs))

for row, (key, data) in enumerate(results.items()):
    X, Y = np.meshgrid(data['x_vals'], data['y_vals'])
    x_label = labels[data['x_name']]
    y_label = labels[data['y_name']]
    fixed_str = ', '.join(
        f'{labels[k]}={v:.2f}' for k, v in data['fixed_kwargs'].items()
    )

    # MSP contour
    ax = axes[row, 0]
    cf = ax.contourf(X, Y, data['MSP'], levels=15, cmap=CMAP_DIV)
    ax.contour(X, Y, data['MSP'], levels=15, colors='k', linewidths=0.4)
    fig.colorbar(cf, ax=ax, label='MSP ($/kg feed)')
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(f'MSP ($/kg feed)\n{fixed_str}', fontsize=8)

    # GWP contour
    ax = axes[row, 1]
    cf = ax.contourf(X, Y, data['GWP'], levels=15, cmap=CMAP_SEQ)
    ax.contour(X, Y, data['GWP'], levels=15, colors='k', linewidths=0.4)
    fig.colorbar(cf, ax=ax, label=r'GWP (kg CO$_2$-eq/kg feed)')
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(r'GWP (kg CO$_2$-eq/kg feed)' + f'\n{fixed_str}', fontsize=8)

    # CAC contour (log-scale colorbar)
    ax = axes[row, 2]
    cac = data['CAC']
    if np.all(np.isnan(cac)):
        ax.text(0.5, 0.5, 'No finite\nCAC values', transform=ax.transAxes,
                ha='center', va='center', fontsize=8)
    else:
        cac_finite = cac[np.isfinite(cac)]
        has_negative = np.any(cac_finite < 0)
        if has_negative:
            # SymLogNorm handles mixed positive/negative values
            abs_max = np.nanmax(np.abs(cac_finite))
            abs_pos = cac_finite[cac_finite > 0]
            linthresh = np.nanmin(abs_pos) if len(abs_pos) > 0 else 1.0
            norm = SymLogNorm(linthresh=linthresh, vmin=-abs_max, vmax=abs_max)
            cf = ax.contourf(X, Y, cac, levels=15, cmap='RdBu_r', norm=norm)
            ax.contour(X, Y, cac, levels=15, colors='k', linewidths=0.4,
                       norm=norm)
        else:
            # Pure positive values — use LogNorm
            vmin = np.nanmin(cac_finite[cac_finite > 0])
            vmax = np.nanmax(cac_finite)
            norm = LogNorm(vmin=vmin, vmax=vmax)
            cf = ax.contourf(X, Y, cac, levels=np.geomspace(vmin, vmax, 15),
                             cmap='plasma', norm=norm)
            ax.contour(X, Y, cac, levels=np.geomspace(vmin, vmax, 15),
                       colors='k', linewidths=0.4, norm=norm)
        fig.colorbar(cf, ax=ax, label=r'CAC ($/kg CO$_2$-eq)')
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(r'CAC ($/kg CO$_2$-eq)' + f'\n{fixed_str}', fontsize=8)

label_panels(axes.ravel())
fig.tight_layout()
savefig(fig, '/Users/markmw/Github/superStructure/system/contours')
plt.show()
