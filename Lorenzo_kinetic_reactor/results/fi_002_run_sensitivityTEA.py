#%%
"""
Simple script to run sensitivity analysis step by step
"""

# Reload module to get latest changes
import os
import numpy as np
import matplotlib.pyplot as plt
from codigestion_bst_continuos_function import create_and_simulate_system


def run_sensitivity_analysis(parameters_config, base_params=None):
    """
    Run sensitivity analysis on specified parameters.

    Parameters
    ----------
    parameters_config : dict
        Dictionary with parameter names as keys and (low, high) tuples as values
        Example: {"reactor_tau": (24, 96), "IRR": (0.05, 0.15)}
    base_params : dict, optional
        Base case parameters to pass to create_and_simulate_system

    Returns
    -------
    results : dict
        Dictionary with parameter names as keys and [low_msp, high_msp] as values
    basecase_msp : float
        MSP for the base case
    """

    # Get base case
    if base_params is None:
        base_params = {}

    print("="*80)
    print("Running BASE CASE simulation...")
    print("="*80)

    system_base, tea_base, streams_base, _ = create_and_simulate_system(**base_params)
    basecase_msp = tea_base.solve_price(streams_base['rng'])

    print(f"✓ Base case MSP: ${basecase_msp:.3f}/kg RNG\n")

    # Run sensitivity for each parameter
    results = {}

    for param_name, (low_val, high_val) in parameters_config.items():
        print(f"Running sensitivity for: {param_name}")
        print(f"  Low value:  {low_val}")
        print(f"  High value: {high_val}")

        try:
            # Low case
            params_low = base_params.copy()
            params_low[param_name] = low_val
            sys_low, tea_low, str_low, _ = create_and_simulate_system(**params_low)
            msp_low = tea_low.solve_price(str_low['rng'])

            # High case
            params_high = base_params.copy()
            params_high[param_name] = high_val
            sys_high, tea_high, str_high, _ = create_and_simulate_system(**params_high)
            msp_high = tea_high.solve_price(str_high['rng'])

            results[param_name] = [msp_low, msp_high]

            print(f"  ✓ Low MSP:  ${msp_low:.3f}/kg")
            print(f"  ✓ High MSP: ${msp_high:.3f}/kg")
            print(f"  Range: ${abs(msp_high - msp_low):.3f}/kg\n")

        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            results[param_name] = [None, None]

    return results, basecase_msp


def plot_tornado(results, basecase_msp, title="Tornado Plot: MSP Sensitivity",
                 xlabel="Minimum Selling Price (USD/kg RNG)", parameter_labels=None):
    """
    Create a tornado plot from sensitivity results.

    Parameters
    ----------
    results : dict
        Results from run_sensitivity_analysis
    basecase_msp : float
        Base case MSP value
    title : str
        Plot title
    xlabel : str
        X-axis label
    parameter_labels : dict, optional
        Dictionary mapping parameter names to display labels
    """

    # Filter out failed runs
    valid_results = {k: v for k, v in results.items() if None not in v}

    # Sort by maximum deviation from basecase
    sorted_results = {
        k: v for k, v in sorted(
            valid_results.items(),
            key=lambda item: max(abs(item[1][0] - basecase_msp),
                                abs(item[1][1] - basecase_msp)),
            reverse=True
        )
    }

    # Use custom labels if provided, otherwise use parameter names
    if parameter_labels is None:
        labels = list(sorted_results.keys())
    else:
        labels = [parameter_labels.get(k, k) for k in sorted_results.keys()]
    lows = [v[0] for v in sorted_results.values()]
    highs = [v[1] for v in sorted_results.values()]

    # Create plot
    y = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot bars
    ax.barh(y, [lo - basecase_msp for lo in lows], left=basecase_msp,
            color="steelblue", label="Low", alpha=0.8)
    ax.barh(y, [hi - basecase_msp for hi in highs], left=basecase_msp,
            color="orange", label="High", alpha=0.8)

    # Base case line
    ax.axvline(basecase_msp, color="red", linestyle="--", linewidth=2,
               label=f"Base case = ${basecase_msp:.2f}")

    # Calculate x-axis limits to ensure labels stay inside
    all_values = lows + highs + [basecase_msp]
    x_min = min(all_values)
    x_max = max(all_values)
    x_range = x_max - x_min
    margin = 0.15 * x_range  # 15% margin for labels

    # Set x-axis limits
    ax.set_xlim(x_min - margin, x_max + margin)

    # Annotate values - position labels outside bars but inside plot limits
    for i, (lo, hi) in enumerate(zip(lows, highs)):
        # For low values: place to the left of the bar
        # If bar extends to the left of basecase, place label inside
        if lo < basecase_msp:
            ax.text(lo, i, f"${lo:.2f} ", va="center", ha="right",
                    fontsize=10, color="black", weight="bold")
        else:
            # Bar is to the right of basecase, place label to the left of basecase edge
            ax.text(lo, i, f" ${lo:.2f}", va="center", ha="left",
                    fontsize=10, color="black", weight="bold")

        # For high values: place to the right of the bar
        # If bar extends to the right of basecase, place label outside
        if hi > basecase_msp:
            ax.text(hi, i, f" ${hi:.2f}", va="center", ha="left",
                    fontsize=10, color="black", weight="bold")
        else:
            # Bar is to the left of basecase, place label to the right of basecase edge
            ax.text(hi, i, f"${hi:.2f} ", va="center", ha="right",
                    fontsize=10, color="black", weight="bold")

    # Formatting
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_title(title, fontsize=15, weight="bold")
    ax.legend(fontsize=11, loc='best')
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    ax.invert_yaxis()

    plt.tight_layout()
    plt.show()

    return fig

