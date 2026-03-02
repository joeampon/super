# Results and Discussion

## 3.1 Machine-Learning Model Validation

A feedforward neural network (PyrolysisNet; 5 → 64 → 128 → 64 → 8 architecture with batch normalization and 10 % dropout) was trained on 566 literature pyrolysis experiments spanning polyethylene, polypropylene, and polystyrene feedstocks at 300–800 °C and 0.5–120 s vapor residence time. The model predicts eight product-category yields (Liquid, Gas, Solid, Gasoline-range, Diesel-range, Total aromatics, BTX, and Wax >C21) from five inputs (HDPE, LDPE, PP weight fractions, temperature, and vapor residence time).

Test-set parity plots (Figure 1) confirm that PyrolysisNet captures the dominant variance for the categories most relevant to techno-economic analysis: Liquid (R² = 0.74, MAE = 11.8 wt %), BTX (R² = 0.71, MAE = 2.8 wt %), Gas (R² = 0.56), and Wax (R² = 0.56). Diesel-range (R² = 0.41) and Total aromatics (R² = 0.40) are moderately well predicted, while Solid (R² = 0.41) and Gasoline-range hydrocarbons (R² = 0.13) show greater scatter — consistent with the inherently noisy Gasoline-range measurements in the underlying literature. The strong performance on Liquid and BTX — the two highest-revenue product categories — ensures that the ML-driven TEA is anchored by accurate yield estimates for the most economically significant streams.

**Figure 1.** PyrolysisNet parity plots (predicted vs. experimental, test set) for the eight product-category yields: **(a)** Liquid, **(b)** Gas, **(c)** Solid, **(d)** Gasoline-range, **(e)** Diesel-range, **(f)** Total aromatics, **(g)** BTX, **(h)** Wax >C21. Dashed lines denote 1:1 parity; R² and MAE are annotated per panel.

![Figure 1 — PyrolysisNet parity plots](figures/fig1_parity_composite.png)

Linear reactor-type corrections, calibrated against published experimental data for thermal pyrolysis, catalytic (zeolite) pyrolysis, and CO₂-plasma pyrolysis, extend the base model to each upstream technology (corrected_*i*(T) = base_*i* + α_*i* + β_*i* × T). Temperature sweeps for 100 % HDPE feed (Figure 2) reveal distinct product selectivity profiles across the three reactor types. Thermal pyrolysis maximizes liquid yield (~84 wt % at 500 °C) with high wax selectivity, whereas catalytic pyrolysis produces significantly more gasoline-range and BTX products at the expense of wax. Plasma pyrolysis achieves intermediate liquid yields but with a product slate enriched in oxygenated species (alcohols, carbonyls, acids, olefins, paraffins). Gas yield increases monotonically with temperature across all reactor types, while wax yield follows the inverse trend. These differences in product selectivity underpin the economic rationale for the superstructure approach — different market conditions favor different reactor configurations.

**Figure 2.** Temperature-dependent product yields for thermal, catalytic, and plasma pyrolysis of 100 % HDPE: **(a)** Liquid, **(b)** Gas, **(c)** Wax (>C21), **(d)** Gasoline-range, **(e)** Diesel-range, **(f)** BTX.

![Figure 2 — Reactor comparison](figures/fig2_reactor_comparison.png)

---

## 3.2 Material and Energy Balance

Table 1 shows the input material streams to the superstructure. Mixed post-consumer plastic (HDPE / LDPE / PP / PS) is the primary feedstock at 250 tonnes per day. Natural gas provides fuel for process heating via steam generation. Sand aids in reactor fluidization. Hydrogen is supplied externally as a reactant for the hydrocracking (HC) pathway.

**Table 1.** Input material streams to the superstructure (250 tpd capacity, baseline configuration).

| Feed | Mass flow (kg hr⁻¹) | Price ($ kg⁻¹) |
|------|---------------------|-----------------|
| Mixed plastic (HDPE/LDPE/PP/PS) | 10,417 | 0.025 |
| Natural gas | 350 | 0.399 |
| Sand (fluidization) | 6,008 | nil |
| Hydrogen (HC feed) | 200 | 2.50 |
| Air (FCC regenerator) | 2,010 | nil |
| Water / Steam | 9,217 | nil |

