# %% Import necessary modules
from builtins import range
from builtins import sum
import time
import math
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

import biosteam as bst 
import thermosteam as tmo
from thermo import SRK
#  import compounds and set thermo  
from ._compounds import *
from ._Hydrocracking_Unit import *
from ._Hydrogen_production import *
from .fluidized_catalytic_cracking import *

from plotnine import *

from ._Grinder import *
from ._CHScreen import *
from ._RYield import *
from ._Cyclone import *
from ._Sand_Furnace import *
from ._UtilityAgents import *    # Created heat utilities that can heat to high temperatures and cool to sub zero temperatures 
from ._process_yields import *
from ._Compressor import *
from ._feed_handling import *
from ._teapyrolysis import *
from ._tea_wax_mfsp import *
from ._pass_unit import *

from ._tea import *

import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.size': 14})

bst.nbtutorial() # Light-mode html diagrams and filter warnings

# Set CEPCI to year of analysis to be 2020
bst.settings.CEPCI = 596.2 # CEPCI 2021 = 708, 2020 = 596.2, 2019	= 607.5

for c in compounds:
    c.default()

# compounds["CO2"].Cn.l.add_method(71, Tmin=-700, Tmax=120)

bst.HeatUtility().cooling_agents.append(NH3_utility)
bst.HeatUtility().heating_agents.append(Liq_utility)
bst.HeatUtility().heating_agents.append(Gas_utility)


# PREFERENCES
bst.preferences.update(flow='kg/hr', T='degK', P='Pa', N=100, composition=True)
 
#  Prices 
actual_prices = {
"HDPE": 25.05/1000, # $/kg from 22 per MT, because feed is defined per MT
"Ethylene": 0.61, # Gracida Al
"Propylene":0.97, # $/kg
"Butene": 1.27,# Butene 1.27 $/kg from Yadav et al. 2023
"Naphtha": 0.86,  # Gracida Alvarez et al
"Diesel": 0.84,  # Gracida Alvarez et al
"Wax": 0.3, #   1989 USD/MT   source: https://www.chemanalyst.com/Pricing-data/paraffin-wax-1205
"NG": 7.40 * 1000 * 1.525/28316.8, 
"Hydrocracking catalyst": 15.5 * 2.20462262,      #15.5 $/lb 2.20462262 is factor to convert to $/kg from Jones et al. 2009 PNNL report SRI international 2007
"Hydrotreating catalyst": 15.5 * 2.20462262,      #15.5 $/lb from Jones et al. 2009 PNNL report SRI international 2007
"Hydrogen plant catalyst": 3.6/885.7,      #3.6 /1000scf/28.317m3/885.71kg 2007 quote from Jones et al. 2009 PNNL report SRI international 2007
"Hydrogen": 2.83      #2.83 USD/kg from Gracida Alvarez et al. 2.1 from Borja Hernandez et al. 2019
}
bst.settings.electricity_price = 0.065 # Gracida Alvarez et al

#%%
# Robust path to FCC model file relative to this module
_MODULE_DIR = Path(__file__).parent
_FCC_MODEL_PATH = _MODULE_DIR / 'fccCycleTimeToProds.pkl'
fccml = None  # Lazy-loaded to avoid import-time failures on version mismatch

# def _load_fcc_model():
#     """Load FCC model from pickle lazily; print helpful info on failure."""
#     global fccml
#     if fccml is None:
#         try:
#             fccml = joblib.load(_FCC_MODEL_PATH)
#         except Exception as e:
#             print(f"Warning: could not load FCC model from '{_FCC_MODEL_PATH}': {e}")
#             try:
#                 import sklearn
#                 print(f"Note: scikit-learn version is {sklearn.__version__}. The pickle may require a different version.")
#             except Exception:
#                 pass

