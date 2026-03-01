import biosteam as bst 

class Dryer(bst.Unit):
    """
    Calculates drying cost based on moisture evaporation
    """
    _N_ins = 1
    _N_outs = 2

    def __init__(self, ID, ins=(), outs=(), T=373.15, P=101325, moisture_content=0.1):
        # this section is called first when the unit is created/simulated
        self.power_utility = bst.PowerUtility()
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo()) # initialize default values for the all units
        # super()._setup()
        self._multistream = bst.MultiStream(None, thermo=self.thermo) # we use an internal multistream to do internal calculations
        self.mc = moisture_content
        self.T = T 
        self.P = P

    # def _setup(self):
    #     # setup is called second after the unit is created
    #     pass

    def _run(self):
        # we make no changes to the feedstock for now. Biosteam does not have information on particle sizes
        ins = self.ins[0]
                
        out_dry, out_wet = self.outs
        out_dry.copy_like(ins)
        out_dry.T = self.T 
        out_wet.T = self.T 

        out_dry.P = self.P
        out_wet.P = self.P

        dry_feed = ins.get_total_flow('kg/hr') - ins.get_flow('kg/hr', 'Water')
        total_flow = ins.get_total_flow('kg/hr')
        if total_flow == 0:
            total_flow = 1e-6
        mc_in = ins.get_flow('kg/hr', 'Water')/total_flow
        #TODO
        if mc_in < self.mc:
            out_dry.T = ins.T 
            out_wet.T = ins.T
            return 
        water_out = dry_feed*self.mc/(1 - self.mc)
        water_evap = ins.get_flow('kg/hr', 'Water') - water_out 

        if water_evap < 0:
            out_wet.set_flow(0, 'kg/hr', "Water")
        else:
            out_wet.set_flow(water_evap, 'kg/hr', "Water")
        out_dry.set_flow(water_out, 'kg/hr', 'Water')
                
    def _design(self):
        # Calculate heat utility requirement (please read docs for HeatUtility objects)
        T_operation = self.T
        duty = (self.H_out - self.H_in)/0.6 # 40% heat loss
        # if duty < 0:
        #     raise RuntimeError(f'{repr(self)} is cooling.')
        # hu = self.heat_utilities[0]
        # hu(duty, T_operation)
        self.design_results["Duty"] = duty


    def _cost(self):
        base_cost = 905000
        base_size = 2000/5 # tonne/day

        number = self.ins[0].get_total_flow("tonne/day")/base_size
        self.purchase_costs["Dryer"] = number*base_cost
