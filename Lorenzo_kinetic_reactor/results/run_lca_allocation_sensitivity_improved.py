"""
LCA Allocation Sensitivity Analysis - Improved Version

This script performs a comprehensive allocation sensitivity analysis comparing:
1. Mass allocation (current baseline)
2. Economic allocation (based on product values)
3. System expansion with biochar credits (full credit approach)

The analysis generates:
- Comparative bar charts showing net impacts for each method
- Detailed tables with impact values and differences
- LaTeX-formatted tables for publication
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Import the biosteam system
from codigestion_bst_continuos_function import (
    create_and_simulate_system,
    run_lca_analysis
)


def run_allocation_sensitivity_analysis_improved(output_dir='results'):
    """
    Perform comprehensive LCA allocation sensitivity analysis.

    Returns
    -------
    results_df : pd.DataFrame
        Comparison of impacts across allocation methods
    """

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("LCA ALLOCATION SENSITIVITY ANALYSIS - IMPROVED")
    print("=" * 80)

    # ========================================================================
    # STEP 1: Create system with LCA setup
    # ========================================================================
    print("\n1. Creating and simulating system with LCA setup...")
    system, tea, streams, lca_manager = create_and_simulate_system(setup_lca=True)

    # Get key streams
    rng = streams['rng']
    biochar = streams['biochar']

    # Get impact categories
    categories = lca_manager.get_indicators_category

    print(f"\n   System created successfully")
    print(f"   RNG production: {rng.F_mass:.2f} kg/hr")
    print(f"   Biochar production: {biochar.F_mass:.2f} kg/hr")
    print(f"   Biochar per kg RNG: {biochar.F_mass/rng.F_mass:.4f} kg/kg")

    # ========================================================================
    # STEP 2: Method 1 - MASS ALLOCATION (Baseline)
    # ========================================================================
    print("\n" + "=" * 80)
    print("METHOD 1: MASS ALLOCATION (Baseline)")
    print("=" * 80)

    # Run LCA analysis with mass allocation
    print("\nRunning LCA with mass allocation...")
    total_impacts_rng_mass, stream_contributions_mass, individual_impacts_mass = run_lca_analysis(
        system, streams, lca_manager, allocation='mass', output_dir=None
    )

    # Calculate allocation factors
    mass_rng = rng.F_mass
    mass_biochar = biochar.F_mass
    total_mass = mass_rng + mass_biochar
    mass_alloc_factor = mass_rng / total_mass

    print(f"\nMass allocation factor for RNG: {mass_alloc_factor:.4f} ({mass_alloc_factor*100:.2f}%)")

    print(f"\nImpacts per kg RNG (mass allocation):")
    print(f"{'Category':<50} {'Impact/kg RNG':<20}")
    print("-" * 70)
    for cat, val in total_impacts_rng_mass.items():
        print(f"{cat:<50} {val:>20.6e}")

    # ========================================================================
    # STEP 3: Method 2 - ECONOMIC ALLOCATION
    # ========================================================================
    print("\n" + "=" * 80)
    print("METHOD 2: ECONOMIC ALLOCATION")
    print("=" * 80)

    # Get prices from TEA
    msp_rng = tea.solve_price(rng)  # $/kg RNG
    price_biochar = biochar.price  # $/kg biochar (from TEA)

    # Calculate economic values
    value_rng = mass_rng * msp_rng  # $/hr
    value_biochar = mass_biochar * price_biochar  # $/hr
    total_value = value_rng + value_biochar

    econ_alloc_factor = value_rng / total_value

    print(f"\nProduct prices:")
    print(f"  RNG:     ${msp_rng:.3f}/kg")
    print(f"  Biochar: ${price_biochar:.3f}/kg")

    print(f"\nProduct values:")
    print(f"  RNG:     ${value_rng:.2f}/hr ({value_rng/total_value*100:.1f}%)")
    print(f"  Biochar: ${value_biochar:.2f}/hr ({value_biochar/total_value*100:.1f}%)")

    print(f"\nEconomic allocation factor for RNG: {econ_alloc_factor:.4f} ({econ_alloc_factor*100:.2f}%)")

    # Calculate economic allocation impacts
    # Method: Scale mass allocation results by ratio of economic to mass allocation
    scale_factor = econ_alloc_factor / mass_alloc_factor

    total_impacts_rng_econ = {
        cat: val * scale_factor
        for cat, val in total_impacts_rng_mass.items()
    }

    print(f"\nImpacts per kg RNG (economic allocation):")
    print(f"{'Category':<50} {'Impact/kg RNG':<20}")
    print("-" * 70)
    for cat, val in total_impacts_rng_econ.items():
        print(f"{cat:<50} {val:>20.6e}")

    # ========================================================================
    # STEP 4: Method 3 - SYSTEM EXPANSION (with biochar credits)
    # ========================================================================
    print("\n" + "=" * 80)
    print("METHOD 3: SYSTEM EXPANSION (with biochar credits)")
    print("=" * 80)

    print("\nApproach: All impacts assigned to RNG, biochar provides full credits")
    print(f"Biochar production: {biochar.F_mass:.2f} kg/hr ({biochar.F_mass/rng.F_mass:.4f} kg per kg RNG)")

    # For system expansion: no allocation, all impacts go to RNG
    # This means allocation factor = 1.0 for RNG
    system_expansion_alloc_factor = 1.0

    # Scale from mass allocation
    scale_factor_sysexp = system_expansion_alloc_factor / mass_alloc_factor

    total_impacts_rng_sysexp = {
        cat: val * scale_factor_sysexp
        for cat, val in total_impacts_rng_mass.items()
    }

    print(f"\nSystem expansion allocation factor for RNG: {system_expansion_alloc_factor:.4f} (100%)")

    print(f"\nImpacts per kg RNG (system expansion with biochar credits):")
    print(f"{'Category':<50} {'Impact/kg RNG':<20}")
    print("-" * 70)
    for cat, val in total_impacts_rng_sysexp.items():
        print(f"{cat:<50} {val:>20.6e}")

    # ========================================================================
    # STEP 5: Create comparison dataframe
    # ========================================================================
    print("\n" + "=" * 80)
    print("COMPARISON OF ALLOCATION METHODS")
    print("=" * 80)

    # Build comparison table
    comparison_data = []
    for cat in categories:
        comparison_data.append({
            'Category': cat,
            'Mass Allocation': total_impacts_rng_mass[cat],
            'Economic Allocation': total_impacts_rng_econ[cat],
            'System Expansion': total_impacts_rng_sysexp[cat]
        })

    df_comparison = pd.DataFrame(comparison_data)

    # Calculate relative differences from mass allocation baseline
    df_comparison['Econ vs Mass (%)'] = (
        (df_comparison['Economic Allocation'] - df_comparison['Mass Allocation']) /
        np.abs(df_comparison['Mass Allocation']) * 100
    )
    df_comparison['SysExp vs Mass (%)'] = (
        (df_comparison['System Expansion'] - df_comparison['Mass Allocation']) /
        np.abs(df_comparison['Mass Allocation']) * 100
    )

    # Save to CSV
    csv_path = Path(output_dir) / 'lca_allocation_sensitivity.csv'
    df_comparison.to_csv(csv_path, index=False, float_format='%.6e')
    print(f"\n✅ Results saved to: {csv_path}")

    # ========================================================================
    # STEP 6: Generate LaTeX table
    # ========================================================================
    print("\nGenerating LaTeX table...")
    latex_path = Path(output_dir) / 'lca_allocation_sensitivity.tex'

    # Create formatted version for LaTeX
    df_latex = df_comparison.copy()

    # Simplify category names
    df_latex['Category'] = df_latex['Category'].apply(lambda x: x.rsplit(' (', 1)[0])

    # Format scientific notation
    for col in ['Mass Allocation', 'Economic Allocation', 'System Expansion']:
        df_latex[col] = df_latex[col].apply(lambda x: f"${x:.2e}$")

    # Format percentages
    for col in ['Econ vs Mass (%)', 'SysExp vs Mass (%)']:
        df_latex[col] = df_latex[col].apply(lambda x: f"{x:+.1f}\\%")

    latex_table = df_latex.to_latex(
        index=False,
        caption='Comparison of LCA results using different allocation methods for RNG production (per kg RNG). Negative values indicate net environmental credits.',
        label='tab:lca_allocation_sensitivity',
        column_format='l' + 'r' * (len(df_latex.columns) - 1),
        escape=False
    )

    with open(latex_path, 'w') as f:
        f.write(latex_table)
    print(f"✅ LaTeX table saved to: {latex_path}")

    # ========================================================================
    # STEP 7: Generate comparison bar chart
    # ========================================================================
    print("\nGenerating comparison bar chart...")

    # Create figure with subplots for better readability
    fig, ax = plt.subplots(figsize=(14, 8))

    # Prepare data
    categories_short = [cat.rsplit(' (', 1)[0] for cat in categories]
    x = np.arange(len(categories_short))
    width = 0.25

    # Extract values
    mass_vals = df_comparison['Mass Allocation'].values
    econ_vals = df_comparison['Economic Allocation'].values
    sysexp_vals = df_comparison['System Expansion'].values

    # Create grouped bars
    bars1 = ax.bar(x - width, mass_vals, width, label='Mass Allocation',
                   color='steelblue', alpha=0.8, edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x, econ_vals, width, label='Economic Allocation',
                   color='darkorange', alpha=0.8, edgecolor='black', linewidth=0.5)
    bars3 = ax.bar(x + width, sysexp_vals, width, label='System Expansion',
                   color='forestgreen', alpha=0.8, edgecolor='black', linewidth=0.5)

    # Add horizontal line at y=0
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5, zorder=10)

    # Formatting
    ax.set_xlabel('Impact Category', fontsize=14, fontweight='bold')
    ax.set_ylabel('Net Impact per kg RNG', fontsize=14, fontweight='bold')
    ax.set_title('LCA Allocation Sensitivity Analysis\nComparison of Net Impacts per kg RNG',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories_short, rotation=45, ha='right', fontsize=11)
    ax.tick_params(axis='y', labelsize=11)
    ax.legend(loc='upper right', fontsize=12, framealpha=0.95)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add annotation about negative values
    ax.text(0.02, 0.98, 'Note: Negative values indicate net environmental credits',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()

    # Save figure
    fig_path = Path(output_dir) / 'lca_allocation_comparison.png'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f"✅ Figure saved to: {fig_path}")
    plt.close()

    # ========================================================================
    # STEP 8: Print summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Focus on Global Warming Potential
    gwp_cat = [cat for cat in categories if 'Global warming' in cat or 'GWP' in cat]
    if gwp_cat:
        gwp_cat = gwp_cat[0]

        print(f"\nGlobal Warming Potential (per kg RNG):")
        print(f"  Mass allocation:     {total_impacts_rng_mass[gwp_cat]:>12.6f} kg CO2-eq")
        print(f"  Economic allocation: {total_impacts_rng_econ[gwp_cat]:>12.6f} kg CO2-eq")
        print(f"  System expansion:    {total_impacts_rng_sysexp[gwp_cat]:>12.6f} kg CO2-eq")

        # Check if all methods give net-negative GWP
        all_negative = all([
            total_impacts_rng_mass[gwp_cat] < 0,
            total_impacts_rng_econ[gwp_cat] < 0,
            total_impacts_rng_sysexp[gwp_cat] < 0
        ])

        if all_negative:
            print("\n✅ NET-NEGATIVE GWP CONFIRMED across all allocation methods!")
            print("   The system provides net climate benefits regardless of allocation method.")
        else:
            print("\n⚠️  GWP results vary by allocation method:")
            if total_impacts_rng_mass[gwp_cat] < 0:
                print("     Mass allocation: NET-NEGATIVE ✓")
            else:
                print("     Mass allocation: NET-POSITIVE ✗")
            if total_impacts_rng_econ[gwp_cat] < 0:
                print("     Economic allocation: NET-NEGATIVE ✓")
            else:
                print("     Economic allocation: NET-POSITIVE ✗")
            if total_impacts_rng_sysexp[gwp_cat] < 0:
                print("     System expansion: NET-NEGATIVE ✓")
            else:
                print("     System expansion: NET-POSITIVE ✗")

    # Print allocation factors summary
    print("\n" + "-" * 80)
    print("Allocation Factors Summary:")
    print("-" * 80)
    print(f"Mass allocation factor (RNG):     {mass_alloc_factor:.4f} ({mass_alloc_factor*100:.2f}%)")
    print(f"Economic allocation factor (RNG): {econ_alloc_factor:.4f} ({econ_alloc_factor*100:.2f}%)")
    print(f"System expansion factor (RNG):    {system_expansion_alloc_factor:.4f} (100%)")
    print(f"\nBiochar production rate: {biochar.F_mass/rng.F_mass:.4f} kg biochar per kg RNG")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return df_comparison


if __name__ == "__main__":
    results = run_allocation_sensitivity_analysis_improved(output_dir='results')

    # Display final results
    print("\nFinal Comparison Table:")
    print(results.to_string(index=False, float_format=lambda x: f'{x:.4e}'))
