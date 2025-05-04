import pandas as pd
import numpy as np
import streamlit as st

from microgridspy.model.model import Model

import pandas as pd
import numpy as np

def get_sizing_results(model) -> pd.DataFrame:
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
            categories.append("Battery")
            capacities.append(np.round((bat_units.values * battery_nominal_capacity.values) / 1000))  # kWh, rounded
            existing_capacities.append(np.round(battery_existing_capacity / 1000))  # Rounded
            capacity_units.append('kWh')

    # Format sizing results into a table
    data = []
    for category, capacity, existing, unit in zip(categories, capacities, existing_capacities, capacity_units):
        row = [f"{category} ({unit})", int(existing)]
        row.extend([int(cap) for cap in capacity])  # Convert to integer
        # Calculate total capacity based on the presence of multiple steps
        if len(capacity) > 1:
            total_capacity = int(existing) + int(capacity[-1])  # Only add the last expansion step
        else:
            total_capacity = int(existing) + sum(int(cap) for cap in capacity)  # Sum existing and single step
        row.append(total_capacity)
        data.append(row)
    # Define columns, including the new "Total" column
    columns = ['Component', 'Existing'] + [f'Step {i+1}' for i in range(len(capacities[0]))] + ['Total']
    return pd.DataFrame(data, columns=columns)

def get_conversion_sizing_results(model) -> pd.DataFrame:
    """
    Get and format the sizing results for inverters, rectifiers, and transformers,
    including existing capacities for brownfield scenarios and the total sizing.

    Args:
        model (Model): The optimization model object.

    Returns:
        pd.DataFrame: A DataFrame with the formatted sizing results, including a "Total" column.
    """
    categories = []
    capacities = []
    existing_capacities = []
    capacity_units = []

    is_brownfield = model.get_settings('brownfield', advanced=True)
    steps = model.sets['steps'].values

    # Renewable inverters (kW)
    inverter_units_res = model.get_solution_variable('Units of Inverters for Renewables')
    if inverter_units_res is not None:
        res_nominal_inverter_capacity = model.parameters['RES_INVERTER_NOMINAL_CAPACITY']
        res_existing_inverter_capacity = model.parameters.get('RES_EXISTING_INVERTER_CAPACITY')
        connected_to_battery = model.parameters.get('RES_CONNECTED_TO_BATTERY')

        for source in inverter_units_res.renewable_sources.values:
            if connected_to_battery.sel(renewable_sources=source).values:
                continue
            categories.append(f"Renewable Inverter ({source})")
            cap = inverter_units_res.sel(renewable_sources=source).values * res_nominal_inverter_capacity.sel(renewable_sources=source).values / 1000
            capacities.append(cap)
            existing = res_existing_inverter_capacity.sel(renewable_sources=source).values / 1000 if is_brownfield and res_existing_inverter_capacity is not None else 0
            existing_capacities.append(existing)
            capacity_units.append('kW')

    # Battery inverters (kW)
    if model.has_battery:
        inverter_units_bat = model.get_solution_variable('Units of Inverters for Battery')
        if inverter_units_bat is not None:
            bat_nominal_inverter_capacity = model.parameters['BATTERY_INVERTER_NOMINAL_CAPACITY']
            bat_existing_inverter_capacity = model.parameters.get('BATTERY_EXISTING_INVERTER_CAPACITY', 0)
            is_dc = any(model.parameters['RES_CONNECTED_TO_BATTERY'].sel(renewable_sources=res).item() for res in model.sets.renewable_sources.values)
            categories.append("DC System Inverter" if is_dc else "Battery Inverter")
            cap = inverter_units_bat.values * bat_nominal_inverter_capacity.values / 1000
            capacities.append(cap)
            existing_capacities.append(bat_existing_inverter_capacity / 1000 if is_brownfield else 0)
            capacity_units.append('kW')

    # Generator rectifiers (kW)
    if model.has_generator:
        rectifier_units_gen = model.get_solution_variable('Units of Rectifiers for Generators')
        if rectifier_units_gen is not None and st.session_state.grid_type == 'Direct Current':
            gen_nominal_rectifier_capacity = model.parameters['GENERATOR_RECTIFIER_NOMINAL_CAPACITY']
            gen_existing_rectifier_capacity = model.parameters.get('GENERATOR_EXISTING_RECTIFIER_CAPACITY')

            for gen_type in rectifier_units_gen.generator_types.values:
                categories.append(f"Generator Rectifier ({gen_type})")
                cap = rectifier_units_gen.sel(generator_types=gen_type).values * gen_nominal_rectifier_capacity.sel(generator_types=gen_type).values / 1000
                capacities.append(cap)
                existing = gen_existing_rectifier_capacity.sel(generator_types=gen_type).values / 1000 if is_brownfield and gen_existing_rectifier_capacity is not None else 0
                existing_capacities.append(existing)
                capacity_units.append('kW')

    # Grid transformers (kVA)
    if model.has_grid_connection:
        transformer_units_grid = model.get_solution_variable('Units of Transformers for Grid')
        if transformer_units_grid is not None:
            grid_nominal_transformer_capacity = model.parameters['GRID_TRANSFORMER_NOMINAL_CAPACITY']
            grid_existing_transformer_capacity = model.parameters.get('GRID_EXISTING_TRANSFORMER_CAPACITY', 0)
            categories.append("Grid Transformer")
            cap = transformer_units_grid.values * grid_nominal_transformer_capacity / 1000
            capacities.append(cap)
            existing_capacities.append(grid_existing_transformer_capacity / 1000 if is_brownfield else 0)
            capacity_units.append('kVA')

    # Format sizing results into a table
    data = []
    for category, capacity, existing, unit in zip(categories, capacities, existing_capacities, capacity_units):
        row = [f"{category} ({unit})", int(existing)]
        row.extend([int(cap) for cap in capacity])
        total_capacity = int(existing) + sum(int(cap) for cap in capacity)
        row.append(total_capacity)
        data.append(row)

    columns = ['Component', 'Existing'] + [f'Step {i + 1}' for i in range(len(capacities[0]))] + ['Total']
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