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
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    total_renewable_production = model.get_solution_variable('Energy Production by Renewables')
    battery_outflow = model.get_solution_variable('Battery Outflow')
    battery_inflow = model.get_solution_variable('Battery Inflow')
    generator_energy_production = model.get_solution_variable('Generator Energy Production')

    years = demand.coords['years'].values
    renewable_sources = total_renewable_production.coords['renewable_sources'].values
    generator_types = generator_energy_production.coords['generator_types'].values if generator_energy_production is not None else []

    yearly_usage = {source: [] for source in renewable_sources}
    yearly_battery_usage = []
    yearly_generator_usage = {gen: [] for gen in generator_types}
    yearly_curtailment_percentage = []

    for year in years:
        yearly_demand = demand.sel(years=year).sum().values.item()
        yearly_curtailment = curtailment.sel(years=year).sum().values.item() if curtailment is not None else 0

        # Calculate renewable energy usage
        for source in renewable_sources:
            yearly_source_production = total_renewable_production.sel(renewable_sources=source, steps=1).sum().values.item()
            yearly_source_curtailment = curtailment.sel(renewable_sources=source, years=year).sum().values.item() if curtailment is not None else 0
            yearly_source_used = yearly_source_production - yearly_source_curtailment
            yearly_usage[source].append((yearly_source_used / yearly_demand) * 100)

        # Calculate battery usage
        if battery_outflow is not None:
            yearly_battery_out = battery_outflow.sel(years=year).sum().values.item()
            yearly_battery_usage.append((yearly_battery_out / yearly_demand) * 100)

        # Calculate generator usage
        if generator_energy_production is not None:
            for gen in generator_types:
                yearly_gen_production = generator_energy_production.sel(generator_types=gen, years=year).sum().values.item()
                yearly_generator_usage[gen].append((yearly_gen_production / yearly_demand) * 100)

        # Calculate curtailment percentage
        yearly_total_production = total_renewable_production.sel(steps=1).sum().values.item()
        if yearly_total_production > 0:
            yearly_curtailment_percentage.append((yearly_curtailment / yearly_total_production) * 100)
        else:
            yearly_curtailment_percentage.append(0)

    # Prepare the results
    results = {}
    for source in renewable_sources:
        results[f"{source} Usage"] = np.mean(yearly_usage[source])
    
    if battery_outflow is not None:
        results["Battery Usage"] = np.mean(yearly_battery_usage)
    
    for gen in generator_types:
        results[f"{gen} Usage"] = np.mean(yearly_generator_usage[gen])
    
    results["Curtailment"] = np.mean(yearly_curtailment_percentage)

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