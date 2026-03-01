# S2. Machine Learning Model Development

## S2.1 PyrolysisNet Architecture

PyrolysisNet is a feedforward neural network that predicts 8 product-category yields (wt%) from feedstock composition and operating conditions.

**Table S6.** PyrolysisNet architecture.

| Layer | Type | Dimensions | Notes |
|-------|------|------------|-------|
| Input | - | 5 | HDPE, LDPE, PP (wt%), Temperature (°C), VRT (s) |
| Hidden 1 | Linear + BN + ReLU + Dropout(0.1) | 5 -> 64 | Batch normalization before activation |
| Hidden 2 | Linear + BN + ReLU + Dropout(0.1) | 64 -> 128 | - |
| Hidden 3 | Linear + BN + ReLU + Dropout(0.1) | 128 -> 64 | - |
| Output | Linear + Sigmoid | 64 -> 8 | Scaled by 100 to [0, 100] wt% |

**Output columns (in order):**
1. Liquid (wt%)
2. Gas (wt%)
3. Solid (wt%)
4. Gasoline range hydrocarbons (wt%)
5. Diesel range hydrocarbons (wt%)
6. Total aromatics (wt%)
7. BTX (wt%)
8. Wax (>C21) (wt%)

**Input normalization:** StandardScaler (z-score normalization) with parameters saved in `scaler_params.pt`.

## S2.2 Training Data

- **Source:** `aston.xlsx` literature database containing 566 pyrolysis experiments
- **Preprocessing:** Standard scaling of input features
- **Input features:** HDPE (wt%), LDPE (wt%), PP (wt%), Temperature (°C), Vapor residence time (s)

## S2.3 Training Configuration

| Parameter | Value |
|-----------|-------|
| Batch size | 32 |
| Epochs | 2,000 (max) |
| Early stopping patience | 200 epochs |
| Learning rate | 1 x 10^-3 |
| Optimizer | Adam |
| Loss function | Masked MSE + phase penalty + BTX constraint |
| Dropout rate | 0.1 |
| Output activation | Sigmoid (scaled to 0-100) |

**Loss components:**
- Masked MSE: Only computes loss for non-missing output values
- Phase penalty: Ensures Liquid + Gas + Solid sums to ~100%
- BTX constraint: Enforces BTX <= Total aromatics

## S2.4 Model Performance

**Table S7.** Model test-set performance metrics per output.

| Output | R² | MAE (wt%) | RMSE (wt%) | N (test samples) |
|--------|-----|-----------|------------|-------------------|
| Liquid | 0.741 | 11.79 | 15.18 | 66 |
| Gas | 0.559 | 12.71 | 18.53 | 78 |
| Solid | 0.406 | 1.81 | 3.01 | 36 |
| Gasoline range hydrocarbons | 0.127 | 8.73 | 12.04 | 40 |
| Diesel range hydrocarbons | 0.407 | 7.88 | 11.57 | 38 |
| Total aromatics (wt%) | 0.402 | 7.66 | 12.38 | 42 |
| BTX (wt%) | 0.706 | 2.78 | 3.83 | 27 |
| Wax (>C21) | 0.559 | 14.39 | 19.35 | 41 |

**Figure S2.** Parity plots for each output category showing predicted vs. experimental values on the test set.

![Figure S2a. Parity plot — Liquid.](../machine_learning/plots/parity_Liquid.png)

![Figure S2b. Parity plot — Gas.](../machine_learning/plots/parity_Gas.png)

![Figure S2c. Parity plot — Solid.](../machine_learning/plots/parity_Solid.png)

![Figure S2d. Parity plot — Gasoline range hydrocarbons.](../machine_learning/plots/parity_Gasoline_range_hydrocarbons.png)

![Figure S2e. Parity plot — Diesel range hydrocarbons.](../machine_learning/plots/parity_Diesel_range_hydrocarbons.png)

![Figure S2f. Parity plot — Total aromatics.](../machine_learning/plots/parity_Total_aromatics_wpct.png)

