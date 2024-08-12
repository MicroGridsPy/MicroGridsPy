import numpy as np
import pandas as pd
import streamlit as st

from microgridspy.model.model import Model

def calculate_yearly_production(model):
    """Calculate yearly energy production by renewables."""
    res_production = model.get_solution_variable('Energy Production by Renewables')
    if res_production is None:
        st.warning("No renewable energy production data available.")
        return pd.DataFrame()

    years = model.sets['years'].values
    num_years = len(years)

    try:
        total_production = res_production.sum(dim=['periods', 'renewable_sources']).values.item()
        avg_yearly_production = total_production / num_years / 1e6  # Convert to MWh
        yearly_prod = {f'Year {year}': avg_yearly_production for year in years}
        
        st.info(f"Total production over all years: {total_production / 1e6:.2f} MWh")
        st.info(f"Average yearly production: {avg_yearly_production:.2f} MWh")

    except Exception as e:
        st.error(f"Error calculating production: {str(e)}")
        return pd.DataFrame()

    return pd.DataFrame.from_dict(yearly_prod, orient='index', columns=['Energy Production (MWh)'])

def calculate_energy_usage(model):
    """Calculate average energy usage by technology."""
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow') if model.has_battery else None
    battery_outflow = model.get_solution_variable('Battery Outflow') if model.has_battery else None
    generator_production = model.get_solution_variable('Generator Energy Production') if model.has_generator else None
    energy_from_grid = model.get_solution_variable('Energy from Grid') if model.has_grid_connection else None
    energy_to_grid = model.get_solution_variable('Energy to Grid') if model.has_grid_connection and model.get_settings('grid_connection_type', advanced=True) == 1 else None
    lost_load = model.get_solution_variable('Lost Load') if model.get_settings('lost_load_fraction') > 0.0 else None

    years = demand.coords['years'].values
    renewable_sources = model.sets['renewable_sources'].values
    generator_types = model.sets['generator_types'].values if model.has_generator else []

    yearly_usage = {source: [] for source in renewable_sources}
    yearly_curtailment_percentage = []
    yearly_battery_usage = []
    yearly_generator_usage = {gen: [] for gen in generator_types}
    yearly_grid_usage = []
    yearly_lost_load = []  

    for year in years:
        yearly_demand = demand.sel(years=year).sum().values.item()
        yearly_curtailment = curtailment.sel(years=year).sum().values.item()
        yearly_curtailment_percentage.append((yearly_curtailment / yearly_demand) * 100)

        # Calculate renewable energy usage
        for source in renewable_sources:
            yearly_source_production = res_production.sel(renewable_sources=source, steps=1).sum().values.item()
            yearly_source_curtailment = curtailment.sel(renewable_sources=source, years=year).sum().values.item()
            yearly_source_used = yearly_source_production - yearly_source_curtailment
            yearly_usage[source].append((yearly_source_used / yearly_demand) * 100)

        # Calculate battery usage
        if model.has_battery:
            yearly_battery_out = battery_outflow.sel(years=year).sum().values.item()
            yearly_battery_usage.append((yearly_battery_out / yearly_demand) * 100)

        # Calculate generator usage
        if model.has_generator:
            for gen in generator_types:
                yearly_gen_production = generator_production.sel(generator_types=gen, years=year).sum().values.item()
                yearly_generator_usage[gen].append((yearly_gen_production / yearly_demand) * 100)

        if model.has_grid_connection:
            yearly_grid_consumption = energy_from_grid.sel(years=year).sum().values.item()
            yearly_grid_usage.append((yearly_grid_consumption / yearly_demand) * 100)

        if model.get_settings('lost_load_fraction') > 0.0:
            yearly_lost_load.append((lost_load.sel(years=year).sum().values.item() / yearly_demand) * 100)

    # Prepare the results
    results = {}
    for source in renewable_sources:
        results[f"{source} Usage"] = np.mean(yearly_usage[source])

    results["Curtailment"] = np.mean(yearly_curtailment_percentage)
    
    if model.has_battery:
        results["Battery Usage"] = np.mean(yearly_battery_usage)
    
    if model.has_generator:
        for gen in generator_types:
            results[f"{gen} Usage"] = np.mean(yearly_generator_usage[gen])

    if model.has_grid_connection:
        results["Grid Usage"] = np.mean(yearly_grid_usage)

    if model.get_settings('lost_load_fraction') > 0.0:
        results["Lost Load"] = np.mean(yearly_lost_load)

    return results

def calculate_renewable_penetration(model: Model):
    """Calculate the total renewable penetration based on the model's constraint logic."""
    sets = model.sets
    years = sets['years'].values
    steps = sets['steps'].values
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    
    total_res_energy_production = model.get_solution_variable('Energy Production by Renewables').sum('renewable_sources')
    total_curtailment = model.get_solution_variable('Curtailment by Renewables').sum('renewable_sources')
    
    total_production = 0
    total_res_production = 0
    
    for year in years:
        step = years_steps_tuples[year - years[0]][1]
        
        yearly_energy_production = (total_res_energy_production.sel(steps=step) - 
                                    total_curtailment.sel(years=year))
        
        total_res_production += yearly_energy_production.sum().values.item()
        total_production += yearly_energy_production.sum().values.item()
        
        if model.has_generator:
            total_generator_energy_production = model.get_solution_variable('Generator Energy Production').sum('generator_types')
            total_production += total_generator_energy_production.sel(years=year).sum().values.item()
    
    renewable_penetration = (total_res_production / total_production) * 100 if total_production > 0 else 0
    
    return renewable_penetration