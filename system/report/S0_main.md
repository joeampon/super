# Supporting Information

## Superstructure Optimization of Waste Plastic Pyrolysis: Integrating Thermal, Catalytic, and Plasma Technologies with Machine Learning

**Authors:** [Author names]

**Affiliation:** [Department, University]

**Corresponding Author:** [Email]

---

## Abstract

This Supporting Information provides detailed documentation of the superstructure optimization framework for waste plastic recycling via pyrolysis. The integrated process considers four upstream conversion technologies (thermal oxodegradation, conventional pyrolysis, catalytic pyrolysis, and plasma pyrolysis) with shared downstream separation and upgrading (fractional distillation, hydrocracking, and fluid catalytic cracking). A feedforward neural network (PyrolysisNet) predicts product yields from feedstock composition and operating conditions. Multi-objective optimization (minimum selling price and global warming potential) is performed across four price scenarios using Nelder-Mead with a weighted-sum objective. Complete process descriptions, economic assumptions, environmental impact methodology, and optimization results are provided herein.

---

## Table of Contents

| Section | Title | Page |
|---------|-------|------|
| S1 | [Process Description & Superstructure Topology](S1_process_description.md) | - |
| S2 | [Machine Learning Model Development](S2_machine_learning.md) | - |
| S3 | [Techno-Economic Analysis](S3_tea.md) | - |
| S4 | [Life Cycle Assessment](S4_lca.md) | - |
| S5 | [Product Price Scenarios](S5_prices.md) | - |
| S6 | [Optimization Results](S6_optimization_results.md) | - |
| S7 | [Sensitivity & Contour Analysis](S7_sensitivity_contours.md) | - |

---

## List of Figures

| Figure | Description | Location |
|--------|-------------|----------|
| Figure S1 | Superstructure process flow diagram | `system_diagram_thorough.png` |
| Figure S2 | ML model parity plots (8 panels) | `machine_learning/plots/parity_*.png` |
| Figure S3 | Temperature sweep parametric study | `machine_learning/plots/temperature_sweep.png` |
| Figure S4 | Vapor residence time sweep | `machine_learning/plots/vrt_sweep.png` |
| Figure S5 | Feedstock composition sensitivity | `machine_learning/plots/composition_sweep.png` |
| Figure S6 | Phase distribution (stacked area) | `machine_learning/plots/phase_stacked.png` |
| Figure S7 | Reactor type comparison | `machine_learning/plots/reactor_comparison.png` |
| Figure S8 | Optimization contour plots (MSP, GWP, CAC) | `contours.png` |

## List of Tables

| Table | Description | Section |
|-------|-------------|---------|
| Table S1 | US MSW plastic feed composition | S1 |
| Table S2 | Upstream pathway operating conditions | S1 |
| Table S3 | TOD fixed product yields | S1 |
| Table S4 | Distillation column specifications | S1 |
| Table S5 | Equipment list by pathway | S1 |
| Table S6 | PyrolysisNet architecture | S2 |
| Table S7 | ML model performance metrics | S2 |
| Table S8 | Gas compound mapping | S2 |
| Table S9 | Liquid sub-category compound mapping | S2 |
| Table S10 | TOD correction coefficients | S2 |
| Table S11 | Catalytic correction coefficients | S2 |
| Table S12 | Plasma correction coefficients | S2 |
| Table S13 | TEA financial assumptions | S3 |
| Table S14 | Labor cost breakdown | S3 |
| Table S15 | Operating cost factors | S3 |
| Table S16 | LCA emission factors (GWP) | S4 |
| Table S17 | Stream-to-resource mapping | S4 |
| Table S18 | Product prices (low/baseline/high) | S5 |
| Table S19 | Scenario definitions | S5 |
| Table S20 | Optimal split fractions by scenario | S6 |
| Table S21 | TEA results by scenario | S6 |
| Table S22 | LCA results by scenario | S6 |
| Table S23 | Sales by product group | S6 |
| Table S24 | Organics revenue breakdown | S6 |
