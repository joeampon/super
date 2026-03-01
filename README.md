# super — Superstructure Optimization

Multi-objective optimization of a waste plastic (HDPE) recycling process, evaluating combinations of upstream pyrolysis technologies and downstream separation/upgrading to maximize profit while minimizing environmental impact.

---

## Download to Your Local Machine

**Option A — Git Clone (recommended)**

```bash
git clone https://github.com/joeampon/super.git
```

**Option B — Download ZIP**

Click the green **Code** button on [github.com/joeampon/super](https://github.com/joeampon/super) → **Download ZIP**, then extract to your Desktop.

---

## Setup

### 1. Create a Python 3.12 virtual environment

```bash
python3.12 -m venv venv
```

### 2. Activate it

**macOS / Linux**
```bash
source venv/bin/activate
```

**Windows**
```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install biosteam==2.51.3 thermosteam pyomo scipy numpy torch matplotlib
```

#### Key package versions

| Package     | Version  |
|-------------|----------|
| Python      | 3.12     |
| biosteam    | 2.51.3   |
| thermosteam | 0.51.2   |
| pyomo       | 6.9.5    |
| scipy       | 1.15.2   |
| numpy       | 1.26.4   |
| torch       | 2.10.0   |

---

## Quick Start

### Full optimization

Run the multi-objective optimization (MSP + GWP) across all four price scenarios from the project root:

```bash
python3.12 -m system.main
```

### Single-configuration evaluation

```python
from system.SUPERSTRUCTURE import evaluate

result = evaluate(split_TOD=0.34, split_CP=0.50, split_CPY=0.50, split_HC=0.50)
print(f"MSP: ${result['MSP']:.4f}/kg feed")
print(f"GWP: {result['GWP']:.4f} kg CO2-eq/kg feed")
```

The four split variables (each bounded 0.05–0.95):

| Variable    | Description                                      |
|-------------|--------------------------------------------------|
| `split_TOD` | Fraction of feed to CP+TOD (vs CPY+PLASMA)       |
| `split_CP`  | Fraction of CP+TOD stream to TOD (vs CP)         |
| `split_CPY` | Fraction of remaining feed to CPY (vs PLASMA)    |
| `split_HC`  | Fraction of wax to HC (vs FCC)                   |

For full architecture documentation see [system/README.md](system/README.md).

---

## Security

Store your OpenAI API key in a `.env` file — never hardcode it in source files:

```bash
OPENAI_API_KEY=your-key-here
```

Read it in code with:

```python
import os
api_key = os.environ.get("OPENAI_API_KEY")
```

The `.env` file is listed in `.gitignore` and will not be committed.
