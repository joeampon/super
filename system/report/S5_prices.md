# S5. Product Price Scenarios

## S5.1 Price Data

All prices are in $/kg, based on US Gulf Coast / North American market data from 2015-2025.

**Table S18.** Product prices by regime ($/kg).

| Product | Group | Low | Baseline | High | Sources |
|---------|-------|-----|----------|------|---------|
| Naphtha | Fuel | 0.25 | 0.55 | 0.80 | [1] |
| Diesel | Fuel | 0.27 | 0.70 | 1.00 | [2], [18] |
| Wax | Fuel | 0.70 | 1.00 | 1.50 | [3] |
| Ethylene | Chemical | 0.30 | 1.10 | 1.30 | [4] |
| Propylene | Chemical | 0.42 | 1.00 | 1.50 | [5], [6] |
| Butene | Chemical | 0.85 | 0.80 | 1.30 | [7] |
| BTX | Chemical | 0.50 | 0.90 | 1.10 | [8] |
| Aromatics | Chemical | 0.30 | 0.85 | 1.10 | [9] |
| Paraffins | Organic | 0.80 | 0.60 | 1.50 | [10] |
| Carbonyls | Organic | 0.50 | 0.50 | 2.40 | [11], [12] |
| Olefins | Organic | 0.90 | 0.85 | 2.00 | [13] |
| Alcohols | Organic | 0.35 | 0.50 | 0.69 | [14] |
| Acids | Organic | 0.45 | 0.35 | 1.90 | [15] |
| C30 | Organic | 0.45 | 0.25 | 1.00 | [17] |
| Hydrogen | Hydrogen | 1.00 | 2.50 | 2.50 | [16] |

**Price regime definitions:**
- **Low:** 2020 COVID demand destruction or 2015-2016 oil price collapse (WTI < $30/bbl)
- **Baseline:** Approximately the 2018-2019 pre-pandemic average
- **High:** 2021 Texas Winter Storm Uri (Feb freeze) or Q1-Q2 2022 post-COVID surge + Russia-Ukraine energy crisis

## S5.2 Scenario Definitions

**Table S19.** Price scenario construction.

| Scenario | Description | Construction Rule |
|----------|-------------|-------------------|
| **baseline** | Mid-range prices for all products | All products use baseline price |
| **high_fuel** | High fuel prices, low chemical/organics | Fuels (Naphtha, Diesel, Wax) use HIGH; all others use LOW |
| **high_chem** | High chemical prices, low fuel/organics | Chemicals (Ethylene, Propylene, Butene, BTX, Aromatics) use HIGH; all others use LOW |
| **high_organics** | High specialty organic prices, low fuel/chem | Organics (Paraffins, Carbonyls, Olefins, Alcohols, Acids, C30) use HIGH; all others use LOW |

The scenario structure tests the sensitivity of optimal superstructure configuration to different market conditions. Each non-baseline scenario maximizes prices for one product group while minimizing all others, representing extreme market conditions.

### Detailed Scenario Prices ($/kg)

| Product | baseline | high_fuel | high_chem | high_organics |
|---------|----------|-----------|-----------|---------------|
| Naphtha | 0.55 | **0.80** | 0.25 | 0.25 |
| Diesel | 0.70 | **1.00** | 0.27 | 0.27 |
| Wax | 1.00 | **1.50** | 0.70 | 0.70 |
| Ethylene | 1.10 | 0.30 | **1.30** | 0.30 |
| Propylene | 1.00 | 0.42 | **1.50** | 0.42 |
| Butene | 0.80 | 0.85 | **1.30** | 0.85 |
| BTX | 0.90 | 0.50 | **1.10** | 0.50 |
| Aromatics | 0.85 | 0.30 | **1.10** | 0.30 |
| Paraffins | 0.60 | 0.80 | 0.80 | **1.50** |
| Carbonyls | 0.50 | 0.50 | 0.50 | **2.40** |
| Olefins | 0.85 | 0.90 | 0.90 | **2.00** |
| Alcohols | 0.50 | 0.35 | 0.35 | **0.69** |
| Acids | 0.35 | 0.45 | 0.45 | **1.90** |
| C30 | 0.25 | 0.45 | 0.45 | **1.00** |
| Hydrogen | 2.50 | 1.00 | 1.00 | 1.00 |

Bold values indicate the HIGH price used in each scenario.

## S5.3 Product Groupings

| Group | Products |
|-------|----------|
| **Fuels** | Naphtha, Diesel, Wax |
| **Chemicals** | Ethylene, Propylene, Butene, BTX, Aromatics |
| **Organics** | Paraffins, Carbonyls, Olefins, Alcohols, Acids, C30 |
| **Hydrogen** | Hydrogen |

## S5.4 Sources

[1] Statista - Global naphtha price forecast & historical. https://www.statista.com/statistics/1171139/price-naphtha-forecast-globally/

[2] EIA - US No. 2 Diesel Wholesale/Resale Price. https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=EMA_EPD2D_PWG_NUS_DPG&f=M

[3] ChemAnalyst - Paraffin Wax Pricing (North America, 2020-2025). https://www.chemanalyst.com/Pricing-data/paraffin-wax-1205

[4] Statista - Global ethylene price forecast & historical. https://www.statista.com/statistics/1170573/price-ethylene-forecast-globally/

[5] OPIS/S&P Global - US ethylene and propylene spot prices (2020-2022). https://blog.opisnet.com/ethylene-propylene-prices-2020

[6] Statista - Global propylene monthly price. https://www.statista.com/statistics/1318104/monthly-price-propylene-worldwide/

[7] ChemAnalyst - Linear Alpha Olefin Pricing (1-Butene, US). https://www.chemanalyst.com/Pricing-data/linear-alpha-olefin-1103

[8] Statista - Global benzene price (proxy for BTX). https://www.statista.com/statistics/1171072/price-benzene-forecast-globally/

[9] ChemAnalyst - Mixed Xylene Pricing (toluene/xylene, US). https://www.chemanalyst.com/Pricing-data/mixed-xylene-80

[10] ChemAnalyst - Liquid Paraffin Pricing (n-paraffins, North America). https://www.chemanalyst.com/Pricing-data/liquid-paraffin-1197

[11] S&P Global - US acetone record highs (Mar 2021, proxy for carbonyls). https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/chemicals/030421

[12] IMARC Group - MEK Pricing Report (methyl ethyl ketone, 2020-2024). https://www.imarcgroup.com/methyl-ethyl-ketone-pricing-report

[13] ChemAnalyst - Linear Alpha Olefin Pricing (C6-C18 LAO, US). https://www.chemanalyst.com/Pricing-data/linear-alpha-olefin-1103

[14] Methanex - Regional Methanol Pricing (US Gulf Coast). https://www.methanex.com/our-products/about-methanol/pricing/

[15] ChemAnalyst - Acetic Acid Pricing (US, 2020-2024). https://www.chemanalyst.com/Pricing-data/acetic-acid-9

[16] BlackRidge Research - Gray hydrogen production costs. https://www.blackridgeresearch.com/blog/what-is-grey-hydrogen-h2-definition

[17] Argus Media - Global Waxes (slack wax / C30+ heavy fractions). https://www.argusmedia.com/en/solutions/products/argus-global-waxes

[18] MacroTrends - US diesel fuel historical prices. https://www.macrotrends.net/4394/us-diesel-fuel-prices
