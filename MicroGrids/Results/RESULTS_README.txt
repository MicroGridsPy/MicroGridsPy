##### RESULTS FILES #####

Results_Summary.xlsx : spreadsheet containing
			- sheet 'Project Total Costs' = summary of main cost items (NPC, Investment cost, Variable costs, final Salvage Value) and LCOE of the installed system
			- sheet 'Components Capacity and Cost' = breakdown of system installed capacity and investment costs associated to each component; if capacity-expansion is considered in the optimization, capacities and NON-ACTUALISED investment costs are given for each investment step
			- sheet 'Yearly Costs Info' = breakdown of yearly NON-ACTUALISED costs (fixed O&M, fuel cost, battery replacement, lost load), grouped by component type (battery, generator, aggregated renewable technologies)
			- sheet 'Yearly Energy Averages' = shares of production from each technology; percentage of curtailed energy

Time_Series.xlsx : spreadsheet containing
			- hourly energy balance of the system (technologies energy production, battery energy flows, load demand)
			- each year of the time horizon is reported on a different sheet

Battery_Data.xlsx : spreadsheet containing
			- sheet 'Battery_Data' = battery capacity and investment cost at each investment step; yearly O&M costs; total actualised cost of battery replacement (NB: if multiple scenarios are considered, the total actualised cost of battery replacement is the average among the scenarios)
			- sheet 'Yearly BRC' = yearly NON-ACTUALISED cost of battery replacement, given for each scenario

Generator_Data.xlsx : spreadsheet containing
			- sheet 'Generator Data' = generator capacity and investment cost at each investment step; yearly O&M costs; total actualised fuel cost (NB: if multiple scenarios are considered, the total actualised cost of battery replacement is the average among the scenarios)
			- sheet 'Yearly Fuel Costs' = yearly NON-ACTUALISED cost of fuel, given for each scenario

Renewable_Sources_Data.xlsx : spreadsheet containing
				- renewable energy technologies units, total capacity and investment cost at each investment step; yearly O&M costs 

Energy_Dispatch.png : printout of system energy dispatch and load demand for the selected date(s)