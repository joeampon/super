# Methods — Section Structure

This document outlines the recommended structure for the Methods section
(Section 2) of the main paper manuscript.  Each subsection lists its purpose,
the key equations/figures/tables to include, and cross-references to the
Supporting Information (SI) where extended data reside.

> **Current status.**  The `system/report/` folder contains detailed SI
> sections (S1–S7) and a Results & Discussion outline
> (`results_section_structure.md`), but no Methods section for the main
> manuscript body.  This file fills that gap.

---

## 2.1  Superstructure Formulation

**Purpose:** Define the topology, feedstock basis, and decision variables that
the optimizer manipulates.

**Content:**
- Present the superstructure process flow diagram (**Figure 1**,
  `system_diagram_thorough.png`): four upstream conversion technologies (TOD,
  CP, CPY, PLASMA) connected through three feed splitters, merging into shared
  downstream separation and upgrading (DISTILLATION → HC / FCC).
- Feedstock: 250 tpd US-average MSW plastic waste.  After excluding
  PET, PVC, and other non-pyrolysable resins, the pyrolysis-eligible fraction
  is renormalised to HDPE 22.0 / LDPE 44.2 / PP 23.4 / PS 10.4 wt%
  (summing to 100%).
- Define the four continuous decision variables that control the superstructure
  configuration:

| Variable | Symbol | Description | Bounds |
|----------|--------|-------------|--------|
| `split_TOD` | x₁ | Fraction of total feed routed to the CP + TOD branch (remainder to CPY + PLASMA branch) | 0.05–0.95 |
| `split_CP`  | x₂ | Fraction of the x₁ stream sent to TOD (remainder to CP) | 0.05–0.95 |
| `split_CPY` | x₃ | Fraction of the (1 − x₁) stream sent to CPY (remainder to PLASMA) | 0.05–0.95 |
| `split_HC`  | x₄ | Fraction of wax to HC (remainder to FCC) | 0.05–0.95 |

- Briefly state that downstream product streams merge across pathways:
  naphtha, diesel, and wax from DISTILLATION + HC + FCC; BTX from CPY;
  hydrogen from HC + FCC; oxygenated organics from PLASMA.  A turbogenerator
  combusts combined flue gas to generate electricity.

**Key figure:** Superstructure PFD (Figure 1).

**SI cross-refs:** S1 (full process description, equipment list, operating
conditions).

---

## 2.2  Machine-Learning Yield Prediction

**Purpose:** Describe PyrolysisNet — the surrogate model that replaces
conventional yield correlations for CP, CPY, and PLASMA.

**Content:**
- Architecture: feedforward neural network (5 → 64 → 128 → 64 → 8) with
  batch normalization, ReLU activation, and 10% dropout; sigmoid output scaled
  to 0–100 wt% (Table S6).
- Inputs: HDPE, LDPE, PP weight fractions (wt%), temperature (°C), and vapor
  residence time (s).
- Outputs: 8 product-category yields — Liquid, Gas, Solid, Gasoline-range,
  Diesel-range, Total aromatics, BTX, and Wax (>C21).
- Training: 566 literature pyrolysis experiments (aston.xlsx); Adam optimizer,
  masked-MSE loss with phase-balance and BTX constraints; early stopping at
  200 epochs patience (Table S7 for test-set R², MAE, RMSE).
- Reactor-type corrections: linear additive shifts calibrated to experimental
  data for TOD (Olafasakin et al., 2023), catalytic (aston.xlsx literature
  comparison), and plasma (Radhakrishnan et al., 2024, Case G).  For each
  product category *i* (i = 1 … 8):
  corrected_i(T) = base_i + α_i + β_i × T.
- Compound mapping: each ML output category is disaggregated into specific
  BioSTEAM compound IDs via fixed sub-distributions (Tables S8–S9); plasma
  uses a separate mapping that includes oxygenated surrogate compounds
  (Section S2.6).

**Key equation:** corrected_i(T) = base_i + α_i + β_i × T  (reactor-type
correction).

**SI cross-refs:** S2 (full architecture table, training config, correction
coefficients, parity plots, parametric sweeps).

---

## 2.3  Process Simulation

**Purpose:** Summarize how each upstream and downstream technology is modelled
in BioSTEAM 2.51.3.

**Content:**
- **BioSTEAM framework:** Steady-state simulation with a unified set of 35+
  chemical species (defined in `_compounds.py`); thermodynamic properties from
  NIST and Joback estimation.
- **Upstream technologies** (one paragraph each):
  - *TOD (Thermal Oxodegradation):* RYield reactor with fixed mass-fraction
    yields (Table S3); O₂ co-feed at 7 wt% equivalence ratio; 600 °C.
  - *CP (Conventional Pyrolysis):* Pyrolyzer with ML-predicted yields
    (`reactor_type = 'thermal'`); inert N₂ atmosphere; 500 °C.
  - *CPY (Catalytic Pyrolysis):* Pyrolyzer with ML + catalytic correction;
    zeolite catalyst; 500 °C; dedicated 4-column aromatics distillation train
    for BTX recovery.
  - *PLASMA (Plasma Pyrolysis):* PlasmaReactor with ML + plasma correction;
    CO₂ feed (0.30 kg/kg plastic); 400 °C reactor; 0.111 kW per kg/hr
    electrical input; product mass exceeds plastic feedstock alone due to
    CO₂ incorporation (total mass factor ≈ 1.30).
