import xarray as xr

from typing import List

from microgridspy.model.model import Model

def calculate_actualized_investment_cost(model: Model) -> float:
    """Calculate the actualized investment cost based on the optimal capacities."""
    
    # Extract necessary parameters and variables from the model
    step_duration: int = model.get_settings('step_duration', advanced=True)
    num_steps: int = model.get_settings('num_steps', advanced=True)
    discount_rate: float = model.parameters['DISCOUNT_RATE'].values.item()
    
    # Create a list of years for each investment step
    investment_steps_years: List = [step * step_duration for step in range(num_steps)]
    
    # Calculate discount factor for each year
    discount_factor = xr.DataArray(
        [1 / ((1 + discount_rate) ** inv_year) for inv_year in investment_steps_years],
        coords={'steps': range(1, num_steps + 1)})
    
    investment_cost = 0
    
    for step in range(1, num_steps + 1):
        if step == 1:
            # Initial Investment Cost
            res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step)
            res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
            res_specific_investment_cost = model.parameters['RES_SPECIFIC_INVESTMENT_COST']
            
            investment_cost += (res_units * res_nominal_capacity * res_specific_investment_cost).sum('renewable_sources').values.item()
            
            if model.has_battery:
                battery_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step)
                battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
                battery_specific_investment_cost = model.parameters['BATTERY_SPECIFIC_INVESTMENT_COST']
                
                investment_cost += (battery_units * battery_nominal_capacity * battery_specific_investment_cost).values.item()
            
            if model.has_generator:
                generator_units = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step)
                generator_nominal_capacity = model.parameters['GENERATOR_NOMINAL_CAPACITY']
                generator_specific_investment_cost = model.parameters['GENERATOR_SPECIFIC_INVESTMENT_COST']
                
                investment_cost += (generator_units * generator_nominal_capacity * generator_specific_investment_cost).sum('generator_types').values.item()
        
        else:
            # Subsequent Investment Cost
            res_units_current = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step)
            res_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step - 1)
            
            investment_cost += ((res_units_current - res_units_previous) * 
                                res_nominal_capacity * 
                                res_specific_investment_cost * 
                                discount_factor.sel(steps=step)).sum('renewable_sources').values.item()
            
            if model.has_battery:
                battery_units_current = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step)
                battery_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step - 1)
                
                investment_cost += ((battery_units_current - battery_units_previous) * 
                                    battery_nominal_capacity * 
                                    battery_specific_investment_cost * 
                                    discount_factor.sel(steps=step)).values.item()
            
            if model.has_generator:
                generator_units_current = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step)
                generator_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step - 1)
                
                investment_cost += ((generator_units_current - generator_units_previous) * 
                                    generator_nominal_capacity * 
                                    generator_specific_investment_cost * 
                                    discount_factor.sel(steps=step)).sum('generator_types').values.item()
    
    return investment_cost / 1000  # Convert to thousands of currency units

def calculate_actualized_salvage_value(model: Model) -> float:
    """Calculate the actualized salvage value based on the optimal capacities."""
    
    # Extract necessary parameters and variables from the model
    project_duration: int = model.get_settings('time_horizon')
    step_duration: int = model.get_settings('step_duration', advanced=True)
    num_steps: int = model.get_settings('num_steps', advanced=True)
    discount_rate: float = model.parameters['DISCOUNT_RATE'].values.item()
    
    # Calculate discount factor
    discount_factor = 1 / ((1 + discount_rate) ** project_duration)
    
    salvage_value = 0
    
    for step in range(1, num_steps + 1):
        if step == 1:
            # Initial investment step
            res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step)
            res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
            res_specific_investment_cost = model.parameters['RES_SPECIFIC_INVESTMENT_COST']
            res_lifetime = model.parameters['RES_LIFETIME']
            
            salvage_value += (res_units * 
                              res_nominal_capacity * res_specific_investment_cost *
                              ((res_lifetime - project_duration) / res_lifetime) *
                              discount_factor).sum('renewable_sources').values.item()
            
            if model.has_battery:
                battery_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step)
                battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
                battery_specific_investment_cost = model.parameters['BATTERY_SPECIFIC_INVESTMENT_COST']
                battery_lifetime = model.parameters['BATTERY_LIFETIME']
                
                salvage_value += (battery_units * 
                                  battery_nominal_capacity * battery_specific_investment_cost *
                                  ((battery_lifetime - project_duration) / battery_lifetime) *
                                  discount_factor).values.item()
            
            if model.has_generator:
                generator_units = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step)
                generator_nominal_capacity = model.parameters['GENERATOR_NOMINAL_CAPACITY']
                generator_specific_investment_cost = model.parameters['GENERATOR_SPECIFIC_INVESTMENT_COST']
                generator_lifetime = model.parameters['GENERATOR_LIFETIME']
                
                salvage_value += (generator_units * 
                                  generator_nominal_capacity * generator_specific_investment_cost *
                                  ((generator_lifetime - project_duration) / generator_lifetime) *
                                  discount_factor).sum('generator_types').values.item()
        
        else:
            # Subsequent investment steps
            res_units_current = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step)
            res_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Renewables').sel(steps=step - 1)
            additional_units = res_units_current - res_units_previous
            remaining_lifetime = res_lifetime - (project_duration - (step * step_duration))
            
            salvage_value += (additional_units * 
                              res_nominal_capacity * res_specific_investment_cost *
                              (remaining_lifetime / res_lifetime) *
                              discount_factor).sum('renewable_sources').values.item()
            
            if model.has_battery:
                battery_units_current = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step)
                battery_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Batteries').sel(steps=step - 1)
                additional_battery_units = battery_units_current - battery_units_previous
                remaining_battery_lifetime = battery_lifetime - (project_duration - (step * step_duration))
                
                salvage_value += (additional_battery_units * 
                                  battery_nominal_capacity * battery_specific_investment_cost *
                                  (remaining_battery_lifetime / battery_lifetime) *
                                  discount_factor).values.item()
            
            if model.has_generator:
                generator_units_current = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step)
                generator_units_previous = model.get_solution_variable('Unit of Nominal Capacity for Generators').sel(steps=step - 1)
                additional_generator_units = generator_units_current - generator_units_previous
                remaining_generator_lifetime = generator_lifetime - (project_duration - (step * step_duration))
                
                salvage_value += (additional_generator_units * 
                                  generator_nominal_capacity * generator_specific_investment_cost *
                                  (remaining_generator_lifetime / generator_lifetime) *
                                  discount_factor).sum('generator_types').values.item()
    
    return salvage_value / 1000

def calculate_lcoe(model: Model, optimization_goal: str) -> float:
    demand = model.parameters['DEMAND'] / 1000 # kW
    discount_rate = model.parameters['DISCOUNT_RATE'].values.item()
    num_years = len(demand.coords['years'])
    project_years = range(num_years)
    pv_demand = sum(demand.isel(years=year-1, scenarios=0).sum().values / ((1 + discount_rate) ** year) for year in project_years)
    if optimization_goal == 'NPC':
        net_present_cost = model.get_solution_variable('Net Present Cost').values.item()
        lcoe = net_present_cost / pv_demand
        return lcoe
    elif optimization_goal == 'Total Variable Cost':
        total_variable_cost = model.get_solution_variable('Total Variable Cost').values.item()
        lvc = total_variable_cost / pv_demand
        return lvc