from typing import Dict
import streamlit as st

import xarray as xr
import linopy
from linopy import Model

from microgridspy.model.parameters import ProjectParameters


def add_energy_balance_constraints(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool) -> None:
    """Add energy balance constraint."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    # Calculate total renewable energy production
    total_res_energy_production = var['res_energy_production'].sum('renewable_sources')
    total_curtailment = var['curtailment'].sum('renewable_sources')

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        
        # Initialize total_energy_production for each year
        yearly_energy_production: linopy.LinearExpression = total_res_energy_production.sel(steps=step) - total_curtailment.sel(years=year)
        yearly_transformation_losses: linopy.LinearExpression = 0

        # Calculate renewable transformation losses and save them
        # Initialize a container for yearly transformation losses per source
        res_yearly_transformation_losses = {}

        for res in sets.renewable_sources.values:
            # Calculate transformation losses for each renewable source
            source_losses = (
                (var['res_energy_production'].sel(renewable_sources=res).sel(steps=step)
                 - var['curtailment'].sel(renewable_sources=res).sel(years=year))
                 * (1 - param['RES_INVERTER_EFFICIENCY'].sel(renewable_sources=res))
            )
            # Save losses for the source into the dictionary
            res_yearly_transformation_losses[res] = source_losses
            # Add constraint for each source's transformation losses
            model.add_constraints(
                source_losses == var['res_transformation_losses'].sel(renewable_sources=res, years=year),
                name=f"RES Transformation Losses - {res} - Year {year}"
            )
        # Optionally: Sum up all sources for total yearly transformation losses
        yearly_transformation_losses = sum(res_yearly_transformation_losses.values())
        
        if has_battery:
            # Calculate battery system energy
            battery_system_energy = (
                var['battery_outflow'].sel(years=year) - var['battery_inflow'].sel(years=year)
            )
            yearly_energy_production += battery_system_energy
            if any(param['RES_CONNECTED_TO_BATTERY'].sel(renewable_sources=res).item() for res in sets.renewable_sources.values):
                # Add renewable sources connected to the battery
                for res in sets.renewable_sources.values:
                    if param['RES_CONNECTED_TO_BATTERY'].sel(renewable_sources=res).item() == True:
                        st.write(f"Battery is connected to {res}.")
                        st.write(f"BATTERY_INVERTER_EFFICIENCY_DC_AC: {param['BATTERY_INVERTER_EFFICIENCY_DC_AC'].item()}")
                        st.write(f"BATTERY_INVERTER_EFFICIENCY_AC_DC: {param['BATTERY_INVERTER_EFFICIENCY_AC_DC'].item()}")
                        battery_system_energy += (
                            var['res_energy_production'].sel(renewable_sources=res, steps=step)
                            - var['curtailment'].sel(renewable_sources=res).sel(years=year)
                        )
                # Big-M constraints to link binary variable with the energy flow condition
                M = 10e9 #var['battery_inverter_units'] * param['BATTERY_INVERTER_NOMINAL_CAPACITY']  # A sufficiently large number
                model.add_constraints(
                    var['ones'].sel(years=year) == 1,
                    name=f"Fix ones to 1 - {year}"
                )

                model.add_constraints(
                    battery_system_energy ==  var['dc_system_energy'].sel(years=year),
                    name=f"Battery Energy Positive - Year {year}"
                )

                model.add_constraints(
                    var['dc_system_energy'].sel(years=year) <=  M * var['single_flow_dc_system'].sel(years=year),
                    name=f"Battery Energy Positive - Year {year}"
                )
                model.add_constraints(
                    var['dc_system_energy'].sel(years=year) >= (-M) * (var['ones'].sel(years=year)-var['single_flow_dc_system'].sel(years=year)),
                    name=f"Battery Energy Negative - Year {year}"
                )
                
                # Define battery losses for positive and negative cases
                battery_losses_positive = (
                    var['dc_system_energy'].sel(years=year) * (1 - param['BATTERY_INVERTER_EFFICIENCY_DC_AC'].item())
                )
                battery_losses_negative = - (
                    var['dc_system_energy'].sel(years=year) * ((1 / param['BATTERY_INVERTER_EFFICIENCY_AC_DC'].item()) - 1)
                )
                model.add_constraints(
                    var['battery_system_feed_in_losses'].sel(years=year) == battery_losses_positive * var['single_flow_dc_system'].sel(years=year),
                    name=f"Battery Losses Positive - Year {year}"
                )
                model.add_constraints(
                    var['battery_system_charge_losses'].sel(years=year) == battery_losses_negative - battery_losses_negative * var['single_flow_dc_system'].sel(years=year),
                    name=f"Battery Losses Negative - Year {year}"
                )

                yearly_transformation_losses += var['battery_system_feed_in_losses'].sel(years=year) + var['battery_system_charge_losses'].sel(years=year)
            

            else:
                st.write("Battery is not connected to any renewable source.")
                battery_losses = (var['battery_outflow'].sel(years=year) * (1 - param['BATTERY_INVERTER_EFFICIENCY_DC_AC'].item()) +
                                  var['battery_inflow'].sel(years=year) * ((1 / param['BATTERY_INVERTER_EFFICIENCY_AC_DC'].item()) - 1))
                
                # Add constraint for battery losses
                model.add_constraints(
                    battery_losses == var['battery_system_transformation_losses'].sel(years=year),
                    name=f"Battery Transformation Losses - Year {year}"
                )

                # Update yearly transformation losses
                yearly_transformation_losses += battery_losses
                
        if has_generator:
            # Initialize a container for yearly transformation losses per generator type
            yearly_generator_transformation_losses = {}

            # Calculate total generator energy production
            total_generator_energy_production = var['generator_energy_production'].sum('generator_types')
            yearly_energy_production += total_generator_energy_production.sel(years=year)

            for generator in sets.generator_types.values:
                # Calculate transformation losses for each generator type
                generator_loss = (
                    var['generator_energy_production'].sel(generator_types=generator).sel(years=year)
                    * (1 - param['GENERATOR_RECTIFIER_EFFICIENCY'].sel(generator_types=generator))
                )
                
                # Save losses for the generator type into the dictionary
                yearly_generator_transformation_losses[generator] = generator_loss
                
                # Add constraint for each generator type's transformation losses
                model.add_constraints(
                    generator_loss == var['generator_transformation_losses'].sel(generator_types=generator, years=year),
                    name=f"Generator Transformation Losses - {generator} - Year {year}"
                )

            # Optionally: Sum up all generator types for total yearly transformation losses
            total_generator_transformation_losses = sum(yearly_generator_transformation_losses.values())
            yearly_transformation_losses += total_generator_transformation_losses

        if has_grid_connection:
            if settings.advanced_settings.grid_connection_type == 1:
                # Calculate energy from grid and energy to grid if Purchase/Sell is selected
                yearly_energy_production += (var['energy_from_grid'].sel(years=year) - var['energy_to_grid'].sel(years=year))
                grid_losses = (
                    var['energy_from_grid'].sel(years=year) * (1 - param['GRID_TO_MICROGRID_EFFICIENCY'])
                    + var['energy_to_grid'].sel(years=year) * ((1 / param['MICROGRID_TO_GRID_EFFICIENCY']) - 1)
                )
            else:
                # Calculate energy from grid if Purchase Only is selected
                yearly_energy_production += var['energy_from_grid'].sel(years=year)
                grid_losses = var['energy_from_grid'].sel(years=year) * (1 - param['GRID_TO_MICROGRID_EFFICIENCY'])
            model.add_constraints(grid_losses == var['grid_transformation_losses'].sel(years=year), name=f"Grid Transformation Losses - Year {year}")

            yearly_transformation_losses += grid_losses

        if settings.project_settings.lost_load_fraction > 0:
            yearly_energy_production += var['lost_load'].sel(years=year)
            
        # Add the energy balance constraint for each year
        model.add_constraints(yearly_energy_production - yearly_transformation_losses == param['DEMAND'].sel(years=year), name=f"Energy Balance Constraint - Year {year}")

    # Add renewable penetration constraint if specified
    if settings.project_settings.renewable_penetration > 0:
        add_renewable_penetration_constraint(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)

    if settings.project_settings.lost_load_fraction > 0:
        add_lost_load_constraint(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)

def add_renewable_penetration_constraint(
    model: Model,
    settings: ProjectParameters,
    sets: xr.Dataset,
    param: xr.Dataset,
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool
) -> None:
    """Add renewable penetration constraint."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    
    # Calculate total renewable energy production
    total_res_energy_production = var['res_energy_production'].sum('renewable_sources')
    total_curtailment = var['curtailment'].sum('renewable_sources')
    
    total_production: linopy.LinearExpression = 0
    total_res_production: linopy.LinearExpression = 0
    
    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        
        # Calculate renewable energy production for each year
        yearly_res_production = total_res_energy_production.sel(steps=step) - total_curtailment.sel(years=year)
        total_res_production += yearly_res_production
        
        # Calculate total energy production/consumption
        yearly_total_production = yearly_res_production
        
        if has_generator:
            yearly_generator_production = var['generator_energy_production'].sum('generator_types').sel(years=year)
            yearly_total_production += yearly_generator_production
        
        if has_grid_connection:
            yearly_grid_import = var['energy_from_grid'].sel(years=year)
            yearly_total_production += yearly_grid_import
        
        total_production += yearly_total_production

    # Add the constraint
    model.add_constraints(
        (1 - param['MINIMUM_RENEWABLE_PENETRATION']) * total_res_production >= 
        param['MINIMUM_RENEWABLE_PENETRATION'] * (total_production - total_res_production),
        name="Renewable Penetration Constraint")
    
def add_lost_load_constraint(
    model: Model, 
    settings: ProjectParameters, 
    sets: xr.Dataset, 
    param: xr.Dataset, 
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool) -> None:

    years = sets.years.values

    for year in sets.years.values:
        # Add the lost load constraint for each year
        model.add_constraints(var['lost_load'].sel(years=year) <= param['DEMAND'].sel(years=year) * param['LOST_LOAD_FRACTION'], name=f"Lost Load Constraint - Year {year}")