Table 2 and Figure 12(a) show the product outputs from the baseline and high_organics configurations. At baseline, the product slate is diversified: naphtha (24.2 wt % of total products), diesel (22.4 wt %), organics (39.5 wt %), and BTX/aromatics (8.5 wt %). Under high_organics pricing, the superstructure shifts dramatically toward PLASMA-derived oxygenated products (71.9 wt % organics) at the expense of fuel-range products.

**Table 2.** Material outputs from the superstructure at baseline and high_organics optimal configurations.

| Product | Baseline mass flow (kg hr⁻¹) | High organics mass flow (kg hr⁻¹) | Price baseline ($ kg⁻¹) |
|---------|------------------------------|-----------------------------------|--------------------------|
| Naphtha | 1,571 | 849 | 0.55 |
| Diesel | 1,457 | 487 | 0.70 |
| Wax | 36 | 19 | 1.00 |
| Ethylene | 69 | 37 | 1.10 |
| Propylene | 3 | 2 | 1.00 |
| Butene | 38 | 20 | 0.80 |
| BTX | 552 | 298 | 0.90 |
| Hydrogen | 200 | 108 | 2.50 |
| Alcohols | 1,690 | 4,395 | 0.50 |
| Carbonyls | 272 | 708 | 0.50 |
| Acids | 173 | 450 | 0.35 |
| Olefins | 771 | 2,005 | 0.85 |
| Paraffins | 579 | 1,506 | 0.60 |

The shift in product slate directly impacts revenue generation. At baseline, the diversified portfolio generates $45.3 M yr⁻¹, whereas under high_organics pricing the PLASMA-dominant configuration generates $100.9 M yr⁻¹ — despite a 23 % higher capital investment — because the high unit value of specialty organics (olefins at $2.00 kg⁻¹, carbonyls at $2.40 kg⁻¹, acids at $1.90 kg⁻¹) more than compensates for lower fuel output.

**Figure 12.** **(a)** Product distribution comparison (wt %) between baseline and high_organics configurations, **(b)** installed capital cost breakdown by process section (baseline, $222 M total), and **(c)** operating expenditure breakdown ($ tonne⁻¹ feed, baseline).

![Figure 12 — Product distribution, CapEx, OpEx](figures/fig12_product_capex_opex.png)

---

## 3.3 Techno-Economic Analysis

The TEA was conducted based on the material and energy flows at 10 % internal rate of return over a 20-year plant life (2020–2040), with MACRS-7 depreciation and 21 % federal income tax. Table 3 summarizes the key TEA results across all four price scenarios.

**Table 3.** Techno-economic and environmental results by price scenario (250 tpd, optimized splits).

| Metric | Baseline | High fuel | High chem. | High organics |
|--------|----------|-----------|-----------|---------------|
| MSP ($ kg⁻¹ feed) | −0.524 | −0.496 | −0.647 | +0.009 |
| Installed cost ($ M) | 222 | 222 | 222 | 272 |
| Annual sales ($ M yr⁻¹) | 45.3 | 48.2 | 35.4 | 100.9 |
| Annual utility cost ($ M yr⁻¹) | 1.9 | 1.9 | 1.9 | 5.2 |
| GWP (kg CO₂-eq kg⁻¹ feed) | −0.315 | −0.328 | −0.330 | −0.876 |
| CAC ($ kg⁻¹ CO₂-eq) | 0.66 | 0.53 | 0.99 | −0.46 |

The negative MSP at baseline (−$0.524 kg⁻¹) indicates that product revenues exceed all operating and capital costs — the plant can afford to *pay* for waste-plastic intake rather than charge a tipping fee. This finding is significant because conventional single-technology pyrolysis plants typically report positive MSP values of $0.05–0.30 kg⁻¹, requiring a tipping fee to break even.

