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

bst.preferences.update(flow='kg/hr', T='degK', P='Pa', N=100, composition=True)

def create_system(
        F3=bst.Stream('F3'),
        HC_hydrogen=bst.Stream('HC_hydrogen', H2=1, units='kg/hr')
        ):
    prices ={
        "Hydrocracking catalyst": 15.5 * 2.20462262
    }
    with bst.System('sys_Hydrocracking') as sys:
        K3 = Compressor('Compressor3', ins=HC_hydrogen, outs=("S301"), P=89.7 * 101325, eta=0.8)
        hydrocracking_catalyst = bst.Stream('hydrocracking_catalyst', Zeolite=1, units='lb/hr')
        hydrocracking_catalyst.set_total_flow(200, "kg/hr")
        hydrocracking_catalyst.price = prices["Hydrocracking catalyst"]
        hydro_crack = Hydrocrack("Hydrocracking", ins=(F3-1, K3-0, hydrocracking_catalyst))
        hydrocrack = bst.units.MixTank('Hydrocracking_Unit', ins=(hydro_crack-0, hydro_crack-1), outs=())
        splitter1 = bst.units.Splitter("H2split", ins=(hydrocrack-0), outs=("ExcessH2"), split={'H2':0.99,})
        D6 = bst.units.BinaryDistillation('NaphthaSplitter2', ins=splitter1-1, outs=("S302",""), LHK=('C10H22','C14H30'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
        D7 = bst.units.BinaryDistillation('DieselSplitter2', ins=D6-1, outs=("S303","S304"), LHK=('C14H30','C24H50'), y_top=0.99, x_bot=0.01, k=2, is_divided=True)
        D7_mx = bst.Mixer('D7_MX', ins=D7-1, outs=("Wax"))

        M6 = bst.units.Mixer('mix_Naphtha_out', ins=(D6-0), outs=("Naphtha"))
        M7 = bst.units.Mixer('mix_Diesel_out', ins=(D7-0), outs=("Diesel"))

    sys = bst.main_flowsheet.create_system('sys')

    return sys