![Figure S2g. Parity plot — BTX.](../machine_learning/plots/parity_BTX_wpct.png)

![Figure S2h. Parity plot — Wax (>C21).](../machine_learning/plots/parity_Wax_gtC21.png)

## S2.5 Compound Mapping

The 8 ML output categories are disaggregated into specific BioSTEAM compound IDs using fixed sub-distributions.

**Table S8.** Gas phase compound mapping.

| Compound | BioSTEAM ID | Sub-fraction |
|----------|------------|--------------|
| Hydrogen | H2 | 0.02 |
| Methane | CH4 | 0.20 |
| Ethylene | C2H4 | 0.25 |
| Propane | C3H8 | 0.25 |
| 1-Butene | C4H8 | 0.15 |
| Carbon monoxide | CO | 0.05 |
| Carbon dioxide | CO2 | 0.08 |
| **Total** | | **1.00** |

**Table S9.** Liquid sub-category compound mapping.

| Category | Compound | BioSTEAM ID | Sub-fraction |
|----------|----------|------------|--------------|
| **Gasoline** | n-Octane | C8H18 | 0.35 |
| | n-Decane | C10H22 | 0.35 |
| | n-Heptane | C7H16 | 0.15 |
| | n-Undecane | C11H24 | 0.15 |
| **Diesel** | n-Tetradecane | C14H30 | 0.40 |
| | 1-Hexadecene | C16H32 | 0.35 |
| | n-Eicosane | C20H42 | 0.25 |
| **BTX** | Benzene | C6H6 | 0.30 |
| | Toluene | C7H8 | 0.40 |
| | Ethylbenzene | C8H10 | 0.30 |
| **Other aromatics** | Styrene | C8H8 | 0.40 |
| | Methylstyrene | C9H10 | 0.30 |
| | Naphthalene | C10H8 | 0.30 |
| **Wax** | n-Tetracosane | C24H50 | 0.60 |
| | n-Tetracontane | C40H82 | 0.40 |

### Consistency constraints applied during mapping:
1. If sub-category total (Gasoline + Diesel + Aromatics + Wax) exceeds Liquid, all sub-categories are scaled down proportionally
2. If Liquid exceeds sub-category total, the residual is assigned to Gasoline
3. All compound fractions are normalized to sum to 1.0
4. BTX is capped at Total aromatics

## S2.6 Plasma-Specific Compound Mapping

Plasma pyrolysis uses a distinct compound mapping due to CO2-derived reactive species:

| Category | Compound | BioSTEAM ID | Sub-fraction |
|----------|----------|------------|--------------|
| **Gas** | Carbon monoxide | CO | 0.90 |
| | Hydrogen | H2 | 0.05 |
| | Methane | CH4 | 0.03 |
| | Ethylene | C2H4 | 0.02 |
| **Gasoline** | n-Octane | C8H18 | 1.00 (single surrogate) |
| **Diesel** | n-Octadecane | C18H38 | 1.00 (single surrogate) |
| **Wax** | n-Triacontane | C30H62 | 1.00 (single surrogate) |
| **Oxygenated** | 1-Dodecanol (Alcohol) | Alcohol | 0.722 |
| (residual liquid) | Fatty acid (Acid) | Acid | 0.171 |
| | 2,6-Di-tert-butyl-4-methylphenol | C14H22O | 0.107 |

The "oxygenated" fraction represents the residual liquid (total Liquid minus Gasoline, Diesel, Aromatics, Wax) and accounts for hydrocarbons oxidized by CO2-derived reactive species. The CO2 factor of 1.298 means total product mass is ~130% of feedstock mass.

## S2.7 Reactor-Type Corrections

The base PyrolysisNet model is trained on conventional (thermal, inert) pyrolysis data. Linear additive corrections shift the 8 predicted wt% outputs for different reactor chemistries:

$$\text{corrected}_i(T) = \text{base}_i + \alpha_i + \beta_i \times T$$

where T is the reaction temperature in °C.

