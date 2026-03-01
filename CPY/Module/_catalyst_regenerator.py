import numpy as np
import warnings
import biosteam as bst
from biosteam import units
import thermosteam as tmo
from biosteam.units.decorators import cost
class catalyst_regenerator(units.Unit):
    _N_ins = 1
    _N_outs = 2
    _units= {'Infeed': 'bbl/day',
                'Duty': 'kJ/hr',
                'Power': 'kW'}  
    regeneration_efficiency = 0.95
    pressure_drop = 0.5
    
    def _init_(self, ID='', ins=(), outs=(), T= 273.15, P= 101325, regeneration_efficiency=0.95, pressure_drop=0.5):
        super()._init_(ID, ins, outs)
        self.regeneration_efficiency = regeneration_efficiency
        self.pressure_drop = pressure_drop
        self.T = T
        self.P = P
        
    def _run(self):
        spent_catalyst = self.ins[0]
        regenerant=self.ins[1]
        fresh_catalyst=self.outs[0]
        waste_stream=self.outs[1]
        regenerated_amount= spent_catalyst.imass['Zeolite'] * self.regeneration_efficiency
        waste_amount=spent_catalyst.imass['Zeolite']-regenerated_amount
        fresh_catalyst.imass['Zeolite']=regenerated_amount
        waste_stream.imass['Zeolite']= waste_amount
        fresh_catalyst.copy_like(spent_catalyst)
        waste_stream.copy_like(spent_catalyst)
        fresh_catalyst.P = spent_catalyst.P - self.pressure_drop
        waste_stream.P = spent_catalyst.P - self.pressure_drop
    def _design(self):
        self.design_results['Regeneration Efficiency'] = self.regeneration_efficiency
    def _cost(self):
        self.capital_cost = 2000  # Example fixed cost
        self.operating_cost = 1000  # Example fixed cost per operation
        pass
#%%