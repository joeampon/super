# Results & Discussion — Section Structure

This document outlines the recommended structure for the Results & Discussion
section of the main paper manuscript.  Each subsection lists its purpose, the
key figures/tables to include, and cross-references to the Supporting
Information (SI) where extended data reside.

---

## 3.1  Machine-Learning Model Validation

**Purpose:** Demonstrate that PyrolysisNet predictions are reliable enough to
drive the superstructure optimization.

**Content:**
- Summarize test-set performance (R², MAE, RMSE) for the 8 output categories
  (Table S7).
- Highlight best-predicted outputs (Liquid R² = 0.74, BTX R² = 0.71) and
  discuss limitations (Gasoline R² = 0.13).
- Show one composite parity-plot figure (8 panels) as **Figure 2** (see
  `machine_learning/plots/parity_*.png`).
- Briefly describe temperature and composition sweeps to confirm physically
  reasonable trends (liquid yield increases then plateaus with temperature; gas
  increases monotonically).

**Key figure:** Parity plots (Figure 2 — 8 panels).

**SI cross-refs:** S2 (full architecture, training, compound mapping).

---

## 3.2  Baseline Process Performance

**Purpose:** Report the techno-economic and environmental performance at the
optimizer's starting point (or a representative equal-split configuration)
before discussing the optimization landscape.

**Content:**
- Feed basis: 250 tpd mixed plastic (HDPE 22.0 / LDPE 44.2 / PP 23.4 / PS
  10.4 wt%, summing to 100% of the pyrolysis-eligible fraction).
- Product slate and mass flows from the four upstream pathways merging through
  distillation + wax upgrading.
- Baseline TEA metrics: MSP = −$0.524/kg feed, installed cost, annual sales
  $45.3 M/yr, utility cost (Table S21).
- Baseline LCA metrics: GWP = −0.315 kg CO₂-eq/kg feed (net negative),
  carbon abatement cost $0.66/kg CO₂-eq (Table S22).
- Discuss the negative MSP: product revenues exceed all operating + capital
  costs at 10% IRR — the plant can afford to *pay* for waste plastic.
- Discuss the negative GWP: displacement credits from fuels, chemicals, and
  organics exceed all process emissions.

**Key table:** Summary of baseline TEA and LCA metrics (Table 1 in main
paper).

**SI cross-refs:** S3 (TEA assumptions), S4 (LCA methodology), S5 (baseline
prices).

---

## 3.3  Multi-Objective Optimization — Pareto Frontiers

**Purpose:** Present the trade-off between minimum selling price (MSP) and
global warming potential (GWP) for the baseline price scenario.

**Content:**
- Describe the 4-variable Nelder-Mead optimization (split_TOD, split_CP,
  split_CPY, split_HC) with the weighted-sum objective
  (0.5 × MSP_norm + 0.5 × (−GWP_norm)).
- Show the Pareto scatter for the baseline scenario as **Figure 3**
  (`pareto_scatter_baseline.png`).
- Report the optimal split fractions: x₁ = 0.342, x₂ = 0.506, x₃ = 0.492,
  x₄ = 0.526 (Table S20).
- Interpret the near-equal CPY/PLASMA and HC/FCC splits: the optimizer
  balances organic revenue (PLASMA) against lower capital cost (CPY) and
  balances diesel selectivity (HC) against lower hydrogen demand (FCC).

**Key figure:** Pareto frontier — baseline (Figure 3).

**SI cross-refs:** S6.1–S6.3 (methodology), S6.4 (optimal splits).

---

## 3.4  Scenario Analysis — Effect of Product Prices

**Purpose:** Show how the optimal superstructure configuration shifts under
four distinct market scenarios (baseline, high_fuel, high_chem, high_organics).

**Content:**
- Overlay or facet Pareto frontiers for all four scenarios as **Figure 4**
  (`pareto_scatter_by_scenario.png` or `pareto_by_scenario.png`).
- Compare optimal splits across scenarios (Table 2 — condensed from
  Table S20):
  - baseline / high_fuel / high_chem converge to similar balanced splits.
  - high_organics shifts to 83.7% CPY+PLASMA, 95% PLASMA, 79.1% HC — a
    PLASMA-dominant regime.
- Compare TEA outcomes (Table 3 — condensed from Table S21):
  - Three scenarios achieve negative MSP (profitable at zero feedstock cost).
  - high_organics: MSP ≈ +$0.009/kg (the plant must charge a small gate
    fee to waste suppliers despite $105 M/yr sales) because non-organic
    products are priced LOW and PLASMA capex/utilities are high.
