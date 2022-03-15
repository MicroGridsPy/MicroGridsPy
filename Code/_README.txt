SCRIPTS:

"Micro-Grids"     : model MAIN script, it contains the run instructions. May be used to change the optimization goal (minimize NPC/ minimize Operation Cost) 
                    or to force minimum renewable penetration or minumum number of days to run with only batteries.
"Constraints"     : contains the definition of all the governing equations of the model
"Initialize"      : contains the import of model parameters and the initialization of specific variables
"Model_Creation"  : contains the creation of the Pyomo variables 
"Model_Resolution": contains the creation of the Pyomo instance, to be elaborated by the external solver (GUROBI, CPLEX, GLPK)
"Results"         : script for results extraction, elaboration and export to Excel; also contains the functions needed for the results plot
"Re_input_data" : script for extraction of input for renewables production script
"RE_calculation" : contains the general calculations for input renewable energy production time-series
"Solar_PV_calculation" : contains calculations for solar PV production
"Wind_calculation" : contains calculations for wind turbine production
"Typical_year" : contains Typical Meteorological Year calculations
"Windrose" : script to construct the windrose plot
"Grid_Availability" : contains the calculations for the national grid availability matrix 


PROPOSED EXAMPLE:
Time horizon: 20 years
Scenarios: 1
Constant demand
Renewable technologies: 1 (solar: 0.3 kW/unit)
Optimization goal: NPC
No calculations for renewables production (RE_Supply_Calculation = 0)
No calculations for demand estimation  (Demand_Profile_Generation = 0
No grid connection (Grid_Connection = 0)