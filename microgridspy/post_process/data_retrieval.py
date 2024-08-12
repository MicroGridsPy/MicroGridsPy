import pandas as pd

from microgridspy.model.model import Model

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