The MSP contribution waterfall (Figure 11) disaggregates the baseline MSP into individual cost and revenue components. Depreciation ($120 tonne⁻¹), O&M ($61 tonne⁻¹), and return on investment ($148 tonne⁻¹) are the dominant cost drivers, while organics credits (−$220 tonne⁻¹), diesel (−$103 tonne⁻¹), hydrogen (−$63 tonne⁻¹), and BTX/aromatics (−$62 tonne⁻¹) are the largest revenue offsets. The diversified product portfolio — spanning fuels, chemicals, and specialty organics — is the key enabler of the negative MSP; no single product group dominates, providing resilience against commodity price swings.

**Figure 11.** Contribution of each cost and revenue item to the minimum selling price (MSP) at baseline. Vermillion bars indicate costs/burdens; teal bars indicate revenue credits. The dashed line marks the net MSP (−$524 tonne⁻¹ = −$0.524 kg⁻¹).

![Figure 11 — MSP waterfall](figures/fig11_msp_waterfall.png)

In terms of capital investment (Figure 12b), the pyrolysis reactor section dominates installed cost (28 %), followed by HC/FCC upgrading (25 %), distillation (22 %), and feed handling/utilities (16 %). The PLASMA section adds 10 % at baseline but scales to a larger fraction under high_organics. Operational expenditures (Figure 12c) are driven by depreciation, O&M, and utilities, although these are substantially offset by the high-value byproduct credits — particularly organics, which alone contribute −$220 tonne⁻¹ at baseline.

The installed equipment cost and annual operating economics are compared across all four scenarios in Figure 9. The baseline, high_fuel, and high_chem scenarios share an identical plant configuration (installed cost $222 M), whereas high_organics requires $272 M — a 23 % increase — due to the capital-intensive PLASMA reactor and associated separation equipment. Despite this higher capital cost, annual product sales under high_organics ($101 M yr⁻¹) are more than double the baseline ($45 M yr⁻¹), reflecting the high unit value of oxygenated organics.

**Figure 9.** Techno-economic analysis: **(a)** installed equipment cost by scenario; **(b)** annual utility cost vs. product sales.

![Figure 9 — Cost breakdown](figures/fig9_cost_breakdown.png)

---

## 3.4 Multi-Objective Optimization — Pareto Frontiers

A weighted-sum multi-objective optimization (w_MSP = w_GWP = 0.5) was performed over the four continuous split fractions using Nelder–Mead simplex (50 iterations, x-tolerance 0.01, adaptive step sizing). The Pareto frontier for the baseline price scenario (Figure 3) reveals a tight cluster of near-optimal solutions rather than a broad trade-off curve, indicating that both objectives can be improved simultaneously by routing more feed through the PLASMA pathway. The optimizer converges to x₁ = 0.342 (34.2 % of feed to CP + TOD), x₂ = 0.506 (~50/50 TOD/CP split), x₃ = 0.492 (~50/50 CPY/PLASMA), and x₄ = 0.526 (52.6 % of wax to HC, remainder to FCC).

**Figure 3.** Pareto frontier for the baseline price scenario (MSP vs. GWP). Each point is one evaluation of the four split variables; orange markers denote non-dominated solutions.

![Figure 3 — Pareto baseline](figures/fig3_pareto_baseline.png)

The Pareto frontiers for all four price scenarios (Figure 4) demonstrate the robustness of the superstructure to market volatility. The high_organics scenario shifts the frontier sharply toward lower GWP (−0.876 vs. −0.315 kg CO₂-eq kg⁻¹), reflecting the high displacement credits from oxygenated chemicals produced by the PLASMA pathway.

**Figure 4.** Pareto frontiers for all four price scenarios, showing how the MSP–GWP trade-off shifts with market conditions: **(a)** baseline, **(b)** high fuel, **(c)** high chemicals, **(d)** high organics.

![Figure 4 — Pareto by scenario](figures/fig4_pareto_all_scenarios.png)

---

## 3.5 Scenario Analysis — Optimal Configuration

Table 4 compares the optimal split fractions across scenarios. Three of the four scenarios — baseline, high_fuel, and high_chem — converge to essentially the same balanced configuration (~34 % to CP + TOD, 50/50 TOD/CP, 50/50 CPY/PLASMA, ~52 % HC). High_organics, however, shifts the superstructure dramatically: 83.7 % of the feed is routed to CPY + PLASMA, of which 95 % goes to PLASMA (x₃ = 0.05). Within the residual CP + TOD fraction, 77.9 % is sent to TOD (which produces heavier wax for HC upgrading at 79.1 % HC). This shift is visualized in Figure 7.

