##### RESULTS FILES #####

Results_Summary.xlsx : spreadsheet containing
			- sheet 'Size': Installed capacity of each component. In case of capacity expansion, it shows the size of each component after every investment step.
			- sheet 'Cost': Economic breakdown of the system. All the costs are ACTUALIZED to the year at which they occur.
			- sheet 'Yearly cash flows': Breakdown of yearly NON-ACTUALISED costs (fixed O&M, fuel cost, battery replacement, lost load), grouped by component type (battery, generators, renewable technologies)
			- sheet 'Yearly energy parameters': 
						* Generators share: total energy provided by generators divided by total electric demand
                                                * Renewables penetration: total energy provided by renewables divided by the sum of total energy provided by both renewables and generators
                                                * Curtailment share: total energy curtailed divided by the sum of total energy provided by both renewables and generators  
                                                * Battery usage: total energy discharged by the batteries divided by total electric demand

Time_Series.xlsx : spreadsheet containing
			- hourly energy balance of the system (technologies energy production, battery energy flows, demand, lost load, curtailment) + state of charge of the batteries and fuel consumed by the generators
			- each year of the time horizon is reported on a different sheet


Plots/: 
DispatchPlot: image print-out of system energy dispatch and load demand for the selected date(s)