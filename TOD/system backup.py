import time
import biosteam as bst
import thermosteam as tmo

from ._compounds import *
from ._Hydrocracking_Unit import *
from ._Hydrogen_production import *
from ._Grinder import *
from ._CHScreen import *
from ._RYield import *
from ._Cyclone import *
from ._Sand_Furnace import *
from ._UtilityAgents import *
from ._process_yields import *
from ._Compressor import *
from ._feed_handling import *
from ._teapyrolysis import *

bst.nbtutorial()
bst.settings.CEPCI = 596.2

for c in compounds:
    c.default()

bst.HeatUtility().cooling_agents.append(NH3_utility)
bst.HeatUtility().heating_agents.append(Liq_utility)
bst.HeatUtility().heating_agents.append(Gas_utility)

bst.preferences.update(flow='kg/hr', T='degK', P='Pa', N=100, composition=True)

actual_prices = {
    "HDPE": 25.05/1000,
    "Ethylene": 0.61,
    "Propylene": 0.97,
    "Butene": 1.27,
    "Naphtha": 0.86,
    "Diesel": 0.84,
    "Wax": 0.3,
    "NG": 7.40 * 1000 * 1.525/28316.8,
    "Hydrocracking catalyst": 15.5 * 2.20462262,
    "Hydrotreating catalyst": 15.5 * 2.20462262,
    "Hydrogen plant catalyst": 3.6/885.7,
    "Hydrogen": 2.83,
}

bst.settings.electricity_price = 0.065

