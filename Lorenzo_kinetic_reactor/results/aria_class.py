import biosteam as bst

class IsentropicCompressor(bst.units.IsentropicCompressor):
    def _run(self):
        feed = self.ins[0]
        out = self.outs[0]
        out.copy_like(feed)
        out.P = self.P
        out.S = feed.S
        if self.vle is True:
            out.vle(S=out.S, P=out.P)
            T_isentropic = out.T
        else:
            T_isentropic = out.T
        self.T_isentropic = T_isentropic
        dH_isentropic = out.H - feed.H
        self.design_results['Ideal power'] = dH_isentropic / 3600. # kW
        self.design_results['Ideal duty'] = 0.
        dH_actual = dH_isentropic / self.eta
        out.H = feed.H + dH_actual        
        if self.vle is True: out.vle(H=out.H, P=out.P)
 
    def _design(self):
        super()._design()            
        self._set_power(self.design_results['Ideal power'] / self.eta)
        self.design_results['Power'] = self.design_results['Ideal power'] / self.eta
        self.power_utility.set_property('consumption', self.design_results['Power'], 'kW')
 
    def _cost(self):
        # Note: Must run `_set_power` before running parent cost algorithm
        design_results = self.design_results
        alg = self.baseline_cost_algorithms[design_results['Type']]
        acfm_lb, acfm_ub = alg.acfm_bounds
        Pc = self.power_utility.get_property('consumption', 'hp')
        N = design_results['Compressors in parallel']
        Pc_per_compressor = Pc / N
        #bounds_warning(self, 'power', Pc, 'hp', alg.hp_bounds, 'cost')
        # modified to have a minimum of 5 hp per compressor
        if Pc_per_compressor < 10.:
            # self.baseline_purchase_costs['Compressor(s)'] = 0.
            Pc_per_compressor = 10.
        # else:
        self.purchase_costs['Compressor(s)'] = N * bst.CE / alg.CE * alg.cost(Pc_per_compressor)
        self.installed_costs['Compressor(s)'] = self.purchase_costs['Compressor(s)'] * 3.25
        self.F_D['Compressor(s)'] = self.design_factors[design_results['Driver']]
 
        # The "Hydrogen Station Compression, Storage, and Dispensing Technical Status and Costs" report discusses uncertainties in compressor costs and installation factors,
        # indicating significant contributions to overall costs. Refer to the bullet points under the "Executive Summary" section. (2.5  - 4 x)