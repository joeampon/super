"""
Parametric study of pyrolysis product yields.

Generates plots showing how the 8 ML-predicted product categories
change with:
  1. Pyrolysis temperature   (at fixed VRT and composition)
  2. Vapor residence time    (at fixed temperature and composition)
  3. Feedstock composition   (discrete cases at fixed T / VRT)
  4. Feedstock sensitivity   (continuous sweep of each polyolefin)
  5. Phase distribution      (stacked bar vs temperature)
  6. Reactor-type comparison (thermal / TOD / catalytic)

Usage:
    python3.12 system/machine_learning/feedstock.py
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add project root so we can import the shared plot style
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from system._plot_style import apply_style, COLORS, LINE_STYLES, MARKERS, savefig, figsize, label_panels

from model import PyrolysisNet, OUTPUT_NAMES
from model import predict_raw as predict_raw_with_correction

# ============================================================================
# Setup
# ============================================================================

apply_style()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(SCRIPT_DIR, 'plots')
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Shorter labels for the 8 outputs
SHORT_NAMES = [
    'Liquid', 'Gas', 'Solid', 'Gasoline', 'Diesel',
    'Aromatics', 'BTX', 'Wax',
]

# ============================================================================
# Model loading (once)
# ============================================================================

def _load_model():
    model_path = os.path.join(SCRIPT_DIR, 'pyrolysis_model.pt')
    scaler_path = os.path.join(SCRIPT_DIR, 'scaler_params.pt')
    scaler = torch.load(scaler_path, weights_only=True)
    model = PyrolysisNet()
    model.load_state_dict(torch.load(model_path, weights_only=True))
    model.eval()
    return model, scaler


def predict_raw(model, scaler, hdpe, ldpe, pp, temperature, vrt):
    """Return the 8 raw product-category wt% predictions."""
    raw = np.array([[hdpe, ldpe, pp, temperature, vrt]], dtype=np.float32)
    mean = scaler['mean'].numpy()
    scale = scaler['scale'].numpy()
    normed = (raw - mean) / scale
    with torch.no_grad():
        pred = model(torch.tensor(normed, dtype=torch.float32)).squeeze().numpy()
    return np.clip(pred, 0.0, 100.0)


# ============================================================================
# Plot helpers
# ============================================================================

def _grouped_bar(ax, data, group_labels, bar_labels, colors, ylabel,
                 title, legend=True):
    """Draw a grouped bar chart on *ax*.

    Parameters
    ----------
    data : ndarray, shape (n_groups, n_bars)
    group_labels : list[str]   - x-tick labels (one per group)
    bar_labels   : list[str]   - legend labels (one per bar within a group)
    """
    n_groups, n_bars = data.shape
    x = np.arange(n_groups)
    width = 0.8 / n_bars

    for j in range(n_bars):
        offset = (j - n_bars / 2 + 0.5) * width
        bars = ax.bar(x + offset, data[:, j], width, label=bar_labels[j],
                      color=colors[j], edgecolor='white', linewidth=0.4)
        # Value labels on bars taller than 5 wt%
        for bar in bars:
            h = bar.get_height()
            if h > 5:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                        f'{h:.0f}', ha='center', va='bottom', fontsize=6)

    ax.set_xticks(x)
    ax.set_xticklabels(group_labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, min(data.max() * 1.25 + 5, 105))
    if legend:
        ax.legend(ncol=4, loc='upper right')


# ============================================================================
# 1. Vary temperature
# ============================================================================

def plot_temperature_sweep(model, scaler):
    """Bar plots: product yields vs temperature for several feedstocks."""
    temperatures = [400, 450, 500, 550, 600, 650, 700, 800]
    feeds = [
        ('100% HDPE',        100,   0,   0),
        ('100% LDPE',          0, 100,   0),
        ('100% PP',            0,   0, 100),
        ('50/25/25 Mix',      50,  25,  25),
    ]
    vrt = 1.0

    fig, axes = plt.subplots(2, 2, figsize=figsize('double', aspect=1.3))
    axes_flat = axes.ravel()

    rows = []
    for idx, (label, hdpe, ldpe, pp) in enumerate(feeds):
        data = np.array([
            predict_raw(model, scaler, hdpe, ldpe, pp, T, vrt)
            for T in temperatures
        ])  # shape (n_temps, 8)

        for i, T in enumerate(temperatures):
            rows.append([label, hdpe, ldpe, pp, T, vrt] + data[i].tolist())

        group_labels = [f'{T} \u00b0C' for T in temperatures]
        _grouped_bar(axes_flat[idx], data, group_labels, SHORT_NAMES, COLORS,
                     'Yield (wt%)',
                     f'{label}, VRT = {vrt} s',
                     legend=(idx == 0))

    label_panels(axes_flat)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'temperature_sweep')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')

    csv_path = os.path.join(DATA_DIR, f'yields_vs_temperature_VRT{vrt}s.csv')
    cols = ['Feed', 'HDPE_wt%', 'LDPE_wt%', 'PP_wt%', 'Temperature_C', 'VRT_s'] + SHORT_NAMES
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
    print(f'  Saved {csv_path}')


# ============================================================================
# 2. Vary vapor residence time
# ============================================================================

def plot_vrt_sweep(model, scaler):
    """Bar plots: product yields vs VRT for several feedstocks."""
    vrts = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    feeds = [
        ('100% HDPE',        100,   0,   0),
        ('100% LDPE',          0, 100,   0),
        ('100% PP',            0,   0, 100),
        ('50/25/25 Mix',      50,  25,  25),
    ]
    temperature = 500

    fig, axes = plt.subplots(2, 2, figsize=figsize('double', aspect=1.3))
    axes_flat = axes.ravel()

    rows = []
    for idx, (label, hdpe, ldpe, pp) in enumerate(feeds):
        data = np.array([
            predict_raw(model, scaler, hdpe, ldpe, pp, temperature, v)
            for v in vrts
        ])

        for i, v in enumerate(vrts):
            rows.append([label, hdpe, ldpe, pp, temperature, v] + data[i].tolist())

        group_labels = [f'{v} s' for v in vrts]
        _grouped_bar(axes_flat[idx], data, group_labels, SHORT_NAMES, COLORS,
                     'Yield (wt%)',
                     f'{label}, T = {temperature} \u00b0C',
                     legend=(idx == 0))

    label_panels(axes_flat)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'vrt_sweep')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')

    csv_path = os.path.join(DATA_DIR, f'yields_vs_vrt_T{temperature}C.csv')
    cols = ['Feed', 'HDPE_wt%', 'LDPE_wt%', 'PP_wt%', 'Temperature_C', 'VRT_s'] + SHORT_NAMES
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
    print(f'  Saved {csv_path}')


# ============================================================================
# 3. Vary feedstock composition
# ============================================================================

def plot_composition_sweep(model, scaler):
    """Bar plots: product yields vs feed composition at several T / VRT."""
    compositions = [
        ('100% HDPE',     100,   0,   0),
        ('100% LDPE',       0, 100,   0),
        ('100% PP',         0,   0, 100),
        ('50/50 HD/LD',    50,  50,   0),
        ('50/50 HD/PP',    50,   0,  50),
        ('50/50 LD/PP',     0,  50,  50),
        ('34/33/33 Mix',   34,  33,  33),
    ]
    conditions = [
        (450, 1.0),
        (500, 1.0),
        (600, 1.0),
        (700, 1.0),
    ]

    fig, axes = plt.subplots(2, 2, figsize=figsize('double', aspect=1.3))
    axes_flat = axes.ravel()

    rows = []
    for idx, (T, vrt) in enumerate(conditions):
        data = np.array([
            predict_raw(model, scaler, hdpe, ldpe, pp, T, vrt)
            for (_, hdpe, ldpe, pp) in compositions
        ])

        for i, (label, hdpe, ldpe, pp) in enumerate(compositions):
            rows.append([label, hdpe, ldpe, pp, T, vrt] + data[i].tolist())

        group_labels = [c[0] for c in compositions]
        _grouped_bar(axes_flat[idx], data, group_labels, SHORT_NAMES, COLORS,
                     'Yield (wt%)',
                     f'T = {T} \u00b0C, VRT = {vrt} s',
                     legend=(idx == 0))
        axes_flat[idx].tick_params(axis='x', rotation=30)

    label_panels(axes_flat)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'composition_sweep')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')

    csv_path = os.path.join(DATA_DIR, 'yields_vs_composition_discrete.csv')
    cols = ['Feed', 'HDPE_wt%', 'LDPE_wt%', 'PP_wt%', 'Temperature_C', 'VRT_s'] + SHORT_NAMES
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
    print(f'  Saved {csv_path}')


# ============================================================================
# 4. Feedstock sensitivity (continuous sweep of each polyolefin)
# ============================================================================

# US average waste-plastic composition (wt%), mapped to ML inputs.
# PS (10.4%) is lumped with HDPE in the Pyrolyzer ML model.
_BASELINE = dict(HDPE=32.4, LDPE=44.2, PP=23.4)  # sums to 100


def plot_composition_sensitivity(model, scaler):
    """Line plots: product yields vs polyolefin fraction (0-100 wt%).

    Each panel sweeps one polyolefin from 0 to 100 wt% while the other
    two redistribute proportionally to their US-average baseline ratio.
    """
    temperature = 500
    vrt = 1.0
    fracs = np.linspace(0, 100, 51)

    sweep_configs = [
        ('HDPE', 'LDPE', 'PP'),
        ('LDPE', 'HDPE', 'PP'),
        ('PP',   'HDPE', 'LDPE'),
    ]

    fig, axes = plt.subplots(1, 3, figsize=figsize('double', aspect=0.38))

    for idx, (sweep_name, other1, other2) in enumerate(sweep_configs):
        ax = axes[idx]
        # Baseline ratio of the two non-swept components
        r1 = _BASELINE[other1]
        r2 = _BASELINE[other2]
        r_total = r1 + r2

        rows = []
        data = np.zeros((len(fracs), 8))
        for i, f in enumerate(fracs):
            remainder = 100.0 - f
            comp = {sweep_name: f}
            if r_total > 0:
                comp[other1] = remainder * r1 / r_total
                comp[other2] = remainder * r2 / r_total
            else:
                comp[other1] = remainder / 2
                comp[other2] = remainder / 2
            data[i] = predict_raw(model, scaler,
                                  comp['HDPE'], comp['LDPE'], comp['PP'],
                                  temperature, vrt)
            rows.append([comp['HDPE'], comp['LDPE'], comp['PP'],
                         temperature, vrt] + data[i].tolist())

        for j in range(8):
            ax.plot(fracs, data[:, j], color=COLORS[j],
                    ls=LINE_STYLES[j], marker=MARKERS[j],
                    label=SHORT_NAMES[j], markersize=3,
                    markevery=5)

        # Mark US average baseline
        ax.axvline(_BASELINE[sweep_name], color='gray', ls='--', lw=0.8,
                   label='US avg.' if idx == 0 else None)

        ax.set_xlabel(f'{sweep_name} (wt%)')
        ax.set_ylabel('Yield (wt%)')
        ax.set_title(f'Vary {sweep_name} (T={temperature} \u00b0C, VRT={vrt} s)')
        ax.set_xlim(0, 100)
        ax.set_ylim(bottom=0)
        if idx == 0:
            ax.legend(ncol=3, loc='upper right', fontsize=6)

        cols = ['HDPE_wt%', 'LDPE_wt%', 'PP_wt%', 'Temperature_C', 'VRT_s'] + SHORT_NAMES
        csv_path = os.path.join(DATA_DIR,
                                f'yields_vs_{sweep_name}_fraction_T{temperature}C_VRT{vrt}s.csv')
        pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
        print(f'  Saved {csv_path}')

    label_panels(axes)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'composition_sensitivity')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')


# ============================================================================
# 5. Stacked bar - phase distribution (Gas + Liquid + Solid)
# ============================================================================

def plot_phase_stacked(model, scaler):
    """Stacked bars showing Gas/Liquid/Solid split across temperatures."""
    temperatures = [400, 450, 500, 550, 600, 650, 700, 750, 800]
    feeds = [
        ('100% HDPE',        100,   0,   0),
        ('100% LDPE',          0, 100,   0),
        ('100% PP',            0,   0, 100),
        ('50/25/25 Mix',      50,  25,  25),
    ]
    vrt = 1.0
    phase_names = ['Liquid', 'Gas', 'Solid']

    fig, axes = plt.subplots(2, 2, figsize=figsize('double', aspect=1.3))
    axes_flat = axes.ravel()

    rows = []
    for idx, (label, hdpe, ldpe, pp) in enumerate(feeds):
        data = np.array([
            predict_raw(model, scaler, hdpe, ldpe, pp, T, vrt)[:3]
            for T in temperatures
        ])  # shape (n_temps, 3): Liquid, Gas, Solid

        for i, T in enumerate(temperatures):
            rows.append([label, hdpe, ldpe, pp, T, vrt] + data[i].tolist())

        x = np.arange(len(temperatures))
        bottom = np.zeros(len(temperatures))
        for j, (name, color) in enumerate(zip(phase_names, COLORS[:3])):
            axes_flat[idx].bar(x, data[:, j], bottom=bottom, label=name,
                          color=color, edgecolor='white', linewidth=0.4,
                          width=0.6)
            # Label inside bar if > 8%
            for k in range(len(temperatures)):
                val = data[k, j]
                if val > 8:
                    axes_flat[idx].text(x[k], bottom[k] + val / 2,
                                   f'{val:.0f}', ha='center', va='center',
                                   fontsize=6, color='white', fontweight='bold')
            bottom += data[:, j]

        axes_flat[idx].set_xticks(x)
        axes_flat[idx].set_xticklabels([f'{T}' for T in temperatures])
        axes_flat[idx].set_xlabel('Temperature (\u00b0C)')
        axes_flat[idx].set_ylabel('Yield (wt%)')
        axes_flat[idx].set_title(label)
        axes_flat[idx].set_ylim(0, 115)
        axes_flat[idx].axhline(100, color='gray', ls='--', lw=0.8)
        if idx == 0:
            axes_flat[idx].legend(loc='upper right')

    label_panels(axes_flat)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'phase_stacked')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')

    csv_path = os.path.join(DATA_DIR, f'phase_distribution_vs_temperature_VRT{vrt}s.csv')
    cols = ['Feed', 'HDPE_wt%', 'LDPE_wt%', 'PP_wt%', 'Temperature_C', 'VRT_s'] + phase_names
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
    print(f'  Saved {csv_path}')


# ============================================================================
# 6. Reactor-type comparison (thermal vs TOD vs catalytic)
# ============================================================================

def plot_reactor_comparison():
    """Compare thermal, TOD, and catalytic yields across temperatures."""
    temperatures = [400, 450, 500, 550, 600, 650, 700, 800]
    reactor_types = ['thermal', 'TOD', 'catalytic']
    rt_labels = ['Thermal', 'TOD', 'Catalytic']

    fig, axes = plt.subplots(2, 4, figsize=figsize('double', aspect=0.5))
    axes_flat = axes.ravel()

    rows = []
    for rt_idx, (rt, label) in enumerate(zip(reactor_types, rt_labels)):
        for T in temperatures:
            pred = predict_raw_with_correction(100, 0, 0, T, 1.0, reactor_type=rt)
            rows.append([label, rt, 100, 0, 0, T, 1.0] + pred.tolist())

    # For each of the 8 output categories, plot lines for each reactor type
    for out_idx in range(8):
        ax = axes_flat[out_idx]
        for rt_idx, (rt, label) in enumerate(zip(reactor_types, rt_labels)):
            values = [r[7 + out_idx] for r in rows
                      if r[1] == rt]
            ax.plot(temperatures, values, color=COLORS[rt_idx],
                    ls=LINE_STYLES[rt_idx], marker=MARKERS[rt_idx],
                    label=label, markersize=4)

        ax.set_xlabel('Temperature (\u00b0C)')
        ax.set_ylabel('Yield (wt%)')
        ax.set_title(SHORT_NAMES[out_idx])
        ax.set_ylim(bottom=0)
        if out_idx == 0:
            ax.legend()

    label_panels(axes_flat)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, 'reactor_comparison')
    savefig(fig, path)
    plt.close(fig)
    print(f'  Saved {path}')

    csv_path = os.path.join(DATA_DIR, 'yields_vs_temperature_reactor_comparison_HDPE100.csv')
    cols = ['Reactor_label', 'Reactor_type', 'HDPE_wt%', 'LDPE_wt%', 'PP_wt%',
            'Temperature_C', 'VRT_s'] + SHORT_NAMES
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False)
    print(f'  Saved {csv_path}')


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print('Loading model...')
    model, scaler = _load_model()

    print('Generating plots...')
    plot_temperature_sweep(model, scaler)
    plot_vrt_sweep(model, scaler)
    plot_composition_sweep(model, scaler)
    plot_composition_sensitivity(model, scaler)
    plot_phase_stacked(model, scaler)
    plot_reactor_comparison()

    print(f'\nAll plots saved to {PLOT_DIR}/')