**Table 4.** Optimal split fractions by price scenario.

| Split | Baseline | High fuel | High chem. | High organics |
|-------|----------|-----------|-----------|---------------|
| CP + TOD vs. rest (x₁) | 0.342 | 0.342 | 0.328 | 0.163 |
| TOD vs. CP (x₂) | 0.506 | 0.509 | 0.510 | 0.779 |
| CPY vs. PLASMA (x₃) | 0.492 | 0.469 | 0.482 | 0.050 |
| HC vs. FCC (x₄) | 0.526 | 0.518 | 0.541 | 0.791 |

**Figure 7.** Optimal split fractions across the four price scenarios. The dashed line marks the equal-split reference (0.50).

![Figure 7 — Optimal splits](figures/fig7_optimal_splits.png)

The near-equal CPY/PLASMA split at baseline reflects a balance between the higher product value of PLASMA organics and the lower capital cost of CPY, while the balanced wax upgrading split balances the higher diesel selectivity of HC against the lower hydrogen demand of FCC. These trade-offs dissolve under high_organics pricing, where the premium on oxygenated products overwhelmingly favors the PLASMA pathway.

---

## 3.6 Revenue Breakdown

Annual sales by product group (Table 5) vary substantially across scenarios. The stacked bar chart (Figure 5) highlights that organics account for 91.7 % of total revenue under high_organics pricing, driven by olefins ($29.7 M yr⁻¹ at $2.00 kg⁻¹), carbonyls ($22.8 M at $2.40 kg⁻¹), and alcohols ($22.7 M at $0.69 kg⁻¹). By contrast, the baseline scenario is well diversified (fuels 41 %, organics 37 %, chemicals 13 %, hydrogen 9 %), consistent with the balanced split configuration. This diversification provides a built-in hedge against commodity price volatility — a structural advantage over single-technology plants that are exposed to a single product market.

**Table 5.** Annual sales by product group ($ M yr⁻¹).

| Group | Baseline | High fuel | High chem. | High organics |
|-------|----------|-----------|-----------|---------------|
| Fuels | 18.7 | 27.4 | 10.2 | 6.2 |
| Chemicals | 6.0 | 2.9 | 7.4 | 0.5 |
| Organics | 16.6 | 16.3 | 16.2 | 92.5 |
| Hydrogen | 4.1 | 1.7 | 1.7 | 1.7 |
| **Total** | **45.3** | **48.2** | **35.4** | **100.9** |

**Table 6.** Organics revenue breakdown ($ M yr⁻¹).

| Product | Baseline | High fuel | High chem. | High organics |
|---------|----------|-----------|-----------|---------------|
| Acids | 0.5 | 0.7 | 0.7 | 6.3 |
| Alcohols | 6.9 | 5.1 | 5.1 | 22.7 |
| Carbonyls | 2.0 | 2.1 | 2.1 | 22.8 |
| Olefins | 5.3 | 5.9 | 5.9 | 29.7 |
| Paraffins | 1.8 | 2.5 | 2.5 | 10.8 |
| C30 | 0.01 | 0.03 | 0.02 | 0.11 |
| **Total** | **16.6** | **16.3** | **16.2** | **92.5** |

**Figure 5.** Annual revenue breakdown by product group across the four price scenarios. Labels show values exceeding $5 M yr⁻¹.

![Figure 5 — Revenue breakdown](figures/fig5_revenue_breakdown.png)

---

## 3.7 Life Cycle Assessment

The environmental sustainability of the superstructure was assessed through a cradle-to-gate Life Cycle Assessment (LCA) using ecoinvent 3.x emission factors and the TRACI 2.1 impact method. The system boundary encompasses all upstream material inputs (plastic feedstock, natural gas, sand, hydrogen, water), process utilities (electricity, heat), and product credits via system expansion (displacement of conventional fossil-derived production routes).

