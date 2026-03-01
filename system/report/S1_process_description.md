# S1. Process Description & Superstructure Topology

## S1.1 Superstructure Architecture

The superstructure integrates four upstream plastic conversion technologies with three downstream separation/upgrading processes through a network of four optimization splitters. The process flow diagram is shown in Figure S1.

![Figure S1. Superstructure process flow diagram.](../system_diagram_thorough.png)

```
HDPE/LDPE/PP/PS Feed (250 tpd)
        |
   Splitter1 (split_TOD: fraction to CP+TOD)
      /                    \
  Splitter3              Splitter2 (split_CPY: fraction to CPY)
  (split_CP:               /              \
   fraction to TOD)      CPY             PLASMA
    /       \          (catalytic)      (plasma)
  TOD       CP
   \       /
   Mixer (SS_mx_pyro)
      |
  DISTILLATION
      |
  Wax -> WaxSplitter (split_HC: fraction to HC)
           /          \
         HC           FCC
```

Product streams are merged across pathways:
- **Naphtha**: DISTILLATION + HC + FCC
- **Diesel**: DISTILLATION + HC + FCC
- **Wax**: HC + FCC (residual heavy fraction)
- **BTX**: CPY (Benzene + Toluene + Xylene)
- **Hydrogen**: HC + FCC (excess H2)
- **Organics**: PLASMA (Paraffins, Carbonyls, Olefins, Alcohols, Acids, C30)

A turbogenerator combusts combined flue gas from CPY, PLASMA, and FCC to generate electricity.

## S1.2 Feed Composition

**Table S1.** US average MSW plastic feed composition (pyrolysis-eligible fraction).

| Resin | Weight Fraction | Raw US MSW (wt%) | Notes |
|-------|----------------|-------------------|-------|
| LDPE/LLDPE | 0.442 (44.2%) | 34% | Bags, film, flexible packaging |
| PP | 0.234 (23.4%) | 18% | Containers, automotive parts |
| HDPE | 0.220 (22.0%) | 17% | Bottles, jugs |
| PS | 0.104 (10.4%) | 8% | Foam, disposables |

PET (12%), PVC (5%), and other (6%) are excluded from the pyrolysis feed. PET produces oxygenated decomposition products incompatible with the hydrocarbon-focused separation train; PVC generates corrosive HCl. The remaining 77 wt% is renormalized to 100%.

**Sources:** Milbrandt et al. (2022), *Resources, Conservation and Recycling*, 183, 106363; National Academies / ACC (2021); Geyer et al. (2017), *Science Advances*, 3(7), e1700782.

**Feedstock price:** $0.02/kg waste plastic.

**Plant capacity:** 250 tonnes per day (10,417 kg/hr).

## S1.3 Upstream Technology Descriptions

### S1.3.1 Thermal Oxodegradation (TOD)

TOD operates via autothermal pyrolysis using a fluidized bed reactor with oxygen co-feed. The exothermic oxidation reactions provide the heat needed for thermal decomposition, eliminating the need for an external furnace.

**Table S2.** TOD operating conditions.

| Parameter | Value |
|-----------|-------|
| Reactor type | RYield (fixed yields) |
| Temperature | 600 °C (873.15 K) |
| Pressure | 1 atm |
| O2 equivalence ratio | 7% of feed mass |
| Fluidizing gas | N2, 15 kg/hr |
| Reactor cost scaling factor | 0.4 |

**Unit operations:** Feed_handling -> Grinder -> Screen (with recycle) -> Mixer (feed + O2 + N2) -> RYield Reactor -> Cyclone (99% efficiency) -> Cooler (10 °C)

**Table S3.** TOD fixed product yields (mass fraction of feedstock).

| Product | Yield (wt/wt) |
|---------|---------------|
| Ash | 0.003 |
| CO | 0.00833 |
| CO2 | 0.06517 |
| H2 | 0.000270 |
| CH4 | 0.00444 |
| C2H4 | 0.02633 |
| C3H8 | 0.01666 |
| C4H8 | 0.01622 |
| C10H22 (naphtha) | 0.0769 |
| C14H30 (diesel) | 0.0431 |
| C24H50 (wax) | 0.3735 |
| C40H82 (heavy wax) | 0.3364 |
| O2 (consumed) | 0.00257 |
| **Total** | **~97.0%** |

The mass balance closure is 90.4% (parameter `wt_closure`); the remainder is attributed to uncharacterized light species.

### S1.3.2 Conventional Pyrolysis (CP)

