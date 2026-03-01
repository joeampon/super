"""
Example script showing how to use name mapping in Sankey diagrams.

This script demonstrates how to:
1. Create and simulate a system
2. Define custom name mappings for streams and units
3. Generate Sankey diagrams with cleaner, more readable labels
"""

from codigestion_bst_continuos_function import create_and_simulate_system
from _sankeys_1 import sankeys, sankeys_energy

# Base parameters for the system
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
    "operating_days": 330
}

# Create and simulate the system
print("Creating and simulating system...")
system_base, tea_base, streams_base, _ = create_and_simulate_system(**base_params)

# ============================================================================
# CUSTOMIZE YOUR NAME MAPPING HERE
# ============================================================================
# Define name mappings for cleaner labels in the Sankey diagram
# Format: {'original_ID': 'Display Name'}

name_mapping = {
    # Input Streams
    'slaughterhouse': 'SHW Feed',
    'DW_feed': 'DW Feed',
    'I_feed': 'BM feed',
    'MEA': 'Fresh MEA',

    # Intermediate Streams
    'Feed': 'Mixed Feed',
    'out': 'Reactor Outlet',
    'Biogas_crudo': 'Raw Biogas',
    'digestate': 'Digestate',
    'compressed_biogas': 'Compressed Biogas',
    'rng_cooler_out': 'Cooled Biogas',
    'dry': 'Dry Digestate',
    'MEARNG': 'MEA-Biogas Mix',
    'MEARecycle': 'MEA Recycle',
    'MEA_rich': 'CO2-Rich MEA',
    'ch4_rich': 'CH4-Rich Stream',

    # Output Streams
    'SoilAmendment': 'Biochar Product',
    'RNG': 'RNG Product',
    'wastewater2': 'Wastewater',
    'FlueGas': 'Flue Gas',
    'CH4_leak': 'CH4 Leaks',
    'co2_waste': 'CO2 Waste',

    # Process Units
    'Mixer_feed': 'Feed Mixing',
    'R1': 'Reactor C-101',
    'SP_biogas': 'Sep. Reactor C-101',
    'CPRNG': 'Biogas Compressor S-101',
    'HXGasCooling': 'Gas Cooler X-101',
    'DRDryer': 'Digestate Dryer T-302',
    'RXPyrolysis': 'Pyrolysis Reactor C-301',
    'SPBiochar': 'Sep. C-301',
    'CO2_Absorber_Mixer': 'MEA T-204',
    'Absorber_A1': 'CO2 Absorber T-201',
    'CLCO2BottomFlash': 'Sep. T-201',
    'Pump_C4': 'Pump P-201',
    'HXCO2': 'MEA Heat Exchanger X-201',
    'CLCO2Stripper': 'CO2 Stripper T-202',
    'CLMEARecovery': 'Sep. T-202',
    'CLRNGFlash': 'CO2 Absorber T-201',
    'SPCH4Leaks': 'Gas Sep.',
    'Pipeline': 'Gas Pipeline',

    # Energy Streams (for energy balance diagram)
    'W_CPRNG': 'Compression Power',
    'W_DRDryer': 'Drying Power',
    'W_Pump_C4': 'Pumping Power',
    'Q_HXGasCooling': 'Gas Cooling',
    'Q_DRDryer': 'Drying Heat',
    'Q_HXCO2': 'MEA Heating',
    'Q_CLCO2Stripper': 'Stripping Heat',
}

# ============================================================================
# GENERATE SANKEY DIAGRAMS
# ============================================================================

# Generate mass balance Sankey diagram with custom names
print("\nGenerating Mass Balance Sankey Diagram...")
sankeys(
    sys=system_base,
    scenario="Codigestion System - Mass Balance",
    limit=0,  # Minimum flow (kg/hr, excluding water) to show
    filename="results/mass_balance_sankey_custom.html",
    save_image=False,
    name_mapping=name_mapping,  # Apply custom names
    collapse_units=False  # Collapse pass-through units for cleaner diagram
)

# Generate energy balance Sankey diagram with custom names
print("\nGenerating Energy Balance Sankey Diagram...")
sankeys_energy(
    sys=system_base,
    scenario="Codigestion System - Energy Balance",
    limit=1000,  # Minimum energy flow (kJ/hr) to show
    filename="results/energy_balance_sankey_custom.html",
    save_image=False,
    name_mapping=name_mapping,  # Apply custom names
    collapse_units=True  # Collapse pass-through units for cleaner diagram
)

print("\n" + "="*80)
print("✓ Done! Sankey diagrams generated successfully.")
print("="*80)
print("\nFiles saved:")
print("  - results/mass_balance_sankey_custom.html")
print("  - results/energy_balance_sankey_custom.html")
print("\nOpen the HTML files in your browser to view interactive diagrams.")
print("\nTips:")
print("  - Hover over flows to see values")
print("  - Edit 'name_mapping' dict to customize labels")
print("  - Adjust 'limit' parameter to filter small flows")
print("  - Set save_image=True to export PNG (requires kaleido)")
