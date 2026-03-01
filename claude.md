This project is a superstructure optimization of a waste plastic (HDPE) recycling process. The goal is to determine the optimal combination of technologies and operating conditions to maximize profit while minimizing environmental impact. The project is implemented in Python 3.12 using BioSTEAM 2.51.3 for process simulation and Pyomo/scipy for optimization.

All modular code lives in the `system/` folder. Do not modify files in any other folders.

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

### Upstream Technologies (4 pathways)
- **TOD** (`TOD.py`) - Thermal oxodegradation with O2, uses RYield reactor with fixed yields
- **CP** (`CP.py`) - Conventional thermal pyrolysis under inert N2, uses Pyrolyzer with ML-predicted yields (`reactor_type='thermal'`)
- **CPY** (`CPY.py`) - Catalytic pyrolysis with zeolite catalyst, aromatics-rich output, uses Pyrolyzer (`reactor_type='catalytic'`)
- **PLASMA** (`PLASMA.py`) - Plasma pyrolysis with electrical energy input, uses PlasmaReactor

### Downstream Technologies
- **DISTILLATION** (`DISTILLATION.py`) - Fractional distillation of merged TOD+CP pyrolysis oil into ethylene, propylene, butene, naphtha, diesel, wax
- **HC** (`HC.py`) - Hydrocracking of wax fraction
- **FCC** (`FCC.py`) - Fluid catalytic cracking of wax fraction (uses `force_reaction` to handle over-specified parallel conversions)

### Supporting Modules
- `_compounds.py` - Unified chemical definitions and thermo setup via `tmo.settings.set_thermo()`
- `_tea.py` - Techno-economic analysis configuration
- `_lca.py` - Life cycle assessment (GWP calculation)
- `units/__init__.py` - Custom BioSTEAM unit operations (Feed_handling, Grinder, Screen, RYield, Cyclone, Compressor, Hydrocrack, FluidizedCatalyticCracking, PlasmaReactor, Pyrolyzer, Turbogenerator)
- `machine_learning/` - ML pyrolysis yield prediction model (PyrolysisNet)

### Integration
- `SUPERSTRUCTURE.py` - Builds the integrated system with 4 optimization split variables, TEA, and `evaluate()` function
- `main.py` - Runs multi-objective optimization (NPV + GWP) via scipy Nelder-Mead over 4 splits: `split_TOD`, `split_CP`, `split_CPY`, `split_HC`

## Optimization Variables

| Variable | Description | Bounds |
|----------|-------------|--------|
| `split_TOD` | Fraction of feed to CP+TOD (rest to CPY+PLASMA) | 0.05 - 0.95 |
| `split_CP` | Fraction of CP+TOD stream to TOD (rest to CP) | 0.05 - 0.95 |
| `split_CPY` | Fraction of remaining feed to CPY (rest to PLASMA) | 0.05 - 0.95 |
| `split_HC` | Fraction of wax to HC (rest to FCC) | 0.05 - 0.95 |

## How to Run

From the project root:
```bash
python3.12 -m system.main
```

## Known Issues / Notes
- C8H16 must use `search_ID='1-octene'` (formula lookup resolves to polybutene with broken Hvap)
- FCC reactions use `force_reaction` because C11H24 parallel reaction conversions sum to >100%
- Always set `check_LHK = False` on BinaryDistillation columns (unified chemical set triggers intermediate volatile errors)
- C12H16 must `copy_models_from(C10H8)` and set `Tb=493` before thermo compilation
- Sfus must be fixed both before and after `set_thermo()` compilation (see `_compounds.py`)