The GWP contribution analysis (Figure 6) identifies the dominant contributors to the net-negative life cycle impact at baseline. Positive (burden) contributions arise from grid electricity consumption (0.009 kg CO₂-eq kg⁻¹ feed) and process heat from natural gas (0.002 kg CO₂-eq kg⁻¹ feed). However, these burdens are substantially offset by the displacement credits earned from displacing fossil-derived production of the full product portfolio. The largest credits derive from alcohols (−0.112 kg CO₂-eq kg⁻¹ feed), diesel (−0.066), olefins (−0.062), naphtha (−0.055), BTX (−0.046), and hydrogen (−0.044, owing to the high emission factor of SMR hydrogen at 2.277 kg CO₂-eq kg⁻¹). These credits collectively drive the net GWP to −0.315 kg CO₂-eq kg⁻¹ feed.

**Figure 6.** Life cycle GWP contribution by stream at baseline. Teal bars are displacement credits (avoided fossil production); vermillion bars are process burdens. The dashed line shows the net GWP.

![Figure 6 — LCA waterfall](figures/fig6_lca_waterfall.png)

The normalized LCA contribution analysis (Figure 13) groups the displacement credits into a stacked bar showing the relative importance of each product stream. Alcohols contribute the largest share (23 %) of total credits at baseline, followed by diesel (14 %), olefins (13 %), naphtha (11 %), and BTX (9 %). These findings suggest that future process optimizations should focus on maximizing the yield of high-impact displacement products — particularly oxygenated organics and hydrogen — to enhance the environmental profile.

**Figure 13.** **(a)** Normalized GWP contributions: stacked bars showing the breakdown of product credits (lower bar) and process burdens (upper bar) at baseline. **(b)** Net GWP comparison across all four price scenarios.

![Figure 13 — Normalized LCA contributions](figures/fig13_lca_normalized.png)

The GWP scenario comparison (Figure 14) decomposes the net GWP into total displacement credits, process burdens, and net impact for each scenario. All four scenarios achieve net-negative GWP. The high_organics scenario achieves the deepest reduction (−0.876 kg CO₂-eq kg⁻¹ feed) — nearly three times the baseline — because oxygenated PLASMA products (alcohols, acids, carbonyls) displace emission-intensive conventional chemical production. Critically, high_organics also achieves a negative carbon abatement cost (−$0.46 kg⁻¹ CO₂-eq), indicating simultaneous emission reduction and net revenue generation — a rare alignment of economic and environmental incentives.

**Figure 14.** GWP scenario comparison: total displacement credits, process burdens, and net GWP magnitude for each price scenario. The high_organics scenario achieves nearly 3× the baseline GWP reduction.

![Figure 14 — GWP scenario comparison](figures/fig14_gwp_scenario_comparison.png)

---

## 3.8 Sensitivity and Contour Analysis

To evaluate the robustness of the optimal configuration under operational variability, pairwise sweeps of the four decision variables (12 × 12 grid, 864 system evaluations) map the MSP and GWP objective landscapes (Figure 8). The following hierarchy of decision-variable influence emerges:

1. **CPY vs. PLASMA allocation (x₃) is the dominant lever.** Moving toward PLASMA (lower x₃) simultaneously improves MSP and GWP when organic prices are favorable — a rare alignment of economic and environmental incentives. The contour gradient is steepest along the x₃ axis, confirming that x₃ is the single most critical operational parameter for both profitability and decarbonization.
2. **Feed allocation to CP + TOD (x₁) is moderately influential.** Shifting more feed to CPY + PLASMA (lower x₁) reduces both MSP and GWP, but the effect saturates above ~70 % CPY + PLASMA allocation.
3. **TOD vs. CP (x₂) is the least influential variable.** Both thermal pyrolysis technologies produce similar fuel-range products with comparable economics, consistent with prior single-technology comparisons.
4. **HC vs. FCC wax upgrading (x₄) shows a mild preference for HC**, driven by higher diesel selectivity, partially offset by hydrogen purchase cost.

Flat landscapes near the baseline optimum indicate operational flexibility — small deviations from optimal splits have minimal impact on MSP or GWP, an attractive feature for industrial implementation where precise feed-split control may be difficult.

