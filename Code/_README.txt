SCRIPTS:

"Micro-Grids"     : model MAIN script, it contains the run instructions. May be used to change the optimization goal (minimize NPC/ minimize Operation Cost) 
                    or to force minimum renewable penetration or minumum number of days to run with only batteries.
"Constraints"     : contains the definition of all the governing equations of the model
"Initialize"      : contains the import of model parameters and the initialization of specific variables
"Model_Creation"  : contains the creation of the Pyomo variables 
"Model_Resolution": contains the creation of the Pyomo instance, to be elaborated by the external solver (GUROBI, CPLEX, GLPK)
"Results"         : script for results extraction, elaboration and export to Excel; also contains the functions needed for the results plot
"RE_calculation"  : script for the download, processing and calculation of PV and wind power hourly time-series, then exported to "Renewable_energy.xlsx". 
"Demand_main"     : script for the calculation of total hourly load demand using demand archetypes and data from "Demand_data.dat"


PROPOSED EXAMPLE:
Time horizon: 5 years
Scenarios: 1
Constant demand
Renewable technologies: 2 (solar: 1 kW/unit, wind: 30 kW/unit)
Optimization goal: NPC