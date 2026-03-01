# S4. Life Cycle Assessment

## S4.1 System Boundary

The LCA follows a cradle-to-gate approach using the ecoinvent 3.x database (Allocation at the Point of Substitution, APOS). The system boundary includes:

- **Inputs:** Feedstock (waste plastic), natural gas, oxygen, CO2, catalysts, electricity, heating/cooling utilities
- **Outputs:** All product streams (fuels, chemicals, organics, hydrogen), flue gas emissions
- **Excluded:** Transportation of feedstock, end-of-life of products, construction/decommissioning of plant

## S4.2 Impact Categories

Ten impact categories from the TRACI 2.1 methodology are evaluated:

| # | Impact Category | Unit |
|---|----------------|------|
| 1 | Global warming (GWP) | kg CO2 eq |
| 2 | Acidification | kg SO2 eq |
| 3 | Eutrophication | kg N eq |
| 4 | Smog | kg O3 eq |
| 5 | Ozone depletion | kg CFC-11 eq |
| 6 | Respiratory effects | kg PM2.5 eq |
| 7 | Ecotoxicity | CTUe |
| 8 | Carcinogenics | CTUh |
| 9 | Non-carcinogenics | CTUh |
| 10 | Fossil fuel depletion | MJ surplus |

GWP is the primary metric for optimization.

## S4.3 Emission Factor Table

**Table S16.** Life cycle emission factors (GWP, kg CO2-eq per unit).

| Resource | ecoinvent Process | GWP (kg CO2-eq/unit) | Unit |
|----------|------------------|---------------------|------|
| Benzene | market for benzene, APOS, U | 1.994 | kg |
| Acetic acid | market for acetoacetic acid, APOS, U | 8.363 | kg |
| Acetaldehyde | market for acetaldehyde, APOS, U | 1.849 | kg |
| Heavy fuel oil | market for heavy fuel oil, APOS, U | 0.348 | kg |
| Lubricating oil | market for lubricating oil, APOS, U | 1.353 | kg |
| Oxygen | market for oxygen, liquid, APOS, U | 1.072 | kg |
| Methanol | market for methanol, APOS, U | 0.629 | kg |
| Butane | market for butane, APOS, U | 0.768 | kg |
| Naphtha | market for naphtha, APOS, U | 0.366 | kg |
| Diesel | market for diesel, APOS, U | 0.475 | kg |
| Ethylene | market for ethylene, average, APOS, U | 1.396 | kg |
| Propylene | market for propylene, APOS, U | 1.435 | kg |
| Wax | market for wax, lost-wax casting, APOS, U | 0.745 | kg |
| Hydrogen | market for hydrogen, liquid, APOS, U | 2.277 | kg |
| Electricity (medium voltage) | market for electricity, medium voltage, APOS, U | 0.456 | MJ |
| Natural gas | market for natural gas, liquefied, APOS, U | 0.574 | m3 |

## S4.4 Stream-to-Resource Mapping

**Table S17.** BioSTEAM stream ID to LCA resource mapping with multipliers.

| Stream ID | LCA Resource | Multiplier | Type |
|-----------|-------------|------------|------|
| comb_nat_gas | Natural gas | +0.8 | Feed (m3 to kg conversion) |
| CPY_residue | Heavy fuel oil | -1.0 | Product credit |
| CPY_AromaticsO | Benzene | -1.0 | Product credit |
| SS_BTX | Benzene | -1.0 | Product credit |
| PLASMA_Carbonyls | Acetaldehyde | -1.0 | Product credit |
| PLASMA_Acids | Acetic acid | -1.0 | Product credit |
| PLASMA_Alcohols | Methanol | -1.0 | Product credit |
| PLASMA_C30 | Lubricating oil | -1.0 | Product credit |
| PLASMA_Olefins | Butane | -1.0 | Product credit |
| PLASMA_Paraffins | Naphtha | -1.0 | Product credit |
| SS_Diesel | Diesel | -1.0 | Product credit |
| SS_Wax | Wax | -1.0 | Product credit |
| SS_Hydrogen | Hydrogen | -1.0 | Product credit |
| SS_Naphtha | Naphtha | -1.0 | Product credit |
| SS_Butene | Butane | -1.0 | Product credit |
| DIST_Ethylene | Ethylene | -1.0 | Product credit |
| DIST_Propylene | Propylene | -1.0 | Product credit |
| DIST_Butene | Butane | -1.0 | Product credit |

**Sign convention:** Negative multiplier = product credit (displaces conventional production); Positive = environmental burden (resource consumed).

## S4.5 GWP Calculation

Total GWP is computed hourly:

$$\text{GWP}_{\text{total}} = \sum_{s \in \text{streams}} F_{s} \times \text{EF}_{s} \times m_{s} + \text{GWP}_{\text{electricity}} + \text{GWP}_{\text{heat}} + \text{GWP}_{\text{FCC offgas}}$$

where:
- $F_s$ = mass flow rate of stream $s$ (kg/hr)
- $\text{EF}_s$ = emission factor of mapped resource (kg CO2-eq/kg)
- $m_s$ = multiplier (positive for burdens, negative for credits)

**Electricity GWP:**

$$\text{GWP}_{\text{elec}} = P_{\text{consumption}} \times 3.6 \times \text{EF}_{\text{electricity}}$$

where $P_{\text{consumption}}$ is net power consumption in kW and 3.6 converts kWh to MJ.

**Heat GWP:**

$$\text{GWP}_{\text{heat}} = Q_{\text{net cooling}} \times \text{EF}_{\text{natural gas}} / 1000 / 3600$$

where $Q_{\text{net cooling}}$ is the sum of negative (cooling) heat duties in kJ/hr.

**FCC off-gas direct emissions:**

$$\text{GWP}_{\text{FCC}} = \dot{m}_{\text{CO2}} + 32 \times \dot{m}_{\text{CH4}}$$

The factor of 32 represents the 100-year GWP of methane relative to CO2.

**Normalization:** GWP per kg feed = GWP_total (kg CO2-eq/hr) / feed mass flow (kg/hr).

## S4.6 Carbon Abatement Cost

The carbon abatement cost (CAC) quantifies the economic cost of avoiding one kg of CO2-equivalent emissions:

$$\text{CAC} = \frac{\text{Net cost per kg feed}}{-\text{GWP per kg feed}}$$

where:
- Net cost per kg feed = (Annual operating cost - Annual sales) / Annual feed mass
- Negative GWP per kg feed represents CO2-eq reduced (positive when GWP is negative)

A negative CAC indicates that the process both reduces emissions and generates net revenue (win-win). A positive CAC indicates the cost per kg CO2-eq avoided.

## S4.7 Product Credit Methodology

Product credits follow the displacement approach: each product stream displaces an equivalent amount of conventional (fossil-derived) production. The environmental burden of conventional production is subtracted from the process GWP, yielding a net negative GWP when product credits exceed process burdens.
