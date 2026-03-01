# -*- coding: utf-8 -*-
"""
Created on Sat Sep 14 01:32:00 2024

@author: yoel
r
"""
import biosteam as bst
import pandas as pd

if __name__ == '__main__':
    LightPyrolysisOil = bst.Chemical('LightPyrolysisOil', search_ID='1-Hexene')
    LightPyrolysisOil._CAS = 'LightPyrolysisOil'
    Catalyst = bst.Chemical('Catalyst', search_db=False, default=True, phase='s')
    composition = pd.read_excel('Jiayang_PCR_HDPE_1_oil.xlsx', sheet_name='composition', index_col=0).values.flatten()
    chemical_feed_names = list(pd.read_excel('Jiayang_PCR_HDPE_1_oil.xlsx', sheet_name='representative_chemicals', index_col=0).values.flatten())
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
    def simple_name(name):
        *_, name = name.split('n-')
        letters = [letter for letter in name if letter.isalpha()]
        return ''.join(letters).capitalize()
    
    chemical_feeds = [bst.Chemical(ID=simple_name(name), search_ID=name) for name in chemical_feed_names]
    chemical_products = list(light_pyrolysis_oil_product_distribution)
    chemicals = bst.Chemicals(
        chemical_feeds
        + chemical_products
        + ['N2', 'Water', 'CO2', 'O2', LightPyrolysisOil, Catalyst]
    )
    bst.settings.set_thermo(chemicals)
    for chemical, name in zip(chemical_feeds, chemical_feed_names): chemicals.set_alias(chemical.ID, name)
    light_pyrolysis_oil_feed_distribution = {i: j for i, j in zip(chemical_feed_names, composition)}
    products = ' + '.join([f'{j}{i}' for i, j in light_pyrolysis_oil_product_distribution.items()])
    reaction = bst.Reaction(
        f'LightPyrolysisOil -> {products}',
        reactant='LightPyrolysisOil', X=1.,
        correct_mass_balance=True
    )
    feed = bst.Stream('light_pyrolysis_oil', **light_pyrolysis_oil_feed_distribution, total_flow=5000, units='kg/hr')
    air = bst.Stream('air', phase='g')
    catalyst = bst.Stream('catalyst', phase='s')
    steam = bst.Stream('steam', phase='g')
    # TODO: Make feed preheating temperature meet product temperature requirement.
    FCC = bst.FluidizedCatalyticCracking(
        ins=[feed, catalyst, air, steam],
        outs=['product', 'spent_catalyst', 'flue_gas'],
        reaction=reaction,
        bulk_reactant=('LightPyrolysisOil', [i.ID for i in chemical_feeds]),
        CO2_concentration=0.10,
        feed_vapor_fraction=1,
        product_loss=0.015, # switch this to 0.5 - 1.5% (conservatively)
        riser_product_residence_time = 0.095 / 3600,
    )
    FCC.simulate()
    FCC.diagram()
    sys = bst.System.from_units(units=[FCC])
    sys.save_report('FCC.xlsx')
