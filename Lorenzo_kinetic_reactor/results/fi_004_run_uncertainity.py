#%%
"""
Monte Carlo Uncertainty Analysis for MSP and GWP

Analyzes the uncertainty in MSP and GWP (Global Warming Potential) based on 4 key parameters:
1. reactor_tau - Residence time (h)
2. ISR - Inoculum to Substrate Ratio
3. S0 - Volatile Solids concentration (mg/L)
4. feedStock_ratio - Fraction of SW vs DW (0-1)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from codigestion_bst_continuos_function import create_and_simulate_system
import os
from tqdm import tqdm
import warnings
import signal
from contextlib import contextmanager
warnings.filterwarnings('ignore')
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression


# Set random seed for reproducibility
np.random.seed(42)


# ============================================================================
# VARIABLE NAME MAPPING - Centralized dictionary for all plots and tables
# ============================================================================
VARIABLE_NAMES = {
    # Input parameters
    'reactor_tau': 'Reactor Residence Time' + '\n' + '[12-240 h]',
'ISR': 'ISR' + '\n' + '[0.5-2.5]',
'S0': r'Initial VS Concentration' + '\n' + r'[200-350 $g\cdot L^{-1}$]',
'feedStock_ratio': 'Feedstock Ratio SW/(SW+DW)' + '\n' + '[0-1]',


    # Output variables
    'MSP': r'Minimum Selling Price ($\$ \cdot kg^{-1}_{RNG}$)',
    'GWP': r'Global Warming Potential ($kg_{CO_2e} kg_{RNG}^{-1}$)',
    'RNG_flow': r'RNG Production Rate ($kg \cdot h^{-1}$)',
    'RNG_production_GJ_year': r'RNG Production (GJ/year)',
    'biochar_flow': r'Biochar Production Rate ($kg \cdot h^{-1}$)',
    'mass_allocation': r'Mass Allocation Factor',

    # Short names for legends
    'reactor_tau_short': 'τ (h)',
    'ISR_short': 'ISR',
    'S0_short': 'S₀ (mg/L)',
    'feedStock_ratio_short': 'f_SW',
    'MSP_short': r'MSP ($\$\cdot kg^{-1}$)',
    'GWP_short': r'GWP ($kg_{CO_2} \cdot kg^{-1}$)',
    'RNG_flow_short': r'RNG ($kg \cdot h^{-1}$)',
}


class TimeoutException(Exception):
    """Exception raised when a simulation times out"""
    pass


@contextmanager
def time_limit(seconds):
    """
    Context manager to limit execution time of a code block.

    Parameters
    ----------
    seconds : int
        Maximum execution time in seconds
    """
    def signal_handler(signum, frame):
        raise TimeoutException(f"Simulation timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def define_parameter_distributions():
    """
    Define probability distributions for uncertain parameters.

    Returns
    -------
    distributions : dict
        Dictionary with parameter names as keys and distribution info as values
    """

    distributions = {
        'reactor_tau': {
            'type': 'uniform',
            'params': {'low': 12, 'high': 240},
            'label': 'Residence Time (h)',
            'base': 48
        },
        'ISR': {
            'type': 'uniform',
            'params': {'low': 0.5, 'high': 2.5},
            'label': 'Inoculum to Substrate Ratio',
            'base': 2.0
        },
        'S0': {
            'type': 'uniform',
            'params': {'low': 200000, 'high': 350000},
            'label': 'VS Concentration (mg/L)',
            'base': 300000
        },
        'feedStock_ratio': {
            'type': 'uniform',
            'params': {'low': 0, 'high': 1},
            'label': 'SW Fraction (-)',
            'base': 0.5
        }
    }

    return distributions


def sample_parameter(distribution_info, n_samples=1):
    """
    Sample from a parameter distribution.

    Parameters
    ----------
    distribution_info : dict
        Distribution information
    n_samples : int
        Number of samples to generate

    Returns
    -------
    samples : np.array
        Array of sampled values
    """

    dist_type = distribution_info['type']
    params = distribution_info['params']

    if dist_type == 'uniform':
        return np.random.uniform(params['low'], params['high'], n_samples)
    elif dist_type == 'normal':
        return np.random.normal(params['mean'], params['std'], n_samples)
    elif dist_type == 'triangular':
        return np.random.triangular(params['left'], params['mode'], params['right'], n_samples)
    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")


def run_monte_carlo_analysis(n_iterations=1000, base_params=None, save_intermediate=True, timeout=120, calculate_gwp=True):
    """
    Run Monte Carlo uncertainty analysis for MSP and GWP.

    Parameters
    ----------
    n_iterations : int
        Number of Monte Carlo iterations
    base_params : dict, optional
        Base case parameters (fixed values)
    save_intermediate : bool
        If True, save results every 100 iterations
    timeout : int, optional
        Maximum time in seconds for each simulation (default: 120s)
    calculate_gwp : bool, optional
        If True, calculate GWP. If False, only calculate MSP (faster, default: True)

    Returns
    -------
    results_df : pd.DataFrame
        DataFrame with all parameter combinations and resulting MSP and GWP
    """

    # Get parameter distributions
    distributions = define_parameter_distributions()

    # Base parameters (fixed values not varied in uncertainty analysis)
    if base_params is None:
        base_params = {
            "F_TOTAL": 100000,
            "X10_ratio": 0.6,
            "reactor_T": 330,
            "IRR": 0.10,
            "lang_factor": 2.7,
            "operating_days": 330,
            "setup_lca": calculate_gwp  # Enable LCA only if calculating GWP
        }

    # Initialize results storage
    results = {param: [] for param in distributions.keys()}
    results['MSP'] = []
    results['GWP'] = []  # Add GWP to results
    # Add flow tracking for analysis
    results['RNG_flow'] = []  # kg/hr
    results['biochar_flow'] = []  # kg/hr
    results['mass_allocation'] = []  # fraction to RNG
    results['iteration'] = []
    results['success'] = []
    results['error_message'] = []

    print("="*80)
    print(f"Starting Monte Carlo Analysis with {n_iterations} iterations")
    print(f"Timeout per simulation: {timeout} seconds")
    print(f"Calculate GWP: {calculate_gwp}")
    print("="*80)
    print("\nParameter Distributions:")
    for param_name, info in distributions.items():
        print(f"  {info['label']}: {info['type']} - {info['params']}")
    print()

    # ========================================================================
    # CREAR LCA MANAGER UNA SOLA VEZ (si se va a calcular GWP)
    # ========================================================================
    shared_lca_manager = None
    if calculate_gwp:
        print("="*80)
        print("SETTING UP LCA MANAGER (one-time setup)")
        print("="*80)
        print("Creating LCA manager and assigning impacts...")
        print("This will be reused for all iterations (MUCH FASTER!)\n")

        # Create a dummy system just to setup LCA
        dummy_params = base_params.copy()
        dummy_params.update({
            'reactor_tau': 48,
            'ISR': 2.0,
            'S0': 300000,
            'feedStock_ratio': 0.5,
            'setup_lca': True  # This will trigger LCA setup
        })

        try:
            _, _, _, shared_lca_manager = create_and_simulate_system(**dummy_params)
            print("\n✓ LCA manager created successfully!")
            print("  This manager will be reused for all iterations.\n")
        except Exception as e:
            print(f"\n❌ Failed to create LCA manager: {e}")
            print("  Setting CALCULATE_GWP to False\n")
            calculate_gwp = False
            shared_lca_manager = None

    # Run Monte Carlo iterations
    successful_runs = 0
    failed_runs = 0
    timeout_runs = 0

    # Create log file for monitoring progress
    import datetime
    log_file = 'results/uncertainty_progress.log'
    with open(log_file, 'w') as f:
        f.write(f"Monte Carlo Analysis Started: {datetime.datetime.now()}\n")
        f.write(f"Total iterations: {n_iterations}\n")
        f.write(f"Calculate GWP: {calculate_gwp}\n")
        f.write("="*80 + "\n\n")

    print(f"\n📝 Progress log: {log_file}")
    print("   You can monitor progress with: tail -f {log_file}\n")

    for i in tqdm(range(n_iterations), desc="Running simulations"):
        # Log iteration start
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"ITERATION {i}/{n_iterations}\n")
            f.write(f"{'='*80}\n")
            f.flush()

        # Sample parameters
        sampled_params = base_params.copy()
        for param_name, dist_info in distributions.items():
            sampled_params[param_name] = sample_parameter(dist_info, n_samples=1)[0]

        # Log sampled parameters
        with open(log_file, 'a') as f:
            f.write(f"Sampled parameters:\n")
            for param_name in distributions.keys():
                f.write(f"  {param_name}: {sampled_params[param_name]:.2f}\n")
            f.flush()

        # Store sampled parameters
        results['iteration'].append(i)
        for param_name in distributions.keys():
            results[param_name].append(sampled_params[param_name])

        # Run simulation with timeout
        try:
            with time_limit(timeout):
                # Create and simulate system
                with open(log_file, 'a') as f:
                    f.write("Creating system...\n")
                    f.flush()

                if i < 3:  # Debug for first 3 iterations
                    tqdm.write(f"\n[Iter {i}] Starting system creation...")

                # Prepare parameters
                sim_params = sampled_params.copy()
                sim_params['setup_lca'] = False  # Don't setup LCA (we reuse it)

                # If calculating GWP, pass the shared LCA manager
                if calculate_gwp and shared_lca_manager is not None:
                    sim_params['lca_manager_reuse'] = shared_lca_manager

                system, tea, streams, lca_manager = create_and_simulate_system(**sim_params)

                with open(log_file, 'a') as f:
                    f.write("✓ System created successfully\n")
                    f.flush()

                if i < 3:
                    tqdm.write(f"[Iter {i}] System created. Starting MSP calculation...")

                # Calculate MSP
                msp = tea.solve_price(streams['rng'])

                # Get flow values for tracking
                rng = streams['rng']
                biochar = streams['biochar']
                rng_flow = rng.F_mass  # kg/hr
                biochar_flow = biochar.F_mass  # kg/hr
                total_flow = rng_flow + biochar_flow

                # Check for zero flows (problematic cases)
                if total_flow < 1e-6:
                    raise Exception(f"Zero total product flow: RNG={rng_flow:.6f}, biochar={biochar_flow:.6f}")

                mass_allocation = rng_flow / total_flow

                if i < 3:
                    tqdm.write(f"[Iter {i}] MSP = ${msp:.3f}")
                    tqdm.write(f"[Iter {i}] RNG flow = {rng_flow:.2f} kg/hr, Biochar = {biochar_flow:.2f} kg/hr")
                    tqdm.write(f"[Iter {i}] Mass allocation = {mass_allocation:.4f}. GWP calculation: {calculate_gwp}")

                # Calculate GWP (Global warming potential) - ONLY IF REQUESTED
                if calculate_gwp:
                    # Log to file
                    with open(log_file, 'a') as f:
                        f.write(f"[Iter {i}] Starting GWP calculation...\n")
                        f.write(f"  RNG flow: {rng_flow:.3f} kg/hr\n")
                        f.write(f"  Mass allocation: {mass_allocation:.4f}\n")
                        f.flush()

                    if i < 3:
                        tqdm.write(f"[Iter {i}] Starting GWP calculation (calling get_net_impact)...")
                        tqdm.write(f"[Iter {i}]   RNG flow = {rng_flow:.3f} kg/hr")
                        tqdm.write(f"[Iter {i}]   Mass allocation = {mass_allocation:.4f}")
                        tqdm.write(f"[Iter {i}]   Operating hours = {system.operating_hours:.1f}")

                    # VERIFICACIÓN: Si RNG flow es muy bajo, saltamos GWP
                    if rng_flow < 0.01:  # Si RNG < 0.01 kg/hr, no tiene sentido calcular GWP
                        if i < 3:
                            tqdm.write(f"[Iter {i}] ⚠️ RNG flow too low ({rng_flow:.6f}), skipping GWP")
                        with open(log_file, 'a') as f:
                            f.write(f"  ⚠️ RNG flow too low, skipping GWP\n")
                            f.flush()
                        gwp_rng = np.nan
                    else:
                        # Get Global warming impact - this can be slow/hang
                        with open(log_file, 'a') as f:
                            f.write(f"  Calling system.get_net_impact()...\n")
                            f.flush()

                        try:
                            gwp_total = system.get_net_impact(key='Global warming (kg CO2 eq)') / system.operating_hours

                            with open(log_file, 'a') as f:
                                f.write(f"  ✓ GWP total: {gwp_total:.3f} kg CO2-eq/hr\n")
                                f.flush()

                            if i < 3:
                                tqdm.write(f"[Iter {i}]   GWP total = {gwp_total:.3f} kg CO2-eq/hr")

                            gwp_rng = gwp_total * mass_allocation / rng_flow  # kg CO2-eq / kg RNG

                            with open(log_file, 'a') as f:
                                f.write(f"  ✓ GWP per kg RNG: {gwp_rng:.3f} kg CO2-eq/kg\n\n")
                                f.flush()

                            if i < 3:
                                tqdm.write(f"[Iter {i}] ✓ GWP = {gwp_rng:.3f} kg CO2-eq/kg RNG")
                        except (KeyError, AttributeError) as e:
                            # If 'Global warming' key doesn't exist, try alternatives
                            raise Exception(f"GWP calculation failed: {e}")
                else:
                    gwp_rng = np.nan  # Skip GWP calculation
                    if i < 3:
                        tqdm.write(f"[Iter {i}] GWP calculation SKIPPED")

            # If we get here, simulation completed within timeout
            if i < 3:
                tqdm.write(f"[Iter {i}] ✓ Simulation completed successfully\n")

            # Log success
            with open(log_file, 'a') as f:
                f.write(f"✓✓✓ ITERATION {i} COMPLETED SUCCESSFULLY ✓✓✓\n")
                f.write(f"  MSP: ${msp:.3f}/kg\n")
                f.write(f"  GWP: {gwp_rng:.3f} kg CO2-eq/kg RNG\n\n")
                f.flush()

            # Store all results
            results['MSP'].append(msp)
            results['GWP'].append(gwp_rng)
            results['RNG_flow'].append(rng_flow)
            results['biochar_flow'].append(biochar_flow)
            results['mass_allocation'].append(mass_allocation)
            results['success'].append(True)
            results['error_message'].append('')
            successful_runs += 1

        except TimeoutException as e:
            results['MSP'].append(np.nan)
            results['GWP'].append(np.nan)
            results['RNG_flow'].append(np.nan)
            results['biochar_flow'].append(np.nan)
            results['mass_allocation'].append(np.nan)
            results['success'].append(False)
            results['error_message'].append(f'TIMEOUT: {str(e)}')
            timeout_runs += 1
            failed_runs += 1
            # Print timeout info for debugging
            if timeout_runs <= 5:  # Only print first 5 timeouts
                tqdm.write(f"\n⚠️  Iteration {i} timed out with params: tau={sampled_params['reactor_tau']:.1f}, ISR={sampled_params['ISR']:.2f}, S0={sampled_params['S0']:.0f}, feedStock={sampled_params['feedStock_ratio']:.2f}")

        except Exception as e:
            results['MSP'].append(np.nan)
            results['GWP'].append(np.nan)
            results['RNG_flow'].append(np.nan)
            results['biochar_flow'].append(np.nan)
            results['mass_allocation'].append(np.nan)
            results['success'].append(False)
            error_msg = str(e)
            results['error_message'].append(error_msg)
            failed_runs += 1
            # Print first few errors for debugging
            if failed_runs - timeout_runs <= 5:
                tqdm.write(f"\n❌ Iteration {i} failed: {error_msg[:100]}")

        # Save intermediate results
        if save_intermediate and (i + 1) % 100 == 0:
            temp_df = pd.DataFrame(results)
            temp_df.to_csv('results/uncertainty_intermediate.csv', index=False)

    # Create final DataFrame
    results_df = pd.DataFrame(results)

    print("\n" + "="*80)
    print("Monte Carlo Analysis Complete!")
    print("="*80)
    print(f"Successful runs: {successful_runs}/{n_iterations} ({successful_runs/n_iterations*100:.1f}%)")
    print(f"Failed runs: {failed_runs}/{n_iterations} ({failed_runs/n_iterations*100:.1f}%)")
    print(f"  - Timeouts: {timeout_runs}/{n_iterations} ({timeout_runs/n_iterations*100:.1f}%)")
    print(f"  - Other errors: {failed_runs - timeout_runs}/{n_iterations} ({(failed_runs - timeout_runs)/n_iterations*100:.1f}%)")

    # Show flow statistics for successful runs
    if successful_runs > 0:
        success_mask = results_df['success']
        print("\n" + "="*80)
        print("PRODUCT FLOW STATISTICS (Successful runs)")
        print("="*80)
        print(f"RNG flow:         {results_df.loc[success_mask, 'RNG_flow'].mean():.2f} ± {results_df.loc[success_mask, 'RNG_flow'].std():.2f} kg/hr")
        print(f"Biochar flow:     {results_df.loc[success_mask, 'biochar_flow'].mean():.2f} ± {results_df.loc[success_mask, 'biochar_flow'].std():.2f} kg/hr")
        print(f"Mass allocation:  {results_df.loc[success_mask, 'mass_allocation'].mean():.4f} ± {results_df.loc[success_mask, 'mass_allocation'].std():.4f}")
        print("="*80)

    # Analyze failed runs if there are many
    if failed_runs > n_iterations * 0.2:  # More than 20% failed
        print("\n⚠️  WARNING: High failure rate detected!")
        print("Consider adjusting parameter ranges or increasing timeout.")

    return results_df


def analyze_results(results_df, save_path='results/uncertainty_analysis.csv'):
    """
    Analyze Monte Carlo results and compute statistics for MSP and GWP.

    Parameters
    ----------
    results_df : pd.DataFrame
        Results from Monte Carlo analysis
    save_path : str
        Path to save results CSV

    Returns
    -------
    stats_df : pd.DataFrame
        DataFrame with statistical summary
    correlations : dict
        Dictionary with correlations for MSP and GWP
    """

    # Filter successful runs
    success_df = results_df[results_df['success']].copy()

    # Check if GWP was calculated
    gwp_available = not success_df['GWP'].isna().all()

    # Save full results
    os.makedirs('results', exist_ok=True)
    success_df.to_csv(save_path, index=False)
    print(f"\n✓ Results saved to {save_path}")

    # Compute statistics for MSP
    msp_stats = {
        'Mean': success_df['MSP'].mean(),
        'Median': success_df['MSP'].median(),
        'Std Dev': success_df['MSP'].std(),
        'Min': success_df['MSP'].min(),
        'Max': success_df['MSP'].max(),
        'Q5': success_df['MSP'].quantile(0.05),
        'Q25': success_df['MSP'].quantile(0.25),
        'Q75': success_df['MSP'].quantile(0.75),
        'Q95': success_df['MSP'].quantile(0.95),
        'CV (%)': (success_df['MSP'].std() / success_df['MSP'].mean()) * 100
    }

    # Compute statistics for GWP (if available)
    if gwp_available:
        gwp_stats = {
            'Mean': success_df['GWP'].mean(),
            'Median': success_df['GWP'].median(),
            'Std Dev': success_df['GWP'].std(),
            'Min': success_df['GWP'].min(),
            'Max': success_df['GWP'].max(),
            'Q5': success_df['GWP'].quantile(0.05),
            'Q25': success_df['GWP'].quantile(0.25),
            'Q75': success_df['GWP'].quantile(0.75),
            'Q95': success_df['GWP'].quantile(0.95),
            'CV (%)': (success_df['GWP'].std() / success_df['GWP'].mean()) * 100
        }
    else:
        gwp_stats = None

    print("\n" + "="*80)
    print("MSP UNCERTAINTY STATISTICS")
    print("="*80)
    for stat, value in msp_stats.items():
        print(f"{stat:15s}: ${value:.3f}/kg RNG")
    print("="*80)

    if gwp_available:
        print("\n" + "="*80)
        print("GWP UNCERTAINTY STATISTICS")
        print("="*80)
        for stat, value in gwp_stats.items():
            if stat == 'CV (%)':
                print(f"{stat:15s}: {value:.2f}%")
            else:
                print(f"{stat:15s}: {value:.3f} kg CO2-eq/kg RNG")
        print("="*80)
    else:
        print("\n⚠️  GWP was not calculated (CALCULATE_GWP=False)")

    # Compute correlations
    param_cols = ['reactor_tau', 'ISR', 'S0', 'feedStock_ratio']
    correlations_msp = success_df[param_cols + ['MSP']].corr()['MSP'].drop('MSP')

    print("\nPEARSON CORRELATIONS WITH MSP")
    print("="*80)
    for param, corr in correlations_msp.items():
        print(f"{param:20s}: {corr:+.3f}")
    print("="*80)

    if gwp_available:
        correlations_gwp = success_df[param_cols + ['GWP']].corr()['GWP'].drop('GWP')
        print("\nPEARSON CORRELATIONS WITH GWP")
        print("="*80)
        for param, corr in correlations_gwp.items():
            print(f"{param:20s}: {corr:+.3f}")
        print("="*80)
    else:
        correlations_gwp = None

    # Combine statistics
    if gwp_available:
        stats_combined = pd.DataFrame({
            'MSP': msp_stats,
            'GWP': gwp_stats
        })
    else:
        stats_combined = pd.DataFrame({
            'MSP': msp_stats
        })
    stats_combined.to_csv('results/uncertainty_statistics.csv')

    correlations = {'MSP': correlations_msp, 'GWP': correlations_gwp if gwp_available else None}

    return stats_combined, correlations


def plot_input_parameters(results_df, distributions, save_dir='results'):
    """
    Generate plots showing the distribution of sampled input parameters.

    Parameters
    ----------
    results_df : pd.DataFrame
        Results from Monte Carlo analysis
    distributions : dict
        Parameter distributions info
    save_dir : str
        Directory to save plots
    """

    print("\n📊 Generating input parameter distribution plots...")

    # Filter successful runs
    success_df = results_df[results_df['success']].copy()

    param_cols = ['reactor_tau', 'ISR', 'S0', 'feedStock_ratio']

    # Create 2x2 subplot for parameter histograms
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    axes = axes.flatten()

    for idx, param in enumerate(param_cols):
        ax = axes[idx]

        # Histogram
        n, bins, patches = ax.hist(success_df[param], bins=50, edgecolor='black',
                                    alpha=0.7, color='coral', density=False)

        # Statistics
        mean_val = success_df[param].mean()
        median_val = success_df[param].median()
        std_val = success_df[param].std()
        min_val = success_df[param].min()
        max_val = success_df[param].max()

        # Add vertical lines for statistics
        ax.axvline(mean_val, color='red', linestyle='--', linewidth=3, label=f'Mean = {mean_val:.2f}')
        ax.axvline(median_val, color='orange', linestyle='--', linewidth=3, label=f'Median = {median_val:.2f}')

        # Labels and title (using VARIABLE_NAMES mapping)
        param_name = VARIABLE_NAMES.get(param, distributions[param]['label'])
        ax.set_xlabel(param_name, fontsize=24, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=24, fontweight='bold')
        ax.set_title(f'Sampled Distribution: {param_name}',
                     fontsize=24, fontweight='bold')

        # Add text box with statistics
        textstr = f'Mean: {mean_val:.2f}\nStd: {std_val:.2f}\nMin: {min_val:.2f}\nMax: {max_val:.2f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.75, 0.95, textstr, transform=ax.transAxes, fontsize=24,
                verticalalignment='top', bbox=props)

        ax.tick_params(axis='both', labelsize=24)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=24, frameon=True, shadow=True)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/input_parameters_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Create summary table
    print("\n" + "="*80)
    print("INPUT PARAMETER STATISTICS")
    print("="*80)

    summary_data = []
    for param in param_cols:
        param_name = VARIABLE_NAMES.get(param, distributions[param]['label'])
        summary_data.append({
            'Parameter': param_name,
            'Mean': f"{success_df[param].mean():.2f}",
            'Std': f"{success_df[param].std():.2f}",
            'Min': f"{success_df[param].min():.2f}",
            'Max': f"{success_df[param].max():.2f}",
            'Distribution': distributions[param]['type'],
        })

    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print("="*80)

    # Save summary table
    summary_df.to_csv(f'{save_dir}/input_parameters_summary.csv', index=False)

    return summary_df


def plot_uncertainty_results(results_df, distributions, save_dir='results'):
    """
    Generate comprehensive uncertainty analysis plots for MSP and GWP.

    Parameters
    ----------
    results_df : pd.DataFrame
        Results from Monte Carlo analysis
    distributions : dict
        Parameter distributions info
    save_dir : str
        Directory to save plots
    """

    # Filter successful runs
    success_df = results_df[results_df['success']].copy()

    # Check if GWP was calculated
    gwp_available = not success_df['GWP'].isna().all()

    os.makedirs(save_dir, exist_ok=True)

    # Set style
    sns.set_style("whitegrid")

    # 1. MSP Histogram with statistics
    fig, ax = plt.subplots(figsize=(10, 10))

    n, bins, patches = ax.hist(success_df['MSP'], bins=50, edgecolor='black',
                                alpha=0.7, color='steelblue', density=False)

    mean_msp = success_df['MSP'].mean()
    median_msp = success_df['MSP'].median()
    q5 = success_df['MSP'].quantile(0.05)
    q95 = success_df['MSP'].quantile(0.95)

    ax.axvline(mean_msp, color='red', linestyle='--', linewidth=3, label=f'Mean = {mean_msp:.2f}')
    ax.axvline(median_msp, color='orange', linestyle='--', linewidth=3, label=f'Median = {median_msp:.2f}')
    ax.axvline(q5, color='green', linestyle=':', linewidth=3, label=f'5th percentile = {q5:.2f}')
    ax.axvline(q95, color='purple', linestyle=':', linewidth=3, label=f'95th percentile = {q95:.2f}')

    ax.set_xlabel(VARIABLE_NAMES['MSP'], fontsize=28, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=28, fontweight='bold')
    #ax.set_title(f'{VARIABLE_NAMES["MSP"]} - Uncertainty Distribution', fontsize=32, fontweight='bold')
    ax.legend(fontsize=26, frameon=True, shadow=True, loc='best')
    ax.tick_params(axis='both', labelsize=26)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/msp_histogram.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 2. Box plot
    fig, ax = plt.subplots(figsize=(10, 8))

    bp = ax.boxplot([success_df['MSP']], labels=['MSP'], vert=True, patch_artist=True,
                     showmeans=True, meanline=True,
                     boxprops=dict(facecolor='lightblue', alpha=0.7, linewidth=2),
                     meanprops=dict(color='red', linewidth=3),
                     medianprops=dict(color='darkblue', linewidth=3),
                     whiskerprops=dict(linewidth=2),
                     capprops=dict(linewidth=2))

    ax.set_ylabel(VARIABLE_NAMES['MSP'], fontsize=28, fontweight='bold')
    ax.set_title(f'{VARIABLE_NAMES["MSP"]} - Box Plot', fontsize=32, fontweight='bold')
    ax.tick_params(axis='both', labelsize=26)
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/msp_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 3. Scatter plots - MSP vs each parameter
    param_cols = ['reactor_tau', 'ISR', 'S0', 'feedStock_ratio']

    fig, axes = plt.subplots(2, 2, figsize=(12, 14))
    axes = axes.flatten()

    for idx, param in enumerate(param_cols):
        ax = axes[idx]

        # Scatter plot
        ax.scatter(success_df[param], success_df['MSP'], alpha=0.6, s=40, color='steelblue', edgecolors='black', linewidth=0.5)

        # Add trend line
        z = np.polyfit(success_df[param], success_df['MSP'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(success_df[param].min(), success_df[param].max(), 100)
        ax.plot(x_trend, p(x_trend), "r--", linewidth=3, label=f'Trend line')

        # Compute correlation
        corr = success_df[param].corr(success_df['MSP'])

        param_name = VARIABLE_NAMES.get(param, distributions[param]['label'])
        ax.set_xlabel(param_name, fontsize=22, fontweight='bold')
        ax.set_ylabel(VARIABLE_NAMES['MSP_short'], fontsize=22, fontweight='bold')
        ax.set_title(f'{param_name} vs {VARIABLE_NAMES["MSP_short"]}\n(r = {corr:+.3f})',
                     fontsize=24, fontweight='bold')
        ax.tick_params(axis='both', labelsize=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=20, frameon=True, shadow=True)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/msp_vs_parameters.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 4. Correlation matrix heatmap
    fig, ax = plt.subplots(figsize=(10, 8))

    corr_matrix = success_df[param_cols + ['MSP']].corr()

    sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                vmin=-1, vmax=1, ax=ax, annot_kws={'size': 18})

    ax.set_title('Correlation Matrix', fontsize=24, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{save_dir}/correlation_matrix.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 5. Cumulative distribution function (CDF)
    fig, ax = plt.subplots(figsize=(10, 6))

    sorted_msp = np.sort(success_df['MSP'])
    cumulative = np.arange(1, len(sorted_msp) + 1) / len(sorted_msp)

    ax.plot(sorted_msp, cumulative, linewidth=2, color='steelblue')
    ax.axhline(0.5, color='red', linestyle='--', alpha=0.7, label='50th percentile')
    ax.axhline(0.05, color='green', linestyle=':', alpha=0.7, label='5th percentile')
    ax.axhline(0.95, color='purple', linestyle=':', alpha=0.7, label='95th percentile')

    ax.set_xlabel('MSP (USD/kg RNG)', fontsize=22, fontweight='bold')
    ax.set_ylabel('Cumulative Probability', fontsize=22, fontweight='bold')
    ax.set_title('MSP Cumulative Distribution Function', fontsize=26, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=20)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/msp_cdf.png', dpi=300, bbox_inches='tight')
    plt.show()

    # ======================== RNG PRODUCTION PLOTS ========================
    print("\n📊 Generating RNG production uncertainty plots...")

    # 5a. RNG Production Histogram
    fig, ax = plt.subplots(figsize=(10, 10))

    n, bins, patches = ax.hist(success_df['RNG_flow'], bins=50, edgecolor='black',
                                alpha=0.7, color='green', density=False)

    mean_rng = success_df['RNG_flow'].mean()
    median_rng = success_df['RNG_flow'].median()
    q5_rng = success_df['RNG_flow'].quantile(0.05)
    q95_rng = success_df['RNG_flow'].quantile(0.95)

    ax.axvline(mean_rng, color='red', linestyle='--', linewidth=3, label=f'Mean = {mean_rng:.2f}')
    ax.axvline(median_rng, color='orange', linestyle='--', linewidth=3, label=f'Median = {median_rng:.2f}')
    ax.axvline(q5_rng, color='darkgreen', linestyle=':', linewidth=3, label=f'5th percentile = {q5_rng:.2f}')
    ax.axvline(q95_rng, color='purple', linestyle=':', linewidth=3, label=f'95th percentile = {q95_rng:.2f}')

    ax.set_xlabel(VARIABLE_NAMES['RNG_flow'], fontsize=24, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=24, fontweight='bold')
    #ax.set_title(f'{VARIABLE_NAMES["RNG_flow"]}', fontsize=24, fontweight='bold')
    ax.legend(fontsize=24, frameon=True, shadow=True, loc='best')
    ax.tick_params(axis='both', labelsize=24)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/rng_production_histogram.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 5b. RNG Production Box Plot
    fig, ax = plt.subplots(figsize=(10, 10))

    bp = ax.boxplot([success_df['RNG_flow']], labels=['RNG Production'], vert=True, patch_artist=True,
                     showmeans=True, meanline=True,
                     boxprops=dict(facecolor='lightgreen', alpha=0.7, linewidth=2),
                     meanprops=dict(color='red', linewidth=3),
                     medianprops=dict(color='darkgreen', linewidth=3),
                     whiskerprops=dict(linewidth=2),
                     capprops=dict(linewidth=2))

    ax.set_ylabel(VARIABLE_NAMES['RNG_flow'], fontsize=24, fontweight='bold')
    #ax.set_title(f'{VARIABLE_NAMES["RNG_flow"]} - Box Plot', fontsize=24, fontweight='bold')
    ax.tick_params(axis='both', labelsize=24)
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/rng_production_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 5c. RNG Production vs Parameters
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    axes = axes.flatten()

    for idx, param in enumerate(param_cols):
        ax = axes[idx]

        # Scatter plot
        ax.scatter(success_df[param], success_df['RNG_flow'], alpha=0.6, s=40, color='green', edgecolors='black', linewidth=0.5)

        # Add trend line
        z = np.polyfit(success_df[param], success_df['RNG_flow'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(success_df[param].min(), success_df[param].max(), 100)
        ax.plot(x_trend, p(x_trend), "r--", linewidth=3, label=f'Trend line')

        # Compute correlation
        corr = success_df[param].corr(success_df['RNG_flow'])

        param_name = VARIABLE_NAMES.get(param, distributions[param]['label'])
        ax.set_xlabel(param_name, fontsize=28, fontweight='bold')
        ax.set_ylabel(VARIABLE_NAMES['RNG_flow_short'], fontsize=28, fontweight='bold')
        ax.set_title(f'{param_name} vs {VARIABLE_NAMES["RNG_flow_short"]}\n(r = {corr:+.3f})',
                     fontsize=30, fontweight='bold')
        ax.tick_params(axis='both', labelsize=26)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=26, frameon=True, shadow=True)

    plt.tight_layout()
    plt.savefig(f'{save_dir}/rng_production_vs_parameters.png', dpi=300, bbox_inches='tight')
    plt.show()

    # ======================== GWP PLOTS ========================
    if gwp_available:
        print("\n📊 Generating GWP uncertainty plots...")

        # 6. GWP Histogram with statistics
        fig, ax = plt.subplots(figsize=(10, 10))

        n, bins, patches = ax.hist(success_df['GWP'], bins=50, edgecolor='black',
                                    alpha=0.7, color='darkgreen', density=False)

        mean_gwp = success_df['GWP'].mean()
        median_gwp = success_df['GWP'].median()
        q5_gwp = success_df['GWP'].quantile(0.05)
        q95_gwp = success_df['GWP'].quantile(0.95)

        ax.axvline(mean_gwp, color='red', linestyle='--', linewidth=3, label=f'Mean = {mean_gwp:.2f}')
        ax.axvline(median_gwp, color='orange', linestyle='--', linewidth=3, label=f'Median = {median_gwp:.2f}')
        ax.axvline(q5_gwp, color='green', linestyle=':', linewidth=3, label=f'5th percentile = {q5_gwp:.2f}')
        ax.axvline(q95_gwp, color='purple', linestyle=':', linewidth=3, label=f'95th percentile = {q95_gwp:.2f}')

        ax.set_xlabel(VARIABLE_NAMES['GWP'], fontsize=24, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=24, fontweight='bold')
        #ax.set_title(f'{VARIABLE_NAMES["GWP"]}', fontsize=24, fontweight='bold')
        ax.legend(fontsize=24, frameon=True, shadow=True, loc='best')
        ax.tick_params(axis='both', labelsize=24)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{save_dir}/gwp_histogram.png', dpi=300, bbox_inches='tight')
        plt.show()

        # 7. GWP Box plot
        fig, ax = plt.subplots(figsize=(10, 8))

        bp = ax.boxplot([success_df['GWP']], labels=['GWP'], vert=True, patch_artist=True,
                         showmeans=True, meanline=True,
                         boxprops=dict(facecolor='lightgreen', alpha=0.7, linewidth=2),
                         meanprops=dict(color='red', linewidth=3),
                         medianprops=dict(color='darkgreen', linewidth=3),
                         whiskerprops=dict(linewidth=2),
                         capprops=dict(linewidth=2))

        ax.set_ylabel(VARIABLE_NAMES['GWP'], fontsize=28, fontweight='bold')
        #ax.set_title(f'{VARIABLE_NAMES["GWP"]} - Box Plot', fontsize=32, fontweight='bold')
        ax.tick_params(axis='both', labelsize=26)
        ax.grid(True, axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{save_dir}/gwp_boxplot.png', dpi=300, bbox_inches='tight')
        plt.show()

        # 8. GWP Scatter plots - GWP vs each parameter
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        axes = axes.flatten()

        for idx, param in enumerate(param_cols):
            ax = axes[idx]

            # Scatter plot
            ax.scatter(success_df[param], success_df['GWP'], alpha=0.6, s=40, color='darkgreen', edgecolors='black', linewidth=0.5)

            # Add trend line
            z = np.polyfit(success_df[param], success_df['GWP'], 1)
            p = np.poly1d(z)
            x_trend = np.linspace(success_df[param].min(), success_df[param].max(), 100)
            ax.plot(x_trend, p(x_trend), "r--", linewidth=3, label='Trend line')

            # Compute correlation
            corr = success_df[param].corr(success_df['GWP'])

            param_name = VARIABLE_NAMES.get(param, distributions[param]['label'])
            ax.set_xlabel(param_name, fontsize=22, fontweight='bold')
            ax.set_ylabel(VARIABLE_NAMES['GWP_short'], fontsize=22, fontweight='bold')
            ax.set_title(f'{param_name} vs {VARIABLE_NAMES["GWP_short"]}\n(r = {corr:+.3f})',
                         fontsize=24, fontweight='bold')
            ax.tick_params(axis='both', labelsize=20)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=20, frameon=True, shadow=True)

        plt.tight_layout()
        plt.savefig(f'{save_dir}/gwp_vs_parameters.png', dpi=300, bbox_inches='tight')
        plt.show()

        # 9. GWP Cumulative distribution function (CDF)
        fig, ax = plt.subplots(figsize=(10, 6))

        sorted_gwp = np.sort(success_df['GWP'])
        cumulative = np.arange(1, len(sorted_gwp) + 1) / len(sorted_gwp)

        ax.plot(sorted_gwp, cumulative, linewidth=2, color='darkgreen')
        ax.axhline(0.5, color='red', linestyle='--', alpha=0.7, label='50th percentile')
        ax.axhline(0.05, color='green', linestyle=':', alpha=0.7, label='5th percentile')
        ax.axhline(0.95, color='purple', linestyle=':', alpha=0.7, label='95th percentile')

        ax.set_xlabel('GWP (kg CO2-eq/kg RNG)', fontsize=22, fontweight='bold')
        ax.set_ylabel('Cumulative Probability', fontsize=22, fontweight='bold')
        #ax.set_title('GWP Cumulative Distribution Function', fontsize=26, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=20)

        plt.tight_layout()
        plt.savefig(f'{save_dir}/gwp_cdf.png', dpi=300, bbox_inches='tight')
        plt.show()

        # 10. MSP vs GWP scatter plot
        fig, ax = plt.subplots(figsize=(10, 10))

        scatter = ax.scatter(success_df['MSP'], success_df['GWP'],
                            c=success_df['feedStock_ratio'], cmap='viridis',
                            alpha=0.6, s=30, edgecolors='black', linewidth=0.5)

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('SW Fraction (-)', fontsize=20, fontweight='bold')
        cbar.ax.tick_params(labelsize=18)

        # Compute correlation
        corr_msp_gwp = success_df['MSP'].corr(success_df['GWP'])

        ax.set_xlabel('MSP (USD/kg RNG)', fontsize=22, fontweight='bold')
        ax.set_ylabel('GWP (kg CO2-eq/kg RNG)', fontsize=22, fontweight='bold')
        ax.set_title(f'MSP vs GWP Trade-off\n(Pearson r = {corr_msp_gwp:+.3f})',
                     fontsize=26, fontweight='bold')
        ax.tick_params(axis='both', labelsize=20)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{save_dir}/msp_vs_gwp.png', dpi=300, bbox_inches='tight')
        plt.show()

        print(f"\n✓ All plots saved to {save_dir}/ (including GWP plots)")
    else:
        print(f"\n✓ MSP plots saved to {save_dir}/")
        print("  ⚠️  GWP plots skipped (CALCULATE_GWP=False)")


def sensitivity_indices(results_df):
    """
    Calculate sensitivity indices (contribution to variance) for MSP, RNG Production, and GWP.

    Parameters
    ----------
    results_df : pd.DataFrame
        Results from Monte Carlo analysis

    Returns
    -------
    sensitivity_msp_df : pd.DataFrame
        Sensitivity indices for MSP
    sensitivity_rng_df : pd.DataFrame
        Sensitivity indices for RNG Production
    sensitivity_gwp_df : pd.DataFrame
        Sensitivity indices for GWP
    """

    success_df = results_df[results_df['success']].copy()
    param_cols = ['reactor_tau', 'ISR', 'S0', 'feedStock_ratio']

    # Check if GWP was calculated
    gwp_available = not success_df['GWP'].isna().all()


    X = success_df[param_cols].values

    # Standardize X
    scaler_X = StandardScaler()
    X_std = scaler_X.fit_transform(X)

    # ============== MSP Sensitivity ==============
    y_msp = success_df['MSP'].values
    scaler_y_msp = StandardScaler()
    y_msp_std = scaler_y_msp.fit_transform(y_msp.reshape(-1, 1)).ravel()

    model_msp = LinearRegression()
    model_msp.fit(X_std, y_msp_std)
    src_msp = model_msp.coef_
    r2_msp = model_msp.score(X_std, y_msp_std)

    # Map parameter names to descriptive names
    param_names_mapped = [VARIABLE_NAMES.get(p, p) for p in param_cols]

    sensitivity_msp_df = pd.DataFrame({
        'Parameter': param_names_mapped,
        'SRC_MSP': src_msp,
        'SRC_MSP_abs': np.abs(src_msp)
    })
    sensitivity_msp_df = sensitivity_msp_df.sort_values('SRC_MSP_abs', ascending=False)

    # ============== RNG Production Sensitivity ==============
    y_rng = success_df['RNG_flow'].values
    scaler_y_rng = StandardScaler()
    y_rng_std = scaler_y_rng.fit_transform(y_rng.reshape(-1, 1)).ravel()

    model_rng = LinearRegression()
    model_rng.fit(X_std, y_rng_std)
    src_rng = model_rng.coef_
    r2_rng = model_rng.score(X_std, y_rng_std)

    sensitivity_rng_df = pd.DataFrame({
        'Parameter': param_names_mapped,
        'SRC_RNG': src_rng,
        'SRC_RNG_abs': np.abs(src_rng)
    })
    sensitivity_rng_df = sensitivity_rng_df.sort_values('SRC_RNG_abs', ascending=False)

    # ============== GWP Sensitivity ==============
    if gwp_available:
        y_gwp = success_df['GWP'].values
        scaler_y_gwp = StandardScaler()
        y_gwp_std = scaler_y_gwp.fit_transform(y_gwp.reshape(-1, 1)).ravel()

        model_gwp = LinearRegression()
        model_gwp.fit(X_std, y_gwp_std)
        src_gwp = model_gwp.coef_
        r2_gwp = model_gwp.score(X_std, y_gwp_std)

        sensitivity_gwp_df = pd.DataFrame({
            'Parameter': param_names_mapped,  # Use the same mapped names
            'SRC_GWP': src_gwp,
            'SRC_GWP_abs': np.abs(src_gwp)
        })
        sensitivity_gwp_df = sensitivity_gwp_df.sort_values('SRC_GWP_abs', ascending=False)
    else:
        sensitivity_gwp_df = None
        r2_gwp = None

    # Print results
    print("\n" + "="*80)
    print("SENSITIVITY INDICES FOR MSP (Standardized Regression Coefficients)")
    print("="*80)
    print(f"Model R² = {r2_msp:.3f}\n")
    print(sensitivity_msp_df.to_string(index=False))
    print("="*80)

    print("\n" + "="*80)
    print("SENSITIVITY INDICES FOR RNG PRODUCTION (Standardized Regression Coefficients)")
    print("="*80)
    print(f"Model R² = {r2_rng:.3f}\n")
    print(sensitivity_rng_df.to_string(index=False))
    print("="*80)

    if gwp_available:
        print("\n" + "="*80)
        print("SENSITIVITY INDICES FOR GWP (Standardized Regression Coefficients)")
        print("="*80)
        print(f"Model R² = {r2_gwp:.3f}\n")
        print(sensitivity_gwp_df.to_string(index=False))
        print("="*80)
    else:
        print("\n⚠️  GWP sensitivity analysis skipped (CALCULATE_GWP=False)")

    # Plot sensitivity indices - MSP
    fig, ax = plt.subplots(figsize=(16, 10))

    colors_msp = ['red' if x < 0 else 'steelblue' for x in sensitivity_msp_df['SRC_MSP']]
    ax.barh(sensitivity_msp_df['Parameter'], sensitivity_msp_df['SRC_MSP'],
            color=colors_msp, alpha=0.7, edgecolor='black', linewidth=2)

    # Center the x-axis at 0 with symmetric limits
    max_abs_val_msp = sensitivity_msp_df['SRC_MSP_abs'].max()
    ax.set_xlim(-max_abs_val_msp * 1.1, max_abs_val_msp * 1.1)

    ax.set_xlabel('Standardized Regression Coefficient (SRC)', fontsize=32, fontweight='bold')
    ax.set_ylabel('Parameter', fontsize=32, fontweight='bold')
    ax.set_title(f'Effect on {VARIABLE_NAMES["MSP_short"]} (R² = {r2_msp:.3f})',
                 fontsize=34, fontweight='bold')
    ax.axvline(0, color='black', linewidth=2)
    ax.tick_params(axis='both', labelsize=28)
    ax.grid(True, axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/sensitivity_indices_msp.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Plot sensitivity indices - RNG Production
    fig, ax = plt.subplots(figsize=(16, 10))

    colors_rng = ['red' if x < 0 else 'green' for x in sensitivity_rng_df['SRC_RNG']]
    ax.barh(sensitivity_rng_df['Parameter'], sensitivity_rng_df['SRC_RNG'],
            color=colors_rng, alpha=0.7, edgecolor='black', linewidth=2)

    # Center the x-axis at 0 with symmetric limits
    max_abs_val_rng = sensitivity_rng_df['SRC_RNG_abs'].max()
    ax.set_xlim(-max_abs_val_rng * 1.1, max_abs_val_rng * 1.1)

    ax.set_xlabel('Standardized Regression Coefficient (SRC)', fontsize=32, fontweight='bold')
    ax.set_ylabel('Parameter', fontsize=32, fontweight='bold')
    ax.set_title(f'Effect on {VARIABLE_NAMES["RNG_flow_short"]} (R² = {r2_rng:.3f})',
                 fontsize=34, fontweight='bold')
    ax.axvline(0, color='black', linewidth=2)
    ax.tick_params(axis='both', labelsize=28)
    ax.grid(True, axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/sensitivity_indices_rng.png', dpi=300, bbox_inches='tight')
    plt.show()

    # GWP sensitivity plots (only if available)
    if gwp_available and sensitivity_gwp_df is not None and r2_gwp is not None:
        # Plot sensitivity indices - GWP
        fig, ax = plt.subplots(figsize=(16, 10))

        colors_gwp = ['red' if x < 0 else 'darkgreen' for x in sensitivity_gwp_df['SRC_GWP']]
        ax.barh(sensitivity_gwp_df['Parameter'], sensitivity_gwp_df['SRC_GWP'],
                color=colors_gwp, alpha=0.7, edgecolor='black', linewidth=2)

        # Center the x-axis at 0 with symmetric limits
        max_abs_val_gwp = sensitivity_gwp_df['SRC_GWP_abs'].max()
        ax.set_xlim(-max_abs_val_gwp * 1.1, max_abs_val_gwp * 1.1)

        ax.set_xlabel('Standardized Regression Coefficient (SRC)', fontsize=32, fontweight='bold')
        ax.set_ylabel('Parameter', fontsize=32, fontweight='bold')
        ax.set_title(f'Effect on {VARIABLE_NAMES["GWP_short"]} (R² = {r2_gwp:.3f})',
                     fontsize=34, fontweight='bold')
        ax.axvline(0, color='black', linewidth=2)
        ax.tick_params(axis='both', labelsize=28)
        ax.grid(True, axis='x', alpha=0.3)

        plt.tight_layout()
        plt.savefig('results/sensitivity_indices_gwp.png', dpi=300, bbox_inches='tight')
        plt.show()

        # # Combined plot (3 subplots: MSP, RNG, GWP)
        # fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 7))

        # # MSP subplot
        # colors_msp = ['red' if x < 0 else 'steelblue' for x in sensitivity_msp_df['SRC_MSP']]
        # ax1.barh(sensitivity_msp_df['Parameter'], sensitivity_msp_df['SRC_MSP'],
        #          color=colors_msp, alpha=0.7, edgecolor='black', linewidth=1.5)
        # ax1.set_xlabel('SRC', fontsize=14, fontweight='bold')
        # ax1.set_ylabel('Parameter', fontsize=14, fontweight='bold')
        # ax1.set_title(f'{VARIABLE_NAMES["MSP_short"]} (R² = {r2_msp:.3f})', fontsize=16, fontweight='bold')
        # ax1.axvline(0, color='black', linewidth=2)
        # ax1.tick_params(axis='both', labelsize=12)
        # ax1.grid(axis='x', alpha=0.3)

        # # RNG subplot
        # colors_rng = ['red' if x < 0 else 'green' for x in sensitivity_rng_df['SRC_RNG']]
        # ax2.barh(sensitivity_rng_df['Parameter'], sensitivity_rng_df['SRC_RNG'],
        #          color=colors_rng, alpha=0.7, edgecolor='black', linewidth=1.5)
        # ax2.set_xlabel('SRC', fontsize=14, fontweight='bold')
        # ax2.set_ylabel('Parameter', fontsize=14, fontweight='bold')
        # ax2.set_title(f'{VARIABLE_NAMES["RNG_flow_short"]} (R² = {r2_rng:.3f})', fontsize=16, fontweight='bold')
        # ax2.axvline(0, color='black', linewidth=2)
        # ax2.tick_params(axis='both', labelsize=12)
        # ax2.grid(axis='x', alpha=0.3)

        # # GWP subplot
        # colors_gwp = ['red' if x < 0 else 'darkgreen' for x in sensitivity_gwp_df['SRC_GWP']]
        # ax3.barh(sensitivity_gwp_df['Parameter'], sensitivity_gwp_df['SRC_GWP'],
        #          color=colors_gwp, alpha=0.7, edgecolor='black', linewidth=1.5)
        # ax3.set_xlabel('SRC', fontsize=14, fontweight='bold')
        # ax3.set_ylabel('Parameter', fontsize=14, fontweight='bold')
        # ax3.set_title(f'{VARIABLE_NAMES["GWP_short"]} (R² = {r2_gwp:.3f})', fontsize=16, fontweight='bold')
        # ax3.axvline(0, color='black', linewidth=2)
        # ax3.tick_params(axis='both', labelsize=12)
        # ax3.grid(axis='x', alpha=0.3)

        # plt.suptitle('Sensitivity Analysis Comparison', fontsize=20, fontweight='bold', y=1.02)
        # plt.tight_layout()
        # plt.savefig('results/sensitivity_indices_combined.png', dpi=300, bbox_inches='tight')
        # plt.show()

    # Save CSV files
    sensitivity_msp_df.to_csv('results/sensitivity_indices_msp.csv', index=False)
    sensitivity_rng_df.to_csv('results/sensitivity_indices_rng.csv', index=False)

    if gwp_available and sensitivity_gwp_df is not None:
        sensitivity_gwp_df.to_csv('results/sensitivity_indices_gwp.csv', index=False)
        # Combined CSV (merge all three)
        sensitivity_combined = pd.merge(sensitivity_msp_df, sensitivity_rng_df, on='Parameter')
        sensitivity_combined = pd.merge(sensitivity_combined, sensitivity_gwp_df, on='Parameter')
        sensitivity_combined.to_csv('results/sensitivity_indices_combined.csv', index=False)
    else:
        # Combined CSV (only MSP and RNG)
        sensitivity_combined = pd.merge(sensitivity_msp_df, sensitivity_rng_df, on='Parameter')
        sensitivity_combined.to_csv('results/sensitivity_indices_combined.csv', index=False)

    return sensitivity_msp_df, sensitivity_rng_df, sensitivity_gwp_df


def plot_from_csv(csv_path='results/uncertainty_analysis.csv',
                  stats_csv='results/uncertainty_statistics.csv'):
    """
    Generate all plots from saved CSV files without running the full analysis.

    This is useful for quickly regenerating plots after changing plot settings,
    or for exploring results from a previous run.

    Parameters
    ----------
    csv_path : str
        Path to uncertainty analysis CSV file
    stats_csv : str
        Path to statistics CSV file (optional)

    Example
    -------
    >>> from uncertainty_analysis_MSP import plot_from_csv
    >>> plot_from_csv('results/uncertainty_analysis.csv')
    """

    print("\n" + "="*80)
    print("GENERATING PLOTS FROM CSV FILES")
    print("="*80)
    print(f"Reading data from: {csv_path}")

    # Load data
    if not os.path.exists(csv_path):
        print(f"\n❌ Error: File not found: {csv_path}")
        print("   Please run the analysis first to generate CSV files.")
        return

    results_df = pd.read_csv(csv_path)

    print(f"✓ Loaded {len(results_df)} simulations")
    print(f"  Successful: {results_df['success'].sum()}")
    print(f"  Failed: {(~results_df['success']).sum()}")

    # Get distributions (we need this for plot labels)
    distributions = define_parameter_distributions()

    # Generate all plots
    if results_df['success'].sum() > 0:
        print("\n📊 Generating plots...")

        # Input parameters distribution
        plot_input_parameters(results_df, distributions)

        # Results plots (MSP, GWP, RNG production)
        plot_uncertainty_results(results_df, distributions)

        # Sensitivity analysis
        print("\n📊 Calculating sensitivity indices...")
        sensitivity_msp_df, sensitivity_rng_df, sensitivity_gwp_df = sensitivity_indices(results_df)

        print("\n✅ All plots generated successfully!")
        print("="*80)
    else:
        print("\n⚠️  No successful runs in CSV file")


#%% Main execution
if __name__ == "__main__":

    # ============================================================================
    # CONFIGURATION - ADJUST THESE PARAMETERS
    # ============================================================================
    N_ITERATIONS = 2500  # TEST: Empezamos con 10 iteraciones para verificar
    TIMEOUT = 120  # Maximum time per simulation in seconds (2 minutes)

    # ⚠️ IMPORTANTE: SI LA SIMULACIÓN SE BLOQUEA, CAMBIA ESTO A False ⚠️
    CALCULATE_GWP = True  # ⬅️ CAMBIA AQUÍ: True = con GWP, False = solo MSP

    # ============================================================================

    def calculate_uncertainty():
        print("\n" + "="*80)
        print("MONTE CARLO UNCERTAINTY ANALYSIS - MSP & GWP")
        print("="*80)
        print("Configuration:")
        print(f"  - Iterations: {N_ITERATIONS}")
        print(f"  - Timeout per simulation: {TIMEOUT} seconds")
        print(f"  - Calculate GWP: {CALCULATE_GWP}")
        print("="*80)

        if not CALCULATE_GWP:
            print("\n  ⚠️  WARNING: GWP calculation is DISABLED")
            print("     Only MSP will be calculated.")
            print("     To enable GWP: Set CALCULATE_GWP = True (line 792)")
            print()
        else:
            print("\n  ✓ GWP calculation is ENABLED")
            print("    If simulations hang, set CALCULATE_GWP = False (line 792)")
            print()

        # Run Monte Carlo analysis
        results_df = run_monte_carlo_analysis(
            n_iterations=N_ITERATIONS,
            save_intermediate=True,
            timeout=TIMEOUT,
            calculate_gwp=CALCULATE_GWP
        )

        # Analyze results
        distributions = define_parameter_distributions()
        stats_df, correlations = analyze_results(results_df)

        # Generate plots (only if we have successful runs)
        if results_df['success'].sum() > 0:
            # First, plot input parameters distribution
            plot_input_parameters(results_df, distributions)

            # Then plot results (MSP, GWP, RNG production)
            plot_uncertainty_results(results_df, distributions)

            # Calculate sensitivity indices
            sensitivity_msp_df, sensitivity_rng_df, sensitivity_gwp_df = sensitivity_indices(results_df)
        else:
            print("\n⚠️  No successful runs - skipping plots and sensitivity analysis")

        print("\n" + "="*80)
        print("UNCERTAINTY ANALYSIS COMPLETE!")
        print("="*80)
        print("\nGenerated files:")
        print("\n  CSV Files:")
        print("  - results/uncertainty_analysis.csv")
        print("  - results/uncertainty_statistics.csv")
        print("  - results/sensitivity_indices_msp.csv")
        print("  - results/sensitivity_indices_gwp.csv")
        print("  - results/sensitivity_indices_combined.csv")
        print("\n  MSP Plots:")
        print("  - results/msp_histogram.png")
        print("  - results/msp_boxplot.png")
        print("  - results/msp_vs_parameters.png")
        print("  - results/msp_cdf.png")
        print("  - results/sensitivity_indices_msp.png")
        print("\n  GWP Plots:")
        print("  - results/gwp_histogram.png")
        print("  - results/gwp_boxplot.png")
        print("  - results/gwp_vs_parameters.png")
        print("  - results/gwp_cdf.png")
        print("  - results/sensitivity_indices_gwp.png")
        print("\n  Combined Plots:")
        print("  - results/correlation_matrix.png")
        print("  - results/msp_vs_gwp.png")
        print("  - results/sensitivity_indices_combined.png")
        print("="*80)
    
    calculate_uncertainty()

    plot_from_csv(
        csv_path='results/uncertainty_analysis.csv',
        stats_csv='results/uncertainty_statistics.csv'
    )  # Uncomment to regenerate plots from CSV files
# %%

