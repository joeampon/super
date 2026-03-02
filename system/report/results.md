# Results and Discussion

## 3.1 Machine-Learning Model Validation

A feedforward neural network (PyrolysisNet; 5 → 64 → 128 → 64 → 8
architecture with batch normalization and 10 % dropout) was trained on 566
literature pyrolysis experiments spanning polyethylene, polypropylene, and
polystyrene feedstocks at 300–800 °C and 0.5–120 s vapor residence time.
Test-set parity plots (Figure 1) show that the model captures the dominant
variance for the categories most relevant to techno-economic analysis: Liquid
(R² = 0.74, MAE = 11.8 wt %), BTX (R² = 0.71, MAE = 2.8 wt %), Gas
(R² = 0.56), and Wax (R² = 0.56).  Diesel-range (R² = 0.41) and Total
aromatics (R² = 0.40) are moderately well predicted, while Solid (R² = 0.41)
and Gasoline-range hydrocarbons (R² = 0.13) show greater scatter — consistent
with the inherently noisy Gasoline-range measurements in the underlying
literature data.

**Figure 1.** PyrolysisNet parity plots (predicted vs. experimental, test
set) for the eight product-category yields: **(a)** Liquid, **(b)** Gas,
**(c)** Solid, **(d)** Gasoline-range, **(e)** Diesel-range, **(f)** Total
aromatics, **(g)** BTX, **(h)** Wax >C21.  Dashed lines denote 1:1 parity;
R² and MAE are annotated per panel.

![Figure 1 — PyrolysisNet parity plots](figures/fig1_parity_composite.png)

## 3.2 Reactor-Type Yield Comparison

Linear reactor-type corrections, calibrated against published experimental
data for thermal pyrolysis, catalytic (zeolite) pyrolysis, and CO₂-plasma
pyrolysis, extend the base model to each upstream technology.
Temperature sweeps for 100 % HDPE feed (Figure 2) reveal distinct product
selectivity profiles across the three reactor types.  Thermal pyrolysis
maximizes liquid yield (~84 wt % at 500 °C) with high wax selectivity,
while catalytic pyrolysis produces significantly more gasoline-range and BTX
products at the expense of wax.  Plasma pyrolysis achieves intermediate
liquid yields but with a distinct product slate enriched in oxygenated
species.  Gas yield increases monotonically with temperature across all
reactor types.  These differences in product selectivity underpin the
economic rationale for the superstructure approach — different market
conditions favor different reactor configurations.

**Figure 2.** Temperature-dependent product yields for thermal, catalytic,
and plasma pyrolysis of 100 % HDPE: **(a)** Liquid, **(b)** Gas, **(c)** Wax
(>C21), **(d)** Gasoline-range, **(e)** Diesel-range, **(f)** BTX.

![Figure 2 — Reactor comparison](figures/fig2_reactor_comparison.png)

## 3.3 Baseline Process Performance

The superstructure was evaluated at a balanced starting configuration
(x₁ = 0.34, x₂ = 0.50, x₃ = 0.50, x₄ = 0.50) with baseline product
prices and a feed rate of 250 tonnes per day of US-average municipal
solid-waste plastic (HDPE 22.0 / LDPE 44.2 / PP 23.4 / PS 10.4 wt % of the
pyrolysis-eligible fraction).  Key performance metrics are summarized in
Table 1.

**Table 1.** Baseline techno-economic and environmental performance
(250 tpd, balanced splits, baseline prices).

| Metric | Value |
|--------|-------|
| Minimum selling price (MSP) | −$0.524 kg⁻¹ feed |
| Annual product sales | $45.3 M yr⁻¹ |
| Installed equipment cost | $222 M |
| Annual utility cost | $1.9 M yr⁻¹ |
| Global warming potential (GWP) | −0.315 kg CO₂-eq kg⁻¹ feed |
| Carbon abatement cost (CAC) | $0.66 kg⁻¹ CO₂-eq |

The negative MSP indicates that product revenues — dominated by fuels (41 %),
organics (37 %), chemicals (13 %), and hydrogen (9 %) — exceed all operating
and capital costs at a 10 % internal rate of return over a 20-year plant
life.  The plant can afford to *pay* for waste-plastic intake rather than
charge a tipping fee.

## 3.4 Multi-Objective Optimization — Pareto Frontiers

A weighted-sum multi-objective optimization (w_MSP = w_GWP = 0.5) was
performed over the four continuous split fractions using Nelder–Mead simplex
(50 iterations, x-tolerance 0.01, adaptive step sizing).  The Pareto frontier
for the baseline price scenario (Figure 3) reveals a tight cluster of
near-optimal solutions rather than a broad trade-off curve, indicating that
both objectives can be improved simultaneously by routing more feed through
the PLASMA pathway.

**Figure 3.** Pareto frontier for the baseline price scenario (MSP vs. GWP).
Each point is one Monte Carlo evaluation of the four split variables; orange
markers denote non-dominated solutions.

