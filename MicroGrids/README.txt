SCRIPTS:

"Micro-Grids"        : model MAIN, contains the run instructions. May be used to change the optimization goal (minimize NPC/ minimize Operation Cost).
"Constraints_MY"     : contains the definition of all the governing equations of the model
"Initialize_MY"      : contains the import of model parameters and the initialization of specific variables
"Model_Creation_MY"  : contains the creation of the Pyomo variables 
"Model_Resolution_MY": contains the creation of the Pyomo instance, to be elaborated by the external solver (GUROBI, CPLEX, GLPK)
"Results_MY"         : script for results extraction, elaboration and export to Excel; also contains the functions needed for the results plot

PROPOSED EXAMPLE:

Time horizon: 5 years
Scenarios: 1
Constant demand
Renewable technologies: 2 (solar: 1 kW/unit, wind: 30 kW/unit)
Optimization goal: NPC