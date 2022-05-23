FOLDERS:

"Inputs"	: inputs for resource availability, demand curve, technology characterization.
"Results"	: results of the model in .XLSX form.
"Demand_archetypes" : list of demand archetypes for different rural users.


SCRIPTS:

"Micro-Grids"     : model MAIN script, it contains the run instructions. May be used to change the optimization goal (minimize NPC/ minimize Operation Cost), to force minimum renewable penetration, minimum number of days to run with only batteries, to select brownfield and two-objective 			optimization
"Constraints_XXfield"     : contains the definition of all the governing equations of the model
"Initialize"      : contains the import of model parameters and the initialization of specific variables
"Model_Creation"  : contains the creation of the Pyomo variables 
"Model_Resolution_XXfield": contains the creation of the Pyomo instance, to be elaborated by the external solver (GUROBI, CPLEX, GLPK)
"Results"         : script for results extraction, elaboration and export to Excel; also contains the functions needed for the results plot
"Demand"	: script for the calculation of the total load profile from demand archetypes.
"Re_input_data" : script for extraction of input for renewables production script
"RE_calculation" : contains the general calculations for input renewable energy production time-series
"Solar_PV_calculation" : contains calculations for solar PV production
"Wind_calculation" : contains calculations for wind turbine production
"Typical_year" : contains Typical Meteorological Year calculations
"Windrose" : script to construct the windrose plot
"Grid_Availability" : contains the calculations for the national grid availability matrix 
"Plots" : script for visual representation of results.

