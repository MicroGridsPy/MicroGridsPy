from typing import Dict

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
    milp_formulation = settings.advanced_settings.milp_formulation
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    # Calculate total renewable energy production
    total_res_energy_production = var['res_energy_production'].sum('renewable_sources')
    total_curtailment = var['curtailment'].sum('renewable_sources')

    for year in sets.years.values:
        step = years_steps_tuples[year - years[0]][1]
        
        # Initialize total_energy_production for each year
        yearly_energy_production: linopy.LinearExpression = total_res_energy_production.sel(steps=step) - total_curtailment.sel(years=year)      
        yearly_conversion_losses: linopy.LinearExpression = 0

        res_yearly_conversion_losses = {}

        for res in sets.renewable_sources.values:
            model.add_constraints(
                var['res_energy_production'].sel(steps=step, renewable_sources=res) - var['curtailment'].sel(years=year, renewable_sources=res) >= 0,
                name=f"Renewable Energy Production Positive - Year {year} - {res}"
            )
            # Calculate conversion losses for each renewable source
            source_losses = (
                (var['res_energy_production'].sel(renewable_sources=res, steps=step)
                 - var['curtailment'].sel(renewable_sources=res, years=year))
                 * (1 - param['RES_INVERTER_EFFICIENCY'].sel(renewable_sources=res))
            )
            # Save losses for the source into the dictionary
            res_yearly_conversion_losses[res] = source_losses
            # Add constraint for each source's conversion losses
            model.add_constraints(
                source_losses == var['res_conversion_losses'].sel(renewable_sources=res, years=year),
                name=f"RES ConversionLosses - {res} - Year {year}"
            )
        yearly_conversion_losses += sum(res_yearly_conversion_losses.values())

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
                        battery_system_energy += (
                            var['res_energy_production'].sel(renewable_sources=res, steps=step)
                            - var['curtailment'].sel(renewable_sources=res, years=year)
                        )
                model.add_constraints(
                    battery_system_energy ==  var['dc_system_energy'].sel(years=year),
                    name=f"DC System Energy - Year {year}"
                )
                if milp_formulation:
                    # Ensure only one of dc_system_energy_positive or dc_system_energy_negative is nonzero
                    model.add_constraints(
                            var['dc_system_energy_positive'].sel(years=year) <= param['M'].sel(years=year) * var['single_flow_dc_system'].sel(years=year),
                            name=f"DC System Energy Positive Constraint - Year {year}"
                        )

                    model.add_constraints(
                        var['dc_system_energy_negative'].sel(years=year) >= -param['M'].sel(years=year) * (var['ones'].sel(years=year) - var['single_flow_dc_system'].sel(years=year)),
                        name=f"DC System Energy Negative Constraint - Year {year}"
                    )
                else:
                    model.add_constraints(
                        var['dc_system_energy_positive'].sel(years=year) + var['dc_system_energy_negative'].sel(years=year) == var['dc_system_energy'].sel(years=year),
                        name=f"DC System Energy Split - Year {year}"
                    )

                model.add_constraints(
                    var['dc_system_energy_positive'].sel(years=year) >=  0,
                    name=f"DC System Energy Positive - Year {year}"
                )

                model.add_constraints(
                    var['dc_system_energy_negative'].sel(years=year) <=  0,
                    name=f"DC System Energy Negative - Year {year}"
                )

                model.add_constraints(
                    var['dc_system_feed_in_losses'].sel(years=year) == var['dc_system_energy_positive'].sel(years=year) * (1 - param['BATTERY_INVERTER_EFFICIENCY_DC_AC'].item()),
                    name=f"DC System Feed In Losses - Year {year}"
                )

                model.add_constraints(
                    var['dc_system_charge_losses'].sel(years=year) == var['dc_system_energy_negative'].sel(years=year) * ((1 / param['BATTERY_INVERTER_EFFICIENCY_AC_DC'].item()) - 1),
                    name=f"DC System Charge Losses - Year {year}"
                )

                yearly_conversion_losses += var['dc_system_feed_in_losses'].sel(years=year) - var['dc_system_charge_losses'].sel(years=year)            
            else:
                battery_losses = (var['battery_outflow'].sel(years=year) * (1 - param['BATTERY_INVERTER_EFFICIENCY_DC_AC'].item()) +
                                  var['battery_inflow'].sel(years=year) * ((1 / param['BATTERY_INVERTER_EFFICIENCY_AC_DC'].item()) - 1))
                
                # Add constraint for battery losses
                model.add_constraints(
                    battery_losses == var['battery_conversion_losses'].sel(years=year),
                    name=f"Battery ConversionLosses - Year {year}"
                )

                # Update yearly conversion losses
                yearly_conversion_losses += battery_losses
                

        if has_generator:
            for generator in sets.generator_types.values:
                yearly_energy_production += var['generator_energy_production'].sel(years=year, generator_types=generator)
                generator_loss = (
                    var['generator_energy_production'].sel(generator_types=generator, years=year)
                    * (1 - param['GENERATOR_RECTIFIER_EFFICIENCY'].sel(generator_types=generator))
                )
                
                # Add constraint for each generator type's conversion losses
                model.add_constraints(
                    generator_loss == var['generator_conversion_losses'].sel(generator_types=generator, years=year),
                    name=f"Generator ConversionLosses - {generator} - Year {year}"
                )
                yearly_conversion_losses += generator_loss

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
            model.add_constraints(grid_losses == var['grid_conversion_losses'].sel(years=year), name=f"Grid ConversionLosses - Year {year}")

            yearly_conversion_losses += grid_losses

        if settings.project_settings.lost_load_fraction > 0:
            yearly_energy_production += var['lost_load'].sel(years=year)

        # Add the energy balance constraint for each year
        model.add_constraints(yearly_energy_production - yearly_conversion_losses == param['DEMAND'].sel(years=year), name=f"Energy Balance Constraint - Year {year}")

    # Add renewable penetration constraint if specified
    if settings.project_settings.renewable_penetration > 0:
        add_renewable_penetration_constraint(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)

    if settings.project_settings.lost_load_fraction > 0:
        add_lost_load_constraint(model, settings, sets, param, var, has_battery, has_generator, has_grid_connection)

# TODO: Consider to AVERAGE on the scenario weights for multi-scenario optimization
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
    """Add renewable penetration constraint with debug logging."""
    years = sets.years.values
    steps = sets.steps.values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]

    # Get renewable energy production and curtailment
    total_res_energy_production = var['res_energy_production'].sum(dim=['renewable_sources', 'periods'])
    total_curtailment = var['curtailment'].sum(dim=['renewable_sources', 'periods'])
    
    for year in years:
        step = years_steps_tuples[year - years[0]][1]

        # Renewable energy after curtailment
        yearly_res_production = (total_res_energy_production.sel(steps=step) - total_curtailment.sel(years=year))

        # Initialize total energy production
        yearly_total_production = yearly_res_production

        # Include generator energy if applicable
        if has_generator:
            yearly_generator_production = var['generator_energy_production'].sum(dim=['generator_types', 'periods']).sel(years=year)
            yearly_total_production += yearly_generator_production

        # Include grid imports if applicable
        if has_grid_connection:
            yearly_grid_import = var['energy_from_grid'].sum('periods').sel(years=year)
            yearly_total_production += yearly_grid_import

        # Calculate expected renewable penetration threshold
        min_required_res_production = param['MINIMUM_RENEWABLE_PENETRATION'] * yearly_total_production

        # Add the constraint
        model.add_constraints(
            yearly_res_production >= min_required_res_production,
            name=f"Renewable Penetration Constraint - Year {year}")

    
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
