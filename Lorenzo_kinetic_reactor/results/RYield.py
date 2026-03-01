import biosteam as bst 

class RYield(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    # _N_heat_utilities = 1
    _F_BM_default = {'Heaters': 1}
    # _units = {'Area', 'm^2'}

    def __init__(self, ID='', ins=None, outs=(), yields=None, *args, **kwargs):
        super().__init__(ID, ins, outs, *args, **kwargs)
        super()._setup()
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = self.ins[0].T
        self.yields = yields
     

    def _setup(self):
        vap = self.outs[0]
        # vap.phase = 'g'

    def _run(self):
        feed = self.ins[0]
        vap = self.outs[0]
        

        ms = bst.Stream(None, thermo=feed.thermo)
        for c, y in self.yields.items():
            try:
                ms.set_flow(feed.F_mass * y, "kg/hr", c)
            except:
                print(c)
                pass
        vap.copy_flow(ms)
        #vap.T = feed.T
        vap.P = feed.P
        vap.T = 400+273.15
        ms.empty()
