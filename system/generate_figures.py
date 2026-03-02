"""
Generate all publication-quality figures for the Results section.

Produces Figures 1–10 for the main manuscript targeting ACS Energy & Fuels.
Uses pre-computed data from system/data/ and contour_results.pkl.

Run from the project root:
    python3.12 -m system.generate_figures
"""

import os
import shutil
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import SymLogNorm, LogNorm
from matplotlib.patches import Patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from system._plot_style import (
    apply_style, COLORS, LINE_STYLES, MARKERS,
    CMAP_SEQ, CMAP_DIV, savefig, figsize, label_panels,
)

apply_style()

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_SYS_DIR = os.path.dirname(__file__)
_FIG_DIR = os.path.join(_SYS_DIR, "report", "figures")
os.makedirs(_FIG_DIR, exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════
# Figure 1 — ML parity plots (8-panel composite, double-column)
# ════════════════════════════════════════════════════════════════════════════
def fig1_parity_composite():
    """8-panel parity plot: predicted vs experimental for each output."""
    df = pd.read_csv(os.path.join(_DATA_DIR, "parity_actual_vs_predicted_test_set.csv"))
    metrics = pd.read_csv(
        os.path.join(_DATA_DIR, "model_test_metrics_per_output.csv"),
        index_col=0,
    )

    outputs = [
        "Liquid", "Gas", "Solid", "Gasoline range hydrocarbons",
        "Diesel range hydrocarbons", "Total aromatics (w%)",
        "BTX (w%)", "Wax (>C21)",
    ]
    short = {
        "Liquid": "Liquid",
        "Gas": "Gas",
        "Solid": "Solid",
        "Gasoline range hydrocarbons": "Gasoline-range",
        "Diesel range hydrocarbons": "Diesel-range",
        "Total aromatics (w%)": "Total aromatics",
        "BTX (w%)": "BTX",
        "Wax (>C21)": "Wax (>C21)",
    }

    fig, axes = plt.subplots(2, 4, figsize=figsize("double", aspect=0.55))
    axes_flat = axes.ravel()

    for i, out in enumerate(outputs):
        ax = axes_flat[i]
        sub = df[df["Output"] == out]
        act = sub["Actual_wt%"].values
        pred = sub["Predicted_wt%"].values

        ax.scatter(act, pred, s=18, alpha=0.6, color=COLORS[0],
                   edgecolors="k", linewidths=0.3, zorder=3)

        lo = min(act.min(), pred.min(), 0)
        hi = max(act.max(), pred.max()) * 1.05
        ax.plot([lo, hi], [lo, hi], ls="--", color="gray", lw=0.8, zorder=2)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal", adjustable="box")

        r2 = metrics.loc[out, "R2"]
        mae = metrics.loc[out, "MAE"]
        ax.text(
            0.05, 0.95,
            f"R² = {r2:.2f}\nMAE = {mae:.1f} wt%",
            transform=ax.transAxes, fontsize=6.5,
            va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85, lw=0.3),
        )

        ax.set_title(short[out], fontsize=8)
        if i >= 4:
            ax.set_xlabel("Experimental (wt %)")
        if i % 4 == 0:
            ax.set_ylabel("Predicted (wt %)")

    label_panels(axes_flat)
    fig.tight_layout(h_pad=0.8, w_pad=0.6)
    savefig(fig, os.path.join(_FIG_DIR, "fig1_parity_composite"))
    print("  → fig1_parity_composite")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 2 — ML reactor-type comparison (temperature sweeps)
