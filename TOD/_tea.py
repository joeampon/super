import biosteam as bst

class TEA(bst.TEA):
    """
    Create a TEA object for techno-economic analysis of a biorefinery.
    """

    __slots__ = ('labor_cost', 'fringe_benefits', 'maintenance',
                 'property_tax', 'property_insurance', '_FCI_cached',
                 'supplies', 'maintanance', 'administration')

    def __init__(self, system, 
             IRR=0.1,
             duration=(2018, 2038),
             depreciation='MACRS7',
             income_tax=0.21,
             operating_days=333,
             lang_factor=2.5, # ratio of total fixed capital cost to equipment cost
             construction_schedule=(0.4, 0.6),
             WC_over_FCI=0.05, #working capital / fixed capital investment
             labor_cost=0,
             fringe_benefits=0.4,# percent of salary for misc things
             property_tax=0.001,
             property_insurance=0.005,
             supplies=0.20,
             maintenance=0.003,
             administration=0.005,
             finance_fraction = 0.4,
             finance_years=10,
             finance_interest=0.07):
        super().__init__(system, IRR, duration, depreciation, income_tax,
                         operating_days, lang_factor, construction_schedule,
                         startup_months=0, startup_FOCfrac=0, startup_VOCfrac=0,
                         startup_salesfrac=0, finance_interest=finance_interest, finance_years=finance_years,
                         finance_fraction=finance_fraction, WC_over_FCI=WC_over_FCI)
        self.labor_cost = labor_cost
        self.fringe_benefits = fringe_benefits
        self.property_tax = property_tax
        self.property_insurance = property_insurance
        self.supplies = supplies
        self.maintenance = maintenance
        self.administration = administration

    def _DPI(self, installed_equipment_cost):
        return installed_equipment_cost # installed_equipment_cost (generic number)

#total direct cost
    def _TDC(self, DPI):
        return DPI

    def _FCI(self, TDC):
        self._FCI_cached = TDC
        return TDC

    def _FOC(self, FCI):
        return (FCI * (self.property_tax + self.property_insurance
                       + self.maintenance + self.administration)
                + self.labor_cost * (1 + self.fringe_benefits + self.supplies))
    @property
    def utility_cost(self):
        return sum([u.utility_cost if u.utility_cost else 0 for u in self.system.units]) * self.operating_hours

    def mfsp_table(self, product=None, solve=True):
        costs = {}
        for f in self.feeds:
            if abs(f.cost) > 1.0:
                costs[f.ID] = f.cost*self.operating_days*24
            else:
                costs["Other"] = costs.get("Other", 0) + f.cost*self.operating_days*24
        costs["Utilities"] = self.utility_cost 
        costs["O&M"] = self.FOC 
        costs["Depreciation"] = self.annual_depreciation

        revenues = 0
        if product == None:
            for f in self.products:
                if abs(f.cost) > 0:
                    costs[f.ID] = -f.cost*self.operating_days*24
                    revenues += -f.cost*self.operating_days*24
        else:
            for f in self.products:
                if product != None and f.ID != product.ID:
                    if abs(f.cost) > 0:
                        costs[f.ID] = -f.cost*self.operating_days*24
                        revenues += -f.cost*self.operating_days*24
        if product != None:
            if solve==True:
                price = self.solve_price(product)
            else:
                price = product.price
            sales = price*product.get_total_flow('kg/year')
            costs["Income Tax"] = self.income_tax*(sales-revenues-self.AOC)
            if costs["Income Tax"] < 0:
                costs["Income Tax"] = 0

            costs["ROI"] = sales - sum([v for v in costs.values()]) 
        else:
            costs["ROI"] = self.ROI
        return costs


employee_costs = {
    "Plant Manager":[ 159000,  1],
    "Plant Engineer":[ 94000,  1],
    "Maintenance Supr":[ 87000,  1],
    "Maintenance Tech":[ 62000,  6],
    "Lab Manager":[ 80000,  1],
    "Lab Technician":[ 58000,  1],
    "Shift Supervisor":[ 80000,  3],
    "Shift Operators":[ 62000,  12],
    "Yard Employees":[ 36000,  4],
    "Clerks & Secretaries":[ 43000,  1],
    "General Manager":[188000, 0]
} # Labor cost taken from Dutta 2002 and adjusted using the U.S. Bureau of Labor Statistics. Number of staff required gotten from Yadav et al.  
#  US BLS (http://data.bls.gov/cgi-bin/srgateCEU3232500008)

labor_costs = sum([
    employee_costs[v][0]* employee_costs[v][1]  for v in employee_costs
            ])
print(f"Labor cost: {labor_costs}")
# %%
# %% TEA component

#--------------------------------------------------------------------------------------------------------------
# Economic Analysis: TEA code for MSP
#----------------------------------------------------------------------------------------------------------------

facility_outputs = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]

def get_tea(system):
    tea_msp = TEA(
        system=system,
        IRR=0.1,
        duration=(2020, 2040),
        depreciation="MACRS7",
        income_tax=0.21,
        operating_days=333,
        lang_factor=5.05,  # ratio of total fixed capital cost to equipment cost
        construction_schedule=(0.4, 0.6),
        WC_over_FCI=0.05,  # working capital / fixed capital investment
        labor_cost=labor_costs,
        fringe_benefits=0.4,  # percent of salary for misc things
        property_tax=0.001,
        property_insurance=0.005,
        supplies=0.20,
        maintenance=0.003,
        administration=0.005,
        finance_fraction=0.4,
        finance_years=10,
        finance_interest=0.07,
    )
    return tea_msp