# S6. Optimization Results

## S6.1 Optimization Methodology

Multi-objective optimization is performed using scipy's Nelder-Mead simplex method with the following configuration:

| Parameter | Value |
|-----------|-------|
| Algorithm | Nelder-Mead (scipy.optimize.minimize) |
| Variables | 4 split fractions |
| Bounds | [0.05, 0.95] for each variable |
| Initial point | [0.34, 0.50, 0.50, 0.50] |
| Max iterations | 50 |
| x tolerance | 0.01 |
| f tolerance | 0.001 |
| Adaptive | True |

## S6.2 Objective Function

The weighted-sum multi-objective function combines MSP and GWP:

$$\text{score} = w_{\text{MSP}} \times \frac{\text{MSP}}{\text{MSP}_{\text{ref}}} + w_{\text{GWP}} \times \frac{-\text{GWP}}{\text{GWP}_{\text{ref}}}$$

| Weight | Value |
|--------|-------|
| w_MSP | 0.50 |
| w_GWP | 0.50 |

Reference values (MSP_ref, GWP_ref) are computed at the initial point for each scenario to normalize the two objectives to comparable scales. Negative GWP is negated so that both terms are maximized (more negative MSP = better economics; more negative GWP = better environment).

## S6.3 Optimization Variables

| Variable | Symbol | Description | Bounds |
|----------|--------|-------------|--------|
| split_TOD | x1 | Fraction of total feed to CP+TOD (rest to CPY+PLASMA) | 0.05-0.95 |
| split_CP | x2 | Fraction of CP+TOD stream to TOD (rest to CP) | 0.05-0.95 |
| split_CPY | x3 | Fraction of remaining feed to CPY (rest to PLASMA) | 0.05-0.95 |
| split_HC | x4 | Fraction of wax to HC (rest to FCC) | 0.05-0.95 |

## S6.4 Optimal Split Fractions

**Table S20.** Optimal split fractions by scenario.

| Split | baseline | high_fuel | high_chem | high_organics |
|-------|----------|-----------|-----------|---------------|
| CP+TOD vs rest (x1) | 0.342 | 0.342 | 0.328 | 0.163 |
| TOD vs CP (x2) | 0.506 | 0.509 | 0.510 | 0.779 |
| CPY vs PLASMA (x3) | 0.492 | 0.469 | 0.482 | 0.050 |
| HC vs FCC (x4) | 0.526 | 0.518 | 0.541 | 0.791 |

**Key observations:**
- **baseline, high_fuel, high_chem** converge to similar splits (~34% to CP+TOD, ~50/50 TOD/CP, ~50/50 CPY/PLASMA, ~52% to HC)
- **high_organics** shifts dramatically: only 16.3% to CP+TOD, 77.9% to TOD (within that fraction), 95% to PLASMA (vs CPY), and 79.1% to HC. This maximizes PLASMA pathway throughput for high-value organics.

## S6.5 TEA Results

**Table S21.** TEA results by scenario.

| Metric | baseline | high_fuel | high_chem | high_organics |
|--------|----------|-----------|-----------|---------------|
| MSP ($/kg feed) | -0.5244 | -0.4955 | -0.6474 | +0.0093 |
| Utility cost ($/yr) | - | - | $1,887,710 | $5,191,586 |
| Annual sales ($/yr) | - | - | $37,895,920 | $104,971,038 |
| Installed cost ($) | - | - | $221,692,625 | $272,118,239 |

**MSP interpretation:**
- **Negative MSP** (baseline, high_fuel, high_chem): The plant is profitable at zero feedstock cost. Product revenues exceed all operating and capital costs at the 10% IRR target. The plant can afford to *pay* for waste plastic intake.
- **Positive MSP** (high_organics: $0.0093/kg): Despite the highest total sales ($105M/yr), the high_organics scenario requires a small tipping fee because non-favored products (fuels, chemicals) are priced at their LOW values, and the larger PLASMA pathway has higher capital and utility costs ($5.2M/yr utilities, $272M installed).