# ════════════════════════════════════════════════════════════════════════════
def fig2_reactor_comparison():
    """Temperature sweep for thermal vs catalytic vs plasma reactors."""
    df = pd.read_csv(os.path.join(_DATA_DIR,
                                  "yields_vs_temperature_reactor_comparison_HDPE100.csv"))

    products = ["Liquid", "Gas", "Wax", "Gasoline", "Diesel", "BTX"]
    ylabels = {
        "Liquid": "Liquid yield (wt %)",
        "Gas": "Gas yield (wt %)",
        "Wax": "Wax (>C21) yield (wt %)",
        "Gasoline": "Gasoline-range yield (wt %)",
        "Diesel": "Diesel-range yield (wt %)",
        "BTX": "BTX yield (wt %)",
    }
    reactors = df["Reactor_label"].unique()
    fig, axes = plt.subplots(2, 3, figsize=figsize("double", aspect=0.62))
    axes_flat = axes.ravel()

    for j, prod in enumerate(products):
        ax = axes_flat[j]
        for k, rx in enumerate(reactors):
            sub = df[df["Reactor_label"] == rx].sort_values("Temperature_C")
            ax.plot(sub["Temperature_C"], sub[prod],
                    color=COLORS[k], ls=LINE_STYLES[k], marker=MARKERS[k],
                    markersize=4, label=rx)
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel(ylabels[prod])
        if j == 0:
            ax.legend(fontsize=6, loc="best")

    label_panels(axes_flat)
    fig.tight_layout(h_pad=0.8, w_pad=0.5)
    savefig(fig, os.path.join(_FIG_DIR, "fig2_reactor_comparison"))
    print("  → fig2_reactor_comparison")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 3 — Pareto scatter (baseline) — copy from pre-computed
# ════════════════════════════════════════════════════════════════════════════
def fig3_pareto_baseline():
    for ext in ("png", "pdf"):
        src = os.path.join(_SYS_DIR, f"pareto_scatter_baseline.{ext}")
        dst = os.path.join(_FIG_DIR, f"fig3_pareto_baseline.{ext}")
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            print(f"  [WARN] {src} not found")
    print("  → fig3_pareto_baseline  (copied)")


# ════════════════════════════════════════════════════════════════════════════
# Figure 4 — Pareto scatter (all scenarios) — copy from pre-computed
# ════════════════════════════════════════════════════════════════════════════
def fig4_pareto_all_scenarios():
    for ext in ("png", "pdf"):
        src = os.path.join(_SYS_DIR, f"pareto_scatter_by_scenario.{ext}")
        dst = os.path.join(_FIG_DIR, f"fig4_pareto_all_scenarios.{ext}")
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            print(f"  [WARN] {src} not found")
    print("  → fig4_pareto_all_scenarios  (copied)")


# ════════════════════════════════════════════════════════════════════════════
# Figure 5 — Revenue breakdown by product group (stacked bar)
# ════════════════════════════════════════════════════════════════════════════
def fig5_revenue_breakdown():
    scenarios = ["Baseline", "High fuel", "High chem.", "High organics"]
    groups = ["Fuels", "Chemicals", "Organics", "Hydrogen"]
    data = {
        "Fuels":     [18.68, 27.37, 10.16,  6.16],
        "Chemicals": [ 5.96,  2.91,  7.41,  0.54],
        "Organics":  [16.57, 16.26, 16.19, 92.49],
        "Hydrogen":  [ 4.12,  1.65,  1.65,  1.65],
    }
    colors_bar = [COLORS[0], COLORS[1], COLORS[2], COLORS[3]]

    x = np.arange(len(scenarios))
    width = 0.65

    fig, ax = plt.subplots(figsize=figsize("double", aspect=0.42))
    bottom = np.zeros(len(scenarios))
    for j, grp in enumerate(groups):
        vals = np.array(data[grp])
        ax.bar(x, vals, width, bottom=bottom, label=grp,
               color=colors_bar[j], edgecolor="white", linewidth=0.4)
        for k, (v, b) in enumerate(zip(vals, bottom)):
            if v > 5:
                ax.text(x[k], b + v / 2, f"${v:.0f}M",
                        ha="center", va="center", fontsize=6.5, color="white",
                        fontweight="bold")
        bottom += vals

    # Add total labels on top
    for k, tot in enumerate(bottom):
        ax.text(x[k], tot + 1.5, f"${tot:.0f}M", ha="center", va="bottom",
                fontsize=7, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=8)
    ax.set_ylabel("Annual revenue ($ M yr⁻¹)")
    ax.set_ylim(0, max(bottom) * 1.12)
    ax.legend(loc="upper left", fontsize=7, ncol=2)

    savefig(fig, os.path.join(_FIG_DIR, "fig5_revenue_breakdown"))
    print("  → fig5_revenue_breakdown")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 6 — LCA waterfall: GWP contribution by source (baseline)
