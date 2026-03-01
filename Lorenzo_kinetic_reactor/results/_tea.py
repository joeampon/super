# %%

import biosteam as bst
import pandas as pd
 
# Custom TEA class definition
class TEA(bst.TEA):
    """
    Create a TEA object for techno-economic analysis of a biorefinery.
    """
 
    __slots__ = (
        "labor_cost",
        "fringe_benefits",
        "maintenance",
        "property_tax",
        "property_insurance",
        "_FCI_cached",
        "supplies",
        "maintanance",
        "administration",
    )
 
    def __init__(
        self,
        system,
        IRR,
        duration,
        depreciation,
        income_tax,
        operating_days,
        lang_factor,
        construction_schedule,
        WC_over_FCI,
        labor_cost,
        fringe_benefits,
        property_tax,
        property_insurance,
        supplies,
        maintenance,
        administration,
        finance_interest=0,
        finance_years=0,
        finance_fraction=0,
    ):
        super().__init__(
            system,
            IRR,
            duration,
            depreciation,
            income_tax,
            operating_days,
            lang_factor,
            construction_schedule,
            startup_months=0,
            startup_FOCfrac=0,
            startup_VOCfrac=0,
            startup_salesfrac=0,
            finance_interest=finance_interest,
            finance_years=finance_years,
            finance_fraction=finance_fraction,
            WC_over_FCI=WC_over_FCI,
        )
        self.labor_cost = labor_cost
        self.fringe_benefits = fringe_benefits
        self.property_tax = property_tax
        self.property_insurance = property_insurance
        self.supplies = supplies
        self.maintenance = maintenance
        self.administration = administration
 
    def _DPI(self, installed_equipment_cost):
        return installed_equipment_cost  # installed_equipment_cost (generic number)
 
    def _TDC(self, DPI):
        return DPI
 
    def _FCI(self, TDC):
        self._FCI_cached = TDC
        return TDC
 
    def _FOC(self, FCI):
        return FCI * (
            self.property_tax
            + self.property_insurance
            + self.maintenance
            + self.administration
        ) + self.labor_cost * (1 + self.fringe_benefits + self.supplies)
    
    @property
    def get_tea_parameters(self):
        
        params = {
    "Internal Rate of Return (IRR)": self.IRR * 100,  # Convert to percentage
    "Duration of Project (years)": f"{self.duration[0]}--{self.duration[1]}",
    "Depreciation Method": self.depreciation,
    "Combined State and Federal Income Tax (\\%)": self.income_tax * 100,
    "Operating Time (days/year)": self.operating_days,
    "Lang Factor": self.lang_factor,
    "Construction Schedule (year 0\\%, year 1\\%)": f"{self.construction_schedule[0]}, {self.construction_schedule[1]}",
    "Working Capital over FCI (\\%)": self.WC_over_FCI * 100,
    "Labor Cost (USD/year)": self.labor_cost,
    "Fringe Benefits (labor cost \\%)": self.fringe_benefits * 100,
    "Property Tax (FCI \\%)": self.property_tax * 100,
    "Property Insurance (FCI \\%)": self.property_insurance * 100,
    "Supplies (labor cost \\%)": self.supplies * 100,
    "Maintenance (FCI \\%)": self.maintenance * 100,
    "Administration (FCI \\%)": self.administration * 100,
    "Finance Fraction (TCC \\%)": self.finance_fraction * 100,
    "Finance Time (years)": self.finance_years,
    "Finance Interest (TCC \\%)": self.finance_interest * 100,
}
        
        return params
   
    def mfsp_table(self, product=None):
        costs = {}
        product.price = self.solve_price(product)
        for f in self.feeds:
            if abs(f.cost) > 1e-6:  # Lower threshold for small flows
                costs[f.ID] = f.cost * self.operating_days * 24
            else:
                costs["Other"] = costs.get("Other", 0) + f.cost * self.operating_days * 24
        costs["Utilities"] = self.utility_cost
        costs["O&M"] = self._FOC(self._FCI_cached)
        # costs["Depreciation"] = self.annual_depreciation
        costs["Capital"] = self.installed_equipment_cost/(self.duration[1] - self.duration[0])
        revenues = 0
        for f in self.products:
            if f.ID != product.ID and abs(f.cost) > 0:  # Only include H₂ revenue
                costs[f.ID] = -f.cost * self.operating_days * 24
                revenues += -f.cost * self.operating_days * 24
        sales = product.price * product.get_total_flow('kg/year')
        costs["Income Tax"] = self.income_tax * (sales - revenues - self.AOC)
        if costs["Income Tax"] < 0:
            costs["Income Tax"] = 0
        costs["ROI"] = sales - sum([v for k, v in costs.items() if k != "ROI"])
        return costs
# %%