![Figure 3 — Pareto baseline](figures/fig3_pareto_baseline.png)

The Pareto frontiers for all four price scenarios (Figure 4) demonstrate the
robustness of the superstructure to market volatility.  The high_organics
scenario shifts the frontier sharply toward lower GWP, reflecting the high
displacement credits from oxygenated chemicals.

**Figure 4.** Pareto frontiers for all four price scenarios, showing how the
MSP–GWP trade-off shifts with market conditions: **(a)** baseline,
**(b)** high fuel, **(c)** high chemicals, **(d)** high organics.

![Figure 4 — Pareto by scenario](figures/fig4_pareto_all_scenarios.png)

## 3.5 Scenario Analysis — Effect of Product Prices

Four price scenarios spanning the 2015–2025 US Gulf Coast range were defined:
*baseline* (all mid-range), *high_fuel* (fuels at peak, others at trough),
*high_chem* (chemicals at peak), and *high_organics* (specialty organics at
peak).  The optimal split fractions for each scenario (Table 2) reveal that
three scenarios converge to essentially the same balanced configuration while
high_organics shifts the superstructure dramatically toward PLASMA.

**Table 2.** Optimal split fractions by price scenario.

| Split | baseline | high_fuel | high_chem | high_organics |
|-------|----------|-----------|-----------|---------------|
| CP + TOD vs. rest (x₁) | 0.342 | 0.342 | 0.328 | 0.163 |
| TOD vs. CP (x₂) | 0.506 | 0.509 | 0.510 | 0.779 |
| CPY vs. PLASMA (x₃) | 0.492 | 0.469 | 0.482 | 0.050 |
| HC vs. FCC (x₄) | 0.526 | 0.518 | 0.541 | 0.791 |

The split fraction comparison (Figure 7) illustrates this divergence: under
high_organics pricing, 83.7 % of the feed is routed to CPY + PLASMA, of
which 95 % goes to PLASMA (x₃ = 0.05).

**Figure 7.** Optimal split fractions across the four price scenarios.  The
dashed line marks the equal-split reference (0.50).

![Figure 7 — Optimal splits](figures/fig7_optimal_splits.png)

**Table 3.** Techno-economic and environmental results by scenario.

| Metric | baseline | high_fuel | high_chem | high_organics |
|--------|----------|-----------|-----------|---------------|
| MSP ($ kg⁻¹ feed) | −0.524 | −0.496 | −0.647 | +0.009 |
| GWP (kg CO₂-eq kg⁻¹ feed) | −0.315 | −0.328 | −0.330 | −0.876 |
| CAC ($ kg⁻¹ CO₂-eq) | 0.66 | 0.53 | 0.99 | −0.46 |

All four scenarios achieve net-negative GWP.  Three scenarios deliver negative
MSP (profitable at zero feedstock cost); high_organics requires only a nominal
tipping fee (+$0.009 kg⁻¹) despite generating annual sales of $101 M yr⁻¹
because the larger PLASMA pathway incurs higher installed cost ($272 M vs.
~$222 M) and utility demand ($5.2 M yr⁻¹).

## 3.6 Revenue Breakdown

Annual sales by product group (Table 4) vary substantially across scenarios.
The stacked bar chart (Figure 5) highlights that organics account for 91.7 %
of total revenue under high_organics pricing, driven by olefins
($29.7 M yr⁻¹), carbonyls ($22.8 M), and alcohols ($22.7 M).  By contrast,
the baseline scenario is well diversified across all product groups.

**Table 4.** Annual sales by product group ($ M yr⁻¹).

| Group | baseline | high_fuel | high_chem | high_organics |
|-------|----------|-----------|-----------|---------------|
| Fuels | 18.7 | 27.4 | 10.2 | 6.2 |
| Chemicals | 6.0 | 2.9 | 7.4 | 0.5 |
| Organics | 16.6 | 16.3 | 16.2 | 92.5 |
| Hydrogen | 4.1 | 1.7 | 1.7 | 1.7 |
| **Total** | **45.3** | **48.2** | **35.4** | **100.9** |

**Figure 5.** Annual revenue breakdown by product group across the four
price scenarios.  Labels show values exceeding $5 M yr⁻¹.

![Figure 5 — Revenue breakdown](figures/fig5_revenue_breakdown.png)

## 3.7 Techno-Economic Cost Analysis

The installed equipment cost and annual operating economics are compared
across scenarios in Figure 9.  The baseline, high_fuel, and high_chem
scenarios share an identical plant configuration (installed cost $222 M),
whereas the high_organics scenario requires $272 M — a 23 % increase — due to
the capital-intensive PLASMA reactor and associated separation equipment.
Despite this higher capital cost, annual product sales under high_organics
($101 M yr⁻¹) are more than double the baseline ($45 M yr⁻¹), reflecting
the high unit value of oxygenated organics.

