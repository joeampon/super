import biosteam as bst
from olumide_TOD_and_CPY.system_builder import run_scenario, scenarios

# Build small CPY-HC scenario for a quick check
sys = run_scenario(scenario=scenarios[1], capacity=50)

# Simulate and print a brief summary
sys.simulate()
print("Units:", len(sys.units))
print("Products:", [str(s) for s in sys.products])
for s in sys.products:
    try:
        # show total mass flow per hour
        print(str(s), "flow kg/hr:", round(sys.flowsheet.stream[str(s)].get_total_flow("kg/hr"), 3))
    except Exception:
        pass
