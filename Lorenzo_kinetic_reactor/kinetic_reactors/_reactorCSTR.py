
import numpy as np
from scipy.integrate import quad
import biosteam as bst

from scipy.optimize import fsolve
from scipy.optimize import least_squares

from ._kineticReactor import BaseReactor
import matplotlib.pyplot as plt

class KineticCSTR(BaseReactor, bst.AbstractStirredTankReactor):
    def _init(self,**kwargs):
        
        self.batch = False
        super()._init(**kwargs)     
        
        
    
    def _setup(self):
        self._setup_reaction_system()
        super()._setup()
        
    
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
    
    
    def _mass_balance(self, species_conc, r, T, V):
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        
        eqs = []
        
        for species in self.c.keys():
            rate = sum(self.stequi[species][i] * reaction_values[name]
                    for i, name in enumerate(self.r.keys()))
            eqs.append(self.Q * (self.C0[species] - species_conc[species]) + V * rate)
        return eqs

    def cstr_energy_balance(self, species_conc, r, T, V):
        """
        Balance de energía algebraico para un CSTR.
        
        Parámetros:
            species_conc (dict): Concentraciones de salida de cada especie {ID: valor}
            r: función cinética (o dict de funciones para reacciones complejas)
            T (float): Temperatura de salida [K]
            V (float): Volumen del reactor
            T_in (float): Temperatura de entrada [K]
            modo_termico (str): 'adiabatico', 'intercambio' o 'isotermo'
            Ta (float): Temperatura del agente externo (solo para 'intercambio')
        
        Returns:
            float: Residuo del balance de energía (para usar en fsolve)
        """
        Ta=None #TODO pasarlo a properties
        
        DHr_dict = self.ReactionModel.deltaH_reaccion(T,self.P) 
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        
        Q_rxn = sum(-reaction_values[name] * DHr_dict[name] * V for name in reaction_values.keys())

        # Cp de la mezcla (en el volumen total)
        
        deltaCp, _ = quad(self.calcular_feed_Cp_flows, self.ins[0].T, T) #TODO pensar si esto es correcto

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
        
        # Balance de energía algebraico:
        # Q_rxn + Q_ext = Cp_total * (T - T_in)
        return Q_rxn + Q_ext - deltaCp 


    def _mass_energy_balance(self, C, T, V):

        # 1. Diccionario de concentraciones de salida
        species_conc = self._get_species_conc(C)

        # 2. Función cinética
        r = self.r

        # 3. Ecuaciones de balance de materia
        eqs_materia = self._mass_balance(species_conc, r, T, V)

        # 4. Ecuación de balance de energía
        eq_energia = self.cstr_energy_balance(species_conc, r, T, V)

        return eqs_materia + [eq_energia]

    def find_time_for_conversion(self, plotting=False):
        def sistema(vars):
            """
            Sistema algebraico de balances de materia y energía para un CSTR.
            vars: [C1, ..., CN, V, T]
            Retorna: lista de ecuaciones (residuos) para usar en fsolve.
            """
            C = vars[:-2]
            V = vars[-2]
            T = vars[-1]
            
            balances = self._mass_energy_balance(C, T, V)
            
            # 5. Ecuación de conversión objetivo
            # Suponiendo que self.Design_spec = (nombre_compuesto, conversión_objetivo)
            compound_target, X_obj = self.Design_spec
            C_in = self._concentraciones_iniciales()
            idx = list(self.c.keys()).index(compound_target)
            eq_conversion = (C_in[compound_target] - C[idx]) / C_in[compound_target] - X_obj
        # Asegúrate de que todos son escalares o listas planas
            return balances + [eq_conversion]
        
        """
        Resuelve el sistema de ecuaciones del CSTR (materia o materia+energía).
        """
        C_in = self._concentraciones_iniciales()
        T_in = self.ins[0].T
        species = list(self.c.keys())
            
        x0 = [C_in[s] for s in species] + [1.0, T_in]
        self.sol = fsolve(sistema, x0)
        C_out = {s: self.sol[i] for i, s in enumerate(species)}
        V = self.sol[-2]
        T_out = self.sol[-1]
        self.tau = V / self.ins[0].F_vol  # Tiempo de residencia
        
        print(f"Concentraciones de salida: {C_out}")
        print(f"Volumen del reactor: {V}")
        print(f"Temperatura de salida: {T_out}")
        #return C_out, V, T_out
        
    
    def find_conversion_for_time(self, plotting=False):
        def sistema(vars):
            C = vars[:-1]
            T = vars[-1]
            V = self.tau * self.ins[0].F_vol
            # 1. Diccionario de concentraciones de salida
            
            balances = self._mass_energy_balance(C, T, V)

            return balances
        
        C_in = self._concentraciones_iniciales()
        T_in = self.ins[0].T
        species = list(self.c.keys())
        x0 = [C_in[s] for s in species] + [T_in]
        

        resultdo = least_squares(sistema, x0, bounds=(0, float(1e6)))
        self.sol = resultdo.x
        T_out = self.sol[-1]
        C_out = {s: self.sol[i] for i, s in enumerate(species)}

        if plotting:
            pass
        
        # print(f"Concentraciones de salida: {C_out}")
        # print(f'Concentraciones de entrada: {C_in}')
        # print(f"Temperatura de salida: {T_out}")

