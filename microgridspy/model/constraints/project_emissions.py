import linopy
import xarray as xr
from typing import Dict
from linopy import Model
from microgridspy.model.parameters import ProjectParameters

def add_res_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add CO2 emissions constraint for renewable installations."""
    res_emissions = 0
    for step in sets.steps.values:
        delta_units = var['res_units'].sel(steps=step) if step == 1 else (
            var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1))
        res_emissions += (delta_units * param['RES_NOMINAL_CAPACITY'] * param['RES_UNIT_CO2_EMISSION']).sum('renewable_sources')

    model.add_constraints(var['res_emission'].sum('steps') == res_emissions, name="RES Emissions Constraint")

def add_battery_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add CO2 emissions constraint for battery installations."""
    battery_emissions = 0
    for step in sets.steps.values:
        delta_units = var['battery_units'].sel(steps=step) if step == 1 else (
            var['battery_units'].sel(steps=step) - var['battery_units'].sel(steps=step - 1))
        battery_emissions += delta_units * param['BATTERY_NOMINAL_CAPACITY'] * param['BATTERY_UNIT_CO2_EMISSION']

    model.add_constraints(var['battery_emission'].sum('steps') == battery_emissions, name="Battery Emissions Constraint")

def add_generator_emissions_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add CO2 emissions constraints for generator installations and fuel usage."""
    generator_emissions = 0
    for step in sets.steps.values:
        delta_units = var['generator_units'].sel(steps=step) if step == 1 else (
            var['generator_units'].sel(steps=step) - var['generator_units'].sel(steps=step - 1))
        generator_emissions += (delta_units * param['GENERATOR_NOMINAL_CAPACITY'] * param['GENERATOR_UNIT_CO2_EMISSION']).sum('generator_types')

    model.add_constraints(var['gen_emission'].sum('steps') == generator_emissions, name="Generator Emissions Constraint")

    # Fuel combustion emissions
    model.add_constraints(
        var['fuel_emission'] == var['generator_fuel_consumption'] * param['FUEL_CO2_EMISSION'],
        name="Fuel Emissions Constraint")

def add_grid_emission_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add CO2 emissions constraints for electricity imported from the grid."""
    grid_factor = settings.grid_params.national_grid_specific_co2_emissions / 1000  # g/kWh to kg/kWh
    model.add_constraints(
        var['grid_emission'] == var['energy_from_grid'] * grid_factor,
        name="Grid Emission Calculation")

    model.add_constraints(
        var['scenario_grid_emission'] == var['grid_emission'].sum(dim=['years', 'periods']),
        name="Scenario Grid Emission Calculation")

def add_project_emissions(
    model: Model,
    settings: ProjectParameters,
    sets: xr.Dataset,
    param: xr.Dataset,
    var: Dict[str, linopy.Variable],
    has_battery: bool,
    has_generator: bool,
    has_grid_connection: bool
) -> None:
    """Aggregate all emission constraints for the system."""
    add_res_emissions_constraints(model, settings, sets, param, var)
    
    total_emissions = var['res_emission'].sum()

    if has_battery:
        add_battery_emissions_constraints(model, settings, sets, param, var)
        total_emissions += var['battery_emission'].sum()

    if has_generator:
        add_generator_emissions_constraints(model, settings, sets, param, var)
        total_emissions += var['gen_emission'].sum()
        total_emissions += var['fuel_emission'].sum(dim=['years', 'generator_types', 'periods'])

    if has_grid_connection:
        add_grid_emission_constraints(model, settings, sets, param, var)
        total_emissions += var['scenario_grid_emission']

    # Total emissions per scenario
    model.add_constraints(
        var['scenario_co2_emission'] == total_emissions,
        name="Total Scenario Emissions Constraint")

    # Weighted total emissions (objective function)
    model.add_constraints(
        var['total_emission'] == (var['scenario_co2_emission'] * param['SCENARIO_WEIGHTS']).sum('scenarios'),
        name="Total Emissions Weighted Constraint")