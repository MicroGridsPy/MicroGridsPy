import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_res_constraints(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add constraints for renewable energy sources."""
    # Calculate the renewable energy production
    add_renewable_energy_production_constraint(model, settings, sets, param, var)
    
    if settings.advanced_settings.capacity_expansion:
        # Add minimum step units constraint for renewables
        add_renewables_min_step_units_constraint(model, settings, sets, param, var)
    
    if settings.advanced_settings.multiobjective_optimization:
        # Calculate the emissions for renewable sources
        add_res_emissions_constraint(model, settings, sets, param, var)
    
    if settings.project_settings.land_availability > 0:
        # Add land availability constraint
        add_land_availability_constraint(model, settings, sets, param, var)

def add_renewable_energy_production_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate renewable energy production considering installation lifetime for each step."""

    res_energy_production = (var['res_units'] * 
                             param['RESOURCE'] * param['RES_INVERTER_EFFICIENCY'])
            
    model.add_constraints(var['res_energy_production'] == res_energy_production, name=f"Renewable Energy Production Constraint")

def add_renewables_min_step_units_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add minimum step units constraint for renewables."""

    for step in sets.steps.values[1:]:
        # Add the constraint
        model.add_constraints(
            var['res_units'].sel(steps=step) >= var['res_units'].sel(steps=step - 1),
            name=f"Renewables Min Step Units Constraint - Step {step}")

def add_res_emissions_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Calculate the emissions for renewable sources."""
    
    res_emissions = linopy.LinearExpression = 0

    for step in sets.steps.values:
        if step == 1:
            res_emissions += (var['res_units'].sel(steps=step) * 
                                 param['RES_NOMINAL_CAPACITY'] * param['RES_UNIT_CO2_EMISSION']).sum('renewable_sources')
        else:
            res_emissions += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                 param['RES_NOMINAL_CAPACITY'] * param['RES_UNIT_CO2_EMISSION']).sum('renewable_sources')

    # Add the constraint
    model.add_constraints(var['res_emission'] == res_emissions,name="RES Emissions Constraint")

def add_land_availability_constraint(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """Add land availability constraint."""

    res_land_use: linopy.LinearExpression = 0

    for step in sets.steps.values:
        if step == 1:
            # Initial land use
            res_land_use += (var['res_units'].sel(steps=step) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_AREA']).sum('renewable_sources')
        else:
            # Subsequent land use
            res_land_use += ((var['res_units'].sel(steps=step) - var['res_units'].sel(steps=step - 1)) * 
                                param['RES_NOMINAL_CAPACITY'] * param['RES_SPECIFIC_AREA']).sum('renewable_sources')
            
    # Add the constraint
    model.add_constraints(res_land_use <= param['LAND_AVAILABILITY'], name="Land Availability Constraint")