fcc_chemicals = {
    'Methane': ['CH4'],
    'Ethane': ['C2H4', 'Ethane'],
    'Ethylene': ['C2H4'],
    'Propane': ['C3H8', 'Propane'],
    'Propylene': ['Propene'],
    'iso-butane': ['C4H8'],
    'n-Butane': ['C4H8'],
    'trans-2-Butene': ['C4H8'],
    '1-Butene': ['C4H8'],
    'cis-2-Butene': ['C4H8'],
    '1,3-Butadiene': ['C4H6'],
    'Pentane': ['C5H12'],
    '2-MethylPentane': ['C6H14'],
    'nHexane': ['C6H14'],
    'Benzene': ['C6H6'],
    'Cyclohexane': ['C6H12'],
    'nHeptane': ['C7H16'],
    'Toluene': ['C7H8'],
    '1-Octene': ['C8H16'],
    'C8?': ['C8H16'],
    'C8??': ['C8H16'],
    'Ethylbenzene': ['C8H10'],
    'C8???': ['C8H10'],
    'Xylene (m, p)': ['C8H10'],
    'Styrene': ['C8H8'],
    '?MethylStyrene?': ['C9H10'],
    '?PropenylBenzene?': ['C9H10'],
    'isoPropylBenzene': ['C9H12'],
    'PropylBenzene': ['C9H12'],
    '1,3,5-trimethylbenzene': ['C9H12'],
    'C9-10?': ['C10H20' ],
    'Decane': ['C10H22'],
    'NA1': ['C24H50'],
    'NA2': ['C24H50'],
    'NA3': ['C24H50'],
    'nDodecane': ['C12H26'],
    'Naphthalene': ['C10H8'],
    '4-tertButylStyrene': ['C12H26']
}

# def get_fcc_products(cycle, cycle_time):
#     """
#     Get the products from the FCC model based on cycle time.
#     """
#     # Ensure model is loaded; if unavailable, return zeros
#     _load_fcc_model()
#     if fccml is None:
#         print("Warning: FCC model unavailable; returning zero selectivities.")
#         return {k.ID: 0 for k in bst.settings.chemicals}

#     # Get the products from the model
#     products = {list(fcc_chemicals.keys())[i]:v for i, v in enumerate(fccml.predict(np.array([[cycle, cycle_time]]))[0])}
#     # print("Products from FCC model: ", sum(products.values()))

#     # Create a dictionary to hold the product names and their chemical formulas
#     selectivities = {k.ID:0 for k in bst.settings.chemicals}
    
#     for k, vs in fcc_chemicals.items():
#         for v in vs:
#             if v in selectivities and k in products:
#                 selectivities[v] += products[k]/len(fcc_chemicals[k])
#             else:
#                 print(f"Warning: {v} not found in selectivities or {k} not found in products")
    
#     return selectivities

# p = get_fcc_products(3, 4)
# print("")
# print(p)
# print(sum(p.values()))
#%%


def get_system(capacity=200,prices=actual_prices, fcc_cycle=3, fcc_cycle_time=4):
    bst.main_flowsheet.set_flowsheet("Plastic Pyrolysis" + time.strftime("%Y%m%d-%H%M%S"))
    # Feed stream, HDPE plastic 
    feed = bst.Stream('HDPE_Feed',
                        HDPE=1,
                        units='kg/hr',
                        T = 298,
                            price = prices['HDPE']/1000  # 22 $/MT; divide by 1000 to get $/kg 
                            )

    feed_mass = capacity             # 250 tonnes per dat    test was 143.435 # kg/hr
    feed.set_total_flow(feed_mass, 'tonnes/day')
    feed.price = prices['HDPE']  # 22 $/MT; divide by 1000 to get $/kg

    # Natural gas and water for hydrogen production and furnace 
    sand_stream = bst.Stream('sand', Sand=100, T=25 + 273.15, P=101325, phase='s')
    natural_gas = bst.Stream('natural_gas', CH4=100, T=25 + 273.15, P=101325, phase='g')
    comb_nat_gas = bst.Stream('comb_nat_gas', CH4=100, T=25 + 273.15, P=101325, phase='g')
    natural_gas.price = prices["NG"]
    comb_nat_gas.price = prices["NG"]
    water = bst.Stream('water',H2O = 100, T=25 + 273.15, P=101325, phase='l')

    # Oxygen for autothermal pyrolysis at 7% equivalence ratio
    pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen',O2=1,units='kg/hr',T=298,price=0.000)
    oxygen_mass = 0.07 * feed_mass * 100/93   # 7% equivalence ratio from Polin et al. 2019
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    # fluidizing gas for the reactor
    fluidizing_gas = bst.Stream('fluidizing_gas',N2=1,units='kg/hr',T=298,price=0.000)
    fluidizing_gas_mass = 15   # fluidizing gas is 20kg/hr for now
    fluidizing_gas.set_total_flow(fluidizing_gas_mass, 'kg/hr')



    recycle = bst.Stream('recycle')
    char_sand = bst.Stream('S108')
    CRHDPE = bst.Stream('S104')
    rec_NCG = bst.Stream('S235')
    hydrocracked = bst.Stream('Cracked_HC')

    ref_Methane = bst.Stream('Methane_ref',Methane=1,units='kg/hr',T= 298,price=0.000)
    ref_Methane.set_total_flow(911*2,units="kg/hr")
    ref_Methane.T = 273.15 - 90

    ref_Methane2 = bst.Stream('Methane_ref2',Methane=1,units='kg/hr',T= 298,price=0.000)
    ref_Methane2.set_total_flow(911*2,units="kg/hr")
    ref_Methane2.T = 273.15 - 90

    ref_ethane = bst.Stream('ethane_ref',Ethane=1,units='kg/hr',T= 298,price=0.000)
    ref_ethane.set_total_flow(911,units="kg/hr")
    ref_ethane.T = 273.15 - 50



    ref_Tetrafluoroethane = bst.Stream('Tetrafluoroethane_ref',Tetrafluoroethane=1,units='kg/hr',T= 298,price=0.000)
    ref_Tetrafluoroethane.set_total_flow(250,units="kg/hr")
    ref_Tetrafluoroethane.T = 273.15 - 50

    ref_Propane = bst.Stream('Propane_ref',Propane=1,units='kg/hr',price=0.000)
    ref_Propane.set_total_flow(250,units="kg/hr")
    ref_Propane.T = 273.15 - 50

    ref_Propene = bst.Stream('Propene_ref',Propene=1,units='kg/hr',T= 298,price=0.000)
    ref_Propene.set_total_flow(1402,units="kg/hr")
    ref_Propene.T = 273.15 - 50
    ref_Propene.P = 1 * 101325
    ref_Propene.phase = 'g'


    HC_hydrogen = bst.Stream('Hydrogen',H2=1,units='kg/hr',T= 298,price=prices["Hydrogen"])


