# Superstructure System

Superstructure optimization of a waste plastic (HDPE) recycling process. Evaluates combinations of upstream pyrolysis technologies and downstream separation/upgrading to maximize profit while minimizing environmental impact.

## Architecture

```
HDPE Feed (250 tpd)
    |
Splitter1 (CP+TOD vs CPY+PLASMA)
   /              \
Splitter3        Splitter2
(TOD vs CP)      (CPY vs PLASMA)
 /     \           /       \
TOD     CP       CPY     PLASMA
 \     /        (full)   (full)
 Mixer
   |
DISTILLATION
   |
Wax -> WaxSplitter -> HC + FCC
```

### Upstream Technologies
- **TOD** (`TOD.py`) - Thermal oxodegradation (autothermal pyrolysis with O2)
- **CP** (`CP.py`) - Conventional pyrolysis (thermal, inert N2 atmosphere)
- **CPY** (`CPY.py`) - Catalytic pyrolysis (zeolite catalyst, aromatics-rich output)
- **PLASMA** (`PLASMA.py`) - Plasma pyrolysis (electrical energy input)

### Downstream Technologies
- **DISTILLATION** (`DISTILLATION.py`) - Fractional distillation of pyrolysis oil
- **HC** (`HC.py`) - Hydrocracking of wax fraction
- **FCC** (`FCC.py`) - Fluid catalytic cracking of wax fraction

### Supporting Modules
- `_compounds.py` - Unified chemical definitions and thermo setup
- `_tea.py` - Techno-economic analysis (TEA) configuration
- `_lca.py` - Life cycle assessment (GWP calculation)
- `units/` - Custom BioSTEAM unit operations
- `machine_learning/` - ML pyrolysis yield prediction model
- `SUPERSTRUCTURE.py` - Builds the integrated system and provides `evaluate()`

## Requirements

Python 3.12 is required. Install dependencies:

```bash
pip install biosteam==2.51.3 thermosteam pyomo scipy numpy torch
```

### Key Package Versions
| Package | Version |
|---------|---------|
| Python | 3.12 |
| biosteam | 2.51.3 |
| thermosteam | 0.51.2 |
| pyomo | 6.9.5 |
| scipy | 1.15.2 |
| numpy | 1.26.4 |
| torch | 2.10.0 |

## How to Run

### Full Optimization

From the project root directory:

```bash
python3.12 -m system.main
```

This runs a multi-objective optimization (NPV + GWP) over 4 split variables:
- `split_TOD` - Fraction of feed to CP+TOD (vs CPY+PLASMA)
- `split_CP` - Fraction of CP+TOD stream to TOD (vs CP)
- `split_CPY` - Fraction of remaining feed to CPY (vs PLASMA)
- `split_HC` - Fraction of wax to HC (vs FCC)

Configuration is set at the top of `main.py`:
- `capacity_tpd` - Plant capacity in tonnes per day (default: 250)
- `maxiter` - Maximum optimizer iterations (default: 50)
- `weight_NPV` - Weight for NPV objective, 0-1 (default: 0.5)

### Single Evaluation

```python
from system.SUPERSTRUCTURE import evaluate

result = evaluate(split_TOD=0.34, split_CP=0.50, split_CPY=0.50, split_HC=0.50)
print(f"NPV: ${result['NPV']:,.0f}")
print(f"GWP: {result['GWP']:,.1f} kg CO2-eq/hr")
```

### Individual Pathways

```python
from system.SUPERSTRUCTURE import build_pathway

system, products = build_pathway('TOD_DIST', capacity_tpd=250)
system.simulate()
```

Available pathways: `TOD_DIST`, `PLASMA`, `CPY`, `SUPERSTRUCTURE`.