**Figure 9.** Techno-economic analysis: **(a)** installed equipment cost by
scenario; **(b)** annual utility cost vs. product sales.

![Figure 9 — Cost breakdown](figures/fig9_cost_breakdown.png)

## 3.8 Life Cycle Assessment

The cradle-to-gate GWP breakdown for the baseline scenario (Figure 6)
identifies the dominant contributors to the net-negative life cycle impact.
The largest displacement credits derive from the high-volume fuel products:
alcohols (−0.112 kg CO₂-eq kg⁻¹ feed), naphtha (−0.055), and diesel
(−0.066) benefit from their large mass flows, while lower-volume but
higher-impact streams such as hydrogen (−0.044, owing to the high emission
factor of SMR hydrogen at 2.277 kg CO₂-eq kg⁻¹) and BTX (−0.046) also
contribute substantially.  Process burdens from grid electricity and natural
gas partially offset these credits, yielding a net GWP of −0.315 kg CO₂-eq
kg⁻¹ feed at baseline.

The high_organics scenario achieves the deepest GWP reduction
(−0.876 kg CO₂-eq kg⁻¹ feed) — nearly three times the baseline — because
oxygenated PLASMA products (alcohols, acids, carbonyls) displace
emission-intensive conventional chemical production.

**Figure 6.** Life cycle GWP contribution by stream at baseline.  Green bars
are displacement credits (avoided fossil production); red bars are process
burdens.  The dashed line shows the net GWP.

![Figure 6 — LCA waterfall](figures/fig6_lca_waterfall.png)

## 3.9 Sensitivity and Contour Analysis

Pairwise sweeps of the four decision variables (12 × 12 grid, 864 system
evaluations) map the MSP and GWP objective landscapes (Figure 8).  The
following hierarchy of decision-variable influence emerges:

1. **CPY vs. PLASMA allocation (x₃) is the dominant lever.**  Moving toward
   PLASMA (lower x₃) simultaneously improves MSP and GWP when organic prices
   are favorable — a rare alignment of economic and environmental incentives.
2. **Feed allocation to CP + TOD (x₁) is moderately influential.**  Shifting
   more feed to CPY + PLASMA (lower x₁) reduces both objectives, but the
   effect saturates above ~70 % CPY + PLASMA allocation.
3. **TOD vs. CP (x₂) is the least influential variable.**  Both thermal
   pyrolysis technologies produce similar fuel-range products with comparable
   economics.
4. **HC vs. FCC wax upgrading (x₄) shows a mild preference for HC**, driven
   by higher diesel selectivity, partially offset by hydrogen purchase cost.

Flat landscapes near the baseline optimum indicate operational flexibility —
small deviations from optimal splits have minimal impact on MSP or GWP, an
attractive feature for industrial implementation.

**Figure 8.** Sensitivity contour plots for four key variable pairs: MSP
(left column) and GWP (right column).  Color scales are independent for
each subplot.

![Figure 8 — Contour plots](figures/fig8_contours.png)

## 3.10 Comparison with Literature

The superstructure framework offers significant advantages over single-pathway
designs.  Figure 10 compares the MSP and GWP of this work against published
waste-plastic pyrolysis TEA/LCA studies.  Conventional pyrolysis-only plants
report positive MSP values of $0.05–0.30 kg⁻¹, requiring a tipping fee.
The baseline configuration achieves an MSP of −$0.524 kg⁻¹ by diversifying
the product portfolio across fuels, chemicals, and oxygenated organics —
revenue streams unavailable to single-technology plants.

Single-pathway pyrolysis GWP values in the literature range from −0.10 to
−0.28 kg CO₂-eq kg⁻¹ feed.  The superstructure matches this range at
baseline (−0.315) and substantially exceeds it under high_organics pricing
(−0.876), owing to the high displacement credits of oxygenated chemicals
from the PLASMA pathway.

**Figure 10.** Comparison of **(a)** minimum selling price (MSP) and
**(b)** global warming potential (GWP) between this work and published
single-technology pyrolysis studies.  Blue bars = literature; orange bars =
this work.

![Figure 10 — Literature comparison](figures/fig10_literature_comparison.png)

## 3.11 Limitations

Three limitations warrant discussion.  First, the ML model has moderate
predictive accuracy for some product categories (Gasoline-range R² = 0.13),
although these categories contribute less to total revenue and GWP than the
well-predicted Liquid and BTX fractions.  Second, the feedstock composition is
fixed at the US MSW average; real-world feeds vary seasonally and regionally.
Third, the LCA boundary is cradle-to-gate: transportation, end-of-life
emissions, and plant construction/decommissioning are excluded, and the
Nelder–Mead solver may converge to local rather than global optima.

Despite these caveats, the results demonstrate that a flexible, multi-pathway
superstructure — enabled by machine-learning yield prediction — can adapt to
volatile markets while simultaneously reducing greenhouse-gas emissions,
offering a compelling pathway for industrial-scale waste-plastic chemical
recycling.
