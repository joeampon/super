"""
Market price data and scenario definitions for superstructure TEA.

Prices are in $/kg, based on US Gulf Coast / North American market data
from 2015-2025.  Three price regimes are defined (LOW, BASELINE, HIGH)
for each product, drawn from publicly available industry data.

Scenarios
---------
    baseline     : Mid-range prices for all products (approx. 2018-2019).
    high_fuel    : High fuel prices (naphtha, diesel, wax) with low
                   chemical and organics prices — e.g., tight crude
                   supply / refinery bottleneck.
    high_chem    : High light-olefin and aromatics prices (ethylene,
                   propylene, butene, BTX, aromatics) — e.g., steam
                   cracker outage / feedstock shortage.
    high_organics: High specialty-organic prices (paraffins, carbonyls,
                   olefins, alcohols, acids, C30+) — e.g., oleo-chemical
                   or alpha-olefin supply disruption.

Sources (accessed Jan-Feb 2026)
-------------------------------
[1]  Statista — Global naphtha price forecast & historical
     https://www.statista.com/statistics/1171139/price-naphtha-forecast-globally/
[2]  EIA — US No. 2 Diesel Wholesale/Resale Price
     https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=EMA_EPD2D_PWG_NUS_DPG&f=M
[3]  ChemAnalyst — Paraffin Wax Pricing (North America, 2020-2025)
     https://www.chemanalyst.com/Pricing-data/paraffin-wax-1205
[4]  Statista — Global ethylene price forecast & historical
     https://www.statista.com/statistics/1170573/price-ethylene-forecast-globally/
[5]  OPIS/S&P Global — US ethylene and propylene spot prices (2020-2022)
     https://blog.opisnet.com/ethylene-propylene-prices-2020
[6]  Statista — Global propylene monthly price
     https://www.statista.com/statistics/1318104/monthly-price-propylene-worldwide/
[7]  ChemAnalyst — Linear Alpha Olefin Pricing (1-Butene, US)
     https://www.chemanalyst.com/Pricing-data/linear-alpha-olefin-1103
[8]  Statista — Global benzene price (proxy for BTX)
     https://www.statista.com/statistics/1171072/price-benzene-forecast-globally/
[9]  ChemAnalyst — Mixed Xylene Pricing (toluene/xylene, US)
     https://www.chemanalyst.com/Pricing-data/mixed-xylene-80
[10] ChemAnalyst — Liquid Paraffin Pricing (n-paraffins, North America)
     https://www.chemanalyst.com/Pricing-data/liquid-paraffin-1197
[11] S&P Global — US acetone record highs (Mar 2021, proxy for carbonyls)
     https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/chemicals/030421
[12] IMARC Group — MEK Pricing Report (methyl ethyl ketone, 2020-2024)
     https://www.imarcgroup.com/methyl-ethyl-ketone-pricing-report
[13] ChemAnalyst — Linear Alpha Olefin Pricing (C6-C18 LAO, US)
     https://www.chemanalyst.com/Pricing-data/linear-alpha-olefin-1103
[14] Methanex — Regional Methanol Pricing (US Gulf Coast)
     https://www.methanex.com/our-products/about-methanol/pricing/
[15] ChemAnalyst — Acetic Acid Pricing (US, 2020-2024)
     https://www.chemanalyst.com/Pricing-data/acetic-acid-9
[16] BlackRidge Research — Gray hydrogen production costs
     https://www.blackridgeresearch.com/blog/what-is-grey-hydrogen-h2-definition
[17] Argus Media — Global Waxes (slack wax / C30+ heavy fractions)
     https://www.argusmedia.com/en/solutions/products/argus-global-waxes
[18] MacroTrends — US diesel fuel historical prices
     https://www.macrotrends.net/4394/us-diesel-fuel-prices

Price notes
-----------
- LOW prices reflect 2020 COVID demand destruction or 2015-2016 oil
  price collapse (WTI < $30/bbl).
- HIGH prices reflect 2021 Texas Winter Storm Uri (Feb freeze) or
  Q1-Q2 2022 post-COVID surge + Russia-Ukraine energy crisis.
- BASELINE is approximately the 2018-2019 pre-pandemic average.
- Hydrogen is priced as gray H2 (SMR) since it is a utility input to
  HC as well as a co-product.
"""