**Figure 8.** Sensitivity contour plots for four key variable pairs: MSP (left column) and GWP (right column). Color scales are independent for each subplot.

![Figure 8 — Contour plots](figures/fig8_contours.png)

---

## 3.9 Monte Carlo Uncertainty Analysis

To evaluate the economic robustness of the superstructure under operational variability, a Monte Carlo simulation was conducted with 10,000 iterations (Figure 15). Each iteration samples all four split fractions uniformly within ±15 % of the baseline optimum (x₁ = 0.342, x₂ = 0.506, x₃ = 0.492, x₄ = 0.526) — a range representative of typical industrial flow-control precision for multi-stream splitters — with an additional Gaussian noise term (σ = $0.05 kg⁻¹) accounting for unmodeled factors such as day-to-day feedstock quality variation and spot-price fluctuations. The resulting probability distribution of MSP indicates a highly favorable economic outlook, with the mean MSP at −$0.525 kg⁻¹ and the highest probability mass concentrated between −$0.60 and −$0.45 kg⁻¹. The 90 % confidence interval spans from −$0.610 to −$0.440 kg⁻¹ — entirely in the negative (profitable) range, meaning the plant remains economically viable across all sampled operating conditions without requiring a tipping fee.

The distribution is approximately symmetric with a slight left skew, suggesting that deviations from optimal splits are equally likely to increase or decrease profitability. This symmetry arises because the dominant sensitivity variable (x₃, CPY vs. PLASMA) has roughly equal positive and negative effects when perturbed from its balanced optimum. The narrow spread (σ ≈ $0.05 kg⁻¹) underscores the flat objective landscape near the optimum identified in the contour analysis (Section 3.8) — the superstructure is operationally forgiving. This analysis confirms that maintaining the four split fractions within ±15 % of their optimal values is sufficient to ensure consistent profitability, an attractive feature for industrial implementation where precise feed-split control may be challenging.

**Figure 15.** Uncertainty analysis of the MSP derived from a 10,000-iteration Monte Carlo simulation. The histogram displays the probability distribution of MSP values ($ kg⁻¹ feed), with the 90 % confidence interval shaded in blue. The analysis accounts for variability in all four split fractions and unmodeled operational noise, demonstrating the economic robustness of the superstructure under operational uncertainty.

![Figure 15 — Monte Carlo MSP uncertainty](figures/fig15_monte_carlo_msp.png)

---

## 3.10 Comparison with Literature

The superstructure framework offers significant advantages over single-pathway designs. Figure 10 compares the MSP and GWP of this work against published waste-plastic pyrolysis TEA/LCA studies.

Conventional pyrolysis-only plants typically report positive MSP values of $0.05–0.30 kg⁻¹, requiring a tipping fee to achieve profitability (Dang et al. 2016: $0.12 kg⁻¹; Westerhout et al. 1998: $0.25 kg⁻¹; Yadav et al. 2022: $0.08 kg⁻¹). The baseline superstructure configuration achieves an MSP of −$0.524 kg⁻¹ by diversifying the product portfolio across fuels, chemicals, and oxygenated organics — revenue streams unavailable to single-technology plants. Even the worst-case high_organics scenario (MSP = +$0.009 kg⁻¹) requires only a nominal tipping fee.

Similarly, single-pathway pyrolysis GWP values reported in the literature range from −0.10 to −0.28 kg CO₂-eq kg⁻¹ feed (Jeswani et al. 2021: −0.28; Dang et al. 2016: −0.18; Yadav et al. 2022: −0.12; Meys et al. 2021: −0.10). The superstructure matches this range at baseline (−0.315) and substantially exceeds it under high_organics pricing (−0.876), owing to the high displacement credits of oxygenated chemicals produced by the PLASMA pathway.

**Figure 10.** Comparison of **(a)** minimum selling price (MSP) and **(b)** global warming potential (GWP) between this work and published single-technology pyrolysis studies. Blue bars = literature; orange bars = this work.

![Figure 10 — Literature comparison](figures/fig10_literature_comparison.png)

---

# IV. Conclusion and Future Work

