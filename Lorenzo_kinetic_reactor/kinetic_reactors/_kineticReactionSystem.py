
import sympy as sp
from scipy.integrate import quad

class KineticExpression:
    def __init__(self, expression, fixed_params=None, species=None, variables=None):
        """
        expression: string simbólico o función de Python (callable)
        fixed_params: dict de parámetros fijos (pueden depender de variables externas como T)
        species: dict de especies {'A': 'CA', ...}
        variables: lista de variables externas (por ejemplo, ['T'])
        """
        self.fixed_params = fixed_params or {}
        self.species_map = species or {}
        self.variables = variables or []
        self.is_callable = callable(expression)
        self.expression = expression

        if not self.is_callable:
            self._build_symbol_maps()
            self._parse_expression()

    def _build_symbol_maps(self):
        self.symbols = {v: sp.Symbol(v) for v in self.species_map.values()}
        self.fixed_symbols = {k: sp.sympify(v) for k, v in self.fixed_params.items()}
        self.external_symbols = {v: sp.Symbol(v) for v in self.variables}
        self.all_symbols = {**self.symbols, **self.external_symbols, **{
            k: sp.Symbol(k) for k in self.fixed_symbols
        }}
        self.symbol_to_species = {v: k for k, v in self.species_map.items()}

    def _parse_expression(self):
        expr = sp.sympify(self.expression, locals=self.all_symbols)
        for name, sym_expr in self.fixed_symbols.items():
            expr = expr.subs(sp.Symbol(name), sym_expr)
        self.sympy_expression = expr
        # Ordena los argumentos: especies primero, luego variables externas
        self.free_symbols = [self.symbols[v] for v in self.species_map.values()] + \
                            [self.external_symbols[v] for v in self.variables]
        self.species_arg_names = list(self.species_map.keys())
        self.external_arg_names = list(self.variables)
        self.all_arg_names = self.species_arg_names + self.external_arg_names
        self.function = sp.lambdify(self.free_symbols, self.sympy_expression, modules="numpy")

    def evaluate(self, **kwargs):
        if self.is_callable:
            # Llama a la función directamente con los argumentos nombrados
            # Acepta especies y variables externas como argumentos
            return self.expression(**kwargs)
        else:
            try:
                args = [kwargs[name] for name in self.all_arg_names]
            except KeyError as e:
                raise ValueError(f"Missing input for: {e}")
            return self.function(*args)

    def get_function(self):
        if self.is_callable:
            return self.expression
        else:
            return lambda **kwargs: self.evaluate(**kwargs)

    def get_expression(self):
        if self.is_callable:
            return self.expression
        else:
            return self.sympy_expression

    def get_latex(self):
        if self.is_callable:
            return str(self.expression)
        else:
            return sp.latex(self.sympy_expression)

