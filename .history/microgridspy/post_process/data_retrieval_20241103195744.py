import pandas as pd
import numpy as np

from microgridspy.model.model import Model

def get_sizing_results(model: Model) -> pd.DataFrame:
    """
    Get and format the sizing results, including existing capacities for brownfield scenarios and the total sizing.
    
    Args:
        model (Model): The optimization model object.
        
    Returns:
        pd.DataFrame: A DataFrame with the formatted sizing results, including a "Total" column.
    """
    categories = []
    capacities = []
    existing_capacities = []
    capacity_units = []

    # Renewable sources and Generators (kW)
    components_kw = []
    is_brownfield = model.get_settings('brownfield', advanced=True)

    res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables')
    if res_units is not None:
        res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
        res_existing_capacity = model.parameters.get('RES_EXISTING_CAPACITY', 0)
        for source in res_units.renewable_sources.values:
            components_kw.append((source, res_units.sel(renewable_sources=source), 
                                  res_nominal_capacity.sel(renewable_sources=source),
                                  res_existing_capacity.sel(renewable_sources=source) if is_brownfield else 0))

    if model.has_generator:
        gen_units = model.get_solution_variable('Unit of Nominal Capacity for Generators')
        if gen_units is not None:
            gen_nominal_capacity = model.parameters['GENERATOR_NOMINAL_CAPACITY']
            gen_existing_capacity = model.parameters.get('GENERATOR_EXISTING_CAPACITY', 0)
            for gen_type in gen_units.generator_types.values:
                components_kw.append((gen_type, gen_units.sel(generator_types=gen_type), 
                                      gen_nominal_capacity.sel(generator_types=gen_type),
                                      gen_existing_capacity.sel(generator_types=gen_type) if is_brownfield else 0))

    for name, units, nominal_capacity, existing_capacity in components_kw:
        categories.append(name)
        capacities.append(np.round((units.values * nominal_capacity.values) / 1000))  # kW, rounded
        existing_capacities.append(np.round(existing_capacity / 1000))  # Rounded
        capacity_units.append('kW')

    # Battery (kWh)
    if model.has_battery:
        bat_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries')
        if bat_units is not None:
            battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
            battery_existing_capacity = model.parameters.get('BATTERY_EXISTING_CAPACITY', 0)
            categories.append("Battery Bank")
            capacities.append(np.round((bat_units.values * battery_nominal_capacity.values) / 1000))  # kWh, rounded
            existing_capacities.append(np.round(battery_existing_capacity / 1000))  # Rounded
            capacity_units.append('kWh')

    # Format sizing results into a table
    data = []
    for category, capacity, existing, unit in zip(categories, capacities, existing_capacities, capacity_units):
        row = [f"{category} ({unit})", int(existing)]
        row.extend([int(cap) for cap in capacity])  # Convert to integer
        total_capacity = int(existing) + sum(int(cap) for cap in capacity)  # Calculate total capacity
        row.append(total_capacity)
        data.append(row)

    # Define columns, including the new "Total" column
    columns = ['Component', 'Existing'] + [f'Step {i+1}' for i in range(len(capacities[0]))] + ['Total']
    return pd.DataFrame(data, columns=columns)



def get_renewables_usage(model: Model, renewable_source=None):
    """Get generator usage for a given generator type or all types."""
    sets = model.sets
    years = sets['years'].values
    steps = sets['steps'].values
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    total_res_production = model.get_solution_variable('Energy Production by Renewables')
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    all_data = []

    if renewable_source is not None:
        # Select the specific renewable_source
        total_res_production = total_res_production.sel(renewable_sources=renewable_source)
        curtailment = curtailment.sel(renewable_sources=renewable_source)
    
    for year in years:
        step = years_steps_tuples[year - years[0]][1]
        res_production = (total_res_production.sel(steps=step) - curtailment.sel(years=year))  
        year_data = res_production.isel(scenarios=0).values / 1000
        all_data.extend(year_data)
    
    column_name = f'{renewable_source} Production (kWh)'
    return pd.DataFrame(all_data, columns=[column_name])

def get_battery_soc(model: Model, year=None):
    """Get battery state of charge for a given year or all years."""
    soc = model.get_solution_variable('Battery State of Charge')
    if soc is None:
        return pd.DataFrame()
    
    if year is not None:
        return pd.DataFrame(soc.isel(scenarios=0, years=year).values / 1000, columns=['State of Charge (kWh)'])
    else:
        all_data = []
        for year in range(len(soc.coords['years'])):
            year_data = soc.isel(scenarios=0, years=year).values / 1000
            all_data.extend(year_data)
        return pd.DataFrame(all_data, columns=['State of Charge (kWh)'])

def get_generator_usage(model, generator_type=None):
    """Get generator usage for a given generator type or all types."""
    gen_production = model.get_solution_variable('Generator Energy Production')
    if gen_production is None:
        return pd.DataFrame()
    
    if generator_type is not None:
        # Select the specific generator type
        gen_production = gen_production.sel(generator_types=generator_type)
    
    all_data = []
    for year in range(len(gen_production.coords['years'])):
        year_data = gen_production.isel(scenarios=0, years=year).values / 1000
        all_data.extend(year_data)
    
    column_name = f'{generator_type} Production (kWh)'
    return pd.DataFrame(all_data, columns=[column_name])

def get_grid_usage(model: Model, year=None):
    """Get grid usage for a given year or all years."""
    grid_usage = model.get_solution_variable('Energy from Grid')
    if grid_usage is None:
        return pd.DataFrame()
    
    if year is not None:
        return pd.DataFrame(grid_usage.isel(scenarios=0, years=year).values / 1000, columns=['Grid Usage (kWh)'])
    else:
        all_data = []
        for year in range(len(grid_usage.coords['years'])):
            year_data = grid_usage.isel(scenarios=0, years=year).values / 1000
            all_data.extend(year_data)
        return pd.DataFrame(all_data, columns=['Grid Usage (kWh)'])