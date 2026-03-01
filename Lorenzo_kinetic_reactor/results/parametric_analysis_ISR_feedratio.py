"""
Análisis Paramétrico 2D: ISR vs feedStock_ratio
Visualiza cómo varían RNG, MSP y GWP con estos dos parámetros clave
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from codigestion_bst_continuos_function import create_and_simulate_system
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Parámetros base del caso base
BASE_PARAMS = {
    "S0": 300000,
    "F_TOTAL": 100000,
    "reactor_tau": 48,
    "reactor_T": 330,
    "IRR": 0.10,
    "lang_factor": 2.7,
    "operating_days": 330,
    "X10_ratio": 0.6  # Fijo
}

# Rangos de variación
ISR_VALUES = np.linspace(0.5, 2.5, 15)  # De 0.5 a 2.5
FEEDSTOCK_RATIO_VALUES = np.linspace(0.0, 1.0, 15)  # De 0 (100% DW) a 1 (100% SW)

print("="*80)
print("ANÁLISIS PARAMÉTRICO 2D: ISR vs feedStock_ratio")
print("="*80)
print(f"\nISR range: {ISR_VALUES.min():.2f} - {ISR_VALUES.max():.2f} ({len(ISR_VALUES)} points)")
print(f"feedStock_ratio range: {FEEDSTOCK_RATIO_VALUES.min():.2f} - {FEEDSTOCK_RATIO_VALUES.max():.2f} ({len(FEEDSTOCK_RATIO_VALUES)} points)")
print(f"Total simulations: {len(ISR_VALUES) * len(FEEDSTOCK_RATIO_VALUES)}")
print(f"\nBase parameters:")
for key, val in BASE_PARAMS.items():
    print(f"  {key}: {val}")

# ========================================================================
# SETUP LCA MANAGER (one time)
# ========================================================================
print("\n" + "="*80)
print("SETTING UP LCA MANAGER")
print("="*80)

shared_lca_manager = None
try:
    dummy_params = BASE_PARAMS.copy()
    dummy_params.update({
        'ISR': 2.0,
        'feedStock_ratio': 0.5,
        'setup_lca': True
    })
    _, _, _, shared_lca_manager = create_and_simulate_system(**dummy_params)
    print("✓ LCA manager created successfully!\n")
    setup_lca = True
except Exception as e:
    print(f"❌ Failed to create LCA manager: {e}")
    print("  Continuing without LCA\n")
    setup_lca = False

# ========================================================================
# RUN PARAMETRIC ANALYSIS
# ========================================================================
print("="*80)
print("RUNNING PARAMETRIC SWEEP")
print("="*80)

# Initialize storage
results = {
    'ISR': [],
    'feedStock_ratio': [],
    'MSP': [],
    'RNG_production_kg_h': [],
    'RNG_production_GJ_year': [],
    'GWP': [],
    'success': []
}

total_sims = len(ISR_VALUES) * len(FEEDSTOCK_RATIO_VALUES)

with tqdm(total=total_sims, desc="Simulations") as pbar:
    for isr in ISR_VALUES:
        for feed_ratio in FEEDSTOCK_RATIO_VALUES:

            # Store input parameters
            results['ISR'].append(isr)
            results['feedStock_ratio'].append(feed_ratio)

            # Setup simulation parameters
            sim_params = BASE_PARAMS.copy()
            sim_params['ISR'] = isr
            sim_params['feedStock_ratio'] = feed_ratio
            sim_params['setup_lca'] = False

            if setup_lca and shared_lca_manager is not None:
                sim_params['lca_manager_reuse'] = shared_lca_manager

            try:
                # Run simulation
                system, tea, streams, lca_manager = create_and_simulate_system(**sim_params)

                # Calculate MSP
                msp = tea.solve_price(streams['rng'])

                # Get RNG production
                rng_kg_h = streams['rng'].F_mass
                rng_gj_year = rng_kg_h * 53 * 8000 / 1000 / 1000

                # Get GWP
                if setup_lca and lca_manager is not None:
                    try:
                        gwp_total_annual = system.get_net_impact('Global warming (kg CO2 eq)')
                        if gwp_total_annual is not None and system.operating_hours is not None:
                            gwp_per_hour = gwp_total_annual / system.operating_hours

                            # Mass allocation
                            biochar_flow = streams['biochar'].F_mass if streams['biochar'].F_mass > 0 else 0
                            total_product_flow = rng_kg_h + biochar_flow

                            if total_product_flow > 1e-6:
                                mass_allocation = rng_kg_h / total_product_flow
                            else:
                                mass_allocation = 1.0

                            # GWP per kg RNG
                            if rng_kg_h > 1e-6:
                                gwp = (gwp_per_hour * mass_allocation) / rng_kg_h
                            else:
                                gwp = np.nan
                        else:
                            gwp = np.nan
                    except:
                        gwp = np.nan
                else:
                    gwp = np.nan

                # Store results
                results['MSP'].append(msp)
                results['RNG_production_kg_h'].append(rng_kg_h)
                results['RNG_production_GJ_year'].append(rng_gj_year)
                results['GWP'].append(gwp)
                results['success'].append(True)

            except Exception as e:
                # Failed simulation
                results['MSP'].append(np.nan)
                results['RNG_production_kg_h'].append(np.nan)
                results['RNG_production_GJ_year'].append(np.nan)
                results['GWP'].append(np.nan)
                results['success'].append(False)

            pbar.update(1)

# Convert to DataFrame
df = pd.DataFrame(results)

# Save results
import os
os.makedirs('results', exist_ok=True)
df.to_csv('results/parametric_ISR_feedratio.csv', index=False)

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print(f"Successful simulations: {df['success'].sum()}/{len(df)} ({df['success'].sum()/len(df)*100:.1f}%)")
print(f"Results saved to: results/parametric_ISR_feedratio.csv")

# ========================================================================
# CREATE VISUALIZATIONS
# ========================================================================
print("\n" + "="*80)
print("GENERATING VISUALIZATIONS")
print("="*80)

df_success = df[df['success']].copy()

# Create meshgrid for contour plots
isr_unique = sorted(df_success['ISR'].unique())
feed_unique = sorted(df_success['feedStock_ratio'].unique())

# Pivot data for heatmaps
msp_pivot = df_success.pivot_table(values='MSP', index='ISR', columns='feedStock_ratio')
rng_pivot = df_success.pivot_table(values='RNG_production_kg_h', index='ISR', columns='feedStock_ratio')
gwp_pivot = df_success.pivot_table(values='GWP', index='ISR', columns='feedStock_ratio')

# ========================================================================
# Figure 1: RNG Production (kg/h)
# ========================================================================
fig, ax = plt.subplots(figsize=(14, 10))

contour = ax.contourf(rng_pivot.columns, rng_pivot.index, rng_pivot.values,
                       levels=20, cmap='RdYlGn', alpha=0.9)

# Add contour lines
contour_lines = ax.contour(rng_pivot.columns, rng_pivot.index, rng_pivot.values,
                            levels=10, colors='black', linewidths=0.5, alpha=0.4)
ax.clabel(contour_lines, inline=True, fontsize=14, fmt='%.0f')

# Colorbar
cbar = plt.colorbar(contour, ax=ax)
cbar.set_label('RNG Production (kg/h)', fontsize=24, fontweight='bold')
cbar.ax.tick_params(labelsize=20)

ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=26, fontweight='bold')
ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=26, fontweight='bold')
ax.set_title('RNG Production as Function of ISR and feedStock Ratio',
             fontsize=28, fontweight='bold', pad=20)
ax.tick_params(axis='both', labelsize=22)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('results/parametric_RNG_production.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/parametric_RNG_production.png")

# ========================================================================
# Figure 2: MSP ($/kg RNG)
# ========================================================================
fig, ax = plt.subplots(figsize=(14, 10))

contour = ax.contourf(msp_pivot.columns, msp_pivot.index, msp_pivot.values,
                       levels=20, cmap='RdYlGn_r', alpha=0.9)

# Add contour lines
contour_lines = ax.contour(msp_pivot.columns, msp_pivot.index, msp_pivot.values,
                            levels=10, colors='black', linewidths=0.5, alpha=0.4)
ax.clabel(contour_lines, inline=True, fontsize=14, fmt='%.2f')

# Colorbar
cbar = plt.colorbar(contour, ax=ax)
cbar.set_label('MSP ($/kg RNG)', fontsize=24, fontweight='bold')
cbar.ax.tick_params(labelsize=20)

ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=26, fontweight='bold')
ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=26, fontweight='bold')
ax.set_title('MSP as Function of ISR and feedStock Ratio',
             fontsize=28, fontweight='bold', pad=20)
ax.tick_params(axis='both', labelsize=22)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('results/parametric_MSP.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/parametric_MSP.png")

# ========================================================================
# Figure 3: GWP (kg CO2-eq/kg RNG)
# ========================================================================
if not gwp_pivot.isna().all().all():
    fig, ax = plt.subplots(figsize=(14, 10))

    contour = ax.contourf(gwp_pivot.columns, gwp_pivot.index, gwp_pivot.values,
                           levels=20, cmap='RdYlGn', alpha=0.9)

    # Add contour lines
    contour_lines = ax.contour(gwp_pivot.columns, gwp_pivot.index, gwp_pivot.values,
                                levels=10, colors='black', linewidths=0.5, alpha=0.4)
    ax.clabel(contour_lines, inline=True, fontsize=14, fmt='%.0f')

    # Colorbar
    cbar = plt.colorbar(contour, ax=ax)
    cbar.set_label('GWP (kg CO2-eq/kg RNG)', fontsize=24, fontweight='bold')
    cbar.ax.tick_params(labelsize=20)

    ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=26, fontweight='bold')
    ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=26, fontweight='bold')
    ax.set_title('GWP as Function of ISR and feedStock Ratio',
                 fontsize=28, fontweight='bold', pad=20)
    ax.tick_params(axis='both', labelsize=22)
    ax.grid(alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig('results/parametric_GWP.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: results/parametric_GWP.png")

# ========================================================================
# Figure 4: 3D Surface Plot - RNG Production
# ========================================================================
fig = plt.figure(figsize=(16, 12))
ax = fig.add_subplot(111, projection='3d')

X, Y = np.meshgrid(rng_pivot.columns, rng_pivot.index)
Z = rng_pivot.values

surf = ax.plot_surface(X, Y, Z, cmap='RdYlGn', alpha=0.9,
                        edgecolor='none', antialiased=True)

ax.set_xlabel('feedStock_ratio\n(0=DW, 1=SW)', fontsize=22, fontweight='bold', labelpad=15)
ax.set_ylabel('ISR', fontsize=22, fontweight='bold', labelpad=15)
ax.set_zlabel('RNG Production\n(kg/h)', fontsize=22, fontweight='bold', labelpad=15)
ax.set_title('3D Surface: RNG Production', fontsize=26, fontweight='bold', pad=20)

# Colorbar
cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
cbar.set_label('RNG (kg/h)', fontsize=20, fontweight='bold')
cbar.ax.tick_params(labelsize=18)

ax.tick_params(axis='both', labelsize=18)
ax.view_init(elev=25, azim=45)

plt.tight_layout()
plt.savefig('results/parametric_RNG_3D.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/parametric_RNG_3D.png")

# ========================================================================
# INDIVIDUAL CONTOUR PLOTS (4 separate figures)
# ========================================================================

# Plot 1: RNG Production (kg/h)
fig, ax = plt.subplots(figsize=(14, 10))
contour = ax.contourf(rng_pivot.columns, rng_pivot.index, rng_pivot.values,
                       levels=20, cmap='RdYlGn', alpha=0.9)
contour_lines = ax.contour(rng_pivot.columns, rng_pivot.index, rng_pivot.values,
                            levels=10, colors='black', linewidths=1.2, alpha=0.6)
ax.clabel(contour_lines, inline=True, fontsize=18, fmt='%.0f', fontweight='bold')
cbar = plt.colorbar(contour, ax=ax)
cbar.set_label('RNG Production (kg/h)', fontsize=26, fontweight='bold')
cbar.ax.tick_params(labelsize=22)
ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=28, fontweight='bold')
ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=28, fontweight='bold')
ax.set_title('RNG Production (kg/h)', fontsize=32, fontweight='bold', pad=20)
ax.tick_params(axis='both', labelsize=24)
ax.grid(alpha=0.3, linestyle='--', linewidth=1)
plt.tight_layout()
plt.savefig('results/contour_RNG_kg_h.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/contour_RNG_kg_h.png")
plt.close()

# Plot 2: RNG Production (GJ/year)
rng_gj_pivot = df_success.pivot_table(values='RNG_production_GJ_year', index='ISR', columns='feedStock_ratio')
fig, ax = plt.subplots(figsize=(14, 10))
contour = ax.contourf(rng_gj_pivot.columns, rng_gj_pivot.index, rng_gj_pivot.values,
                       levels=20, cmap='RdYlGn', alpha=0.9)
contour_lines = ax.contour(rng_gj_pivot.columns, rng_gj_pivot.index, rng_gj_pivot.values,
                            levels=10, colors='black', linewidths=1.2, alpha=0.6)
ax.clabel(contour_lines, inline=True, fontsize=18, fmt='%.0f', fontweight='bold')
cbar = plt.colorbar(contour, ax=ax)
cbar.set_label('RNG Production (GJ/year)', fontsize=26, fontweight='bold')
cbar.ax.tick_params(labelsize=22)
ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=28, fontweight='bold')
ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=28, fontweight='bold')
ax.set_title('RNG Production (GJ/year)', fontsize=32, fontweight='bold', pad=20)
ax.tick_params(axis='both', labelsize=24)
ax.grid(alpha=0.3, linestyle='--', linewidth=1)
plt.tight_layout()
plt.savefig('results/contour_RNG_GJ_year.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/contour_RNG_GJ_year.png")
plt.close()

# Plot 3: MSP ($/kg RNG)
fig, ax = plt.subplots(figsize=(14, 10))
contour = ax.contourf(msp_pivot.columns, msp_pivot.index, msp_pivot.values,
                       levels=20, cmap='RdYlGn_r', alpha=0.9)
contour_lines = ax.contour(msp_pivot.columns, msp_pivot.index, msp_pivot.values,
                            levels=10, colors='black', linewidths=1.2, alpha=0.6)
ax.clabel(contour_lines, inline=True, fontsize=18, fmt='%.2f', fontweight='bold')
cbar = plt.colorbar(contour, ax=ax)
cbar.set_label('MSP ($/kg RNG)', fontsize=26, fontweight='bold')
cbar.ax.tick_params(labelsize=22)
ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=28, fontweight='bold')
ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=28, fontweight='bold')
ax.set_title('Minimum Selling Price ($/kg RNG)', fontsize=32, fontweight='bold', pad=20)
ax.tick_params(axis='both', labelsize=24)
ax.grid(alpha=0.3, linestyle='--', linewidth=1)
plt.tight_layout()
plt.savefig('results/contour_MSP.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/contour_MSP.png")
plt.close()

# Plot 4: GWP (kg CO2-eq/kg RNG)
if not gwp_pivot.isna().all().all():
    fig, ax = plt.subplots(figsize=(14, 10))
    contour = ax.contourf(gwp_pivot.columns, gwp_pivot.index, gwp_pivot.values,
                           levels=20, cmap='RdYlGn', alpha=0.9)
    contour_lines = ax.contour(gwp_pivot.columns, gwp_pivot.index, gwp_pivot.values,
                                levels=10, colors='black', linewidths=1.2, alpha=0.6)
    ax.clabel(contour_lines, inline=True, fontsize=18, fmt='%.0f', fontweight='bold')
    cbar = plt.colorbar(contour, ax=ax)
    cbar.set_label('GWP (kg CO2-eq/kg RNG)', fontsize=26, fontweight='bold')
    cbar.ax.tick_params(labelsize=22)
    ax.set_xlabel('feedStock_ratio (0=100% DW, 1=100% SW)', fontsize=28, fontweight='bold')
    ax.set_ylabel('ISR (Inoculum to Substrate Ratio)', fontsize=28, fontweight='bold')
    ax.set_title('Global Warming Potential (kg CO2-eq/kg RNG)', fontsize=32, fontweight='bold', pad=20)
    ax.tick_params(axis='both', labelsize=24)
    ax.grid(alpha=0.3, linestyle='--', linewidth=1)
    plt.tight_layout()
    plt.savefig('results/contour_GWP.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: results/contour_GWP.png")
    plt.close()
else:
    print("⚠ Skipped: GWP contour (no valid data)")

print("\n" + "="*80)
print("ALL VISUALIZATIONS COMPLETE!")
print("="*80)
print("\nGenerated files:")
print("  - results/parametric_ISR_feedratio.csv")
print("  - results/parametric_RNG_production.png")
print("  - results/parametric_MSP.png")
print("  - results/parametric_GWP.png")
print("  - results/parametric_RNG_3D.png")
print("  - results/parametric_combined.png")
print("="*80)

plt.show()