class ReactionModel:
    def __init__(self, reactions, kinetics):
     
        self.reactions = reactions
        self.kinetics = kinetics
        self._prepare_reaction_kinetics()
        self.c = self.get_all_species()
        self.stequi = self.extract_stequiometries()
        self.DHr_calculos = {}
        self.DHr = self.deltaH_reaccion(T=298.15, P = 101325)  # Default temperature for enthalpy calculation
        self.time_units = 'h' # Default time units
        self.conc_units = 'mol/L'  # Default concentration units
    
    @property
    def show_enthalpies(self):
        print('='*0)
        print("Enthalpies for each reaction in the model:")
        print('='*50)
        for name, enthalpy in self.DHr_calculos.items():
            print(f"{name}: {enthalpy} J/mol")
        return self.DHr_calculos
    
    @property
    def show_stequiometries(self):
        print('='*50)
        print("Stoichiometric coefficients for each species in the reaction model:")
        print('='*50)
        for species, coeffs in self.stequi.items():
            print(f"{species}: {coeffs}")
        return self.stequi
    
    @property
    def show_chemicals(self):
        print('='*50)
        print("All chemicals in the reaction model:")
        print('='*50)
        for name, chem in self.c.items():
            print(f"{name}: {chem}")
        return self.c
    
    def set_units(self, time_units='h', conc_units='mol/L'):
        """
        Set the units for time and concentration in the reaction model.
        
        Parameters
        ----------
        time_units : str, optional
            Time units (default is 'h').
        conc_units : str, optional
            Concentration units (default is 'mol/L').
        """
        self.time_units = time_units
        self.conc_units = conc_units
    
    @property
    def show_kinetic_model_units(self) :
        print('='*50)
        print("Current units for the reaction model:")
        print(f"Time units: {self.time_units}")
        print(f"Concentration units: {self.conc_units}")
        
    @property  
    def show_model_summary(self):
        """Muestra un resumen completo del modelo cinético."""
        print('='*70)
        print("📋 RESUMEN DEL MODELO CINÉTICO")
        print('='*70)
        
        print(f"\n🔢 NÚMERO DE REACCIONES: {len(self.reactions)}")
        print(f"🧪 NÚMERO DE ESPECIES: {len(self.c)}")
        
        print(f"\n⚗️  REACCIONES:")
        for name, reaction in self.reactions.items():
            print(f"   • {name}: {reaction}")

        print(f"\n ⏲️ UNIDADES:")
        print(f"   • Tiempo: {self.time_units}")
        print(f"   • Concentración: {self.conc_units}")

        print(f"\n📊 COEFICIENTES ESTEQUIOMÉTRICOS:")
        for name, coeffs in self.stequi.items():
            print(f"   • {name}: {coeffs}")
        print('='*70)

    
    def get_all_species(self):
        """
        Get all species involved in the reactions, including inerts, and store them in self.c.

        Parameters
        ----------
        reactions : bst.Reaction or tmo.ParallelReaction

        Returns
        -------
        dict
            {ID: Chemical} for all species involved in the reactions.
        """
        primera_clave = next(iter(self.reactions))
        species = self.reactions[primera_clave].chemicals
        self.c = {i.ID: i for i in species}

        return self.c

    
    def extract_stequiometries(self):
        """
        Extract stoichiometric coefficients for each species in a set of reactions.

        Parameters
        ----------
        reactions : bst.Reaction or tmo.ParallelReaction
            Single or parallel reaction.

        Returns
        -------
        dict
            Dictionary where keys are species IDs and values are lists of stoichiometric
            coefficients for each reaction.
        """
            
        stequi = {sp: [] for sp in self.c.keys()}
        for rj in self.reactions.values():
            for sp in self.c.keys():
                coeff = rj.istoichiometry[sp]
                stequi[sp].append(coeff)
        return stequi
    
    def _prepare_reaction_kinetics(self):
        # Comprobar que ambos son diccionarios
        if not isinstance(self.reactions, dict) or not isinstance(self.kinetics, dict):
            raise TypeError("Ambos argumentos deben ser diccionarios.")

        # Comprobar que tienen el mismo número de elementos
        if len(self.reactions) != len(self.kinetics):
            raise ValueError("El número de reacciones y cinéticas debe ser el mismo.")

        # Comprobar que los nombres coinciden
        if set(self.reactions.keys()) != set(self.kinetics.keys()):
            raise ValueError("Los nombres de las reacciones y cinéticas deben coincidir.")

    def deltaH_reaccion(self, T: float, P = 101325):
        """
        Calcula la entalpía de reacción a temperatura T para cada reacción del sistema.

        Este método devuelve SIEMPRE un diccionario {nombre_reacción: ΔH_reacción}, 
        donde cada valor es un escalar (no un array), aunque internamente los objetos 
        de reacción puedan tener arrays de más de un elemento (por ejemplo, dH o X 
        en ParallelReaction). Para asegurar esto, se toma solo el primer elemento 
        del array si es necesario.

        Esto es importante para evitar errores al usar los resultados en balances 
        de energía y con fsolve, que requieren listas planas de escalares.
        """
        def get_Cp_reaccion(coeffs, T_):
            a = 0
            for sp, coeff in coeffs.items():  # noqa: F402

                phase = self.c[sp].get_phase()

                if phase == 's':
                    a += coeff * self.c[sp].Cn(phase,T_, P)
                else:
                    a += coeff * self.c[sp].Cn(phase, T_, P)
            return a

        DHRs_T = {} 
        
        for i, name in enumerate(self.reactions.keys()):
            coeffs = {sp: self.stequi[sp][i] for sp in self.c}
            
            rxn_obj = self.reactions[name]
            # Toma solo el primer elemento si es array de más de un valor
            deltaH0 = (rxn_obj.dH / rxn_obj.X)

            Cp_reaccion = lambda T_: get_Cp_reaccion(coeffs, T_)

            deltaCp, _ = quad(Cp_reaccion, 298.15, T)

            DHRs_T[name] = deltaH0 + deltaCp
            
            self.DHr_calculos[name] = {
                'deltaH0': deltaH0,
                'deltaCp': deltaCp,
                'DHRs_T': DHRs_T[name]
            }

        return DHRs_T
