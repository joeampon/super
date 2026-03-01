"""
Publication-quality plot style for engineering journals.

Usage:
    from system._plot_style import apply_style, COLORS, LINE_STYLES, MARKERS, savefig

    apply_style()                       # call once at top of script
    fig, ax = plt.subplots()
    ax.plot(x, y, color=COLORS[0])
    savefig(fig, 'my_figure')           # saves PDF + PNG at 600 dpi

Style follows Elsevier / ACS / Nature guidelines:
  - Sans-serif font (Arial/Helvetica), 8 pt base
  - Single-column: 3.5 in, double-column: 7.0 in
  - Inward ticks, L-frame (no top/right spines)
  - Colorblind-safe Okabe-Ito palette
  - 600 dpi raster, PDF vector output
"""

import matplotlib as mpl
import matplotlib.pyplot as plt

# ============================================================================
# Colorblind-safe palette (Okabe-Ito)
# ============================================================================
COLORS = [
    '#0072B2',  # blue
    '#E69F00',  # orange
    '#009E73',  # green
    '#CC79A7',  # pink
    '#56B4E9',  # sky blue
    '#D55E00',  # vermillion
    '#F0E442',  # yellow
    '#000000',  # black
]

# Line styles for distinguishing series (use with COLORS)
LINE_STYLES = ['-', '--', '-.', ':', '-', '--', '-.', ':']
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', '*']

# Sequential / diverging colormaps (colorblind-safe)
CMAP_SEQ = 'viridis'
CMAP_DIV = 'RdBu_r'

# ============================================================================
# Figure dimensions (inches)
# ============================================================================
SINGLE_COL = 3.5
DOUBLE_COL = 7.0
ASPECT = 3 / 4  # height = width * ASPECT

# ============================================================================
# rcParams
# ============================================================================
RCPARAMS = {
    # Font
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 8,
    'axes.labelsize': 9,
    'axes.titlesize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7,
    'mathtext.fontset': 'dejavusans',

    # Lines and markers
    'lines.linewidth': 1.0,
    'lines.markersize': 5,

    # Axes
    'axes.linewidth': 0.6,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': False,
    'axes.prop_cycle': (mpl.cycler(color=COLORS)
                        + mpl.cycler(linestyle=LINE_STYLES)),

    # Ticks
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'xtick.minor.size': 2,
    'ytick.minor.size': 2,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.minor.width': 0.3,
    'ytick.minor.width': 0.3,
    'xtick.major.pad': 3,
    'ytick.major.pad': 3,
    'xtick.minor.visible': True,
    'ytick.minor.visible': True,

    # Legend
    'legend.frameon': False,
    'legend.handlelength': 1.5,
    'legend.handletextpad': 0.4,
    'legend.borderaxespad': 0.5,
    'legend.columnspacing': 1.0,
    'legend.labelspacing': 0.3,

    # Grid (off by default, subtle if enabled)
    'grid.color': '#CCCCCC',
    'grid.linestyle': '--',
    'grid.linewidth': 0.4,
    'grid.alpha': 0.3,

    # Saving
    'savefig.dpi': 600,
    'savefig.pad_inches': 0.02,
    'savefig.transparent': False,
    'figure.dpi': 150,

    # PDF font embedding (required by most journals)
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
}


def apply_style():
    """Apply publication-quality rcParams globally."""
    mpl.rcParams.update(RCPARAMS)


def figsize(width='single', aspect=None):
    """Return (width, height) tuple in inches.

    Parameters
    ----------
    width : float or 'single' or 'double'
        Figure width in inches, or a preset name.
    aspect : float, optional
        height/width ratio. Defaults to module-level ASPECT (3/4).
    """
    if width == 'single':
        w = SINGLE_COL
    elif width == 'double':
        w = DOUBLE_COL
    else:
        w = float(width)
    h = w * (aspect if aspect is not None else ASPECT)
    return (w, h)


def savefig(fig, path, formats=('pdf', 'png')):
    """Save figure in multiple formats.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    path : str
        Base path without extension (e.g. 'plots/my_figure').
    formats : tuple of str
        File formats to save. Default: PDF (vector) + PNG (raster at 600 dpi).
    """
    for fmt in formats:
        fig.savefig(f'{path}.{fmt}', format=fmt, bbox_inches='tight')


def label_panels(axes, x=-0.15, y=1.05):
    """Add bold (a), (b), (c), ... panel labels to a list of axes."""
    for i, ax in enumerate(axes):
        label = chr(ord('a') + i)
        ax.text(x, y, f'({label})', transform=ax.transAxes,
                fontsize=9, fontweight='bold', va='bottom', ha='right')