cpy = {"Technology":"CPY","Hydrocracking": "No", "Yield": cpy_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"low"}
cpy_hc = {"Technology":"CPY","Hydrocracking": "Yes", "Yield": cpy_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" : "low"}
tod = {"Technology":"TOD","Hydrocracking": "No", "Yield": tod_comp_yield, "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"low"}
tod_hc = {"Technology":"TOD","Hydrocracking": "Yes", "Yield": tod_comp_yield,"Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"low"}
hrt = {"Technology":"CPY","Hydrocracking": "No", "Yield": hrt_comp_yield, "Reactor size" : 1, "wt_closure": 92.5, "NG_req":2.0,"residence_time" :"high"}
hrt_hc = {"Technology":"CPY","Hydrocracking": "Yes", "Yield": hrt_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"high"}

scenarios = [cpy, cpy_hc, tod, tod_hc, hrt, hrt_hc]


def run_scenario(scenario=cpy, capacity=250, prices=actual_prices):
    bst.main_flowsheet.set_flowsheet("Plastic Pyrolysis" + time.strftime("%Y%m%d-%H%M%S"))

    feed = bst.Stream('HDPE_Feed', HDPE=1, units='kg/hr', T=298, price=prices['HDPE']/1000)
    feed.set_total_flow(capacity, 'tonnes/day')
    feed.price = prices['HDPE']

    sand_stream = bst.Stream('sand', Sand=100, T=25 + 273.15, P=101325, phase='s')
    comb_nat_gas = bst.Stream('comb_nat_gas', CH4=100, T=25 + 273.15, P=101325, phase='g')
    comb_nat_gas.price = prices["NG"]

    pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen', O2=1, units='kg/hr', T=298, price=0.0)
    oxygen_mass = 0.07 * capacity * 100/93
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    fluidizing_gas = bst.Stream('fluidizing_gas', N2=1, units='kg/hr', T=298, price=0.0)
    fluidizing_gas.set_total_flow(15, 'kg/hr')

    recycle = bst.Stream('recycle')
    char_sand = bst.Stream('S108')
    CRHDPE = bst.Stream('S104')
    rec_NCG = bst.Stream('S235')

    HC_hydrogen = bst.Stream('Hydrogen', H2=1, units='kg/hr', T=298, price=prices["Hydrogen"])

    with bst.System('sys_pretreatment'):
        handling = Feed_handling('Handling', ins=feed, outs=("S102"))
        M1 = bst.units.Mixer('Mixer', ins=[handling-0, recycle])
        grinder = Grinder('Grinder', ins=[M1-0], outs="S103")
        CHscreen = Screen("CHScreen", ins=grinder-0, outs=[CRHDPE, recycle])
        M2 = bst.units.Mixer('Mixer2', ins=[CRHDPE, pyrolysis_oxygen, fluidizing_gas, rec_NCG])
        reactor = RYield('CFB_Reactor', ins=M2-0, outs=("S106"), yields=scenario["Yield"], factor=scenario["Reactor size"], wt_closure=scenario["wt_closure"])
        Cyclone1 = Cyclone('Cyclone1', ins=reactor-0, outs=['S107', "S108"], efficiency=0.99)
        cooler1 = bst.units.HXutility('cooler', ins=Cyclone1-0, outs='S109', T=273.15 + 10, rigorous=False)

    with bst.System('sys_Product_Fractionation'):
        F1 = bst.units.Flash('Condenser', ins=cooler1-0, outs=('S201','S239'), P=101325, T=(cooler1-0).T)
        H7 = bst.HXutility('Heater7', ins=F1-1, outs=("S232"), T=273.15 + 150, rigorous=False)
        F3 = bst.units.Flash('FlashSeparator', ins=H7-0, outs=("S233","S234"), P=1.01*101325, T=273.15)
        K1 = bst.units.IsentropicCompressor('Compressor1', ins=F1-0, outs=("S202"), P=2 * 101325, eta=0.8)
        H2 = bst.units.HXutility('Heater2', ins=K1-0, outs=("S203"), T=273.15 + 30, rigorous=False)
        K2 = bst.units.IsentropicCompressor('Compressor2', ins=H2-0, outs=("S205"), P=7 * 101325, eta=0.8)
        F2 = bst.units.Flash('Condenser2', ins=K2-0, outs=("S210","S209"), P=(K2-0).P, T=273.15 - 110)
        P1 = bst.units.Pump('Pump', ins=F2-1, outs=("S211"), P=25 * 101325)
        H6 = bst.HXutility('Heater6', ins=P1-0, outs=("S212"), T=273.15 + 2, rigorous=False)
        D1 = bst.units.BinaryDistillation('De_ethanizer', ins=H6-0, outs=('S213',"S214"), LHK=('C2H4', 'C3H8'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
        D1.check_LHK = False
        D1_spl = bst.units.Splitter("EthyleneFractionator", ins=(D1-0), outs=("S215","S216"), split={'C2H4':0.99,'CO2':0.10,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D1_spllMx = bst.Mixer('D1_spplMX', ins=D1_spl-0, outs=("Ethylene"))
        H8 = bst.HXutility('Heater8', ins=D1-1, outs=("S217"), T=273.15 + 100, rigorous=False)
        D2 = bst.units.BinaryDistillation('Depropanizer', ins=H8-0, outs=('S218','S219'), LHK=('C3H8', 'C4H8'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
        H9 = bst.HXutility('Heater9', ins=D2-0, outs=("S220"), T=273.15 + 70, rigorous=False)
        KD2 = bst.units.IsentropicCompressor('CompressorD2', ins=H9-0, outs=("S221"), P=22 * 101325, eta=0.8)
        D2_spl = bst.units.Splitter("PropyleneFractionator", ins=(KD2-0), outs=("S222","S223"), split={'C3H8':0.99,'C2H4':1,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D2_spllMx = bst.Mixer('D2_spplMX', ins=D2_spl-0, outs=("Propylene"))
        M3 = bst.Mixer('Mixer3', ins=[F3-0, D2-1], outs=("S224"))
        Mrec = bst.Mixer('Mixer_rec', ins=[D2_spl-1, F2-0, D1_spl-1], outs=rec_NCG)
        D3 = bst.units.BinaryDistillation('Debutanizer', ins=M3-0, outs=('S225','S226'), LHK=('C4H8','C10H22'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
        D3_mx = bst.Mixer('D3_MX', ins=D3-0, outs=("Butene"))
        if scenario['Hydrocracking'] == "No":
            if scenario['residence_time'] == "high":
                D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1, outs=('S227','S228'), LHK=('C10H22','C14H30'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
                D4_mx = bst.Mixer('D4_MX', ins=D4-0, outs=("Naphtha"))
                Mdiesel = bst.Mixer('MixerDiesel', ins=D4-1, outs=("S229"))
                Md_mx = bst.Mixer('MixerDiesel_mx', ins=Mdiesel-0, outs=("Diesel"))
                Mwax = bst.Mixer('Mwax', ins=F3-1, outs=("S236"))
                Mwax_mx = bst.Mixer('Mwax_mx', ins=Mwax-0, outs=("Wax"))
            else:
                D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1, outs=('S227',"S228"), LHK=('C10H22','C14H30'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
                D4_mx = bst.Mixer('D4_MX', ins=D4-0, outs=("Naphtha"))
                D5 = bst.units.BinaryDistillation('DieselSplitter', ins=D4-1, outs=('S229','S230'), LHK=('C14H30','C24H50'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
                D5_mx = bst.Mixer('D5_MX', ins=D5-0, outs=("Diesel"))
                M4 = bst.Mixer('Mixer4', ins=[F3-1, D5-1], outs=("S236"))
                M4_mx = bst.Mixer('Mixer4_mx', ins=M4-0, outs=("Wax"))
        else:
            D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1, outs=('S227',"S228"), LHK=('C10H22','C14H30'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
            if scenario['residence_time'] == "low":
                D5 = bst.units.BinaryDistillation('DieselSplitter', ins=D4-1, outs=('S229','S230'), LHK=('C14H30','C24H50'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
                M4 = bst.Mixer('Mixer4', ins=[F3-1, D5-1], outs=())

    if scenario['Hydrocracking'] == "Yes":
        with bst.System('sys_Hydrocracking'):
            K3 = Compressor('Compressor3', ins=HC_hydrogen, outs=("S301"), P=89.7 * 101325, eta=0.8)
            hydrocracking_catalyst = bst.Stream('hydrocracking_catalyst', Zeolite=1, units='lb/hr')
            hydrocracking_catalyst.set_total_flow(200, "kg/hr")
            hydrocracking_catalyst.price = prices["Hydrocracking catalyst"]
            if scenario['residence_time'] == "low":
                hydro_crack = Hydrocrack("Hydrocracking", ins=(M4-0, K3-0, hydrocracking_catalyst))
            else:
                hydro_crack = Hydrocrack("Hydrocracking", ins=(F3-1, K3-0, hydrocracking_catalyst))
            hydrocrack = bst.units.MixTank('Hydrocracking_Unit', ins=(hydro_crack-0, hydro_crack-1), outs=())
            splitter1 = bst.units.Splitter("H2split", ins=(hydrocrack-0), outs=("ExcessH2"), split={'H2':0.99,})
            D6 = bst.units.BinaryDistillation('NaphthaSplitter2', ins=splitter1-1, outs=("S302",""), LHK=('C10H22','C14H30'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
            D7 = bst.units.BinaryDistillation('DieselSplitter2', ins=D6-1, outs=("S303","S304"), LHK=('C14H30','C24H50'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
            D7_mx = bst.Mixer('D7_MX', ins=D7-1, outs=("Wax"))

        M6 = bst.units.Mixer('mix_Naphtha_out', ins=(D4-0, D6-0), outs=("Naphtha"))
        if scenario['residence_time'] == "low":
            M7 = bst.units.Mixer('mix_Diesel_out', ins=(D5-0, D7-0), outs=("Diesel"))
        else:
            M7 = bst.units.Mixer('mix_Diesel_out', ins=(D4-1, D7-0), outs=("Diesel"))

    sys = bst.main_flowsheet.create_system('sys')

    for stream in sys.products:
        try:
            stream.price = prices[str(stream)]
        except Exception:
            pass

    return sys
