import biosteam as bst
#from _ANN_model_recent import DeepNN
from _DeepNN import DeepNN


import torch   
import joblib

class Pyrolyzer(bst.Unit):
    _N_ins = 1
    _N_outs = 1

    def __init__(self, ID, ins=(), outs=(), T=550+273.15, P=101325, tau=1,scaler_path='pyrolysis_scaler.gz', *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs )
        self.T = T
        self.P = P
        self.tau = tau
        self.model = DeepNN(input_size=4,output_size=5)
        self.model.load_state_dict(torch.load('deepnn_model.pth'))
        self.model.eval()
        self.scaler = joblib.load(scaler_path)  
        #loaded_model = LinearRegressionTorch(input_size=4, output_size=2)
        #loaded_model.load_state_dict(torch.load('pyrolysis_model.pth'))
        #loaded_model.eval()
        #self.model = joblib.load('PlasticMar3.pkl')

    def _run(self):
    # Get inputs from feed stream
        feed = self.ins[0]
        inputs = [
            feed.imass['PS'] / (feed.imass['PS'] + feed.imass['HDPE']) * 100,  # PS%
            feed.imass['HDPE'] / (feed.imass['PS'] + feed.imass['HDPE']) * 100,  # HDPE%
            self.T - 273.15,  # Temperature in °C
            self.tau  # Residence time in seconds
        ]
        
        catalyst_present = 'ZSM5' in feed.chemicals
        catalyst_frac = feed.imass['ZSM5'] / feed.F_mass * 100 if catalyst_present else 0
        
    # Scale inputs using training scaler
        assert len(inputs) == 4, f"Expected 4 features, got {len(inputs)}"
        scaled_inputs = self.scaler.transform([inputs])
    
    # Convert to tensor and predict
        with torch.no_grad():
            input_tensor = torch.tensor(scaled_inputs, dtype=torch.float32)
            product_yields = self.model(input_tensor).numpy()[0]

        if catalyst_present:
            product_yields[0] *= 1.1  # BTX +10%
            product_yields[3] *= 0.95  # Gas -5%
        
        
        print("Product Yields (wt%):")
        print(product_yields)

        
    # Assign outputs
        products = self.outs[0]
        self.outs[0].copy_like(self.ins[0])
        self.outs[0].imass["PS"] = 0
        #products.imass['C6H6'] = product_yields[0] * feed.F_mass / 100  # BTX
        #products.imass['C8H8'] = product_yields[2] * feed.F_mass / 100  # Styrene
        #products.imass['C8H10'] = product_yields[0] * feed.F_mass / 100
        #roducts.imass['C7H8'] = product_yields[0] * feed.F_mass / 100
        #memory = joblib.Memory(location=None)
        #memory.clear(warn=False)
        #product_yields = self.model.predict([inputs])[0]
        
        # --- Aromatics distribution (literature inspired) ---
        # Total aromatics predicted by surrogate model (w%)
        Liquid_yield = product_yields[4]  # Liquid yield from feed (w%)
        aromatic_content = product_yields[2]  

        _btx, _styrene, _aromatics, _gas, _liquids = [p/100 for p in product_yields]


# Convert to mass basis
        products.imass['C8H8'] += _styrene * _aromatics * _liquids * feed.imass['PS']  # Styrene
        products.imass['C6H6'] += 1/3*_btx * _aromatics * _liquids * feed.imass["PS"] # Benzene
        products.imass['C7H8'] += 1/3*_btx * _aromatics * _liquids * feed.imass["PS"]  # Toluene
        products.imass['C8H10'] += 1/3*_btx * _aromatics * _liquids * feed.imass["PS"]  # Xylene
        products.imass['C9H12'] += (1 - _styrene - _btx) * _aromatics * _liquids * feed.imass['PS']  # Other aromatics
        products.imass["C10H22"] += (1-_aromatics) * _liquids * feed.imass["PS"]  # Alkanes
        products.imass["H2"] += 0.01 * _gas * feed.imass["PS"] 
        products.imass["CO2"] += 0.9 * _gas * feed.imass["PS"] 
        products.imass["CH4"] += 0.02 * _gas * feed.imass["PS"] 
        products.imass["C2H4"] += 0.07 *  _gas * feed.imass["PS"] 
        products.imass["C"] += feed.imass["PS"]* max([0, 1-_liquids-_gas]) # Solid by difference

        # normalize the output flow rates to 100% of the input flow rate
        # inputFlowRate = feed.F_mass
        # for i in products.available_chemicals:
        #     products.imass[i.ID] = products.imass[i.ID] * inputFlowRate / products.F_mass 

        # for ID in products.chemicals.IDs:
        #     val = products.imass[ID]
        #     val_real = float(val.real if isinstance(val, complex) else val)
        #     products.imass[ID] = max(0.0, val_real)
        
        #assert not any(x != x for x in products.imass.values()), "NaN detected in Pyrolyzer output"
        #assert products.F_mass <= F_mass + 1e-6, f"Mass balance error: output {products.F_mass:.3f} > input {F_mass:.3f}"

    
    def _design(self):
        pass 

    # Based on the NREL report https://www.nrel.gov/docs/fy15osti/62455.pdf
    def _cost(self):
        self.purchase_costs["Reactor"] = (
            2 * 3818000 * (self.ins[0].get_total_flow("lb/hr") / 2526000) ** 0.5
        )
        self.installed_costs["Reactor"] = self.purchase_costs["Reactor"] * 2.3
