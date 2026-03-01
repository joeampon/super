import biosteam as bst
from _units import (
    MyDistillation,
    MyBinaryDistillation,
    PlasmaReactor,
    Centrifuge,
    Filtration,
    Crystalizer,
) 
from _compounds0 import *
import numpy as np
for c in chems:
    c.default()

# plasma energy is 0.111 MJ/kg
# We use this equation: powerkJkg = 0.241*feedRate^0.234/feedRate
def create_system(plasma_yields,o2in_r,co2_r, plasmaEnergy = 0.111):
    # global plasma_yields
    bst.main_flowsheet.clear()
    # plasmaEnergy = 3000  # from paper Dave and Joshi "Plasma pyrolysis and gasification of plastic waste - A review"
    # plasmaEnergy ranges from 40 to 100 MJ/kg according to Harish's measurements

    with bst.System("sys_plasma") as sys_plasma:
        plant_size = 200 # tonnes/day
        feed = bst.Stream("Plastic", Plastic=1)
        feed.set_total_flow(plant_size, "tonnes/day")

        co2in = bst.Stream("CO2", CO2=1)
        co2in.set_total_flow(plant_size * co2_r, "tonnes/day")

        o2in = bst.Stream(
            "O2",
            O2=1)
        o2in.set_total_flow(plant_size* o2in_r, "tonnes/day")

        recycle_stream = bst.Stream("recycle_stream")

        mxFeed = bst.units.Mixer('mxFeed', ins=(feed, co2in,o2in, recycle_stream)) # bmix plastic , CO2, and O2
       # mxFeed = bst.units.Mixer("mxFeed", ins=(feed, co2in))

        #Sum the values of plasma yield, and divide each value by the total to normalize each yield
        total_yield = sum(list(plasma_yields.values()))
        plasma_yields = {k: v / total_yield for k, v in plasma_yields.items()}

        rxplasma = PlasmaReactor(
            "rxPlasma",
            ins=mxFeed - 0,
            outs="",
            yields=plasma_yields,
            power=plasmaEnergy,  # # Dave and Joshi "Plasma pyrolysis and gasification of plastic waste - A review"
        )  # ToDo: Use a special plasma reactor unit

    # sys_plasma = bst.main_flowsheet.create_system('plasma_sys')
        # condense the vapor product of plasma reactor to liquid (400C to 32 C)
        hxcond = bst.units.heat_exchange.HXutility(
            "hxcond", ins=rxplasma - 0, outs=("hxcond"), T=32 + 273.15, rigorous=False
        )

       

     # sys_pha = bst.main_flowsheet.create_system('pha_sys')
    # with bst.System("sys_pha_recovery") as sys_pha_recovery:

       


        



        
    # sys_pha_recovery = bst.main_flowsheet.create_system('pha_recovery')
    # Boiling points
    # Water 373.124
    # LacticAcid 505.49
    # Polymer None
    # C8H18 391.35
    # C11H24 448.0
    # Alcohol 537.25
    # Acid 546.15
    # C18H38 589.15 Paraffins
    # C14H22O 637.0
    # C30H62 724.15
    # PLA 505.49
    # PHA 505.49
    with bst.System("HeavySeparations") as heavySeparations:

        # separate non-condensable gases to liquid oil
        # flash separator separate gas to liquid 
        gasSplit = bst.units.Flash(
            "spGasSplit", ins=hxcond - 0, outs=("", ""), # outs[0] is vapor, outs[1] is liquid 
            P = 101325,
            T= 273.15 + 200,
        )

        hxLiquids = bst.units.HXutility(  # use a heat exchanger to cool down the liquid to 32C 
            "hxLiquids",
            ins=gasSplit - 1,
            outs=(""),
            T=32 + 273.15
        )
        
        # flHeavy = bst.units.Flash(
        #     "flHeavy",
        #     ins=(hxLiquids- 0),
        #     T= C30H62.Tb-185,
        #     P=101325,
        # )\

        #Products
        # Paraffins (C18H38), Olefins(ethylene, propylene, butanyle, C8H16), fatty acid, alcohol(C15), Carbonyl, residue 
       #distillation columns to separate C18H38 to heavy compounds. 
        clHeavy = bst.units.ShortcutColumn(
            "clHeavy",
            ins=(hxLiquids- 0),
            outs=("", ""), # [0] is the distillate(C18H38) , in gas state, and the [1] is the liquid. 
            # LHK specify the light key and the heavy keys. The light key corresponds to the compound with lowest boiling point 
            LHK=("C18H38", "C30H62"),
            k=1.5, #reflux ratio , ratio of liquid returned to top of column  to liquid leaving columns as distillate. 
            Lr=0.98, # light key recovery is 98%, meaning 98% of C18H38 and other light compounds are recovered at top
            Hr=0.98, # heavy recovery, 98% of heavy compounds recoved at bottom of columns 
        )

    with bst.System("LightSeparations") as lightSeparations:
        de_propanizer_bottom = bst.Stream("de_propanizer_bottom") #create new stream 
        mxHeavy = bst.units.Mixer("mxHeavy", ins=(clHeavy-0, de_propanizer_bottom)) # mix of distillate from clHeavy columns with de_propanoizer stream


        # Use a distillation columns to separate C8H18(LK) to alcohols. 
        deButanizer = bst.units.ShortcutColumn( 
            "deButanizer",
            ins=(mxHeavy- 0),  
            outs=("", ""),
            LHK=("C8H18", "Alcohol"),
            k=1.5,
            Lr=0.95, #95% of C8H18 is recovered at the top 
            Hr=0.95,
        )
        deButanizer.check_LHK = False # check_LHK check whether the LK and HK present in the input stream. set at False to disable verification 
        
        hxLights = bst.units.HXutility(
            # light keys (distillate gas @boiling temperature of C8H18), Temperature decrease to 32 celcius 
            "hxLights",
            ins=deButanizer - 0,  
            outs=("FlueGases2"), # output is flue gas 
            T=32 + 273.15,
        )
        # heavy keys(95% alcohols and other heavy compounds(C14,C18), and ~5% C8H18) from debutanizer is further separated using distillation
        # carbonyl C14H22O is separated from mixture 
        clC14 = bst.units.ShortcutColumn(
            "clCarbonyls",
            ins=(deButanizer - 1), # input is the heavy compounds - Alcohols from debutanizer
            outs=("", ""),
            LHK=("C14H22O", "C18H38"),
            k=1.5,
            Lr=0.95,
            Hr=0.95,
        )
        clC14.check_LHK = False

        def carbonyls():
            try:
                clC14._run()
            except:
                for c in clC14.ins[0].available_chemicals:
                    if c.Tb < 552.15:
                        clC14.outs[0].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.95
                        clC14.outs[1].imass[c.ID] = clC14.ins[0].imass[c.ID] * (1-  0.95)
                    else:
                        clC14.outs[0].imass[c.ID] = clC14.ins[0].imass[c.ID] * 0.05
                        clC14.outs[1].imass[c.ID] = clC14.ins[0].imass[c.ID] * (1-  0.05)
        clC14.add_specification(carbonyls)  

            


        hxCarbonyls = bst.units.HXutility(
            "hxCarbonyls", ins=clC14 - 0, outs=("Carbonyls1"), T=32 + 273.15, rigorous=False # Carbonyl C14 is condensed to liquid 
        )

        

    with bst.System("HeavyCracking") as heavyCracking:
        heavyColumn = bst.units.ShortcutColumn(
            # Separate C18H38 from mixture. The input is the heavy key of the clc14 distillation
            "clHeavy2",
            ins=(clC14 - 1),
            outs=("", ""),
            LHK=("C18H38", "C30H62"),
            k=1.5,
            Lr=0.98,
            Hr=0.98,
        )
        heavyColumn.check_LHK = False

        hxC30 = bst.units.HXutility( # decrease temperature of heavy keys (c30h62) to 32 C 
            "hxC30",
            ins=heavyColumn - 1,
            outs=("C30"),
            T=32 + 273.15,
        )

        # Steam Methane reforming 
         # Heavy key from the ClHeavy ( C30 and other heavy compounds) are pumped 
        ppHeavy = bst.units.Pump("ppHeavy", ins=clHeavy-1, outs="HeavyOil")

        # h2In = bst.Stream("h2In", H2=1)
        ngIn = bst.Stream("ngIn", CH4=1) # stream for natural gas 
        # natural gas is compressed and reach P=20*Patm. NG in VLE 
        cpReformer = bst.units.IsentropicCompressor(
            "cpReformer",
            ins=ngIn,
            outs=(""),
            P=20*101325,
            vle=True  # vapor-liquid equilibrium 
        )

        waterIn = bst.Stream("waterIn", Water=1) # stream for water 
        #Increase the pressure of water to 20Patm,
        ppReformer = bst.units.Pump(
            "ppReformer",
            ins=waterIn,
            outs=(""),
            P=20*101325,
        )

        rxReformer = bst.units.MixTank(
            "rxReformer", # reaction of  NG and water for half an hour in mixtank
            ins=(cpReformer- 0, ppReformer-0),
            outs=(""),
            tau=0.5,
        )
        # define reaction for steam methane reforming process 
        def reforming():
            rxReformer._run()
            # 2 wt.% H2/kg of oil; 16/4 kg CH4/kg H2; 90% reforming efficiency; 80% H2 recovery
            ngIn.F_mass = ppHeavy.outs[0].F_mass*0.02*16/4/0.9/0.8 # specifying the total mass rate of input NG
            waterIn.F_mol = ngIn.F_mol*2 # 2:1 water to methane ratio for steam reforming
            rxn = bst.Reaction("CH4+H2O->CO+3H2 ", reactant="CH4", X=0.9) # 90% of CH4 is converted 
            rxn(rxReformer.outs[0])
        rxReformer.add_specification(reforming)

        # split H2 and CO2. 
        # one outlet stream contain 80% H2, and other stream contains 100% CO and 20% H2
        psa = bst.units.Splitter(
            "psa",
            ins=rxReformer- 0,
            split={
                "H2": 0.8,
            })

        #hydrocracking:
        # hydrocracking reaction of heavy oil C30 and hydrogen 
        hcReactor = bst.units.MixTank(
            "Hydrocracker",
            ins=(ppHeavy- 0, psa-0),
            outs=("HydrocrackedOil"),
            tau=0.5,
        )
        # specify hydrocracking reaction
        def hydrocracking():
            hcReactor._run()
            # h2In.imass["H2"] = 0.02*ppHeavy.outs[0].F_mass # 2 wt.% H2 is typical rate for hydrocracking (may need reference or in Olumide's paper)
            rxn = bst.Reaction("3C30H62+2H2->5C18H38 ", reactant="C30H62", X=0.95)
            rxn(hcReactor.outs[0])
        hcReactor.add_specification(hydrocracking)


        hcFlash = bst.units.Flash( # separate vapor from reaction products
            "hcFlash",
            ins=hcReactor- 0,
            outs=("FlueGas3",""), # output is flue gas and a liquid of light HCs(CH18H38)
            T= 273.15 + 40,
            P=101325,
        )


        mxDiesel = bst.units.Mixer("mxParaffins", ins=(hcFlash- 1, heavyColumn-0)) #mix output pf heavyclomun[0] which contain C18h38, paraffins mixture 

        # HX to cool paraffins stream to 32 C  
        hxParaffins = bst.units.HXutility(
            "hxParaffins",
            ins=mxDiesel - 0,
            outs=("Paraffins1"),
            T=32 + 273.15,
        )

   # Recovery of light compounds- non-condensable gases
    with bst.System("LightRecovery") as lightRecovery:
        # Increase pressure of vapor through compressor
        cpOlefins = bst.units.IsentropicCompressor(
            "cpOlefins",
            ins=gasSplit - 0, # vapor stream from gasSplit
            P=2*101325,
        )

         # boiling point of ethane is -88 C
         #boiling point of propane is -42 C
         #Heat exhchange between coolant and streams. Stream temperature is cooled down to -42 C.
         # At this temperature, propane change phase to liquid 
        HX1 = bst.HXutility("evaporator1",ins = (cpOlefins-0), T=273.15-42) 
        #At second evaporator, The stream is further cooled down to -88C
        # At this temperature, ethane change phase to liquid 
        HX2 = bst.HXutility("evaporator2",ins = (HX1-0), T=273.15-88) # add propane stream with T = 273.15 -42
        # Isentropic compressor will increase pressure and temperature of streams 
        C2 = bst.units.IsentropicCompressor("cp2",ins=HX2-0,outs=(""),P=2*101325,eta = 0.7, vle=True) #efficiency 70%
        # Condensation phase: gas condense to liquid at higher boiling temperature since pressure increases.
        HXc2 = bst.units.HXutility("cond2",ins=C2-0,T = 273.15-45) #propane boiling point is -42C
        # V2 = bst.units.IsenthalpicValve("valve2", ins = HXc2, outs = propyl, P = 1*101325)
        HX2c2 = bst.units.HXutility("cond3",ins=HXc2-0, T = 273.15-50) #propane boiling point is -42C
        HX3c2 = bst.units.HXutility("cond4",ins=HX2c2-0, T = 273.15-60) #propane boiling point is -42C
        # stream is a mixture of liquid propane, liquid ethane and some other liquid compounds, and some C gases 
        
        #Flash separator operating at -78 celcius (CO2 boilig point) to separate C gases to liquid mixture 
        flash1 = bst.units.Flash("Flash", ins = HX3c2-0, outs = ("RecycleCO2",), T= 273.15-78, P=(HX3c2-0).P )#separate C gases to mixture
        P1 = bst.units.Pump("pump", ins =flash1-1,P=25*101325) # liquid from flash1 is pumped to HX, P = 25 atm 
        # HX to increase temperature of stream to 2 C
        HX3 = bst.units.HXutility("heater", ins= P1-0, T= 273.15+2) # rigourous=False, means no vapor-liquid equilibrium


        # Olefins separation from mixture 
        dist1 = bst.units.ShortcutColumn(
            "clEthanizer",
            ins=(HX3 - 0),
            outs=("", ""),
            LHK=("C8H18", "Alcohol"),
            k=1.5,
            Lr=0.99,
            Hr=0.98,
        )
        #additional separation to purify olefins stream and remove other compounds 
        ethylene_factionator = bst.units.ShortcutColumn(
            "clEthylene",
            ins=(dist1 - 0),
            outs=("Olefins1",""),
            LHK=("C8H18", "Alcohol"),
            k=1.5,
            Lr=0.99,
            Hr=0.99,
        )
        ethylene_factionator.check_LHK = False
        
        # Propylene separation
        HX4 = bst.units.HXutility("heater2", ins= dist1-1, outs ="S8", T= 273.15+50, rigorous = False) # heavy keys from dist1 is heated 

        dist2 = bst.units.ShortcutColumn( #Separate alcohols from mixture 
                    "De_propanizer",
                    ins=(HX4 - 0),
                    LHK=("Alcohol", "C14H22O"),
                    outs=("", de_propanizer_bottom),
                    k=1.5,
                    Lr=0.98,
                    Hr=0.98,
                )
        dist2.check_LHK = False
        
        HX5 = bst.units.HXutility("heater3", ins= dist2-0,  T= 273.15+30, rigorous = False) # light keys(alcohols)
        C3 = bst.units.IsentropicCompressor("cp3", ins = HX5-0,  P = 25*101325, eta = 0.7) # increase pressure by 25
        clAlcohol = bst.units.ShortcutColumn(
                    "clAlcohol",
                    ins=(C3 - 0),
                    outs=("Alcohols1", ""), # separe alcohols from acids 
                    LHK=("Alcohol", "Acid"),
                    P =  25*101325,
                    k=1.5,
                    Lr=0.95,
                    Hr=0.95,
                )
        clAlcohol.check_LHK = False

        clAcid = bst.units.ShortcutColumn(
                    "clAcid",
                    ins=(clAlcohol - 1),
                    outs=("", "Acids1"),
                    LHK=("Alcohol", "Acid"), # Recover acids 
                    P =  25*101325,
                    k=1.5,
                    Lr=0.98,
                    Hr=0.98,
                )
        
        recycle_mixer = bst.units.Mixer("recycle_mixer", ins = ( clAcid-0, ethylene_factionator-1, flash1-0)) # mix remaining streams
        
        recycle_splitter = bst.units.Splitter("recycle_splitter", ins = recycle_mixer-0, outs = (recycle_stream, ""), split = 0.9) #Splitter to separate recycle stream 

        fluegas_mixer = bst.units.Mixer("flueGasMixer", # flue gas mix 
                                        ins = (
                                            recycle_splitter-1,
                                            hcFlash-0,
                                            hxLights-0,
                                            psa-1
                                        ),
                                        outs="FlueGases",
                                        )

    # boiler turbine generator to generate electricity from feed 
    # [0] Liquid/solid feed that will be burned.

    # [1] Gas feed that will be burned.

    # [2] Make-up water.

    # [3] Natural gas to satisfy steam and power requirement.

    # [4] Lime for flue gas desulfurization.

    # [5] Boiler chemicals.

    # [0] Total emissions produced.

    # [1] Blowdown water.

    # [2] Ash disposal.
    pf2 = bst.Stream("ProcessFuel2")
    mw = bst.Stream("MakeupWater")
    ng = bst.Stream("NaturalGasH")
    lime = bst.Stream("Lime")
    bc = bst.Stream("BoilerChemicals")
    ash = bst.Stream("AshDisposal")
    emissions = bst.Stream("Emissions")
    boilerBlowdown = bst.Stream("BoilerBlowdown")

    btg = bst.facilities.BoilerTurbogenerator("HRSG", ins=(fluegas_mixer-0, pf2, mw, ng, lime, bc), outs=(emissions, boilerBlowdown, ash), turbogenerator_efficiency=0.85,
                                              satisfy_system_electricity_demand=False) 


 
    # sys_oil_recovery = bst.main_flowsheet.create_system('oil_recovery_sys')

    # sys_plasma-0-6-sys_pha
    # sys_oil_recovery.ins[0] = sys_plasma.outs[1]

    sys = bst.main_flowsheet.create_system("sys")
    sys.track_recycle(recycle_stream) # recycle back to the plasma reactor 

    
    def column_costs(unit):
        unit.installed_costs = {}
        unit.installed_costs["Column"] = 1264000*(unit.ins[0].get_total_flow("tonne/hr") / 4.37) ** 0.6

    def hydrocracker_costs(unit):
        unit.installed_costs = {}
        unit.installed_costs["Hydrocracker"] = 556/585.7*1.43*6046000*(unit.ins[0].get_total_flow("lb/hr") / 55000) ** 0.7

    sys.flowsheet.unit["clAlcohol"]._design = lambda: 0
    sys.flowsheet.unit["clAlcohol"]._cost = lambda: column_costs(sys.flowsheet.unit["clAlcohol"])
    sys.flowsheet.unit["clAcid"]._design = lambda: 0
    sys.flowsheet.unit["clAcid"]._cost = lambda: column_costs(sys.flowsheet.unit["clAcid"])
    sys.flowsheet.unit["clCarbonyls"]._design = lambda: 0
    sys.flowsheet.unit["clCarbonyls"]._cost = lambda: column_costs(sys.flowsheet.unit["clCarbonyls"])
    sys.flowsheet.unit["Hydrocracker"]._design = lambda: 0
    sys.flowsheet.unit["Hydrocracker"]._cost = lambda: hydrocracker_costs(sys.flowsheet.unit["Hydrocracker"])
   
    # sys = bst.main_flowsheet.create_system('sys')
    # sys.track_recycle(waterRecycle)

    return sys
