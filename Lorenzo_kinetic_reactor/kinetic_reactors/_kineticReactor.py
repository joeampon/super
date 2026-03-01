
import numpy as np
from typing import Optional
from ._kineticReactionSystem import ReactionModel
import matplotlib.pyplot as plt
import biosteam as bst

class BaseReactor(bst.Unit):
    
    _N_ins = 1 # Number of inlets
    _N_outs = 1 # Number of outlets

    #: Default operating temperature [K]
    T_default: Optional[float] = 300
    
    #: Default operating pressure [K]
    P_default: Optional[float] = None
    
    #: Default residence time [hr]
    tau_default: Optional[float] = 10
    
    #: Default maximum change in temperature for the heat exchanger loop.
    dT_hx_loop_default: Optional[float] = 10
    
    #: Default fraction of working volume over total volume.
    V_wf_default: Optional[float] = 0.8
    
    #: Default maximum volume of a reactor in m3.
    V_max_default: Optional[float] = 355
    
    #: Default length to diameter ratio.
    length_to_diameter_default: Optional[float] = 3
    
    #: Default power consumption for agitation [kW/m3].
    kW_per_m3_default: Optional[float] = 0.985
    
    #: Default cleaning and unloading time (hr).
    tau_0_default: Optional[float]  = 0
    
    #: Whether to default operation in batch mode or continuous
    batch_default = True
    
    Rendimientos_default = None
    
    Plot_profiles_default: Optional[bool]=None
    
    Design_spec_default: Optional[tuple] = None
    
    Ta_intercambio_default: Optional[float] = None
    
    modo_termico_default: Optional[str] = "isotermo"
    
    simul_default: Optional[str] = 'conversion'
    
    tau_default: Optional[float] = 10  # Default residence time in hours
    
    def _init(
            self, 
            T: Optional[float]=None, 
            P: Optional[float]=None, 
            dT_hx_loop: Optional[float]=None,
            tau: Optional[float]=None,
            V_wf: Optional[float]=None, 
            V_max: Optional[float]=None,
            length_to_diameter: Optional[float]=None, 
            kW_per_m3: Optional[float]=None,
            vessel_material: Optional[str]=None,
            vessel_type: Optional[str]=None,
            batch: Optional[bool]=None,
            tau_0: Optional[float]=None,
            adiabatic: Optional[bool]=None,
            Rendimientos: Optional[float]=None,
            ReactionModel: Optional[ReactionModel]=None,
            Design_spec: Optional[tuple] = None,
            Plot_profiles: Optional[bool]=None,
            modo_termico: Optional[str]=None,
            Ta_inetercambio: Optional[float]=None, 
            simul: Optional[str]=None,
            **kwargs
        ):
        super()._init(**kwargs)
        self.load_auxiliaries()
        self.P = self.ins[0].P
        self.T = T
        self.adiabatic = adiabatic
        self.Type_Reaction = None
        self.ReactionModel = ReactionModel
        self.Design_spec = self.Design_spec_default if Design_spec is None else Design_spec
        self.Plot_profiles = self.Design_spec_default if Plot_profiles is None else Plot_profiles
        self.sol = None
        self.modo_termico = self.modo_termico_default if modo_termico is None else modo_termico
        self.Ta_intercambio = self.Ta_intercambio_default if Ta_inetercambio is None else Ta_inetercambio
        self.simul = self.simul_default if simul is None else simul
        self.tau = tau if tau is not None else self.tau_default
        
          # Verificar conflicto entre tau y Design_spec
        if tau is not None and Design_spec is not None:
            print("⚠️  AVISO: Se han especificado tanto 'tau' como 'Design_spec'.")
            print(f"   • tau = {tau} h")
            print(f"   • Design_spec = {Design_spec}")
            print("   📋 La simulación se realizará usando 'tau' y 'Design_spec' será ignorado.")
            print("   💡 Para calcular tau, especifica solo 'Design_spec' y deja 'tau=None'.\n")
            self.Design_spec = None
    
    def _setup_reaction_system(self):
        self.c = self.ReactionModel.get_all_species()
        self.stequi = self.ReactionModel.stequi
        self.rxn = self.ReactionModel.reactions
        self.kinetics = self.ReactionModel.kinetics
        self.r = {name: func.get_function() for name, func in self.kinetics.items()}
        self.Q = self.get_caudal_vol()
        self.C0 = self._concentraciones_iniciales()
        self.F0 = self._caudales_iniciales()
        
    def get_caudal_vol(self):
        """
        Return the volumetric flow rate of the inlet stream.

        Returns
        -------
        float
            Volumetric flow rate of the inlet stream (m3/h).
        """
        has_liquid_phase = any(i.phase != 'g' for i in self.ins)
        has_gas_phase = any(i.phase == 'g' for i in self.ins)
        if has_liquid_phase and has_gas_phase:
            raise ValueError("Feed contains a mixture of phases (liquid and gas).")
        if has_liquid_phase:
            ins_F_vol = sum(i.F_vol for i in self.ins if i.phase != 'g')
        elif has_gas_phase:
            ins_F_vol = sum(i.F_vol for i in self.ins if i.phase == 'g')
        else:
            raise ValueError("No valid inlet streams.")
        
        self.Q = ins_F_vol
        return self.Q

    def _concentraciones_iniciales(self):
        """
        Calculate initial concentrations or molar flows depending on phase.
        Raises an error if input streams are a mixture of phases.
        """
        
        has_liquid_phase = any(i.phase != 'g' for i in self.ins)
        has_gas_phase = any(i.phase == 'g' for i in self.ins)
        if has_liquid_phase and has_gas_phase:
            raise ValueError("Input streams contain a mixture of liquid and gas phases.")
        if has_liquid_phase:
            ins_F_vol = sum(i.F_vol for i in self.ins if i.phase != 'g')
            self.estado = 'liquido'
        elif has_gas_phase:
            ins_F_vol = sum(i.F_vol for i in self.ins if i.phase == 'g')
            self.estado = 'gas'
        else:
            raise ValueError("No valid input streams detected.")
        
        if self.ReactionModel.conc_units == 'mol/L':
            units = 'mol/L'
        elif self.ReactionModel.conc_units == 'mg/L':
            units = 'mg/L'
        else:
            raise ValueError("Invalid concentration units specified in ReactionModel.")
        
        if units == 'mol/L':
        
            n0 = {j: sum(i.imol[j] for i in self.ins) for j in self.c}
            c_mol_L = {clave: valor / ins_F_vol for clave, valor in n0.items()}
            return c_mol_L
        
        elif units == 'mg/L':
            m0 = {j: sum(i.imass[j] for i in self.ins) for j in self.c}
            
            c_mg_L = {clave: valor / ins_F_vol * 1000 for clave, valor in m0.items()}
            return c_mg_L

    def _caudales_iniciales(self):
        """
        Return a dictionary with the initial molar flows of each species.

        Returns
        -------
        dict
            {ID: molar flow} for each species in the feed (units: kmol/h).
        """
        F0_mol = {j: sum(i.imol[j] for i in self.ins) for j in self.c}
        return F0_mol

    def _get_species_conc(self, C):
        """
        Return a dictionary with the concentrations of species, limited to physical values.

        Parameters
        ----------
        C : list or array
            Vector of species concentrations.

        Returns
        -------
        dict
            {ID: concentration} for each species, values limited between 0 and 1e6.
        """
        return {species: np.clip(C[i], 0, 1e6)
                for i, species in enumerate(self.c.keys())}

    def _get_species_flows(self, F):
        """
        Return a dictionary with the molar flows of species, limited to physical values.

        Parameters
        ----------
        F : list or array
            Vector of species molar flows.

        Returns
        -------
        dict
            {ID: molar flow} for each species, values limited between 0 and 1e6.
        """
        return {species: np.clip(F[i], 0, 1e6)
                for i, species in enumerate(self.stequi.keys())}
    
    def calcular_feed_Cp_flows(self, T):
        """
        Calculate the total heat capacity (Cp) of the mixture [J/K] at temperature T.
    
        Parameters
        ----------
        T : float
            Current temperature [K].
        concentrations : dict
            Instantaneous concentrations [mol/L] of each reactive/product species.
    
        Returns
        -------
        Cp_total : float
            Total heat capacity of the mixture [J/K], including reactives, products, and inerts.
        """
        # Cp for reactives/products (using current concentrations) 
        F0 = self._caudales_iniciales()
        
        Cp_total = sum(F0[comp] * self.c[comp].Cn(self.ins[0].phase, T, self.P)
                        for comp in self.c)
        return Cp_total
     
    def calcular_Cp(self, T: float, concentrations: dict, V: float) -> float: #TODO cambiar la phase
        """
        Calculate the total heat capacity (Cp) of the mixture [J/K] at temperature T.
    
        Parameters
        ----------
        T : float
            Current temperature [K].
        concentrations : dict
            Instantaneous concentrations [mol/L] of each reactive/product species.
        V : float
            Reactor volume [L or m3, consistent with concentrations].
    
        Returns
        -------
        Cp_total : float
            Total heat capacity of the mixture [J/K], including reactives, products, and inerts.
        """
        # Cp for reactives/products (using current concentrations)
        Cp_total = sum(
            concentrations[comp] * V * self.c[comp].Cn(self.ins[0].phase, T, self.P)
            for comp in self.c
        )
        return Cp_total

    def corriente_efluente(self, sol):
        """
        Crea una corriente de efluente a partir de las corrientes de entrada.
        """
        y = sol
        ultimos_valores = {compuesto:   y[i] for i, compuesto in enumerate(self.c)}
        if self.modo_termico != 'isotermo':
            self.outs[0].T = y[-1]
        else:
            self.outs[0].T = self.T
        self.outs[0].P = self.P

        
        if self.ReactionModel.conc_units == 'mol/L':
            units = 'mol/L'
        elif self.ReactionModel.conc_units == 'mg/L':
            units = 'mg/L'
        # Asignar los valores molares a la corriente de salida
        
        if units == 'mol/L':
            for compuesto, valor in ultimos_valores.items():
                self.outs[0].imol[compuesto] = valor * self.Q
        elif units == 'mg/L':
            # Convertir mg/L a kg/h asumiendo que Q está en m³/h
            # 1 mg/L = 1e-6 kg/m³, por lo tanto, multiplicamos por Q para obtener kg/h
            # y dividimos por 1e6 para convertir a kg
            for compuesto, valor in ultimos_valores.items():
                self.outs[0].imass[compuesto] = valor/1e6 * self.Q * 1000 # Ajustar por el volumen de entrada

        # Copiar otras propiedades de la corriente de entrada

        #self.outs[0].vle()  # Calcular el equilibrio de fases si es necesario

    def _run(self):
        effluent, = self.outs
        effluent.mix_from(self.ins, energy_balance=False)

        if self.Design_spec is not None:
            #print("Simulando por conversion...")
            self.find_time_for_conversion(plotting = self.Plot_profiles)
        else:
            #print("Simulando por tiempo...")
            self.find_conversion_for_time(plotting= self.Plot_profiles)
        self.corriente_efluente(self.sol)
