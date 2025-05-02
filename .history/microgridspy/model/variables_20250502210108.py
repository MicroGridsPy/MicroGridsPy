"""
This module provides functions to add various energy-related variables to a Linopy model.
These include variables related to renewable energy sources (RES), batteries, generators, the grid, energy balance, and project-specific variables.
The functions are designed to accommodate both Linear Programming (LP) and Mixed Integer Linear Programming (MILP) formulations.
"""
from typing import Dict

import linopy
from linopy import Model
import xarray as xr

from microgridspy.model.parameters import ProjectParameters

def add_project_variables(model: Model, settings: ProjectParameters, sets: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add project-related variables to the Linopy model.
    """
    project_variables = {}
    # Total Investment Cost [USD] of the system
    project_variables['total_investment_cost'] = model.add_variables(lower=0, name="Total Investment Cost")
    
    if settings.project_settings.optimization_goal == 0:
        # Net Present Cost [USD] of the system
        project_variables['net_present_cost'] = model.add_variables(lower=0, name='Net Present Cost')
        # Net Present Cost [USD] of the system for each scenario
        project_variables['scenario_net_present_cost'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Net Present Cost')
         # Salvage Value [USD] of the system
        project_variables['salvage_value'] = model.add_variables(lower=0, name='Salvage Value')
        # Total Actualized Variable Cost [USD] of the system for each scenario
        project_variables['total_scenario_variable_cost_act'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Total Variable Cost (Actualized)')
        # Total Actualized Fixed O&M Cost [USD] of the system
        project_variables['operation_maintenance_cost_act'] = model.add_variables(lower=0, name='Operation and Maintenance Cost (Actualized)')
    else:
        # Total Variable Cost [USD] of the system (objective function variable)
        project_variables['total_variable_cost'] = model.add_variables(lower=0, name='Total Variable Cost')
        # Total Not Actualized Variable Cost [USD] of the system for each scenario
        project_variables['total_scenario_variable_cost_nonact'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Total Variable Cost (Not Actualized)')
        # Total Not Actualized Fixed O&M Cost [USD] of the system
        project_variables['operation_maintenance_cost_nonact'] = model.add_variables(lower=0, name='Operation and Maintenance Cost (Not Actualized)')
    
    if settings.advanced_settings.multiobjective_optimization:
        # Total CO2 Emission [kgCO2] of the system (objective function variable)
        project_variables['total_emission'] = model.add_variables(lower=0, name='Total CO2 Emissions')
        # CO2 Emission [kgCO2] of the system for each scenario
        project_variables['scenario_co2_emission'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Total CO2 Emissions')

    # TODO: Check if this is needed
    if settings.advanced_settings.milp_formulation:
        project_variables['ones'] = model.add_variables(binary=True, coords=[sets.scenarios, sets.years, sets.periods], name='Ones')
        model.add_constraints(project_variables['ones'] == 1, name=f"Fix ones to 1")

    return project_variables

def add_res_variables(model: Model, settings: ProjectParameters, sets: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add renewable energy source (RES) variables to the Linopy model.
    """
    res_variables = {}

    # Installed capacity [W] for each renewable source in each investment step
    if settings.advanced_settings.unit_commitment:
        res_variables['res_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps, sets.renewable_sources], name='Unit of Nominal Capacity for Renewables')
        if any('same Inverter' in ct for ct in settings.renewables_params.res_connection_types):
            res_variables['res_inverter_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps, sets.renewable_sources], name='Units of Inverters for Renewables')    
    else:
        res_variables['res_units'] = model.add_variables(lower=0, coords=[sets.steps, sets.renewable_sources], name='Unit of Nominal Capacity for Renewables')
        if any('same Inverter' in ct for ct in settings.renewables_params.res_connection_types):
            res_variables['res_inverter_units'] = model.add_variables(lower=0, coords=[sets.steps, sets.renewable_sources], name='Units of Inverters for Renewables')
    
    # Total energy production [W*period] by each renewable source
    res_variables['res_energy_production'] = model.add_variables(lower=0,coords=[sets.scenarios, sets.steps, sets.periods, sets.renewable_sources],name='Energy Production by Renewables')

    # Curtailment [W*period] by each renewable source
    res_variables['curtailment'] = model.add_variables(lower=0,coords=[sets.scenarios, sets.years, sets.periods, sets.renewable_sources],name='Curtailment by Renewables')

    # Conversion losses [W*period] due to inverter by each renewable source
    res_variables['res_conversion_losses'] = model.add_variables(lower=0,coords=[sets.scenarios, sets.years, sets.periods, sets.renewable_sources], name="Conversion Losses - Renewable Sources")

    if settings.advanced_settings.multiobjective_optimization:
        # Indirect emissions [kgCO2] of each renewable source associated with installed capacity (LCA)
        res_variables['res_emission'] = model.add_variables(lower=0, coords=[sets.steps, sets.renewable_sources], name='CO2 Emissions for Unit of Renewables Installed Capacity')
    
    if settings.project_settings.land_availability > 0:
        # Land use [m^2] of each renewable source associated with installed capacity
        res_variables['res_land_use'] = model.add_variables(lower=0, coords=[sets.steps, sets.renewable_sources], name='Land Use for Unit of Renewables Installed Capacity')
    
    return res_variables


def add_battery_variables(model: Model, settings: ProjectParameters, sets: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add battery-related variables to the Linopy model.
    """
    battery_variables = {}

    # Installed capacity [W*period] for battery bank in each investment step
    if settings.advanced_settings.milp_formulation:
        # Boolean variable to determine single flow (inflow or outflow)
        battery_variables['single_flow_bess'] = model.add_variables(binary=True, coords=[sets.scenarios, sets.years, sets.periods], name='Binary for BESS Single Flow')
    
    if settings.advanced_settings.unit_commitment:
        # MILP Formulation: integer units
        battery_variables['battery_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps], name='Unit of Nominal Capacity for Batteries')
        battery_variables['battery_inverter_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps], name='Units of Inverters for Battery')    
    else:
        # LP Formulation: continuous units
        battery_variables['battery_units'] = model.add_variables(lower=0, coords=[sets.steps], name='Unit of Nominal Capacity for Batteries')
        battery_variables['battery_inverter_units'] = model.add_variables(lower=0, coords=[sets.steps], name='Units of Inverters for Battery')
    
    # Energy stored [W*period] in the battery bank 
    battery_variables['battery_outflow'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.periods], name='Battery Outflow')
    
    # Energy provided [W*period] by the battery bank
    battery_variables['battery_inflow'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.periods], name='Battery Inflow')
    
    if any(conn_type == 'Connected with the same Inverter as the Battery to the Microgrid' for conn_type in settings.renewables_params.res_connection_types):
        battery_variables['single_flow_dc_system'] = model.add_variables(binary=True, coords=[sets.scenarios, sets.years, sets.periods], name='Binary for DC System Single Flow') 
        battery_variables['dc_system_feed_in_losses'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], lower=0, name="Feed In Losses - DC System")
        battery_variables['dc_system_charge_losses'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], upper=0, name="Charge Losses - DC System")
        battery_variables['dc_system_energy'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], name='DC System Energy')
        battery_variables['dc_system_energy_positive'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], lower=0, name="Positive DC System Energy")
        battery_variables['dc_system_energy_negative'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], upper=0, name="Negative DC System Energy")

    else:
        battery_variables['battery_conversion_losses'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.periods], name="Conversion Losses - Battery")
        battery_variables['dc_system_energy'] = model.add_variables(coords=[sets.scenarios, sets.years, sets.periods], name='DC System Energy')  
    
    # State of charge [W*period] of the battery bank
    battery_variables['battery_soc'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.periods], name='Battery State of Charge')

    # Maximum charge and discharge power [W] of the battery bank
    battery_variables['battery_max_charge_power'] = model.add_variables(lower=0, coords=[sets.steps], name='Battery Maximum Charge Power')
    battery_variables['battery_max_discharge_power'] = model.add_variables(lower=0, coords=[sets.steps], name='Battery Maximum Discharge Power')

    # Battery replacement cost [USD] for actualized and non-actualized scenarios
    battery_variables['battery_replacement_cost_act'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Battery Replacement Cost (Actualized)')
    battery_variables['battery_replacement_cost_nonact'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Battery Replacement Cost (Not Actualized)')
    
    if settings.advanced_settings.multiobjective_optimization:
        # Indirect emissions [kgCO2] of the battery bank associated with installed capacity (LCA)
        battery_variables['battery_emission'] = model.add_variables(lower=0, coords=[sets.steps], name='Battery Emissions')

    return battery_variables


def add_generator_variables(model: Model, settings: ProjectParameters, sets: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add generator-related variables to the Linopy model.
    """
    generator_variables = {}
    
    # Installed capacity [W] for each generator type in each investment step
    if settings.advanced_settings.unit_commitment:
        # MILP Formulation: integer units
        generator_variables['generator_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps, sets.generator_types], name='Unit of Nominal Capacity for Generators')
        generator_variables['generator_rectifier_units'] = model.add_variables(lower=0, integer=True, coords=[sets.steps, sets.generator_types] , name='Units of Rectifiers for Generators')        
    else:
        # LP Formulation: continuous units
        generator_variables['generator_units'] = model.add_variables(lower=0, coords=[sets.steps, sets.generator_types], name='Unit of Nominal Capacity for Generators')
        generator_variables['generator_rectifier_units'] = model.add_variables(lower=0, coords=[sets.steps, sets.generator_types], name='Units of Rectifiers for Generators')

    # Energy produced [W*period] by each generator type
    generator_variables['generator_energy_production'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.generator_types, sets.periods], name='Generator Energy Production')
    # Fuel consumption [W*period] by each generator type
    generator_variables['generator_fuel_consumption'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.generator_types, sets.periods], name='Generator Fuel Consumption')

    generator_variables['generator_conversion_losses'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.generator_types, sets.periods], name="Conversion Losses - Generator")

    generator_variables['total_fuel_cost_act'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.generator_types], name='Total Fuel Cost (Actualized)')
    generator_variables['total_fuel_cost_nonact'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.generator_types], name='Total Fuel Cost (Non-Actualized)')
    
    if settings.advanced_settings.multiobjective_optimization:
        # Indirect emissions [kgCO2] of each generator type associated with installed capacity (LCA)
        generator_variables['gen_emission'] = model.add_variables(lower=0, coords=[sets.steps, sets.generator_types], name='Generator Emissions')
    
        # Direct emissions [kgCO2] of each generator type associated with fuel consumption
        generator_variables['fuel_emission'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.generator_types, sets.periods], name='Fuel Emissions')
        generator_variables['scenario_fuel_emission'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Fuel Emissions')


    return generator_variables

def add_grid_variables(model: Model, settings: ProjectParameters, data: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add grid-related variables to the Linopy model.
    """
    grid_variables = {}
    
    # Total grid_connection cost [USD] for actualized and non-actualized scenarios
    grid_variables['scenario_grid_connection_cost_act'] = model.add_variables(lower=0, coords=[data.scenarios], name='Total Grid Connection Cost (Actualized)')
    grid_variables['scenario_grid_connection_cost_nonact'] = model.add_variables(lower=0, coords=[data.scenarios], name='Total Grid Connection Cost (Not Actualized)')

    # Energy purchased from the grid [W*period]
    grid_variables['energy_from_grid'] = model.add_variables(lower=0, coords=[data.scenarios, data.years, data.periods], name='Energy from Grid')
    # Conditionally add variables related to purchase/sell mode
    if settings.advanced_settings.grid_connection_type == 1:
        # Energy provided to the grid [W*period]
        grid_variables['energy_to_grid'] = model.add_variables(lower=0, coords=[data.scenarios, data.years, data.periods], name='Energy to Grid')
    
    grid_variables['grid_conversion_losses'] = model.add_variables(lower=0, coords=[data.scenarios, data.years, data.periods], name="Conversion Losses - Grid")

    if settings.advanced_settings.unit_commitment:
        # MILP Formulation: integer units
        grid_variables['grid_transformer_units'] = model.add_variables(lower=0, integer=True, coords=[data.steps], name='Units of Transformers for Grid')
    else:
        # LP Formulation: continuous units
        grid_variables['grid_transformer_units'] = model.add_variables(lower=0, coords=[data.steps], name='Units of Transformers for Grid')
    
    if settings.advanced_settings.milp_formulation == 1:
        # Boolean variable allowing single flow (inflow or outflow)
        grid_variables['single_flow_grid'] = model.add_variables(binary=True, coords=[data.scenarios, data.years, data.periods], name='Binary for Grid Single Flow')
    
    if settings.advanced_settings.multiobjective_optimization:
        # Indirect emissions [kgCO2] associated with national energy mix emissions coefficient 
        grid_variables['grid_emission'] = model.add_variables(lower=0, coords=[data.scenarios, data.years, data.periods], name='Electricity from Grid Emission')
        # Total indirect CO2 emissions [kgCO2] associated with national energy mix emissions coefficient for each scenario
        grid_variables['scenario_grid_emission'] = model.add_variables(lower=0, coords=[data.scenarios], name='Scenario Grid Emission')

    return grid_variables


def add_lost_load_variables(model: Model, settings: ProjectParameters, sets: xr.Dataset) -> Dict[str, linopy.Variable]:
    """
    Add energy balance-related variables to the Linopy model.
    """
    lost_load_variables = {}
    lost_load_specific_cost = settings.project_settings.lost_load_specific_cost
    # Conditionally add Lost_Load and Lost_Load_Cost variables
    if settings.project_settings.lost_load_fraction > 0.0:
        # Lost Load [W*period]
        lost_load_variables['lost_load'] = model.add_variables(lower=0, coords=[sets.scenarios, sets.years, sets.periods], name='Lost Load')
        if lost_load_specific_cost is not None and lost_load_specific_cost > 0.0:
            # Lost Load Cost [USD] for actualized and non-actualized scenarios
            lost_load_variables['scenario_lost_load_cost_act'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Lost Load Cost (Actualized)')
            lost_load_variables['scenario_lost_load_cost_nonact'] = model.add_variables(lower=0, coords=[sets.scenarios], name='Scenario Lost Load Cost (Non-Actualized)')

    return lost_load_variables

