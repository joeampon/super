import biosteam as bst
from _ANN_model_recent import LinearRegressionTorch
import torch   
import joblib

class Pyrolyzer(bst.Unit):
    _N_ins = 1
    _N_outs = 1

    def __init__(self, ID, ins=(), outs=(), T=780+273.15, P=101325, tau=10 scaler_path='pyrolysis_scaler.gz', *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs )
        self.T = T
        self.P = P
        #self.tau
        self.model = LinearRegressionTorch(input_size=4, output_size=2)
        self.model.load_state_dict(torch.load('pyrolysis_model.pth'))
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
            feed.imass['PS'] / feed.F_mass * 100,  # PS%
            feed.imass['HDPE'] / feed.F_mass * 100,  # HDPE%
            self.T - 273.15,  # Temperature in °C
              # Residence time in seconds
        ]
    
    # Scale inputs using training scaler
        assert len(inputs) == 4, f"Expected 4 features, got {len(inputs)}"
        scaled_inputs = self.scaler.transform([inputs])
    
    # Convert to tensor and predict
        with torch.no_grad():
            input_tensor = torch.tensor(scaled_inputs, dtype=torch.float32)
            product_yields = self.model(input_tensor).numpy()[0]
    
    # Assign outputs
        products = self.outs[0]
        products.imass['C6H6'] = product_yields[0] * feed.F_mass / 100  # BTX
        products.imass['C8H8'] = product_yields[1] * feed.F_mass / 100  # Styrene


        #memory = joblib.Memory(location=None)
        #memory.clear(warn=False)
        #product_yields = self.model.predict([inputs])[0]

        products.imass["C6H6"] = 1/3*feed.imass["PS"] * product_yields[4]/100# BTX
        products.imass["C7H8"] = 1/3*feed.imass["PS"] * product_yields[4]/100# BTX
        products.imass["C8H10"] = 1/3*feed.imass["PS"] * product_yields[4]/100# BTX
        products.imass["C8H18"] =  feed.imass["PS"] * (product_yields[3] - product_yields[4])/100 # Aromatics without BTX
        products.imass["PS"] = feed.imass["PS"] * ( product_yields[5])/100
        products.imass["H2"] = 0.01 *  feed.imass["PS"] * (product_yields[1])/100 # Gas
        products.imass["CO2"] = 0.9 *  feed.imass["PS"] * (product_yields[1])/100
        products.imass["CH4"] = 0.02 *  feed.imass["PS"] * (product_yields[1])/100
        products.imass["C2H4"] = 0.07 *  feed.imass["PS"] * (product_yields[1])/100
        products.imass["C"] = feed.imass["PS"] - sum([products.imass[c.ID] for c in products.available_chemicals ]) # Solid by difference

        for i in ["C6H6", "C7H8", "C8H10", "C8H18", "PS", "H2", "CO2", "CH4", "C"]:
            products.imass[i] = max(0.0001, products.imass[i])

        # normalize the output flow rates to 100% of the input flow rate
        inputFlowRate = feed.F_mass
        for i in products.available_chemicals:
            products.imass[i.ID] = products.imass[i.ID] * inputFlowRate / products.F_mass 


    
    def _design(self):
        pass 

    # Based on the NREL report https://www.nrel.gov/docs/fy15osti/62455.pdf
    def _cost(self):
        self.purchase_costs["Reactor"] = (
            2 * 3818000 * (self.ins[0].get_total_flow("lb/hr") / 2526000) ** 0.5
        )
        self.installed_costs["Reactor"] = self.purchase_costs["Reactor"] * 2.3
