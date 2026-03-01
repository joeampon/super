# /plot — Publication-Quality Plot Style

When creating or updating plots in this project, follow these rules to ensure journal-quality figures suitable for Elsevier, ACS, Nature, and IEEE engineering publications.

## Setup

Always import and apply the style at the top of any plotting script:

```python
from system._plot_style import (
    apply_style, COLORS, LINE_STYLES, MARKERS,
    CMAP_SEQ, CMAP_DIV, savefig, figsize, label_panels,
)
apply_style()
```

## Figure Sizes

- **Single-column** (3.5 in wide): `figsize('single')` → `(3.5, 2.625)`
- **Double-column** (7.0 in wide): `figsize('double')` → `(7.0, 5.25)`
- Custom: `figsize(5.0, aspect=0.6)` → `(5.0, 3.0)`
- For multi-panel figures, use double-column width

## Colors

- Use `COLORS[0]` through `COLORS[7]` for categorical data (Okabe-Ito, colorblind-safe)
- Use `CMAP_SEQ` (`'viridis'`) for sequential data (heatmaps, contours)
- Use `CMAP_DIV` (`'RdBu_r'`) for diverging data
- **Never use** `jet`, `rainbow`, or `RdYlGn` colormaps

## Fonts & Sizes (set automatically by `apply_style()`)

| Element | Size |
|---------|------|
| Base font | 8 pt |
| Axis labels | 9 pt |
| Tick labels | 8 pt |
| Legend | 7 pt |
| Panel labels | 9 pt bold |

## Saving

Always save with the `savefig()` helper which produces both PDF (vector) and PNG (600 dpi raster):

```python
savefig(fig, 'path/to/figure_name')  # creates .pdf and .png
```

## Panel Labels

For multi-panel figures, add (a), (b), (c) labels:

```python
label_panels(axes.ravel())
```

## Axis Formatting Rules

- Axis labels must include units: `'Temperature (K)'`, `'Yield (wt%)'`
- Use inward ticks (set automatically)
- L-frame only (no top/right spines, set automatically)
- No grid by default; enable only when it aids readability
- No figure-level suptitle — use panel titles or captions instead

## Contour/Heatmap Plots

- Use `CMAP_SEQ` for single-sign data, `CMAP_DIV` for diverging
- Colorbar label must include units
- Contour line width: 0.4 pt, color: `'k'` (black)

## Bar Charts

- Edge color: `'white'`, linewidth: 0.4
- Bar width: 0.6-0.8 of available space
- Value labels only on bars > 5% of range

## Line Plots

- Line width: 1.0 pt (set automatically)
- Markers: size 5 (set automatically)
- **Every series must differ in both color AND linestyle** — this is set automatically by `apply_style()` via the `axes.prop_cycle` (cycles `COLORS` and `LINE_STYLES` together)
- Available line styles: `LINE_STYLES = ['-', '--', '-.', ':', '-', '--', '-.', ':']`
- Available markers: `MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', '*']`
- When plotting manually (not relying on the cycle), pair each series with `color=COLORS[i], ls=LINE_STYLES[i], marker=MARKERS[i]`
- Reference/diagonal lines: dashed, gray, 0.8 pt

## Scatter / Parity Plots

- Marker size: 15-25
- Alpha: 0.6 for overlapping data
- Edge: `'k'`, linewidth 0.3
- Diagonal reference: `color=COLORS[0]`, dashed, 0.8 pt

## Checklist Before Saving

1. All axis labels have units
2. Font size is readable at print size (minimum 6 pt after scaling)
3. Colors are from the Okabe-Ito palette or `viridis`/`RdBu_r`
4. `apply_style()` was called before creating figures
5. Saved as both PDF and PNG via `savefig()`
6. Multi-panel figures have (a), (b), (c) labels