# ============================================================================
# Per-product price data: (low, baseline, high) in $/kg
# ============================================================================

#: Mapping from product name → (low, baseline, high) in $/kg.
#: Baseline is the value currently used in SUPERSTRUCTURE.PRODUCT_PRICES.
PRICE_DATA = {
    # --- Fuels -----------------------------------------------------------
    #   low: 2020 COVID lows;  high: Q1-Q2 2022 peaks [1][2][3]
    'Naphtha':   (0.25, 0.55, 0.80),
    'Diesel':    (0.27, 0.70, 1.00),
    'Wax':       (0.70, 1.00, 1.50),

    # --- Light olefins & aromatics (chemicals) ---------------------------
    #   low: Mar-May 2020 spot;  high: Feb 2021 freeze / 2022 peak [4-9]
    'Ethylene':  (0.30, 1.10, 1.30),
    'Propylene': (0.42, 1.00, 1.50),
    'Butene':    (0.85, 0.80, 1.30),
    'BTX':       (0.50, 0.90, 1.10),
    'Aromatics': (0.30, 0.85, 1.10),

    # --- Specialty organics ----------------------------------------------
    #   low: 2020 depressed;  high: 2021-2022 supply crunch [10-17]
    'Paraffins':  (0.80, 0.60, 1.50),
    'Carbonyls':  (0.50, 0.50, 2.40),
    'Olefins':    (0.90, 0.85, 2.00),
    'Alcohols':   (0.35, 0.50, 0.69),  # bulk methanol proxy (low purity)
    'Acids':      (0.45, 0.35, 1.90),
    'C30':        (0.45, 0.25, 1.00),

    # --- Hydrogen (gray, SMR) -------------------------------------------
    #   low: 2019 cheap natgas;  high: 2022 natgas spike [16]
    'Hydrogen':  (1.00, 2.50, 2.50),
}

# Product groupings used to build scenarios
FUEL_PRODUCTS = {'Naphtha', 'Diesel', 'Wax'}
CHEMICAL_PRODUCTS = {'Ethylene', 'Propylene', 'Butene', 'BTX', 'Aromatics'}
ORGANIC_PRODUCTS = {'Paraffins', 'Carbonyls', 'Olefins', 'Alcohols', 'Acids', 'C30'}

# ============================================================================
# Scenario builders
# ============================================================================

def _build_prices(high_group):
    """Return a price dict where *high_group* products use their HIGH price
    and all other products use their LOW price."""
    prices = {}
    for name, (low, _base, high) in PRICE_DATA.items():
        prices[name] = high if name in high_group else low
    return prices


#: Pre-built scenario price dicts (product name → $/kg).
SCENARIOS = {
    'baseline': {name: base for name, (_l, base, _h) in PRICE_DATA.items()},
    'high_fuel':     _build_prices(FUEL_PRODUCTS),
    'high_chem':     _build_prices(CHEMICAL_PRODUCTS),
    'high_organics': _build_prices(ORGANIC_PRODUCTS),
}


def get_prices(scenario='baseline'):
    """
    Return product prices for a named scenario.

    Parameters
    ----------
    scenario : str
        One of ``'baseline'``, ``'high_fuel'``, ``'high_chem'``,
        ``'high_organics'``.

    Returns
    -------
    dict
        {product_name: price_per_kg}
    """
    if scenario not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario {scenario!r}. "
            f"Choose from {sorted(SCENARIOS)}."
        )
    return dict(SCENARIOS[scenario])