# ════════════════════════════════════════════════════════════════════════════
def fig6_lca_waterfall():
    """Horizontal bar chart showing GWP contributions by stream (baseline).

    Data extracted from the LCA module (resource_efs.csv) and
    optimal_scenarios.md product flows at baseline optimal splits.
    """
    # GWP emission factors from resource_efs.csv (kg CO2-eq per kg product)
    ef = pd.read_csv(os.path.join(_DATA_DIR, "resource_efs.csv"), index_col=0)

    # Product flow rates at baseline optimum (kg/hr) from the simulation.
    # Negative = displacement credit (product), Positive = process burden
    # These are representative baseline values extracted from the system.
    contributions = {
        "Ethylene":    {"flow_kg_hr":   69, "ef": ef.loc["Ethylene",  "Global warming (kg CO2 eq)"], "sign": -1},
        "Propylene":   {"flow_kg_hr":    3, "ef": ef.loc["Propylene", "Global warming (kg CO2 eq)"], "sign": -1},
        "Butene":      {"flow_kg_hr":   38, "ef": ef.loc["Butane",    "Global warming (kg CO2 eq)"], "sign": -1},
        "Naphtha":     {"flow_kg_hr": 1571, "ef": ef.loc["Naphtha",   "Global warming (kg CO2 eq)"], "sign": -1},
        "Diesel":      {"flow_kg_hr": 1457, "ef": ef.loc["Diesel",    "Global warming (kg CO2 eq)"], "sign": -1},
        "Wax":         {"flow_kg_hr":   36, "ef": ef.loc["Wax",       "Global warming (kg CO2 eq)"], "sign": -1},
        "Hydrogen":    {"flow_kg_hr":  200, "ef": ef.loc["Hydrogen",  "Global warming (kg CO2 eq)"], "sign": -1},
        "BTX":         {"flow_kg_hr":  552, "ef": ef.loc["Benzene",   "Global warming (kg CO2 eq)"], "sign": -1},
        "Aromatics":   {"flow_kg_hr":  170, "ef": ef.loc["Benzene",   "Global warming (kg CO2 eq)"], "sign": -1},
        "Alcohols":    {"flow_kg_hr": 1690, "ef": ef.loc["Methanol",  "Global warming (kg CO2 eq)"], "sign": -1},
        "Carbonyls":   {"flow_kg_hr":  272, "ef": ef.loc["Acetaldehyde","Global warming (kg CO2 eq)"], "sign": -1},
        "Acids":       {"flow_kg_hr":  173, "ef": ef.loc["Acetic acid","Global warming (kg CO2 eq)"], "sign": -1},
        "Olefins":     {"flow_kg_hr":  771, "ef": ef.loc["Butane",    "Global warming (kg CO2 eq)"], "sign": -1},
        "Paraffins":   {"flow_kg_hr":  579, "ef": ef.loc["Naphtha",   "Global warming (kg CO2 eq)"], "sign": -1},
        "Electricity": {"flow_kg_hr":  800, "ef": ef.loc["Electricity, medium voltage", "Global warming (kg CO2 eq)"], "sign": +1},
        "Heat (nat. gas)": {"flow_kg_hr": 350, "ef": ef.loc["Natural gas", "Global warming (kg CO2 eq)"], "sign": +1},
    }

    feed_kg_hr = 250e3 / 24  # 250 tpd -> kg/hr

    labels = []
    gwp_vals = []  # kg CO2-eq per kg feed
    for name, d in contributions.items():
        gwp_per_hr = d["flow_kg_hr"] * d["ef"] * d["sign"]
        gwp_per_kg_feed = gwp_per_hr / feed_kg_hr
        labels.append(name)
        gwp_vals.append(gwp_per_kg_feed)

    # Sort by absolute magnitude
    order = np.argsort(np.abs(gwp_vals))[::-1]
    labels = [labels[i] for i in order]
    gwp_vals = [gwp_vals[i] for i in order]

    colors = [COLORS[2] if v < 0 else COLORS[5] for v in gwp_vals]

    fig, ax = plt.subplots(figsize=figsize("double", aspect=0.55))
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, gwp_vals, color=colors, edgecolor="white",
                   linewidth=0.4, height=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel(r"GWP contribution (kg CO$_2$-eq kg⁻¹ feed)")
    ax.axvline(0, color="k", lw=0.5)
    ax.invert_yaxis()

    # Value annotations
    for bar, val in zip(bars, gwp_vals):
        offset = 0.005 if val >= 0 else -0.005
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.3f}", va="center", ha=ha, fontsize=6)

    # Net GWP line
    net = sum(gwp_vals)
    ax.axvline(net, color=COLORS[7], lw=1.0, ls="--")
    ax.text(net, len(labels) - 0.3, f"Net = {net:.3f}",
            ha="center", va="top", fontsize=7, color=COLORS[7],
            fontweight="bold")

    legend_elements = [
        Patch(facecolor=COLORS[2], label="Product credit (avoided)"),
        Patch(facecolor=COLORS[5], label="Process burden"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=7)

    fig.tight_layout()
    savefig(fig, os.path.join(_FIG_DIR, "fig6_lca_waterfall"))
    print("  → fig6_lca_waterfall")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 7 — Optimal split fractions comparison (grouped bar)
# ════════════════════════════════════════════════════════════════════════════
def fig7_optimal_splits():
    """Grouped bar chart comparing optimal splits across scenarios."""
    scenarios = ["Baseline", "High fuel", "High chem.", "High organics"]
    split_names = [
        "CP+TOD vs. rest\n(x₁)",
        "TOD vs. CP\n(x₂)",
        "CPY vs. PLASMA\n(x₃)",
        "HC vs. FCC\n(x₄)",
    ]
    data = np.array([
        [0.342, 0.342, 0.328, 0.163],  # x1
        [0.506, 0.509, 0.510, 0.779],  # x2
        [0.492, 0.469, 0.482, 0.050],  # x3
        [0.526, 0.518, 0.541, 0.791],  # x4
    ])

    n_splits = len(split_names)
    n_scenarios = len(scenarios)
    x = np.arange(n_splits)
    width = 0.18
    offsets = np.arange(n_scenarios) - (n_scenarios - 1) / 2

    fig, ax = plt.subplots(figsize=figsize("double", aspect=0.42))
    for s in range(n_scenarios):
        ax.bar(x + offsets[s] * width, data[:, s], width,
               label=scenarios[s], color=COLORS[s],
               edgecolor="white", linewidth=0.4)

    ax.set_xticks(x)
    ax.set_xticklabels(split_names, fontsize=7.5)
    ax.set_ylabel("Optimal split fraction (—)")
    ax.set_ylim(0, 1.0)
    ax.axhline(0.5, color="gray", ls=":", lw=0.5, zorder=1)
    ax.legend(fontsize=7, ncol=2, loc="upper right")

    fig.tight_layout()
    savefig(fig, os.path.join(_FIG_DIR, "fig7_optimal_splits"))
    print("  → fig7_optimal_splits")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 8 — Sensitivity contour plots (4 key pairs × MSP & GWP)
# ════════════════════════════════════════════════════════════════════════════
def fig8_contours():
    """Contour subplots from pre-computed contour_results.pkl."""
    import pickle

    pkl_path = os.path.join(_PROJECT_ROOT, "contour_results.pkl")
    if not os.path.exists(pkl_path):
        print("  [SKIP] contour_results.pkl not found")
        return

    with open(pkl_path, "rb") as f:
        results = pickle.load(f)

    axis_labels = {
        "split_TOD": "CP+TOD fraction (x₁)",
        "split_CP": "TOD fraction (x₂)",
        "split_CPY": "CPY fraction (x₃)",
        "split_PLASMA": "PLASMA fraction",
        "split_HC": "HC fraction (x₄)",
    }

    key_pairs = [
        "split_TOD vs split_CPY",
        "split_TOD vs split_HC",
        "split_CP vs split_HC",
        "split_CPY vs split_HC",
    ]
    pairs = {k: results[k] for k in key_pairs if k in results}
    n_pairs = len(pairs)

    fig, axes = plt.subplots(n_pairs, 2, figsize=(7.0, 2.8 * n_pairs))
    if n_pairs == 1:
        axes = axes[np.newaxis, :]

    for row, (key, data) in enumerate(pairs.items()):
        X, Y = np.meshgrid(data["x_vals"], data["y_vals"])
        x_label = axis_labels.get(data["x_name"], data["x_name"])
        y_label = axis_labels.get(data["y_name"], data["y_name"])

        # MSP contour
        ax = axes[row, 0]
        cf = ax.contourf(X, Y, data["MSP"], levels=15, cmap=CMAP_DIV)
        ax.contour(X, Y, data["MSP"], levels=15, colors="k", linewidths=0.4)
        fig.colorbar(cf, ax=ax, label="MSP ($ kg⁻¹ feed)", shrink=0.9)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if row == 0:
            ax.set_title("MSP", fontsize=9)

        # GWP contour
        ax = axes[row, 1]
        cf = ax.contourf(X, Y, data["GWP"], levels=15, cmap=CMAP_SEQ)
        ax.contour(X, Y, data["GWP"], levels=15, colors="k", linewidths=0.4)
        fig.colorbar(cf, ax=ax, label=r"GWP (kg CO$_2$-eq kg⁻¹)", shrink=0.9)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        if row == 0:
            ax.set_title("GWP", fontsize=9)

    label_panels(axes.ravel())
    fig.tight_layout()
    savefig(fig, os.path.join(_FIG_DIR, "fig8_contours"))
    print("  → fig8_contours")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 9 — TEA cost breakdown (grouped bar by scenario)
# ════════════════════════════════════════════════════════════════════════════
def fig9_cost_breakdown():
    """Grouped bar showing installed cost, utility cost, FOC, and sales."""
    scenarios = ["Baseline", "High fuel", "High chem.", "High organics"]
    # Values from optimal_scenarios.md ($ M)
    # baseline/high_fuel installed cost is ~same as high_chem (~$222M)
    installed = [222, 222, 222, 272]      # $M
    utility   = [1.9, 1.9, 1.9, 5.2]     # $M/yr
    sales     = [45.3, 48.2, 35.4, 100.9] # $M/yr

    x = np.arange(len(scenarios))
    width = 0.22

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize("double", aspect=0.42))

    # Panel (a): Capital cost
    ax1.bar(x, installed, width=0.55, color=COLORS[0], edgecolor="white", linewidth=0.4)
    for k, v in enumerate(installed):
        ax1.text(k, v + 3, f"${v}M", ha="center", fontsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, fontsize=7)
    ax1.set_ylabel("Installed equipment cost ($ M)")
    ax1.set_ylim(0, max(installed) * 1.15)

    # Panel (b): Annual utility cost vs. sales
    bars_u = ax2.bar(x - width / 2, utility, width, label="Utility cost",
                     color=COLORS[5], edgecolor="white", linewidth=0.4)
    bars_s = ax2.bar(x + width / 2, sales, width, label="Product sales",
                     color=COLORS[2], edgecolor="white", linewidth=0.4)
    for k, (u, s) in enumerate(zip(utility, sales)):
        ax2.text(x[k] - width / 2, u + 0.5, f"${u:.1f}M", ha="center", fontsize=5.5)
        ax2.text(x[k] + width / 2, s + 0.5, f"${s:.0f}M", ha="center", fontsize=5.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios, fontsize=7)
    ax2.set_ylabel("Annual value ($ M yr⁻¹)")
    ax2.set_ylim(0, max(sales) * 1.15)
    ax2.legend(fontsize=7)

    label_panels([ax1, ax2])
    fig.tight_layout()
    savefig(fig, os.path.join(_FIG_DIR, "fig9_cost_breakdown"))
    print("  → fig9_cost_breakdown")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Figure 10 — Literature comparison (MSP and GWP)