### S2.7.1 TOD Correction

Anchored so delta(400 °C) = 0 for all outputs. Measured at 600 °C from Olafasakin et al. (2023), *Energy Fuels*, 37, 15832-15842 (100% HDPE, 93:7 HDPE/O2).

**Table S10.** TOD correction coefficients.

| Output | Intercept (alpha) | Slope (beta, per °C) | Delta at 600 °C |
|--------|-------------------|---------------------|-----------------|
| Liquid | +7.00 | -0.0175 | -3.50 |
| Gas | -16.40 | +0.0410 | +8.20 |
| Solid | -0.54 | +0.00135 | +0.27 |
| Gasoline | -11.00 | +0.0275 | +5.50 |
| Diesel | -5.96 | +0.0149 | +2.98 |
| Aromatics | 0.0 | 0.0 | 0.0 |
| BTX | 0.0 | 0.0 | 0.0 |
| Wax | +24.00 | -0.0600 | -12.00 |

### S2.7.2 Catalytic Correction

Fit to two temperature-bin midpoints (600 °C and 725 °C) derived from aston.xlsx comparison of catalytic (>10 wt% total aromatics, N~70) vs. thermal (<=5 wt%, N~120) polyolefin experiments.

**Table S11.** Catalytic correction coefficients.

| Output | Intercept (alpha) | Slope (beta, per °C) |
|--------|-------------------|---------------------|
| Liquid | +61.7 | -0.1064 |
| Gas | +76.7 | -0.0952 |
| Solid | -36.1 | +0.0512 |
| Gasoline | -13.5 | +0.0128 |
| Diesel | -6.8 | -0.0048 |
| Aromatics | +142.3 | -0.1672 |
| BTX | -8.5 | +0.0264 |
| Wax | -146.0 | +0.1816 |

Post-correction normalization:
1. Phase totals (Gas + Liquid + Solid) renormalized to 100%
2. Sub-categories scaled to fit within Liquid
3. BTX capped at Total aromatics

### S2.7.3 Plasma Correction

Calibrated so that at virtual_temperature = 450 °C with HDPE = 100% the corrected categories reproduce Case G (CO2 plasma, tR = 20 s) from Radhakrishnan et al. (2024).

**Table S12.** Plasma correction coefficients.

| Output | Type | Correction Value | Notes |
|--------|------|-----------------|-------|
| Liquid | Additive | +29.61 | CO2 incorporation -> oxygenated products |
| Gas | Additive | +8.05 | CO-dominated |
| Solid | Additive | -1.61 | Eliminated under plasma conditions |
| Gasoline | Multiplicative | x 0.850 | 13.1 / 15.42 |
| Diesel | Multiplicative | x 0.329 | 11.4 / 34.70 |
| Aromatics | Additive | -2.15 | Suppressed (no catalyst) |
| BTX | Additive | -1.59 | Suppressed |
| Wax | Multiplicative | x 0.058 | 3.1 / 53.23 |

Phase totals are NOT normalized to 100% because CO2 mass incorporation inflates the liquid fraction (total yields ~130%). Sub-categories (Gasoline, Diesel, Wax) use multiplicative scaling to prevent negative values when the ML model predicts different raw distributions for non-HDPE feeds.

## S2.8 Parametric Studies

![Figure S3. Temperature sweep showing effect of pyrolysis temperature on product yields.](../machine_learning/plots/temperature_sweep.png)

![Figure S4. Vapor residence time sweep.](../machine_learning/plots/vrt_sweep.png)

![Figure S5a. Feedstock composition sweep.](../machine_learning/plots/composition_sweep.png)

![Figure S5b. Feedstock composition sensitivity.](../machine_learning/plots/composition_sensitivity.png)

![Figure S6. Phase distribution (Liquid/Gas/Solid) stacked area plot.](../machine_learning/plots/phase_stacked.png)

![Figure S7. Reactor type comparison: thermal vs. TOD vs. catalytic vs. plasma.](../machine_learning/plots/reactor_comparison.png)
