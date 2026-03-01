
import numpy as np
from scipy.integrate import solve_ivp, quad
import biosteam as bst
import thermosteam as tmo
import matplotlib.pyplot as plt

import sympy as sp

from ._kineticReactor import BaseReactor

class KineticBATCH(BaseReactor,bst.AbstractStirredTankReactor):
    def _init(self, **kwargs):
        self.sol_profile = None
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
    
    
    def _mass_balance(self, species_conc, T):
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        dC_dt = []
        for species in self.c.keys():
            rate = sum(self.stequi[species][i] * reaction_values[name]
                    for i, name in enumerate(self.rxn.keys()))
            dC_dt.append(rate)
        
        return dC_dt
    
    def show_balance_equations(self):
        """
        Muestra las ecuaciones de balance de materia y energía del reactor por pantalla.
        """
        
        print("ECUACIONES DE BALANCE DEL REACTOR")
        print("="*50)
        
        # BALANCE DE MATERIA
        print("\n📊 BALANCE DE MATERIA:")
        for species in self.c.keys():
            terms = []
            for i, rxn_name in enumerate(self.rxn.keys()):
                coeff = self.stequi[species][i]
                if coeff != 0:
                    if coeff == 1:
                        terms.append(f"r_{rxn_name}")
                    elif coeff == -1:
                        terms.append(f"-r_{rxn_name}")
                    else:
                        terms.append(f"{coeff}*r_{rxn_name}")
            
            if terms:
                equation = " + ".join(terms).replace("+ -", "- ")
                print(f"  d[{species}]/dt = {equation}")
            else:
                print(f"  d[{species}]/dt = 0")
        
        # BALANCE DE ENERGÍA
        print(f"\n🌡️ BALANCE DE ENERGÍA:")
        print(f"  dT/dt = Σ(-ΔHᵣⱼ * rⱼ * V) / (ρCₚ)")
        
        if self.modo_termico == 'isotermo':
            print(f"  dT/dt = 0  (modo isotérmico)")
        elif self.modo_termico == 'adiabatico':
            print(f"  dT/dt = Σ(-ΔHᵣⱼ * rⱼ * V) / (ρCₚ)  (modo adiabático)")
        elif self.modo_termico == 'intercambio':
            print(f"  dT/dt = [Σ(-ΔHᵣⱼ * rⱼ * V) + U*(Ta-T)] / (ρCₚ)")
        
        print("\nVelocidades de reacción:")
        for rxn_name in self.rxn.keys():
            print(f"  r_{rxn_name} = f({', '.join(self.c.keys())}, T)")
        
        print("="*50)
   
    def _energy_balance(self, species_conc, T, Ta=None):
        """Generalizado para reacciones simples y complejas."""
        V = self.Q
        #concentraciones = {species: C[i] for i, species in enumerate(self.c)}
        Cp_t = self.calcular_Cp(T, species_conc, V)#TODO tengo que pensar como generalizar esto

        Ta=None #TODO pasarlo a properties
        
        DHr_dict = self.ReactionModel.deltaH_reaccion(T, self.P)  
        
        reaction_values = {name: func(**species_conc, T=T) for name, func in self.r.items()}
        
        Q_rxn = sum(-reaction_values[name] * DHr_dict[name] * V for name in reaction_values.keys())
       
    
        # Lógica térmica generalizada
        if self.modo_termico == 'adiabatico':
            Q_ext = 0.0
            self.duty = 0.0
        elif self.modo_termico == 'intercambio':
            if Ta is None:
                raise ValueError("Se requiere Ta (temperatura del agente) para modo 'intercambio'.")
            Q_ext = self.U * (Ta - T) #TODO esta A debe ser con el volumen, esto creo que no está bien, pensar sobre el factor de escala
            self.duty = Q_ext #TODO este es el total en todo el volumen????
        
        elif self.modo_termico == 'isotermo':
            # En isotermo, todo el calor de reacción debe ser removido/suministrado
            Q_ext = -Q_rxn
            self.duty = Q_ext
        else:
            raise ValueError("Modo térmico no reconocido.")
        
        dT_dt = (Q_rxn + Q_ext) / Cp_t

        return dT_dt
    
    def _mass_energy_balance(self, t, y):
        """
        ODE system for mass and energy balances.
        """
        C = y[:-1]
        T = y[-1]
        T = np.clip(T, 1e-3, 5e3)
        species_conc = self._get_species_conc(C)

        dC_dt = self._mass_balance(species_conc, T)
        dT_dt = self._energy_balance(species_conc, T)

        return dC_dt + [dT_dt]
    
    def find_conversion_for_time(self, rtol=1e-6, atol=1e-8, plotting=False):
        #TODO confirmar que esto es correcto, creo que no está bien
        initial_condition = self.C0
        T0 = self.T
        y0 = [initial_condition[c] for c in self.c] + [T0]
        interval = (0, self.tau)  # Intervalo de integración en segundos
        t_eval = np.linspace(interval[0], interval[1], 100)  # Puntos de evaluación
        sol = solve_ivp(
            self._mass_energy_balance,
            interval,
            y0,
            t_eval=t_eval,
            rtol=rtol,
            atol=atol
        )
        self.sol_profile = sol
        self.sol = [sol.y[i, -1] for i in range(len(y0))]
    
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
        
        initial_condition = self.C0
        T0 = self.T
        y0 = [initial_condition[c] for c in self.c] + [T0]
        compound_target = self.Design_spec[0]
        print(compound_target)
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
        print(X_target)
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
        self.sol_profile = sol
        self.sol = [sol.y[i, -1] for i in range(len(y0))]

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
            self.plot_profiles(initial_condition, compound_target)

        return times_to_conversion
    
    def plot_profiles(self, Ca0, compound_target):
        t = self.sol.t
        y = self.sol.y
        n_species = len(self.c)

        # Concentraciones
        plt.figure(figsize=(10, 6))
        for i, specie in enumerate(self.c):
            plt.plot(t, y[i], label=f'C_{specie}')
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Concentración')
        plt.title('Perfiles de concentración')
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()

        # Temperatura
        T = y[-1]
        plt.figure()
        plt.plot(t, T, color='orange')
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Temperatura (K)')
        plt.title('Perfil de temperatura')
        plt.grid()
        plt.tight_layout()
        plt.show()

        # Conversión de A
        Ca = self.sol_profile .y[list(self.c.keys()).index(compound_target)]
        X = 1 - Ca / Ca0[compound_target]
        plt.figure()
        plt.plot(t, X, color='green')
        plt.xlabel('Tiempo (s)')
        plt.ylabel('Conversión de ' + compound_target)
        plt.title('Perfil de conversión')
        plt.grid()
        plt.tight_layout()
        plt.show()

    def plot_specific_profiles(self, compounds_list, title_suffix="", save_fig=False, filename=None):
        """
        Grafica los perfiles de concentración de compuestos específicos.
        
        Parameters
        ----------
        sol : object
            Solución del solver de ecuaciones diferenciales con atributos t (tiempo) y y (concentraciones).
        compounds_list : list
            Lista de strings con los IDs de los compuestos a graficar (ej: ['CO2', 'CH4']).
        title_suffix : str, optional
            Sufijo adicional para el título del gráfico. Por defecto "".
        save_fig : bool, optional
            Si True, guarda la figura. Por defecto False.
        filename : str, optional
            Nombre del archivo para guardar. Si None, usa un nombre automático.
        
        Returns
        -------
        None
            Muestra el gráfico y opcionalmente lo guarda.
        
        Examples
        --------
        >>> R1.plot_specific_profiles(R1.sol, ['CO2', 'CH4'])
        >>> R1.plot_specific_profiles(R1.sol, ['SW', 'VFA', 'X1'], "- Sustratos y Biomasa")
        """
        t = self.sol_profile.t
        y = self.sol_profile.y
        
        # Verificar que los compuestos existen en el sistema
        available_compounds = list(self.c.keys())
        invalid_compounds = [comp for comp in compounds_list if comp not in available_compounds]
        
        if invalid_compounds:
            print(f"⚠️  Advertencia: Los siguientes compuestos no están en el sistema: {invalid_compounds}")
            print(f"📋 Compuestos disponibles: {available_compounds}")
            # Filtrar solo los compuestos válidos
            compounds_list = [comp for comp in compounds_list if comp in available_compounds]
        
        if not compounds_list:
            print("❌ Error: No hay compuestos válidos para graficar.")
            return
        
        # Crear la figura
        plt.figure(figsize=(12, 8))
        
        # Definir colores y estilos para mejor visualización
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        line_styles = ['-', '--', '-.', ':']
        
        # Graficar cada compuesto
        for i, compound in enumerate(compounds_list):
            try:
                # Encontrar el índice del compuesto en la lista de especies
                compound_index = list(self.c.keys()).index(compound)
                color = colors[i % len(colors)]
                line_style = line_styles[i % len(line_styles)]
                
                plt.plot(t, y[compound_index], 
                        label=f'{compound}', 
                        color=color, 
                        linestyle=line_style,
                        linewidth=2,
                        marker='o' if len(t) < 50 else None,
                        markersize=4 if len(t) < 50 else 0)
                        
            except ValueError:
                print(f"⚠️  No se pudo encontrar el compuesto {compound}")
                continue
        
        # Configurar el gráfico
        plt.xlabel(f'Tiempo ({self.ReactionModel.time_units})', fontsize=12)
        plt.ylabel(f'Concentración ({self.ReactionModel.conc_units})', fontsize=12)
        plt.title(f'Perfiles de concentración{title_suffix}', fontsize=14, fontweight='bold')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Agregar información adicional
        if hasattr(self.sol_profile, 'success') and not self.sol_profile.success:
            plt.text(0.02, 0.98, '⚠️ Simulación no convergió completamente', 
                    transform=plt.gca().transAxes, fontsize=10, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
                    verticalalignment='top')
        
        # Guardar figura si se solicita
        if save_fig:
            if filename is None:
                compounds_str = "_".join(compounds_list)
                filename = f"perfiles_{compounds_str}_{self.ID}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"💾 Figura guardada como: {filename}")
        
        plt.show()
    

    
    
    
