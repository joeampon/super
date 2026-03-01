# HDPE Superstructure Optimization

Multi-objective optimization of a waste-plastic (HDPE) recycling superstructure using BioSTEAM, Pyomo, and SciPy.

## Download to Your Local Machine

### Option A — Git Clone (recommended)

1. Install [Git](https://git-scm.com/downloads) if you don't already have it.
2. Open a terminal (Mac/Linux) or **Git Bash** / **Command Prompt** (Windows).
3. Run:

```bash
git clone https://github.com/joeampon/super.git
cd super
```

### Option B — Download ZIP (no Git required)

1. Go to <https://github.com/joeampon/super>.
2. Click the green **Code** button → **Download ZIP**.
3. Extract the ZIP file to a folder on your desktop (e.g., `~/Desktop/super`).
4. Open a terminal and navigate into the folder:

```bash
cd ~/Desktop/super
```

## Setup

**Python 3.12** is required.

```bash
# Create a virtual environment (recommended)
python3.12 -m venv .venv

# Activate it
# macOS / Linux:
source .venv/bin/activate
# Windows (Command Prompt):
.venv\Scripts\activate

# Install dependencies
pip install biosteam==2.51.3 thermosteam pyomo scipy numpy torch matplotlib
```

## Quick Start

```bash
# Run the full multi-objective optimization (from the project root)
python3.12 -m system.main
```

Or evaluate a single configuration in Python:

```python
from system.SUPERSTRUCTURE import evaluate

result = evaluate(split_TOD=0.34, split_CP=0.50, split_CPY=0.50, split_HC=0.50)
print(f"NPV: ${result['NPV']:,.0f}")
print(f"GWP: {result['GWP']:,.1f} kg CO2-eq/hr")
```

See [`system/README.md`](system/README.md) for full architecture details, optimization variables, and individual pathway usage.