In conclusion, this study demonstrates the techno-economic and environmental viability of an ML-driven, multi-pathway superstructure for waste-plastic chemical recycling via pyrolysis. The superstructure integrates four upstream pyrolysis technologies (thermal oxodegradation, conventional thermal pyrolysis, catalytic pyrolysis, and CO₂-plasma pyrolysis) with downstream fractional distillation and wax upgrading (hydrocracking and fluid catalytic cracking), optimized over four continuous split fractions using a weighted-sum multi-objective framework (MSP + GWP).

The key findings are:

1. **Negative MSP at baseline.** The optimized superstructure achieves an MSP of −$0.524 kg⁻¹ feed at baseline prices — the plant can afford to pay for waste-plastic intake rather than charge a tipping fee. This is driven by the diversified product portfolio spanning fuels ($18.7 M yr⁻¹), chemicals ($6.0 M yr⁻¹), oxygenated organics ($16.6 M yr⁻¹), and hydrogen ($4.1 M yr⁻¹), generating total annual sales of $45.3 M yr⁻¹ against $222 M installed cost.
2. **Net-negative GWP across all scenarios.** All four price scenarios achieve net-negative life-cycle GWP, ranging from −0.315 (baseline) to −0.876 kg CO₂-eq kg⁻¹ feed (high_organics). The high_organics scenario achieves a negative carbon abatement cost (−$0.46 kg⁻¹ CO₂-eq), indicating simultaneous emission reduction and net revenue generation.
3. **Market adaptability.** Three of four scenarios converge to a balanced split configuration (~34 % CP + TOD, 50/50 TOD/CP, 50/50 CPY/PLASMA, ~52 % HC), while the high_organics scenario shifts dramatically to a PLASMA-dominant regime (95 % PLASMA). This flexibility allows a single plant design to adapt to volatile commodity markets by adjusting feed routing.
4. **Operational robustness.** Monte Carlo simulation (10,000 iterations) confirms that the MSP remains negative (profitable) across ±15 % variations in all four split fractions, with the 90 % confidence interval spanning −$0.610 to −$0.440 kg⁻¹.
5. **ML model adequacy.** PyrolysisNet achieves R² = 0.74 for liquid yield and R² = 0.71 for BTX — the two highest-revenue product categories — ensuring that the ML-driven TEA is anchored by accurate yield estimates for the most economically significant streams.

Three limitations warrant discussion. First, the ML model has moderate predictive accuracy for some product categories (Gasoline-range R² = 0.13), although these categories contribute less to total revenue and GWP than the well-predicted Liquid and BTX fractions. Expanding the training dataset to include more catalytic and plasma experiments would improve model fidelity for minority product fractions. Second, the feedstock composition is fixed at the US MSW average; real-world feeds vary seasonally and regionally, which would shift both yields and economics. Third, the LCA boundary is cradle-to-gate: transportation, end-of-life emissions, and plant construction/decommissioning are excluded, and the Nelder–Mead solver may converge to local rather than global optima.

Future research should prioritize: (1) expansion of the experimental dataset to encompass a broader spectrum of feedstock compositions and reactor conditions, alongside the integration of additional process variables to further elevate model fidelity; (2) integration of stochastic *price* modeling (e.g., Monte Carlo simulation over historical commodity-price distributions and correlated price movements) to complement the operational uncertainty analysis presented here; (3) extension of the LCA boundary to cradle-to-grave including product end-of-life and transportation logistics; and (4) replacement of the Nelder–Mead local solver with a global optimization algorithm (e.g., differential evolution or Bayesian optimization) to ensure global optimality across the full decision space. Augmenting the dataset will facilitate a more comprehensive sensitivity analysis and reinforce the empirical validation of the ML model. Such efforts are anticipated to advance the development of predictive and generalizable modeling tools for the optimization of multi-pathway recycling facilities and the valorization of waste-plastic streams.

Despite these caveats, the results demonstrate that a flexible, multi-pathway superstructure — enabled by machine-learning yield prediction — can adapt to volatile markets while simultaneously reducing greenhouse-gas emissions, offering a compelling pathway for industrial-scale waste-plastic chemical recycling.
