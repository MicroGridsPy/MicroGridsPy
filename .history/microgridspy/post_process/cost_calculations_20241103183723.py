import xarray as xr
import numpy as np

from typing import List, Tuple

from microgridspy.model.model import Model

def calculate_grid_costs(model: Model, actualized: bool) -> Tuple[float, float, float, float]:
    """Calculate grid-related costs."""
    grid_investment_cost = model.parameters['GRID_CONNECTION_COST'].values * model.parameters['GRID_DISTANCE'].values
    grid_fixed_om_cost = grid_investment_cost * model.parameters['GRID_MAINTENANCE_COST'].values
    
    years = model.sets['years'].values
    start_year = years[0]
    discount_rate = model.parameters['DISCOUNT_RATE'].values.item()
    energy_from_grid = model.get_solution_variable("Energy from Grid")
    electricity_cost = model.parameters['ELECTRICTY_PURCHASED_COST']
    
    if actualized:
        cost_electricity_purchased = sum(
            np.sum(energy_from_grid.sel(years=year).values * electricity_cost.values) / 
            ((1 + discount_rate) ** (year - start_year + 1))
            for year in years
        )
    else:
        cost_electricity_purchased = sum(
            np.sum(energy_from_grid.sel(years=year).values * electricity_cost.values)
            for year in years
        )
    
    cost_electricity_sold = 0
    if model.get_settings('grid_connection_type', advanced=True) == 1:
        energy_to_grid = model.get_solution_variable("Energy to Grid")
        electricity_price = model.parameters['ELECTRICTY_SOLD_PRICE']
        if actualized:
            cost_electricity_sold = sum(
                np.sum(energy_to_grid.sel(years=year).values * electricity_price.values) / 
                ((1 + discount_rate) ** (year - start_year + 1))
                for year in years
            )
        else:
            cost_electricity_sold = sum(
                np.sum(energy_to_grid.sel(years=year).values * electricity_price.values)
                for year in years
            )
    
    return grid_investment_cost.item(), grid_fixed_om_cost.item(), cost_electricity_purchased, cost_electricity_sold


def calculate_actualized_investment_cost(model: Model) -> float:
    """Calculate the actualized investment cost based on the optimal capacities."""
    
    step_duration: int = model.get_settings('step_duration', advanced=True)
    num_steps: int = model.get_settings('num_steps', advanced=True)
    discount_rate: float = model.parameters['DISCOUNT_RATE'].values.item()
    
    investment_steps_years: List = [step * step_duration for step in range(num_steps)]
    
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
    
    # Add grid investment cost if applicable
    if model.has_grid_connection:
        grid_investment_cost, _, _ = calculate_grid_costs(model)
        investment_cost += grid_investment_cost
    
    return investment_cost

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
    """Calculate the Levelized Cost of Energy (LCOE) or Levelized Variable Cost (LVC)."""
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
    
def get_cost_details(model: Model, optimization_goal: int) -> dict:
    """Get detailed cost breakdown."""
    def get_cost(var_name: str) -> float:
        value = model.get_solution_variable(var_name)
        return value.values.item() / 1000 if value is not None else 0

    actualized = optimization_goal == "NPC"
    suffix = "(Actualized)" if actualized else "(Not Actualized)"
    
    cost_details = {
        "Total Investment Cost (Actualized)": get_cost("Total Investment Cost") if actualized else calculate_actualized_investment_cost(model),
        f"Total Variable Cost {suffix}": get_cost(f"Scenario Total Variable Cost {suffix}"),
        f"Total Fixed O&M Cost {suffix}": get_cost(f"Operation and Maintenance Cost {suffix}"),
        f"Total Battery Replacement Cost {suffix}": get_cost(f"Battery Replacement Cost {suffix}") if model.has_battery else 0,
        f"Total Fuel Cost {suffix}": get_cost(f"Total Fuel Cost {suffix}") if model.has_generator else 0,
        f"Total Salvage Value (Actualized)": get_cost("Salvage Value") if actualized else calculate_actualized_salvage_value(model)
    }
    
    if model.has_grid_connection:
        grid_investment_cost, grid_fixed_om_cost, cost_electricity_purchased, cost_electricity_sold = calculate_grid_costs(model, actualized)
        cost_details.update({
            f"Total Grid Connection Cost (Actualized)": get_cost("Total Grid Connection Cost (Actualized)"),
            f"Grid Investment Cost (Actualized)": grid_investment_cost / 1000,
            f"Grid Fixed O&M Cost {suffix}": grid_fixed_om_cost / 1000,
            f"Total Electricity Purchased Cost {suffix}": cost_electricity_purchased / 1000
        })
        if model.get_settings('grid_connection_type', advanced=True) == 1:
            cost_details[f"Total Electricity Sold Revenue {suffix}"] = cost_electricity_sold / 1000
    
    return cost_details