# 2.2 GJ of natural gas per tonne of HDPE needed for combustion
# 49.88 kg of NG need for 1 GJ of energy assuming 44.1 MJ/kg of NG

    #--------------------------------------------------------------------------------------------------------------
    # Pretreatment & Pyrolysis
    #--------------------------------------------------------------------------------------------------------------
    with bst.System('sys_pretreatment') as sys_pretreatment:
        # Pretreatment
        handling = Feed_handling('Handling',ins=feed,outs=("S102"))
        M1 = bst.units.Mixer('Mixer',ins = [handling-0,recycle])     # Mix for feed and recycled NCG stream
        grinder = Grinder('Grinder',ins=[M1-0],outs="S103")       #crush the feed
        CHscreen = Screen("CHScreen",ins=grinder-0,outs=[CRHDPE,recycle]) # screen the feed
        

        comb_nat_gas.set_total_flow(2.0 * 26.68 * feed.get_total_flow("tonne/hr"),units="m3/hr")
        # comb_nat_gas.set_total_flow(scenario["NG_req"] *49.88* feed.get_total_flow("tonne/hr"),units="kg/hr")
        furnace = Combustor("furnace", ins=[comb_nat_gas,sand_stream,rec_NCG,char_sand],outs=('S105'))
        M2 = bst.units.Mixer('Mixer2',ins = [CRHDPE,pyrolysis_oxygen,fluidizing_gas,furnace-0]) #mix oxygen, fluidizing gas and feed

        reactor = RYield('CFB_Reactor',ins=M2-0,outs=("S106"),yields=cpy_comp_yield,factor= 1,wt_closure=92.5)
        # separate the gas and solids in products stream
        Cyclone1 = Cyclone('Cyclone1',ins= reactor-0,outs=['S107',char_sand],efficiency=0.99)
        
        cooler1 = bst.units.HXutility('cooler', ins=Cyclone1-0, outs='S109', T=273.15 +10, rigorous=False) # rigorous = False ignores VLE calculations


    #--------------------------------------------------------------------------------------------------------------
    # product fractionation 
    #--------------------------------------------------------------------------------------------------------------

    with bst.System('sys_Product_Fractionation') as sys_product_fractionation:
        F1 = bst.units.Flash('Condenser', ins=cooler1-0, outs=('S201','S239'), P=101325, T = (cooler1-0).T)     

        H7 = bst.units.HXutility('Heater7',ins = F1-1, outs=("S232"),T = 273.15 + 150, rigorous=False)
        F3 = bst.units.Flash('FlashSeparator', ins= H7-0, outs=("S233","S234"), P= 1.01*101.325 ,T=273.15) # T = (heater4-0).T)
        K1 = bst.units.IsentropicCompressor('Compressor1',ins=F1-0,outs=("S202"),P = 2 * 101325, eta=0.8)