#%% Step 1: Define base case parameters
base_params = {
    "ISR": 2.0,
    "S0": 300000,
    "F_TOTAL": 100000,
    "feedStock_ratio": 0.5,
    "X10_ratio": 0.6,
    "reactor_tau": 48,
    "reactor_T": 330,
    "IRR": 0.10,
    "lang_factor": 2.7,
    "operating_days": 330,
    "WC_over_FCI": 0.15
}

#%% Step 2: Define parameters with labels
parameters = {
    "reactor_tau": {
        "range": (24, 96),
        "label": "Reactor Residence Time [24-96h]"
    },
    "IRR": {
        "range": (0.05, 0.15),
        "label": "Internal Rate of Return [5-15%]"
    },
    "lang_factor": {
        "range": (2.0, 5.0),
        "label": "Lang Factor [2.0-5.0]"
    },
    "F_TOTAL": {
        "range": (80000, 120000),
        "label": r"SHW Feed Flow [13-20 $ton\cdot h^{-1}$]"
    },
    "biochar_price": {
        "range": (0.15, 0.25),
        "label": r"Biochar Price [150-250 \$$\cdot ton^{-1}$]"
    },
    "DW_feed_price": {
        "range": (0.005, 0.02),
        "label": r"Domestic waste price [5-20 \$$ton^{-1}$]"
    },
    
    "I_feed_price": {
        "range": (0.005, 0.02),
        "label": r"BM price [5-20 \$$ton^{-1}$]"
    },
    "SW_feed_price": {
        "range": (0.01, 0.06),
        "label": r"Sludge waste price [10-60 \$$ton^{-1}$]"
    },
    
    "ISR": {
        "range": (1.5, 2.5),
        "label": "ISR [1.5-2.5]"
    },
    
    "S0": {
        "range": (250000, 350000),
        "label": "Substrate Concentration [250-350 g/L]"
    },
    
    "feedStock_ratio": {
        "range": (0.3, 0.7),
        "label": "SHW Fraction [0.3-0.7]"
    },

    "X10_ratio": {
        "range": (0.4, 0.8),
        "label": "X1 Biomass Fraction in BM [0.4-0.8]"
    },
    
    "WC_over_FCI": {
        "range": (0.05, 0.25),
        "label": "Working Capital over FCI [5-25%]"
    },

}

# Extract ranges and labels
parameters_config = {k: v["range"] for k, v in parameters.items()}
parameter_labels = {k: v["label"] for k, v in parameters.items()}


print("Starting sensitivity analysis...")
results, basecase = run_sensitivity_analysis(parameters_config, base_params)


print("\nGenerating tornado plot...")
fig = plot_tornado(results, basecase, parameter_labels=parameter_labels)

# Save figure to results directory
os.makedirs("results", exist_ok=True)
fig.savefig("results/tornado_plot_TEA.png", dpi=300, bbox_inches='tight')
print("✓ Tornado plot saved to results/tornado_plot_TEA.png")

# %%
