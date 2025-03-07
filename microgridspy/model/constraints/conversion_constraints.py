import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict
import streamlit as st

def add_minimum_conversion_size_constraints(model: Model, 
                                          settings: ProjectParameters, 
                                          sets: xr.Dataset, 
                                          param: xr.Dataset, 
                                          var: Dict[str, linopy.Variable], 
                                          has_battery: bool, 
                                          has_generator: bool, 
                                          has_grid_connection: bool) -> None:
    """Add constraints for inverters, rectifiers and transformators."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    is_brownfield = settings.advanced_settings.brownfield

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]

        for res in sets.renewable_sources.values:
            if is_brownfield:
                # Calculate total_age over 'res_types' and 'years'
                total_age = param['RES_INVERTER_EXISTING_YEARS'].sel(renewable_sources=res) + (year - years[0])

                # Calculate lifetime_exceeded over 'res_types' and 'years'
                lifetime_exceeded = total_age > param['RES_INVERTER_LIFETIME'].sel(renewable_sources=res)

                if lifetime_exceeded is False:
                    inverter_capacity = (param['RES_INVERTER_EXISTING_CAPACITY'].sel(renewable_sources=res) + var['res_inverter_units'].sel(steps=step, renewable_sources=res) * param['RES_INVERTER_NOMINAL_CAPACITY'].sel(renewable_sources=res))
                else:
                    inverter_capacity = var['res_inverter_units'].sel(steps=step, renewable_sources=res) * param['RES_INVERTER_NOMINAL_CAPACITY'].sel(renewable_sources=res)
            else:
                inverter_capacity = var['res_inverter_units'].sel(steps=step, renewable_sources=res) * param['RES_INVERTER_NOMINAL_CAPACITY'].sel(renewable_sources=res)

            model.add_constraints(
                (var['res_energy_production'].sel(renewable_sources=res).sel(steps=step)
                - var['curtailment'].sel(renewable_sources=res).sel(years=year)) <= inverter_capacity,
                name=f"Renewable Inverter Size - {res} - Year {year}"
            )
            
        if has_battery:
                if is_brownfield:
                    total_age = param['BATTERY_INVERTER_EXISTING_YEARS'] + (year - years[0])
                    lifetime_exceeded = total_age > param['BATTERY_INVERTER_LIFETIME']
                    if lifetime_exceeded is False:
                        inverter_capacity = (param['BATTERY_INVERTER_EXISTING_CAPACITY'] + var['battery_inverter_units'].sel(steps=step) * param['BATTERY_INVERTER_NOMINAL_CAPACITY'])
                    else:
                        inverter_capacity = var['battery_inverter_units'].sel(steps=step) * param['BATTERY_INVERTER_NOMINAL_CAPACITY']
                else:
                    inverter_capacity = var['battery_inverter_units'].sel(steps=step) * param['BATTERY_INVERTER_NOMINAL_CAPACITY']
                if any(param['RES_CONNECTED_TO_BATTERY'].sel(renewable_sources=res).item() for res in sets.renewable_sources.values):
                    model.add_constraints(
                        var['dc_system_energy'].sel(years=year) <= inverter_capacity,
                        name=f"Battery Inverter Size Outflow - Year {year}"
                    )
                    model.add_constraints(
                        var['dc_system_energy'].sel(years=year) >= -inverter_capacity,
                        name=f"Battery Inverter Size Inflow - Year {year}"
                    )
                else:
                    model.add_constraints(
                        var['battery_outflow'].sel(years=year) <= inverter_capacity,
                        name=f"Battery Inverter Size Outflow - Year {year}"
                    )
                    model.add_constraints(
                        var['battery_inflow'].sel(years=year) <= inverter_capacity,
                        name=f"Battery Inverter Size Inflow - Year {year}"
                    )

        if has_generator:
            for generator in sets.generator_types.values:
                if is_brownfield:   
                    total_age = param['GENERATOR_RECTIFIER_EXISTING_YEARS'].sel(generator_types=generator) + (year - years[0])
                    lifetime_exceeded = total_age > param['GENERATOR_RECTIFIER_LIFETIME'].sel(generator_types=generator)

                    if lifetime_exceeded is False:
                        inverter_capacity = (param['GENERATOR_RECTIFIER_EXISTING_CAPACITY'].sel(generator_types=generator) + var['generator_rectifier_units'].sel(generator_types=generator, steps=step) * param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY']).sel(generator_types=generator)
                    else:
                        inverter_capacity = var['generator_rectifier_units'].sel(generator_types=generator, steps=step) * param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'].sel(generator_types=generator)
                else:
                    inverter_capacity = var['generator_rectifier_units'].sel(generator_types=generator, steps=step) * param['GENERATOR_RECTIFIER_NOMINAL_CAPACITY'].sel(generator_types=generator)
                model.add_constraints(
                    var['generator_energy_production'].sel(generator_types=generator, years=year) <= inverter_capacity,
                    name=f"Generator Rectifier Size - {generator} - Year {year}"
                )

        if has_grid_connection:
            if settings.advanced_settings.grid_connection_type == 1:
                model.add_constraints(
                    var['energy_from_grid'].sel(years=year) <= var['grid_transformer_units'].sel(steps=step) * param['GRID_TRANSFORMER_NOMINAL_CAPACITY'],
                )
                model.add_constraints(
                    var['energy_to_grid'].sel(years=year) <= var['grid_transformer_units'].sel(steps=step) * param['GRID_TRANSFORMER_NOMINAL_CAPACITY'],
                )
            else:
                model.add_constraints(
                    var['energy_from_grid'].sel(years=year) <= var['grid_transformer_units'].sel(steps=step) * param['GRID_TRANSFORMER_NOMINAL_CAPACITY'],
                )

    for step in sets.steps.values[1:]:
        model.add_constraints(
            var['res_inverter_units'].sel(steps=step) >= var['res_inverter_units'].sel(steps=step - 1),
            name=f"RES Inverter Min Step Units Constraint - Step {step}")
        if has_battery:
            model.add_constraints(
                var['battery_inverter_units'].sel(steps=step) >= var['battery_inverter_units'].sel(steps=step - 1),
                name=f"Battery Inverter Min Step Units Constraint - Step {step}")
        if has_generator:
            model.add_constraints(
                var['generator_rectifier_units'].sel(steps=step) >= var['generator_rectifier_units'].sel(steps=step - 1),
                name=f"Generator Rectifier Min Step Units Constraint - Step {step}")
        if has_grid_connection:
            model.add_constraints(
                var['grid_transformer_units'].sel(steps=step) >= var['grid_transformer_units'].sel(steps=step - 1),
                name=f"Grid Transformer Min Step Units Constraint - Step {step}")