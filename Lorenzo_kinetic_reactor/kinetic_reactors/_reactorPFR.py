from typing import Optional, Union
import numpy as np
from scipy.integrate import solve_ivp, quad
import matplotlib.pyplot as plt
import biosteam as bst
import thermosteam as tmo
import sympy as sp
from biosteam.units.heat_exchange import Cb_dict, x, y, p2, compute_double_pipe_purchase_cost, compute_shell_and_tube_material_factor
from biosteam.units.design_tools.geometry import cylinder_diameter_from_volume
from biosteam.units.design_tools.specification_factors import (
    shell_and_tube_material_factor_coefficients,
    compute_shell_and_tube_material_factor)

from biosteam.utils import list_available_names


from typing import Optional, Union
import numpy as np
from scipy.integrate import quad
import biosteam as bst
import thermosteam as tmo
from scipy.optimize import fsolve
import sympy as sp

from ._kineticReactor import BaseReactor

class KineticPFR(BaseReactor, bst.AbstractStirredTankReactor, bst.design_tools.PressureVessel):
       
    _units = {'Area': 'ft^2',
              'Overall heat transfer coefficient': 'kW/m^2/K',
              'Log-mean temperature difference': 'K',
              'Tube side pressure drop': 'Pa',
              'Shell side pressure drop': 'Pa',
              'Operating pressure': 'psi',
              'Total tube length': 'ft',
              'Vertical vessel weight': 'lb',
              'Horizontal vessel weight': 'lb',
              'Length': 'ft',
              'Diameter': 'ft',
              'Weight': 'lb',
              'Wall thickness': 'in',
              'Pressure': 'psi',
              'Residence time': 'hr',
              'Total volume': 'm3',
              'Reactor volume': 'm3'}
    
    _F_BM_default = {'Double pipe': 1.8,
                     'Floating head': 3.17,
                     'Fixed head': 3.17,
                     'U tube': 3.17,
                     'Kettle vaporizer': 3.17,
                     'Furnace': 2.19}
    
        
    heat_exchanger_type_default: Optional[str] = "Floating head"
    
    modo_termico_default: Optional[str] = "adiabatico"
    
    reactor_material_default: Optional[str] = "Carbon steel/carbon steel"
    
    def _init(self, heat_exchanger_type: Optional[str]=None,
        reactor_material: Optional[str]=None,**kwargs):
        self.heat_exchanger_type = self.heat_exchanger_type_default if heat_exchanger_type is None else heat_exchanger_type
        self.reactor_material = self.reactor_material_default if reactor_material is None else reactor_material
    
        
        super()._init(**kwargs)
   
    
    def _setup(self):
        
        self._setup_reaction_system()
   
        super()._setup()
    
    @property
    def modo_termico(self):
        """[str] Thermal mode. Default 'isotermo'."""
        return self._modo_termico
    
        
    @property
    def material(self):
        """Default 'Carbon steel/carbon steel'."""
        return self._material
    
    @modo_termico.setter
    def modo_termico(self, value):
        self._modo_termico = value

    @material.setter
    def material(self, material):
        try:
            self._F_Mab = shell_and_tube_material_factor_coefficients[material]
        except KeyError:
            raise AttributeError("material must be one of the following: "
                                    f"{list_available_names(shell_and_tube_material_factor_coefficients)}") #TODO
        self._material = material
    
    @property
    def heat_exchanger_type(self):
        """[str] Heat exchanger type. Purchase cost depends on this selection."""
        return self._heat_exchanger_type

    @heat_exchanger_type.setter
    def heat_exchanger_type(self, heat_exchanger_type):
        try:
            self._Cb_func = Cb_dict[heat_exchanger_type]
        except KeyError:
            raise AttributeError("heat exchange type must be one of the following: "
                                 f"{list_available_names(Cb_dict)}")
        self._heat_exchanger_type = heat_exchanger_type   
    
    @property
    def Ta_intercambio(self):
        """[float] Temperature of the external agent (for 'intercambio' mode)."""
        return self._Ta_intercambio
    @Ta_intercambio.setter
    def Ta_intercambio(self, value):
        self._Ta_intercambio = value
    
    @property
    def modo_termico(self):
        """[str] Thermal mode. Default 'isotermo'."""
        return self._modo_termico
    @modo_termico.setter
    def modo_termico(self, value):
        self._modo_termico = value
        
    def _get_species_conc(self, species_flow, T):
        """Return dict of concentrations depending on phase."""
        
        if self.estado == 'gas':
            Q = sum(species_flow.values()) * 0.082 * T / (self.P/101325)
            print(f"Q: {Q}")
            return {species: species_flow[species] / Q for species in species_flow}
        elif self.estado == 'liquido':
            Q = sum(i.F_vol for i in self.ins if i.phase != 'g')
            return {species: species_flow[species] / Q for species in species_flow}
    
    def _mass_balance(self, species_conc, r, T, V):
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        
        print(f"reaction_values: {reaction_values}")
        dF_dV = []
        
        for species in self.c.keys():
            rate = sum(self.stequi[species][i] * reaction_values[name]
                    for i, name in enumerate(self.r.keys()))
            dF_dV.append(rate)
        return dF_dV
      
    def _energy_balance(self, species_conc, r, T, F, Ta=None):
        
        Ta=None #TODO pasarlo a properties
        
        DHr_dict = self.ReactionModel.deltaH_reaccion(T,self.P)  
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        
        Q_rxn = sum(-reaction_values[name] * DHr_dict[name] for name in reaction_values.keys())

        # Cp de la mezcla
        concentraciones = {species: F[i] for i, species in enumerate(self.c)}
        self.Cp_t = self.calcular_Cp(T, concentraciones, 1) # El V = 1 porque es el volumen es caudal

            # Lógica térmica generalizada
        if self.modo_termico == 'adiabatico':
            Q_ext = 0.0
            self.duty = 0.0 #TODO esto es correcto?
        
        elif self.modo_termico == 'intercambio':
            if Ta is None:
                raise ValueError("Se requiere Ta (temperatura del agente) para modo 'intercambio'.")
            Q_ext = self.U * (Ta - T) #TODO esta A debe ser con el volumen, esto creo que no está bien, pensar sobre el factor de escala
            
            self.duty = abs(Q_ext) #TODO este es el total en todo el volumen????
        
        elif self.modo_termico == 'isotermo':
            # En isotermo, todo el calor de reacción debe ser removido/suministrado
            Q_ext = -Q_rxn
            
            self.duty = abs(Q_ext)
        else:
            raise ValueError("Modo térmico no reconocido.")
        
        dT_dV = (Q_rxn + Q_ext) / self.Cp_t

        return dT_dV
   
    def _mass_energy_balance(self, t, y):
        """
        ODE system for mass and energy balances in PFR.
        y = [F1, ..., Fn, T, Ta] si intercambio, [F1, ..., Fn, T] si no.
        """
        if self.modo_termico == 'intercambio':
            F = y[:-2]
            T = y[-2]
            Ta = y[-1]
        
        else:
            F = y[:-1]
            T = y[-1]
            Ta = None
        
        T = np.clip(T, 1e-3, 5e3)
        
        if Ta is not None:
            Ta = np.clip(Ta, 1e-3, 5e3)
        
        species_flow = self._get_species_flows(F)
        species_conc = self._get_species_conc(species_flow, T)
        print(f"species_conc: {species_conc}")
        print(f'species_flow: {species_flow}')
        r = self.r
        dF_dV = self._mass_balance(species_conc, r, T, F)
        dT_dV = self._energy_balance(species_conc, r, T, F, Ta)
        
        if self.modo_termico == 'intercambio':
            dTa_dV = self._energy_balance_agent(T, Ta)
            return dF_dV + [dT_dV, dTa_dV]
        
        else:
            return dF_dV + [dT_dV]
        
    def find_time_for_conversion(self, interval=(0, 1e10), rtol=1e-6, atol=1e-8, plotting=False):
        """
        Encuentra el tiempo necesario para alcanzar una conversión objetivo en el reactor.

        Parameters:
        -----------
        interval : tuple, optional
            Intervalo de integración en segundos (por defecto: (0, 1e4)).
        rtol : float, optional
            Tolerancia relativa para la integración (por defecto: 1e-6).
        atol : float, optional
            Tolerancia absoluta para la integración (por defecto: 1e-8).
        plotting : bool, optional
            Si es True, genera gráficos de los perfiles de concentración, temperatura y conversión.

        Raises:
        -------
        RuntimeError:
            Si no se alcanza la conversión deseada dentro del intervalo de integración.

        Returns:
        --------
        float
            Tiempo necesario para alcanzar la conversión objetivo.
        """
        # Validar condiciones iniciales
        initial_condition = self._caudales_iniciales()
        T0 = self.T
        y0 = [initial_condition[c] for c in self.c] + [T0]
        compound_target = self.Design_spec[0]
        if compound_target is None:
            raise ValueError("No se ha definido un objetivo de conversión.")
        if compound_target not in self.c:
            raise ValueError(f"El compuesto objetivo {compound_target} no está presente en el reactor.")
        
        X_target = self.Design_spec[1]
        if X_target is None:
            raise ValueError("No se ha definido un objetivo de conversión.")
        if X_target <= 0 or X_target > 1:
            raise ValueError("El objetivo de conversión debe estar en el rango (0, 1].")
        # Definir las condiciones iniciales
        
        # Definir eventos para detener la integración
        def make_event(C_target, idx):
            
            def event_reach_conversion(t, y):
                return y[idx] - C_target  # Se anula cuando la concentración alcanza el objetivo
            
            event_reach_conversion.terminal = True
            
            event_reach_conversion.direction = -1  # La concentración disminuye
            
            return event_reach_conversion

        events = []
        
        Ca0 = initial_condition[compound_target]
        C_target = Ca0 * (1 - X_target)
        idx = list(self.c.keys()).index(compound_target)
        
        events.append(make_event( C_target, idx))
        

        # Resolver las ecuaciones diferenciales
        sol = solve_ivp(
            self._mass_energy_balance,
            interval,
            y0,
            events=events,
            rtol=rtol,
            atol=atol
        )
        
        self.sol = sol

        # Verificar si se alcanzaron las conversiones objetivo
        times_to_conversion = {}
        
        if sol.t_events[0].size == 0:
            raise RuntimeError(
                f"No se alcanzó la conversión deseada para {compound_target} en el intervalo de integración {interval}."
            )
        times_to_conversion[compound_target] = sol.t_events[0][0]

        # Actualizar el tiempo de residencia (tau) con el máximo tiempo alcanzado
        self.tau = max(times_to_conversion.values())

        # Graficar perfiles si es necesario
        if plotting:
            self.plot_profiles(sol, initial_condition, compound_target)

        return times_to_conversion

    def corriente_efluente(self, sol):
        """
        Crea una corriente de efluente a partir de las corrientes de entrada.
        """
        self.outs[0] = bst.Stream('efluente')
        
        y = sol.y
        
        ultimos_valores = {compuesto: sol.y[i, -1] for i, compuesto in enumerate(self.c)}

        
        # Asignar los valores molares a la corriente de salida
        for compuesto, valor in ultimos_valores.items():
            self.outs[0].imol[compuesto] = valor  # Ajustar por el volumen de entrada
    
        # Copiar otras propiedades de la corriente de entrada
        self.outs[0].T = y[-1,-1]
        self.outs[0].P = self.P
        #self.outs[0].vle(T=y[-1,-1], P=self.P )  # Calcular el equilibrio de fases si es necesario
        
    def _design(self, size_only=False):
        print('diseño sobreescrito')
        self.material = self.reactor_material
        
        Design= self.design_results
        # Aqui se tiene que pomer como caclular el área de tranferencia de calor
        V =  self.tau # Esto es en m3
        #ins_F_vol = sum([i.F_vol for i in self.ins)
        P_pascal = (self.P if self.P else self.outs[0].P)
        P_psi = P_pascal * 0.000145038 # Pa to psi
        Design['Reactor volume'] = V
        Design['Reactor Material'] = self.material
        Design['Reactor opeation'] = self.modo_termico
        
        
        if self.modo_termico in ('intercambio', 'isotermo'):
            L_tubos = 20 #Se suponen 20 ft
            L_tubos_m = L_tubos * 0.3048 # Se convierte a m
            D_tubos = 3/4 * 0.0254 #Se suponen 3/4 in
            V_tubo = np.pi * (D_tubos/2)**2 * L_tubos_m
            n_tubos = np.ceil(V/V_tubo)
            A_m2 = n_tubos * np.pi * D_tubos * L_tubos_m
            A = A_m2 * 10.7639 # Se convierte a ft
            Design['Area'] = A
            Design['Length'] = L_tubos
            Design['Number of tubes'] = n_tubos
            Design['Operating pressure'] = self.P * 14.7/101325  # psi
            Design['Overall heat transfer coefficient'] = 1 #TODO
            Design['Reactor type'] = self.heat_exchanger_type
        
        if self.modo_termico == 'adiabatico': #TODO aquí falta elegir si es vertical o horizontal, por defecto es horizontal
            self.vessel_type = 'Horizontal'
            
            Design['Reactor type'] = self.vessel_type
            length_to_diameter = self.length_to_diameter    #TODO
            D = cylinder_diameter_from_volume(V, self.length_to_diameter)
            D *= 3.28084 # Convert from m to ft
            L = D * length_to_diameter
            Design.update(self._vessel_design(float(P_psi), float(D), float(L)))
    
    def _cost(self):
        if self.modo_termico in ('intercambio', 'isotermo'):
            Design = self.design_results
            baseline_purchase_costs = self.baseline_purchase_costs
            volume = Design['Reactor volume']
            
            
            A = Design['Area']
            L = Design['Length']
            P = Design['Operating pressure']

            if A < 150:  # Double pipe
                P = P/600
                F_p = 0.8510 + 0.1292*P + 0.0198*P**2
                # Assume outer pipe carbon steel, inner pipe stainless steel
                F_m = 2
                A_min = 2.1718
                if A < A_min:
                    F_l = A/A_min
                    A = A_min
                else:
                    F_l = 1
                heat_exchanger_type = 'Double pipe'
                C_b = compute_double_pipe_purchase_cost(A, bst.CE)
            else:  # Shell and tube
                F_m = compute_shell_and_tube_material_factor(A,  *(self._F_Mab))
                F_l = 1 if L > 20 else np.polyval(p2, L)
                P = P/100
                F_p = 0.9803 + 0.018*P + 0.0017*P**2
                heat_exchanger_type = self.heat_exchanger_type
                C_b = self._Cb_func(A, bst.CE)

            # Free on board purchase prize
            self.F_M[heat_exchanger_type] = F_m
            self.F_P[heat_exchanger_type] = F_p
            self.F_D[heat_exchanger_type] = F_l
            self.baseline_purchase_costs[heat_exchanger_type] = C_b
            # Aqui se tiene que poner como calcular el costo del reactor #TODO Reactor con catalizador, quizás un PFR y un FBR
            
            # Note: Flow and duty are rescaled to simulate an individual
            # heat exchanger, then BioSTEAM accounts for number of units in parallel
            # through the `parallel` attribute.

            reactor_duty = self.duty
            duty = reactor_duty
            N=1#TODO Pensar esto
            dT_hx_loop = self.dT_hx_loop
            reactor_product = self.effluent.copy()
            reactor_product.scale(1 / N)
            hx_inlet = reactor_product.copy()
            hx_outlet = hx_inlet.copy()
            hx_outlet.T += (dT_hx_loop if duty > 0. else -dT_hx_loop)
            dH = hx_outlet.H - hx_inlet.H
            recirculation_ratio = reactor_duty / dH # Recirculated flow over net product flow
            hx_inlet.scale(recirculation_ratio)
            hx_outlet.scale(recirculation_ratio)
            
            if self.batch:
                self.recirculation_pump.ins[0].copy_like(hx_inlet)
                self.recirculation_pump.simulate()
            else:
                self.recirculation_pump.ins[0].mix_from([hx_inlet, reactor_product])
                self.recirculation_pump.simulate()
                self.splitter.split = recirculation_ratio / (1 + recirculation_ratio)
                self.splitter.simulate()
                self.scaler.scale = N
                self.scaler.simulate()
            self.heat_exchanger.T = hx_outlet.T
            self.heat_exchanger.simulate()                        
            
        if self.modo_termico == 'adiabatico':
            Design = self.design_results
            baseline_purchase_costs = self.baseline_purchase_costs
            volume = Design['Reactor volume']
            
            if volume != 0:
                baseline_purchase_costs.update(
                    self._vessel_purchase_cost(
                        Design['Weight'], Design['Diameter'], Design['Length'],
                    )
                )  
                
    def _run(self):
        effluent, = self.outs
        effluent.mix_from(self.ins, energy_balance=False)
        self.find_time_for_conversion(plotting = self.Plot_profiles)
        self.corriente_efluente(self.sol)