CP uses thermal pyrolysis under inert N2 atmosphere (no oxygen feed). Product yields are predicted by the PyrolysisNet ML model with `reactor_type='thermal'`.

| Parameter | Value |
|-----------|-------|
| Reactor type | Pyrolyzer (ML-predicted yields) |
| Temperature | 500 °C (773.15 K) |
| Pressure | 1 atm |
| Vapor residence time | 1.0 s |
| ML reactor type | `thermal` (base model, no correction) |
| Fluidizing gas | N2, 15 kg/hr |

**Unit operations:** Feed_handling -> Grinder -> Screen (with recycle) -> Mixer (feed + N2) -> Pyrolyzer -> Cyclone (99%) -> Cooler (10 °C)

### S1.3.3 Catalytic Pyrolysis (CPY)

CPY uses zeolite-catalyzed pyrolysis to produce aromatics-rich products. Product yields are predicted by PyrolysisNet with `reactor_type='catalytic'`, which applies a linear additive correction derived from the aston.xlsx literature database.

| Parameter | Value |
|-----------|-------|
| Reactor type | Pyrolyzer (ML + catalytic correction) |
| Temperature | 500 °C (773.15 K) |
| Pressure | 1 atm |
| Vapor residence time | 1.0 s |
| ML reactor type | `catalytic` |
| O2 equivalence ratio | 7% |
| Fluidizing gas | N2, 15 kg/hr |

**Unit operations:** Feed_handling -> Grinder -> Screen (with recycle) -> Mixer -> Pyrolyzer -> Cyclone -> Cooler (10 °C) -> Flash F0 (10 °C) -> Pump -> Flash F1 (285 K) -> D1-D4 aromatics distillation train -> Product coolers

**CPY Distillation train:**
- D1: BinaryDistillation, LHK = C6H6/C7H8 (Benzene separation)
- D2: BinaryDistillation, LHK = C7H8/C8H18, Lr=0.95, Hr=0.95 (Toluene separation)
- D3: BinaryDistillation, LHK = C8H18/C8H10 (Aromatics separation)
- D4: BinaryDistillation, LHK = C8H10/PS, Lr=0.95, Hr=0.95 (Xylene separation)

All CPY columns use `check_LHK=False` and fixed purchase costs of $320,258 per column.

**Products:** Benzene, Toluene, Aromatics (other), Xylene, FlueGas (from F0 vapor).

### S1.3.4 Plasma Pyrolysis (PLASMA)

PLASMA converts waste plastic via non-equilibrium CO2 plasma, producing oxygenated products (alcohols, acids, carbonyls) alongside conventional hydrocarbons. CO2 is incorporated into products, causing total yields to exceed 100% of feedstock mass (CO2 factor ~1.298).

| Parameter | Value |
|-----------|-------|
| Reactor type | PlasmaReactor (ML-predicted yields) |
| Temperature | 400 °C (reactor); ML queried at 450 °C virtual temperature |
| CO2 feed ratio | 0.30 kg/kg plastic |
| O2 feed ratio | 0.05 kg/kg plastic |
| Vapor residence time | 20.0 s |
| Power consumption | 0.111 kW per kg/hr feed |
| CO2 factor | 1.298 (total yield/feedstock mass) |

**Reference:** Radhakrishnan et al. (2024), *Green Chem.*, 26, 9156-9175 (Case G: CO2 plasma, tR = 20 s).

**Unit operations:** Mixer (feed + CO2 + O2 + recycle) -> PlasmaReactor -> Condenser (32 °C) -> Flash (200 °C, heavy/light split) -> Heavy separation train -> Light recovery train (compression to -78 °C) -> Alcohol/Acid/Carbonyl fractionation -> Steam methane reforming -> Hydrocracking of C30+ fraction -> Recycle loop (90% recycle split)

**Products:** Paraffins (C18H38), Carbonyls (C14H22O), Olefins (light hydrocarbons), Alcohols (1-Dodecanol), Acids (fatty acid), C30 (heavy wax).

## S1.4 Downstream Technology Descriptions

### S1.4.1 Fractional Distillation (DISTILLATION)

Shared separation train for the combined TOD + CP pyrolysis product. Separates cooled crude vapor into six product fractions.

**Table S4.** Distillation system specifications.