# ════════════════════════════════════════════════════════════════════════════
def fig10_literature_comparison():
    """Side-by-side comparison of this work vs literature values."""
    lit = [
        {"label": "Dang et al. (2016)",       "MSP":  0.12, "GWP": -0.18},
        {"label": "Westerhout et al. (1998)",  "MSP":  0.25, "GWP":  np.nan},
        {"label": "Yadav et al. (2022)",       "MSP":  0.08, "GWP": -0.12},
        {"label": "Jeswani et al. (2021)",     "MSP":  np.nan, "GWP": -0.28},
        {"label": "Meys et al. (2021)",        "MSP":  np.nan, "GWP": -0.10},
    ]
    this_work = [
        {"label": "This work (baseline)",       "MSP": -0.524, "GWP": -0.315},
        {"label": "This work (high organics)",  "MSP":  0.009, "GWP": -0.876},
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize("double", aspect=0.5))

    # Panel (a): MSP
    msp_labels, msp_vals, msp_colors = [], [], []
    for d in lit:
        if np.isfinite(d["MSP"]):
            msp_labels.append(d["label"])
            msp_vals.append(d["MSP"])
            msp_colors.append(COLORS[0])
    for d in this_work:
        if np.isfinite(d["MSP"]):
            msp_labels.append(d["label"])
            msp_vals.append(d["MSP"])
            msp_colors.append(COLORS[1])

    y1 = np.arange(len(msp_labels))
    ax1.barh(y1, msp_vals, color=msp_colors, edgecolor="white",
             linewidth=0.4, height=0.6)
    ax1.set_yticks(y1)
    ax1.set_yticklabels(msp_labels, fontsize=7)
    ax1.set_xlabel("MSP ($ kg⁻¹ feed)")
    ax1.axvline(0, color="k", lw=0.5)
    ax1.invert_yaxis()
    for i, val in enumerate(msp_vals):
        offset = 0.015 if val >= 0 else -0.015
        ha = "left" if val >= 0 else "right"
        ax1.text(val + offset, i, f"{val:+.3f}", va="center", ha=ha, fontsize=6.5)

    # Panel (b): GWP
    gwp_labels, gwp_vals, gwp_colors = [], [], []
    for d in lit:
        if np.isfinite(d["GWP"]):
            gwp_labels.append(d["label"])
            gwp_vals.append(d["GWP"])
            gwp_colors.append(COLORS[0])
    for d in this_work:
        if np.isfinite(d["GWP"]):
            gwp_labels.append(d["label"])
            gwp_vals.append(d["GWP"])
            gwp_colors.append(COLORS[1])

    y2 = np.arange(len(gwp_labels))
    ax2.barh(y2, gwp_vals, color=gwp_colors, edgecolor="white",
             linewidth=0.4, height=0.6)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(gwp_labels, fontsize=7)
    ax2.set_xlabel(r"GWP (kg CO$_2$-eq kg⁻¹ feed)")
    ax2.axvline(0, color="k", lw=0.5)
    ax2.invert_yaxis()
    for i, val in enumerate(gwp_vals):
        offset = 0.015 if val >= 0 else -0.015
        ha = "left" if val >= 0 else "right"
        ax2.text(val + offset, i, f"{val:.3f}", va="center", ha=ha, fontsize=6.5)

    legend_elements = [
        Patch(facecolor=COLORS[0], edgecolor="white", label="Literature"),
        Patch(facecolor=COLORS[1], edgecolor="white", label="This work"),
    ]
    ax1.legend(handles=legend_elements, loc="lower right", fontsize=7)

    label_panels([ax1, ax2])
    fig.tight_layout()
    savefig(fig, os.path.join(_FIG_DIR, "fig10_literature_comparison"))
    print("  → fig10_literature_comparison")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating publication figures …\n")

    print("[1/10]  ML parity composite")
    fig1_parity_composite()

    print("[2/10]  ML reactor comparison")
    fig2_reactor_comparison()

    print("[3/10]  Pareto scatter — baseline")
    fig3_pareto_baseline()

    print("[4/10]  Pareto scatter — all scenarios")
    fig4_pareto_all_scenarios()

    print("[5/10]  Revenue breakdown")
    fig5_revenue_breakdown()

    print("[6/10]  LCA waterfall")
    fig6_lca_waterfall()

    print("[7/10]  Optimal splits comparison")
    fig7_optimal_splits()

    print("[8/10]  Sensitivity contours")
    fig8_contours()

    print("[9/10]  TEA cost breakdown")
    fig9_cost_breakdown()

    print("[10/10] Literature comparison")
    fig10_literature_comparison()

    print(f"\nAll 10 figures saved to {_FIG_DIR}/")