- **Downstream technologies** (one paragraph each):
  - *DISTILLATION:* Shared train for merged TOD + CP crude vapour.  Flash
    condensation → compression → deep cooling → de-ethanizer → depropanizer →
    boiling-point-cutoff splitters for naphtha / diesel / wax.
  - *Hydrocracking (HC):* Wax cracking with H₂ at 300 °C, 89.7 atm; product
    fractionation into naphtha / diesel / residual wax.
  - *Fluid Catalytic Cracking (FCC):* Zeolite-catalysed riser-regenerator
    with 24 parallel cracking reactions; 5:1 catalyst-to-feed ratio.

**SI cross-refs:** S1 (operating conditions tables, column specs, equipment
summary).

---

## 2.4  Techno-Economic Analysis

**Purpose:** Define the economic evaluation framework and the minimum selling
price metric.

**Content:**
- DCFROR methodology (BioSTEAM `solve_price`): iterate on the feedstock price
  until NPV = 0 at a 10% internal rate of return over a 20-year plant life.
- Key financial parameters (condensed from Table S13): 21% income tax, MACRS
  7-year depreciation, Lang factor 5.05, 333 operating days/yr, 40/60%
  construction schedule, 40% debt at 7% interest.
- Capital costs: purchased equipment costs scaled via the six-tenths rule and
  Chemical Engineering Plant Cost Index; total installed cost = PEC × Lang
  factor.
- Operating costs: utilities (electricity, steam, refrigeration), labor
  (scaled from a 2,000 tpd reference plant to 250 tpd), fixed charges (tax,
  insurance, maintenance, administration; Table S14–S15).
- MSP interpretation: a negative MSP means the plant is profitable at zero
  feedstock cost and can afford to *pay* for waste plastic intake.

**Key metric:** MSP ($/kg feed) — breakeven feedstock price at 10% IRR.

**SI cross-refs:** S3 (full financial assumptions, equipment cost references,
labor breakdown).

---

## 2.5  Life Cycle Assessment

**Purpose:** Define the environmental evaluation framework and the GWP metric.

**Content:**
- System boundary: cradle-to-gate; ecoinvent 3.x APOS; TRACI 2.1 impact
  categories (10 evaluated; GWP is the primary optimisation metric).
- Inputs: feedstock, natural gas, O₂, CO₂, catalysts, grid electricity,
  heating/cooling utilities.  Outputs: all product streams, flue-gas
  emissions.  Excluded: transportation, end-of-life, plant construction.
- Product credits via displacement: each product stream offsets the GWP of
  an equivalent mass of the conventional (fossil-derived) analogue
  (Table S16 for emission factors; Table S17 for stream-to-resource mapping).
- GWP equation (per kg feed):

  GWP_total = Σ (F_s × EF_s × m_s) + GWP_electricity + GWP_heat + GWP_FCC_offgas

  where F_s is stream mass flow, EF_s is the emission factor, and m_s is the
  multiplier (negative = product credit).
- Carbon abatement cost: CAC = net cost per kg feed / (−GWP per kg feed).
  A negative CAC indicates simultaneous emission reduction and net revenue.

**Key metrics:** GWP (kg CO₂-eq/kg feed), CAC ($/kg CO₂-eq).

**SI cross-refs:** S4 (full emission factor table, stream mapping,
electricity/heat/FCC GWP formulae).

---

## 2.6  Multi-Objective Optimization

**Purpose:** Describe the optimization formulation, solver, and price-scenario
design.

**Content:**
- **Objective function** — weighted-sum of normalized MSP and GWP:

  score = w_MSP × (MSP / MSP_ref) + w_GWP × (−GWP / GWP_ref)

  where MSP_ref and GWP_ref are reference values at the initial point
  (x₀ = [0.34, 0.50, 0.50, 0.50]) for each scenario, and
  w_MSP = w_GWP = 0.5.
- **Solver:** Scipy Nelder-Mead simplex (`scipy.optimize.minimize`) with
  adaptive step sizing; max 50 iterations; x-tolerance 0.01, f-tolerance
  0.001.  Bounds enforced via the `bounds` argument.
- **Price scenarios** (4 cases, Table S19):

| Scenario | Rule |
|----------|------|
| baseline | All products at baseline price |
| high_fuel | Fuels at HIGH; chemicals and organics at LOW |
| high_chem | Chemicals at HIGH; fuels and organics at LOW |
| high_organics | Organics at HIGH; fuels and chemicals at LOW |

- Each scenario recomputes MSP_ref and GWP_ref at x₀ so that the two
  objectives contribute equally at the starting point.
- **Sensitivity analysis:** 12 × 12 pairwise sweeps of all 6 variable pairs
  (remaining variables held at optimal values) for MSP, GWP, and CAC →
  18 contour subplots.  This maps the objective landscape and identifies
  dominant decision variables (Section 3.5).

**Key equation:** Weighted-sum objective.

**SI cross-refs:** S5 (product prices), S6.1–S6.3 (optimisation methodology),
S7 (contour sweep methodology).

---

## Figure & Table Summary for the Methods Section

| # | Type | Description | Source / SI Ref |
|---|------|-------------|-----------------|
| Figure 1 | PFD | Superstructure process flow diagram | `system_diagram_thorough.png` / S1 |
| Table 1 | Methods | Decision variables and bounds | S6.3 / `main.py` |
| Table 2 | Methods | Price scenarios (4 cases) | S5 / `_prices.py` |
| Eq. 1 | Equation | Reactor-type correction for ML yields | S2.7 |
| Eq. 2 | Equation | GWP calculation (displacement credits) | S4.5 |
| Eq. 3 | Equation | Weighted-sum multi-objective function | S6.2 |