#         # # Reduce temperature of gas stream to 30C and then use refrigeration cycle to reduce to -40 C
        H2 = bst.units.HXutility('Heater2',ins=K1-0,outs=("S203"),T=273.15 + 30, rigorous=False)
 
        H3 = bst.units.HXprocess('evaporator_ref', ins = (ref_Propane,H2-0),outs=("","S204"), U=1000, phase0='g')
        H3_K = bst.units.IsentropicCompressor('compressor_ref',ins = H3-0,P=2 * 101325)
        H3_Con = bst.units.HXutility('condenser_ref', H3_K-0,T=273.15 - 50, V=1)
        H3_Exp = bst.units.IsenthalpicValve('expansion_device', H3_Con-0,outs=ref_Propane,P=1 * 101325)

#         # Compress the gaseous stream to 7 bars
        K2 = bst.units.IsentropicCompressor('Compressor2',ins=H3-1,outs=("S205"),P = 7 * 101325, eta=0.8) # originally 7 

        H4 = bst.units.HXprocess('evaporator_ref2', ins = (ref_ethane,K2-0),outs = ("","S206"), U=1000, phase0='g',T_lim1=273.15-50)
        # H3 = bst.units.HXprocess('evaporator_ref', ins = (ref_Propene,olu), U=1000, phase0='g',T_lim0=273.15-40)
        H4_K = bst.units.IsentropicCompressor('compressor_ref2',ins = H4-0,P=2 * 101325)
        H4_Con = bst.units.HXutility('condenser_ref2', H4_K-0,T=273.15 - 50, V=1)
        H4_Exp = bst.units.IsenthalpicValve('expansion_device2', H4_Con-0,outs=ref_ethane,P=1 * 101325) 


        H5 = bst.units.HXprocess('evaporator_ref3', ins = (ref_Methane,H4-1),outs=("","S207"), U=1000, phase0='g',T_lim1=273.15-80)
        # # H3 = bst.units.HXprocess('evaporator_ref', ins = (ref_Propene,olu), U=1000, phase0='g',T_lim0=273.15-40)
        H5_K = bst.units.IsentropicCompressor('compressor_ref3',ins = H5-0,P=2 * 101325)
        H5_Con = bst.units.HXutility('condenser_ref3', H5_K-0,T=273.15 - 50, V=1)
        H5_Exp = bst.units.IsenthalpicValve('expansion_device3', H5_Con-0,outs=ref_Methane,P=1 * 101325) 

        H5_2 = bst.units.HXprocess('evaporator_ref4', ins = (ref_Methane2,H5-1),outs=("","S208"), U=1000, phase0='g',T_lim1=273.15-90)
        H5_K2 = bst.units.IsentropicCompressor('compressor_ref3',ins = H5_2-0,P=2 * 101325)
        H5_Con2 = bst.units.HXutility('condenser_ref3', H5_K2-0,T=273.15 - 50, V=1)
        H5_Exp2 = bst.units.IsenthalpicValve('expansion_device3', H5_Con2-0,outs=ref_Methane2,P=1 * 101325) 


        F2 = bst.units.Flash('Condenser2', ins=H5_2-1, outs=("S210","S209"), P= (H5_2-1).P,T=273.15 - 110) # T = (heater4-0).T)

        P1 = bst.units.Pump('Pump',ins=F2-1,outs=("S211"),P = 25 * 101325) # 25 bars
        H6 = bst.units.HXutility('Heater6',ins = P1-0, outs=("S212"),T = 273.15 +2, rigorous=False)


        D1 = bst.units.BinaryDistillation('De_ethanizer', ins=H6-0,
                                outs=('S213',"S214"),   # ethylene
                                LHK=('C2H4', 'C3H8'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)     #  (97.2% purity)
        D1.check_LHK = False
        D1._design = lambda: None
        D1._cost = lambda: None
        def d1_spec():
            try:
                D1.run()
            except:
                pass 
        D1.add_specification(d1_spec)

        D1_spl = bst.units.Splitter("EthyleneFractionator",ins=(D1-0),outs=("S215","S216"), split={'C2H4':0.99,'CO2':0.10,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D1_spllMx = bst.units.Mixer('D1_spplMX', ins = D1_spl-0,outs= ("Ethylene"))
        ethyleneOut = (D1_spl-0)


        ethyleneOut = (D1-0)
        H8 = bst.units.HXutility('Heater8',ins = D1-1, outs=("S217"),T = 273.15 +100, rigorous=False)
        D2 = bst.units.BinaryDistillation('Depropanizer', ins=H8-0,
                                outs=('S218','S219'),   # propylene
                                LHK=('C3H8', 'C4H8'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)
        
        def d2_spec():
            try:
                D2.run()
            except:
                pass 
        D2.add_specification(d2_spec)

        
        def d2_spec():
            try:
                D2.run()
            except:
                pass 
        D2.add_specification(d2_spec)

        H9 = bst.units.HXutility('Heater9',ins = D2-0, outs=("S220"),T = 273.15 +70, rigorous=False)
        KD2 = bst.units.IsentropicCompressor('CompressorD2',ins=H9-0,outs=("S221"),P = 22 * 101325, eta=0.8) # 25 bars
        D2_spl = bst.units.Splitter("PropyleneFractionator",ins=(KD2-0),outs=("S222","S223"), split={'C3H8':0.99,'C2H4':1,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D2_spllMx = bst.units.Mixer('D2_spplMX', ins = D2_spl-0,outs= ("Propylene"))
        propyleneOut = (D2_spl-0)  

        M3 = bst.units.Mixer('Mixer3',ins = [F3-0,D2-1],outs=("S224"))    #,D2_spl-1,D1_spl-1])
        Mrec = bst.units.Mixer('Mixer_rec',ins = [D2_spl-1,F2-0,D1_spl-1],outs=rec_NCG)    #,D2_spl-1,D1_spl-1])
        D3 = bst.units.BinaryDistillation('Debutanizer', ins=M3-0,
                                outs=('S225','S226'),
                                LHK =('C4H8','C10H22'),      #=('C10H22', 'C14H30'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)
        D3_mx = bst.units.Mixer('D3_MX',ins = D3-0,outs=("Butene"))
        buteneOut = (D3-0)

        D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1,
                    outs=('S227',"S228"),
                    LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                    y_top=0.99, x_bot=0.01, k=2,
                    is_divided=True)  
        D4.check_LHK = False

        # D5 = bst.units.BinaryDistillation('DieselSplitter', ins=D4-1,
        #                         outs=('S229','S230'),
        #                         LHK =('C14H30','C24H50'),      #=('C10H22', 'C14H30'),
        #                         y_top=0.99, x_bot=0.01, k=2,
        #                         is_divided=True)
        # M4 = bst.units.Mixer('Mixer4',ins = [F3-1,D5-1],outs=())

    #--------------------------------------------------------------------------------------------------------------
    # Hydrogen production 
    #--------------------------------------------------------------------------------------------------------------
        # with bst.System('sys_Hydrogen_Production') as sys_hydrogen_production:
        #     smr_catalyst = bst.Stream('H2_production_catalyst',Nickel_catalyst = 1 , units='kg/hr')
        #     smr_catalyst.price = prices["Hydrogen plant catalyst"]

        #     smr_pre = SteamReformer("Steam_Reformer", ins = (natural_gas,water,smr_catalyst),outs=())
        #     M5 = bst.units.Mixer('Mixer5',ins=(smr_pre-0,smr_pre-1),outs=())
        #     smr = bst.units.MixTank('Hydrogen_production', ins=(M5-0),outs=('H2andCO2'))
        #     hydrogenPSA = bst.units.Splitter("PSA",ins=(smr-0),outs=("","Other_Gases"), split={'H2':0.99,})  
    #     ["","Other gases"]
    #--------------------------------------------------------------------------------------------------------------
    # Hydrocracking Unit 
    #--------------------------------------------------------------------------------------------------------------
    # Hydrocracking catalyst calculation (reactor 1  + reactor 2)/(catalyst life year * feed (MT/day) * 365 * stream factor)
    # Hydrocracker details from Dutta et al. 2015. Liquid feed = 16,654 lb/hr;Total H2 feed = 2109 lb/hr; H2 purity = 90%, Make up H2 pure = 647 lb/hr,
    # Power in KW/hr for hydroprocessing 1811, hydrocracking electrucak cpnsumption 369kw, recycle compressor = 31
   
        with bst.System('sys_cat_cracking') as sys_cat_cracking:           
            cracking_catalyst = bst.Stream('cracking_catalyst',Zeolite = 1 , units='lb/hr')
            cracking_catalyst.set_total_flow(200,"kg/hr")
            cracking_catalyst.price = prices["Hydrocracking catalyst"]    # Need to update to Cat_cracking price        
            air = bst.Stream('air', phase='g')
            # catalyst = bst.Stream('catalyst', phase='s')
            steam = bst.Stream('steam', phase='g')
            # reaction = bst.Reaction(
            #     f'LightPyrolysisOil -> {products}',
            #     reactant='LightPyrolysisOil', X=1.,
            #     riser_product_residence_time = 0.095 / 3600,
            #     correct_mass_balance=True
            # )
            # catalytic_cracking_reaction = bst.Reaction([])
            
            # tmo.ParallelReaction([
            # tmo.Reaction('3C24H50 +  2C6H6 -> 7C10H22 + 2C7H8 + 7C2H4',  reactant='C24H50',  X=0.49,
            #     correct_mass_balance=True),
            # tmo.Reaction('6C24H50 -> 4C14H30 + 10C7H8 + 10C6H6 + 5C2H4',  reactant='C24H50',  X=0.49,
            #     correct_mass_balance=True),
            # tmo.Reaction(' 56C40H82 -> 149C10H22 + 26C7H8 + 5C6H6 + 15C2H4',  reactant='C40H82',  X=0.49,
            #     correct_mass_balance=True),
            # tmo.Reaction('74C40H82 -> 191C14H30 + 26C7H8 + 13C6H6 + 13C2H4',  reactant='C40H82',  X=0.49,
            #     correct_mass_balance=True),  
            # ]) 

            catalytic_cracking_reaction = tmo.ParallelReaction([
                tmo.Reaction('C11H24 -> C2H6 + C9H18',  reactant='C11H24',  X=0.85, correct_mass_balance=True),
                tmo.Reaction('C8H16 -> C2H4 + C6H12',  reactant='C8H16',  X=0.85, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C3H8 + C8H16',  reactant='C11H24',  X=0., correct_mass_balance=True),
                tmo.Reaction('C9H18 -> C3H6 + C6H12',  reactant='C9H18',  X=1.0, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C4H10 + C7H14',  reactant='C11H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C12H24 -> C4H8 + C8H16',  reactant='C12H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C12H26 -> C4H8 + C8H18',  reactant='C12H26',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C4H8 -> C4H6 + H2',  reactant='C4H8',  X=1.0, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C5H12 + C6H12',  reactant='C11H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C6H14 + C5H10',  reactant='C11H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C7H14O2 -> C6H14 + CO2',  reactant='C7H14O2',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C7H16 + C4H8',  reactant='C11H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C16H32 -> 2C8H16',  reactant='C16H32',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C11H24 -> C8H18 + C3H6',  reactant='C11H24',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C15H30 -> C9H18 + C6H12',  reactant='C15H30',  X=0.7, correct_mass_balance=True),
                tmo.Reaction('C24H50 -> C12H26 + C12H24',  reactant='C24H50',  X=0.999, correct_mass_balance=True),
                tmo.Reaction('C40H82 -> C20H42 + C20H40',  reactant='C40H82',  X=0.999, correct_mass_balance=True),
                tmo.Reaction('C20H42 -> C10H22 + C10H20',  reactant='C20H42',  X=0.999, correct_mass_balance=True),
                tmo.Reaction('C8H16 -> C8H8 + 4H2',  reactant='C8H16',  X=0.3, correct_mass_balance=True), # Styrene production
                tmo.Reaction('C8H16 -> C8H10 + 3H2',  reactant='C8H16',  X=0.3, correct_mass_balance=True), # Ethylbenzene production
                tmo.Reaction('C9H18 -> C9H10 + 4H2',  reactant='C9H18',  X=0.3, correct_mass_balance=True), # Methylstyrene production
                tmo.Reaction('C10H22 -> C10H8 + 7H2',  reactant='C10H22',  X=0.2, correct_mass_balance=True), # Naphthalene production
                tmo.Reaction('C10H20 -> C10H8 + 6H2',  reactant='C10H20',  X=0.2, correct_mass_balance=True), # Naphthalene production
                tmo.Reaction('C20H40 -> 2C10H20',  reactant='C20H40',  X=1.0, correct_mass_balance=True),
            ]) # Catalytic cracking reactions based on Yadav et al. 2023, and Dutta et al. 2015
            hydro_crack = FluidizedCatalyticCracking("Cat_cracking",ins=(F3-1,cracking_catalyst,air,steam),reaction=catalytic_cracking_reaction)
            # hydro_crack._design = lambda: None 
            # hydro_crack._cost = lambda: None
            

            cat_crack = bst.units.MixTank('Cat_cracking_Unit', ins=(hydro_crack-0,hydro_crack-1),outs=()) #hydrocracking_catalyst),outs=())
            splitter1 = bst.units.Splitter("H2split",ins=(cat_crack-0),outs=("ExcessH2"), split={'H2':0.99,})
            H2excess = (splitter1-0)
            # Olumide supplied H2 for Hydrocracking, and removed the excess H2 from the system
            # We use steam and air, so we need to remove the excess water out of the system
            splitter2 = bst.units.Splitter("water_split",ins=(splitter1-1),outs=("ExcessH2O"), split={'water':0.99,})
            # cat_monitor = bst.units.Mixer('cat_monitor',ins=(hydrocracking_catalyst-0),outs=('outlet'))

            D6 = bst.units.BinaryDistillation('NaphthaSplitter2', ins=splitter2-1,
                                    outs=("S302",""),
                                    LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                                    y_top=0.99, x_bot=0.01, k=2,
                                    is_divided=True)
            D6.check_LHK = False
            D6._cost = lambda: None
            D6._design = lambda: None # ToDo: check the cost calculation for D6
            D7 = bst.units.BinaryDistillation('DieselSplitter2', ins=D6-1,
                                    outs=("S303","S304"),
                                    LHK =('C14H30','C24H50'),      #=('C10H22', 'C14H30'),
                                    y_top=0.99, x_bot=0.01, k=2,
                                    is_divided=True)
            D7_mx = bst.units.Mixer('D7_MX',ins = D7-1,outs=("Wax"))

            waxOut = (D7-1)

# Consolidate product streams
        M6 = bst.units.Mixer('mix_Naphtha_out',ins=(D4-0,D6-0),outs=("Naphtha"))
        naphthaOut = (M6-0)

        M7 = bst.units.Mixer('mix_Diesel_out',ins=(D4-1,D7-0),outs=("Diesel"))
        dieselOut = (M7-0)

    #  Create system
    sys = bst.main_flowsheet.create_system('sys')

    


    for stream in sys.products:
        try:
            stream.price = prices[str(stream)]
        except:
            pass

    return sys

#%%
system = get_system(capacity=200, prices=actual_prices)
system.diagram(format="png")
#%%
system.simulate()
# %%
system.flowsheet.unit["Cat_cracking"]

# %%
tea = get_tea(system)

gasoline = tea.system.flowsheet.stream["Naphtha"]
msp = tea.solve_price(gasoline)
msp
#%% 
print("Calculating the Contribution of Each Cost/Revenue Item to the Minimum Selling Price (MSP) using")
{k: v/gasoline.get_total_flow("tonnes/year") for k, v in tea.mfsp_table(gasoline).items()}
#%% 
print("Final Output Streams (Products):")
for s in system.products:
    print(f"- {s.ID}: {s.F_mass:.2f} kg/hr (Price: ${s.price:.4f}/kg)")

#%% 
print("Final Input Streams:")
for s in system.feeds:
    print(f"- {s.ID}: {s.F_mass:.2f} kg/hr (Price: ${s.price:.4f}/kg)")
# No uncertainty analysis, due to fixed reactions
#%%
# get_fcc_products(3, 4)
# # %%
# # FCC uncertainty analysis
# msps = []
# for i in range(3000):
#     try:
#         cycle = 3 + np.random.normal(0, 1)
#         cycle_time = 4 + np.random.normal(0, 1)
#         system = get_system(capacity=200, prices=actual_prices, fcc_cycle=cycle, fcc_cycle_time=cycle_time)
#         system.simulate()
#         tea = get_tea(system)
#         gasoline = tea.system.flowsheet.stream["Naphtha"]
#         msp = tea.solve_price(gasoline)
#         msps.append(msp)
#     except Exception as e:
#         print(f"Error in iteration {i}: {e}")
# # msps
# # %%
# df = pd.DataFrame(msps, columns=["MSP"])
# df.to_csv("fcc_msp_uncertainty.csv", index=False)
# # %%
# df = pd.read_csv("fcc_msp_uncertainty.csv")
# # %%
# (
#     ggplot(df, aes(x='MSP')) +
#     geom_histogram(bins=30, fill='blue', color='black', alpha=  0.7) +
#     labs(title='FCC MSP Uncertainty Analysis', x='MSP ($/tonne)', y='Frequency') +
#     theme_tufte() +
#     theme(text=element_text(size=14)) +
#     #background
#     theme(panel_background=element_rect(fill='white', color='black'),
#           plot_background=element_rect(fill='white', color='black'),
#           panel_grid_major=element_line(color='lightgrey'),
#           panel_grid_minor=element_line(color='lightgrey'))
# )
# # %%
#%%
system.flowsheet.stream["s17"].show()
# %%

"""
Connected to myenvNew (Python 3.10.13)

Labor cost: 2021000

FluidizedCatalyticCracking: Cat_cracking
ins...
[0] S234  from  Flash-FlashSeparator
    phase: 'l', T: 273.15 degK, P: 102.338 Pa
    composition (%): CO      7.9e-15
                     H2      2.29e-27
                     CH4     8.18e-10
                     C2H4    5.65e-06
                     C3H8    0.00211
                     C4H8    0.00724
                     C10H22  2.29
                     C14H30  1.54
                     C24H50  43.3
                     C40H82  52.9
                     ------  7.37e+03 kg/hr
[1] cracking_catalyst  
    phase: 'l', T: 298.15 degK, P: 101325 Pa
    composition (%): Zeolite  100
                     -------  0.00737 kg/hr
[2] air  
    phase: 'g', T: 298.15 degK, P: 101325 Pa
    composition (%): O2  21
                     N2  79
                     --  2.01e+03 kg/hr
[3] steam  
    phase: 'g', T: 412.19 degK, P: 344738 Pa
    composition (%): water  100
                     -----  9.22e+03 kg/hr
outs...
[0] s15  to  MixTank-Cat_cracking_Unit
    phase: 'g', T: 412.11 degK, P: 162120 Pa
    composition (%): CO      3.51e-15
                     H2      0.0203
                     CH4     3.64e-10
                     C2H4    2.51e-06
                     C3H8    0.00094
                     C4H6    0.0031
                     C12H26  9.66
                     C10H22  0.813
                     C12H24  9.55
                     C14H30  0.684
                     C20H42  11.8
                     C20H40  11.7
                     C10H8   0.183
                     C24H50  0.0192
                     C40H82  0.0235
                     water   55.6
                     ------  1.65e+04 kg/hr
[1] s16  to  MixTank-Cat_cracking_Unit
    phase: 'l', T: 454.58 degK, P: 242155 Pa
    composition (%): Zeolite  100
                     -------  0.00737 kg/hr
[2] s17  
    phase: 'g', T: 454.58 degK, P: 242155 Pa
    composition (%): O2     14.1
                     N2     75.9
                     water  4.53
                     CO2    5.5
                     -----  2.09e+03 kg/hr
1.771450183992711
#%% 
print("Calculating the Contribution of Each Cost/Revenue Item to the Minimum Selling Price (MSP) using")
{k: v/gasoline.get_total_flow("tonnes/year") for k, v in tea.mfsp_table(gasoline).items()}

{'HDPE_Feed': 103.15162417714514,
 'Other': 0.12450969783087697,
 'comb_nat_gas': 57.5209786229306,
 'Utilities': 194.49411330707886,
 'O&M': 442.73402948280614,
 'Depreciation': 867.1532342176083,
 'Propylene': -5.349641182375667,
 'Diesel': -711.5929509151422,
 'Butene': -90.97640025879603,
 'Ethylene': -18.63848903854211,
 'Wax': -575.2789039876685,
 'Income Tax': 498.80487595836325,
 'ROI': 1009.3032039114726}

 Final Output Streams (Products):
- Propylene: 11.16 kg/hr (Price: $0.9700/kg)
- s17: 2092.83 kg/hr (Price: $0.0000/kg)
- ExcessH2: 3.31 kg/hr (Price: $0.0000/kg)
- ExcessH2O: 9079.37 kg/hr (Price: $0.0000/kg)
- Naphtha: 1845.03 kg/hr (Price: $0.8600/kg)
- Diesel: 1714.36 kg/hr (Price: $0.8400/kg)
- Butene: 144.97 kg/hr (Price: $1.2700/kg)
- Ethylene: 61.83 kg/hr (Price: $0.6100/kg)
- Wax: 3880.68 kg/hr (Price: $0.3000/kg)

Final Input Streams:
- HDPE_Feed: 8333.33 kg/hr (Price: $0.0250/kg)
- pyrolysis_oxygen: 15.05 kg/hr (Price: $0.0000/kg)
- fluidizing_gas: 15.00 kg/hr (Price: $0.0000/kg)
- comb_nat_gas: 292.09 kg/hr (Price: $0.3985/kg)
- sand: 6008.43 kg/hr (Price: $0.0000/kg)
- cracking_catalyst: 0.01 kg/hr (Price: $34.1717/kg)
- air: 2009.88 kg/hr (Price: $0.0000/kg)
- steam: 9217.17 kg/hr (Price: $0.0000/kg)
"""