## S6.6 LCA Results

**Table S22.** LCA results by scenario.

| Metric | baseline | high_fuel | high_chem | high_organics |
|--------|----------|-----------|-----------|---------------|
| GWP (kg CO2-eq/kg feed) | -0.3147 | -0.3275 | -0.3302 | -0.8760 |
| Carbon abatement cost ($/kg CO2-eq) | 0.66 | 0.53 | 0.99 | -0.46 |

**GWP interpretation:**
- All scenarios achieve net-negative GWP, indicating that product displacement credits exceed process emissions.
- **high_organics** has the most negative GWP (-0.876 kg CO2-eq/kg feed) because PLASMA products (alcohols, acids, carbonyls) displace more emission-intensive conventional production.
- **high_organics** also has a negative CAC (-$0.46/kg CO2-eq), meaning CO2 reduction is achieved while generating net revenue.

## S6.7 Sales by Product Group

**Table S23.** Annual sales by product group ($/yr).

| Group | baseline | high_fuel | high_chem | high_organics |
|-------|----------|-----------|-----------|---------------|
| Fuels | $18.68M | $27.37M | $10.16M | $6.16M |
| Chemicals | $5.96M | $2.91M | $7.41M | $0.54M |
| Organics | $16.57M | $16.26M | $16.19M | $92.49M |
| Hydrogen | $4.12M | $1.65M | $1.65M | $1.65M |
| **Total** | **$45.33M** | **$48.19M** | **$35.42M** | **$100.85M** |

**Key observations:**
- Organics dominate in high_organics ($92.5M, 91.7% of total), reflecting the optimizer's shift toward PLASMA
- Fuels dominate in high_fuel ($27.4M, 56.8% of total)
- Baseline is well-diversified (Fuels 41%, Organics 37%, Chemicals 13%, Hydrogen 9%)
- High_chem has the lowest total sales ($35.4M) despite favorable chemical prices, because chemicals represent a small mass fraction of total products

## S6.8 Organics Revenue Breakdown

**Table S24.** Organics revenue breakdown by product ($/yr).

| Product | baseline | high_fuel | high_chem | high_organics |
|---------|----------|-----------|-----------|---------------|
| Acids | $0.51M | $0.67M | $0.67M | $6.32M |
| Alcohols | $6.94M | $5.07M | $5.05M | $22.72M |
| C30 | $0.01M | $0.03M | $0.02M | $0.11M |
| Carbonyls | $2.00M | $2.08M | $2.08M | $22.84M |
| Olefins | $5.31M | $5.88M | $5.85M | $29.69M |
| Paraffins | $1.81M | $2.54M | $2.53M | $10.81M |
| **Total** | **$16.57M** | **$16.26M** | **$16.19M** | **$92.49M** |

**Key observations:**
- In high_organics, Olefins ($29.7M) and Carbonyls ($22.8M) are the top revenue streams, driven by their high prices ($2.00/kg and $2.40/kg respectively)
- Alcohols contribute significantly across all scenarios due to their large mass fraction in PLASMA output
- C30 contributes negligibly (<$0.11M) due to very low production volume
- Non-high_organics scenarios show similar organic revenues (~$16M), indicating organic production is relatively stable across split configurations

## S6.9 Cross-Scenario Analysis

The optimization reveals three distinct regimes:

1. **Balanced operation** (baseline, high_fuel, high_chem): ~34% to CP+TOD, balanced CPY/PLASMA, balanced HC/FCC. The superstructure distributes feed to capture value across all product groups.

2. **PLASMA-dominant** (high_organics): 83.7% to CPY+PLASMA, with 95% of that going to PLASMA. Only 16.3% goes to the CP+TOD pathway, and within that, 77.9% goes to TOD (which produces more wax for HC upgrading at 79.1% HC split).

3. **Price sensitivity**: The optimal configuration is relatively robust to fuel/chemical price changes but highly sensitive to organic prices, which can shift the entire superstructure toward PLASMA dominance.
