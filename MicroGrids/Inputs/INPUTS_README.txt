##### INPUT DATA FILES #####

data_MY.dat : text file containing
		- optimization parameters (time horizon, duration of investment steps, time resolution, number of scenarios)
		- technical parameters (renewable technologies number and capacity, battery technical data, generator efficiency and fuel LHV, components lifetime)
		- economic parameters (unitary cost of components, discount rate, O&M costs, fuel cost)

Demand.xls : spreadsheet containing
		- yearly electricity demand profile
		- one column for each year of the time horizon (numbered 1 to Y)
		- N rows (N depends on time resolution, e.g. 8760 rows for hourly resolution)
		- if multiple load demand scenarios are considered, Y*S columns must be provided (with Y=number_years, S=number_scenarios); numbered 1 to Y*S

Renewable_Energy.xls : spreadsheet containing
		- yearly output of renewable technologies
		- one column for each technology (numbered 1 to R, with R=number_technologies)
		- N rows (N depends on time resolution, e.g. 8760 rows for hourly resolution)
		- if multiple scenarios of resources availability are considered, R*S columns must be provided; numbered 1 to R*S