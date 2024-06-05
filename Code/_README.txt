FOLDERS:

"Inputs"	: inputs for resource availability, demand curve, technology characterization.
"Results"	: results of the model in .XLSX form.
"Demand_archetypes" : list of demand archetypes for different rural users.
"Environments" : contains the YML files with the anaconda environments (for windows and MAC users)


SCRIPTS:

"MicroGrids"     : model MAIN script, it contains the run instructions. May be used to change the optimization goal (minimize NPC/ minimize Operation Cost), to force minimum renewable penetration, minimum number of days to run with only batteries, to select brownfield and two-objective 			optimization
"Constraints"     : contains the definition of all the governing equations of the model (for greenfield and bwonfield investment)
"Initialize"      : contains the import of model parameters and the initialization of specific variables
"Model_Creation"  : contains the creation of the Pyomo variables 
"Model_Resolution": contains the creation of the Pyomo instance, to be elaborated by the external solver (GUROBI, CPLEX, GLPK)
"Results"         : script for results extraction, elaboration and export to Excel; also contains the functions needed for the results plot
"Demand"	: script for the calculation of the total load profile from demand archetypes.
"RE_calculation" : contains the calculations for input renewable energy production time-series
"Grid_Availability" : contains the calculations for the national grid availability matrix 
"Plots" : script for visual representation of results.