- Compare LCA outcomes:
  - All scenarios are net-negative GWP.
  - high_organics achieves the deepest GWP reduction (−0.876 kg CO₂-eq/kg)
    because oxygenated PLASMA products displace emission-intensive
    conventional chemical production.
  - high_organics also achieves a negative carbon abatement cost
    (−$0.46/kg CO₂-eq): CO₂ reduction with net revenue.
- Revenue breakdown by product group (Table 4 — from Table S23): discuss the
  dominance of organics in high_organics ($92.5 M, 91.7% of total) vs.
  balanced diversification in baseline.

**Key figures:** Pareto by scenario (Figure 4); revenue breakdown bar chart
(Figure 5 — to be generated).

**SI cross-refs:** S5 (price scenarios), S6.4–S6.9 (full results).

---

## 3.5  Sensitivity & Contour Analysis

**Purpose:** Map the objective landscape around the optimum to identify the
most influential decision variables and assess operational flexibility.

**Content:**
- Describe the 12 × 12 pairwise sweep methodology (6 pairs × 3 objectives =
  18 subplots).
- Show the composite contour figure as **Figure 6** (`contours.png`).
- Highlight key findings:
  1. **split_CPY (CPY vs. PLASMA) is the dominant lever.** Moving toward
     PLASMA simultaneously improves MSP and GWP when organic prices are
     favorable.
  2. **split_TOD (feed allocation) is moderately influential.** Shifting more
     feed to CPY+PLASMA reduces MSP and GWP.
  3. **split_CP (TOD vs. CP) is the least influential variable.** TOD and CP
     produce similar fuel-range products with comparable economics.
  4. **split_HC (HC vs. FCC) shows mild preference for HC** due to higher
     diesel selectivity, partially offset by hydrogen cost.
  5. **Flat landscapes near the baseline optimum** indicate operational
     flexibility — small deviations from optimal splits have minimal impact.
  6. **Non-convex regions** at extreme splits (>0.90 or <0.10) where one
     pathway receives negligible feed.

**Key figure:** Contour plots (Figure 6 — 18-panel composite).

**SI cross-refs:** S7 (full contour methodology and discussion).

---

## 3.6  Comparison with Literature

**Purpose:** Contextualize the superstructure results against published
single-technology studies.

**Content:**
- Compare MSP to published waste-plastic pyrolysis economics:
  - Conventional pyrolysis-only plants typically report MSP of $0.05–$0.30/kg
    (positive tipping fee required).
  - The superstructure achieves negative MSP (−$0.52/kg baseline) by
    diversifying the product portfolio across fuels, chemicals, and organics.
- Compare GWP to published LCA studies:
  - Single-pathway pyrolysis GWP is typically −0.1 to −0.3 kg CO₂-eq/kg.
  - The superstructure matches (baseline, −0.31) or exceeds (high_organics,
    −0.88) these benchmarks.
- Discuss the value of the superstructure approach: rather than committing to
  one technology, the flexible multi-pathway design adapts to market
  conditions.
- Acknowledge limitations:
  - ML model accuracy (moderate R² for some outputs).
  - Fixed feedstock composition (US MSW average — real feeds vary).
  - Scope of LCA (cradle-to-gate, no transportation or end-of-life).
  - Nelder-Mead may find local, not global, optima.

---

## Figure & Table Summary for the Main Paper

| # | Type | Description | Source File |
|---|------|-------------|-------------|
| Figure 1 | PFD | Superstructure process flow diagram | `system_diagram_thorough.png` |
| Figure 2 | Parity | ML model parity plots (8 panels) | `machine_learning/plots/parity_*.png` |
| Figure 3 | Scatter | Pareto frontier — baseline scenario | `pareto_scatter_baseline.png` |
| Figure 4 | Scatter | Pareto frontiers — all four scenarios | `pareto_scatter_by_scenario.png` |
| Figure 5 | Bar | Revenue breakdown by product group | *(to be generated)* |
| Figure 6 | Contour | Sensitivity contour plots (18 panels) | `contours.png` |
| Table 1 | Data | Baseline TEA & LCA summary | SI Tables S21, S22 |
| Table 2 | Data | Optimal split fractions by scenario | SI Table S20 |
| Table 3 | Data | TEA & LCA comparison across scenarios | SI Tables S21, S22 |
| Table 4 | Data | Annual sales by product group | SI Table S23 |