| Unit | Type | Separation | Key Details |
|------|------|------------|-------------|
| F1 (Condenser) | Flash | Initial condensation | T = 10 °C, P = 1 atm |
| H7 | Heater | Re-heat condensate | T = 150 °C |
| F3 (FlashSep) | Flash | Gas/liquid split | T = 0 °C, P = 1.01 atm |
| K1, K2 | Compressors | Gas compression | 2 atm, then 7 atm; eta = 0.8 |
| F2 | Flash | Deep cooling | T = -110 °C, P = 7 atm |
| D1 (De-ethanizer) | BinaryDistillation | C2H4/C3H8 | y_top = 0.99, x_bot = 0.01 |
| D2 (Depropanizer) | BinaryDistillation | C3H8/C4H8 | y_top = 0.99, x_bot = 0.01 |
| D3 (Debutanizer) | Tb-cutoff Splitter | Tb < Tb(C10H22) | Butene/heavier cut |
| D4 (NaphthaSplitter) | Tb-cutoff Splitter | Tb < Tb(C14H30) | Naphtha/diesel cut |
| D5 (DieselSplitter) | Tb-cutoff Splitter | Tb < Tb(C24H50) | Diesel/wax cut |

D1 and D2 use rigorous BinaryDistillation because their LHK compounds (C2H4/C3H8, C3H8/C4H8) are always present in the compressed-gas path. D3, D4, and D5 use boiling-point-based component splitting (Tb-cutoff Splitters) for robustness against variable feed compositions. F3 liquid (0 °C condensate) is routed through D4 for proper naphtha/diesel/wax classification.

**Products:** Ethylene, Propylene, Butene, Naphtha, Diesel, Wax. NCG recycle stream is returned upstream.

### S1.4.2 Hydrocracking (HC)

Takes the wax fraction from DISTILLATION and cracks it into lighter fuel-range products using hydrogen.

| Parameter | Value |
|-----------|-------|
| H2 feed | 2% of plant capacity (5 tpd at 250 tpd) |
| H2 compressor pressure | 89.7 atm |
| Catalyst | Zeolite, 200 kg/hr, $15.5/lb |
| Reactor temperature | 300 °C |
| Reactor cost basis | $30M at 2,250 bbl/day (CE = 468.2) |

Post-HC separation uses the same Tb-cutoff Splitter approach:
- Naphtha cut: Tb < Tb(C14H30)
- Diesel cut: Tb < Tb(C24H50)
- Residual: Wax

**Products:** Naphtha, Diesel, Wax (residual), Excess H2 (99% split).

### S1.4.3 Fluid Catalytic Cracking (FCC)

Takes the wax fraction and catalytically cracks it into lighter products via a riser-regenerator system.

| Parameter | Value |
|-----------|-------|
| Catalyst | Zeolite, 200 kg/hr, $15.5/lb |
| Catalyst-to-feed ratio | 5:1 |
| Feed pressure | 2 atm |
| Regenerator pressure | 2.79 atm |
| Product loss | 0.5% |

FCC uses `force_reaction` to handle over-specified parallel conversions (C11H24 reactions sum to >100% individual conversion). 24 parallel reactions crack C11-C40 hydrocarbons into C2-C10 products with aromatization side reactions.

Post-FCC separation: H2 split (99%) -> H2O split (99%) -> Naphtha (Tb < C14H30) -> Diesel (Tb < C24H50) -> Wax.

**Products:** Naphtha, Diesel, Wax, Excess H2, FlueGas (from regenerator combustion).

## S1.5 Equipment Summary

**Table S5.** Equipment list by pathway.

| Pathway | Unit Count | Key Equipment |
|---------|-----------|---------------|
| TOD | 7 | Feed_handling, Grinder, Screen, Mixer (x2), RYield Reactor, Cyclone, Cooler |
| CP | 7 | Feed_handling, Grinder, Screen, Mixer (x2), Pyrolyzer, Cyclone, Cooler |
| CPY | 15 | Feed_handling, Grinder, Screen, Mixer, Pyrolyzer, Cyclone, Cooler, Flash (x2), Pump, BinaryDistillation (x4), Product coolers (x4) |
| PLASMA | 30+ | PlasmaReactor, Flash (x3), ShortcutColumn (x8), Compressor (x3), HXutility (x10+), Pump (x3), MixTank (x2), Splitter (x2), Mixer (x3) |
| DISTILLATION | 18 | Flash (x3), Compressor (x3), Pump, Heater (x4), BinaryDistillation (x2), Splitter (x5), Mixer (x4) |
| HC | 6 | Compressor, Hydrocrack Reactor, MixTank, Splitter (x3), Mixer (x2) |
| FCC | 8 | FluidizedCatalyticCracking, MixTank, Splitter (x4), Mixer (x2) |
| Integration | 8 | Feed Splitters (x3), Wax Splitter, Product Mixers (x5), Turbogenerator |
