# S3. Techno-Economic Analysis

## S3.1 TEA Framework

The techno-economic analysis uses a discounted cash flow rate of return (DCFROR) methodology implemented in BioSTEAM 2.51.3. The minimum selling price (MSP) of feedstock is calculated as the breakeven feedstock price at which the net present value equals zero at the specified internal rate of return.

## S3.2 Financial Assumptions

**Table S13.** TEA financial parameters.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Internal rate of return (IRR) | 10% | Target return on equity |
| Plant life | 20 years | 2020-2040 |
| Depreciation | MACRS 7-year | Modified Accelerated Cost Recovery System |
| Income tax rate | 21% | US federal corporate rate |
| Operating days | 333 days/year | 91.2% availability |
| Operating hours | 7,992 hr/year | 333 x 24 |
| Lang factor | 5.05 | Total installed cost / purchased equipment cost |
| Construction schedule | 40% / 60% | Year 1 / Year 2 |
| Working capital | 5% of FCI | Working capital over fixed capital investment |
| Debt fraction | 40% | Fraction of capital financed by debt |
| Loan term | 10 years | |
| Loan interest rate | 7% | |
| Startup period | 0 months | No startup ramp assumed |

## S3.3 Capital Cost Methodology

The total installed equipment cost is calculated as:

$$\text{Installed Cost} = \text{Purchased Equipment Cost} \times \text{Lang Factor}$$

Individual equipment costs are scaled from reference sizes using the six-tenths rule:

$$C = C_{\text{ref}} \times \left(\frac{S}{S_{\text{ref}}}\right)^n \times \frac{\text{CE}}{\text{CE}_{\text{ref}}}$$

where C is the estimated cost, S is the capacity, n is the scaling exponent, and CE is the Chemical Engineering Plant Cost Index.

Key equipment cost references:

| Equipment | Reference Cost | Reference Size | Exponent | CE |
|-----------|---------------|----------------|----------|-----|
| Feed handling (conveyor + hopper) | $534,114 | 500 tpd | 0.6 | 596.2 |
| Grinder | $616,711 | 500 tpd | 0.6 | 550.8 |
| Screen | $39,934 | 500 tpd | 0.6 | 550.8 |
| Cyclone | $982,511 | 500 tpd | 0.6 | 567.5 |
| RYield Reactor (TOD) | $8,766,342 | 500 tpd | 0.6 | 567.5 |
| Hydrocracker | $30,000,000 | 2,250 bbl/d | 0.65 | 468.2 |
| Plasma Reactor | $20,000,000 | 200,000 kg/d | 0.7 | - |
| Turbogenerator | $600/kW | variable | 1.0 | - |

## S3.4 Operating Cost Breakdown

**Table S14.** Fixed operating cost factors (fraction of FCI unless noted).

| Cost Category | Factor | Basis |
|---------------|--------|-------|
| Property tax | 0.1% of FCI | |
| Property insurance | 0.5% of FCI | |
| Maintenance | 0.3% of FCI | |
| Administration | 0.5% of FCI | |
| Fringe benefits | 40% of labor cost | Health, retirement, etc. |
| Supplies | 20% of labor cost | Consumables, office |

Fixed operating cost (FOC):

$$\text{FOC} = \text{FCI} \times (\text{property tax} + \text{insurance} + \text{maintenance} + \text{administration}) + \text{labor} \times (1 + \text{fringe} + \text{supplies})$$

## S3.5 Labor Cost

Labor costs are scaled from a 2,000 tpd reference plant (Dutta et al., 2002) to the 250 tpd plant capacity using linear scaling.

**Table S15.** Labor cost breakdown (2,000 tpd reference basis).

| Position | Annual Salary ($) | Number of Staff | Total ($) |
|----------|------------------|----------------|-----------|
| Plant Manager | 159,000 | 1 | 159,000 |
| Plant Engineer | 94,000 | 1 | 94,000 |
| Maintenance Supervisor | 87,000 | 1 | 87,000 |
| Maintenance Technician | 62,000 | 6 | 372,000 |
| Lab Manager | 80,000 | 1 | 80,000 |
| Lab Technician | 58,000 | 1 | 58,000 |
| Shift Supervisor | 80,000 | 3 | 240,000 |
| Shift Operators | 62,000 | 12 | 744,000 |
| Yard Employees | 36,000 | 4 | 144,000 |
| Clerks & Secretaries | 43,000 | 1 | 43,000 |
| General Manager | 188,000 | 0 | 0 |
| **Total (2,000 tpd)** | | **31** | **$2,021,000** |
| **Scaled to 250 tpd** | | | **$252,625** |

Scaling factor: 250 / 2,000 = 0.125.

**Source:** Dutta (2002), adjusted using US Bureau of Labor Statistics data (http://data.bls.gov/cgi-bin/srgate). Staffing numbers from Yadav et al.

## S3.6 MSP Calculation

The minimum selling price (MSP) of feedstock is determined using BioSTEAM's `solve_price()` method, which iterates on the feedstock price until NPV = 0 at the specified IRR (10%).

A negative MSP indicates the plant is profitable at zero feedstock cost and can afford to pay for waste plastic intake (i.e., the plant generates a net revenue even without charging a tipping fee). A positive MSP indicates a tipping fee is required to achieve the target IRR.

## S3.7 Utility Costs

Utility costs are computed from BioSTEAM's built-in utility agent pricing:
- **Electricity:** Medium voltage grid electricity
- **Heating:** High-temperature steam (1000 K), hot water (75 °C)
- **Cooling:** Ammonia refrigerant (0 °C) for sub-ambient cooling
- **Heat transfer price:** $1.32 x 10^-5 per kJ
