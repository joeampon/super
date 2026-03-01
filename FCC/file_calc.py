S228+S234

# -*- coding: utf-8 -*-
"""
Created on Sat Sep 14 01:32:00 2024

@author: yoelr
"""

#%%
import biosteam as bst

#%%
# if __name__ == '__main__':
chemical_feeds = [bst.Chemical('LightPyrolysisOil', search_ID='1-Hexene')]
Catalyst = bst.Chemical('Catalyst', search_db=False, default=True, phase='s')
light_pyrolysis_oil_product_distribution = dict(
    Propene=6.2,
    Ethene=0.3,
    Butene=16.9,
    Pentene=9.5,
    Benzene=27.3,
    Toluene=19.1,
    Xylene=5.2,
    Styrene=0.8,
    Propane=0.1,
    Butane=0.3,
    EthylBenzene=2.3,
)
chemical_products = list(light_pyrolysis_oil_product_distribution)
chemicals = bst.Chemicals(
    chemical_feeds + chemical_products + ['N2', 'Water', 'CO2', 'O2', Catalyst]
)
bst.settings.set_thermo(chemicals)
products = ' + '.join([f'{j}{i}' for i, j in light_pyrolysis_oil_product_distribution.items()])

#%%
reaction = bst.Reaction(
    f'LightPyrolysisOil -> {products}',
    reactant='LightPyrolysisOil', X=1.,
    riser_product_residence_time = 0.095 / 3600,
    correct_mass_balance=True
)
feed = bst.Stream('light_pyrolysis_oil', LightPyrolysisOil=5000, units='kg/hr')
air = bst.Stream('air', phase='g')
catalyst = bst.Stream('catalyst', phase='s')
steam = bst.Stream('steam', phase='g')
FCC = bst.FluidizedCatalyticCracking(
    ins=[feed, catalyst, air, steam],
    outs=['product', 'spent_catalyst', 'flue_gas'],
    reaction=reaction,
    CO2_concentration=0.10,
    product_loss=1e-1,
)
FCC.simulate()
sys = bst.System.from_units(units=[FCC])
sys.save_report('FCC.xlsx')
