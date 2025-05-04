"""
This module defines a set of classes for configuring and managing parameters.
It includes models for project  information, settings, advanced configurations, 
resource assessments, archetype parameters, and renewable energy sources. 
These models are built using Pydantic  for data validation and can be instantiated 
from YAML file or saved to it for ease of configuration management.
"""

from datetime import datetime
from typing import List, Optional

import yaml
from pydantic import BaseModel, ConfigDict


class ProjectInfo(BaseModel):
    """
    Model representing project information.

    Attributes:
        project_name (str): The name of the project.
        project_description (str): A brief description of the project.
    """
    project_name: str
    project_description: str

class ProjectSettings(BaseModel):
    """
    Model representing project settings parameters.

    Attributes:
        time_horizon (int): The time horizon for the project.
        start_date (datetime): The start date of the project.
        discount_rate (float): The discount rate used in the project.
        currency (str): The currency used in the project.
        time_resolution (int): The time resolution for the project.
        optimization_goal (int): The optimization goal for the project.
        investment_cost_limit (Optional[float]): The investment cost limit for the project.
        system_configuration (int): The system configuration for the project.
        distribution_type (str): The distribution type of the minigrid (AC or DC).
        renewable_penetration (float): The renewable penetration percentage.
        land_availability (float): The land availability for renewables in m2.
        battery_independence (int): The battery independence (number of days).
        lost_load_fraction (float): The lost load fraction percentage.
        lost_load_specific_cost (Optional[float]): The specific cost of lost load.
    """
    time_horizon: int
    start_date: datetime
    discount_rate: float
    currency: str
    time_resolution: int
    optimization_goal: int
    investment_cost_limit: Optional[float]
    system_configuration: int
    distribution_type: str 
    renewable_penetration: float
    land_availability: float
    battery_independence: int
    lost_load_fraction: float
    lost_load_specific_cost: Optional[float]

class AdvancedSettings(BaseModel):
    """
    Model representing advanced settings parameters.

    Attributes:
        capacity_expansion (bool): Indicates if capacity expansion is enabled.
        step_duration (Optional[int]): The step duration for the project.
        num_steps (Optional[int]): The number of steps for the project.
        min_step_duration (Optional[int]): The minimum step duration for the project.
        milp_formulation (bool): The MILP formulation used in the project allowing for binary variables (more realistic)
        unit_committment (bool): Allows for unit committment approach on the sizing variables (integers)
        brownfield (bool): Indicates if brownfield is enabled.
        grid_connection (bool): Indicates if grid connection is enabled.
        grid_connection_type (Optional[int]): The type of grid connection.
        wacc_calculation (bool): Indicates if WACC calculation is enabled.
        cost_of_equity (Optional[float]): The cost of equity.
        cost_of_debt (Optional[float]): The cost of debt.
        tax (Optional[float]): The tax percentage.
        equity_share (Optional[float]): The equity share percentage.
        debt_share (Optional[float]): The debt share percentage.
        multiobjective_optimization (bool): Indicates if multiobjective optimization is enabled.
        pareto_points (Optional[int]): The number of Pareto points.
        pareto_solution (Optional[int]): The Pareto solution.
        multi_scenario_optimization (bool): Indicates if multi-scenario optimization is enabled.
        num_scenarios (Optional[int]): The number of scenarios.
        scenario_weights (Optional[List[float]]): The weights of the scenarios.
    """
    capacity_expansion: bool
    step_duration: Optional[int]
    num_steps: Optional[int]
    min_step_duration: Optional[int]
    milp_formulation: bool
    unit_commitment: bool
    brownfield: bool
    grid_connection: bool
    grid_connection_type: Optional[int]
    wacc_calculation: bool
    cost_of_equity: Optional[float]
    cost_of_debt: Optional[float]
    tax: Optional[float]
    equity_share: Optional[float]
    debt_share: Optional[float]
    multiobjective_optimization: bool
    pareto_points: Optional[int]
    multi_scenario_optimization: bool
    num_scenarios: Optional[int]
    scenario_weights: Optional[List[float]]
       
    
class NasaPowerParams(BaseModel):
    """
    NasaPowerParams configuration model.

    This class represents the NASA POWER API parameters which are non-editable.

    Attributes:
        base_url (str): Base URL for the NASA POWER API.
        loc_id (str): Location ID for the spatial resolution.
        parameters_1 (str): Parameters for daily data with 1° x 1° resolution.
        parameters_2 (str): Parameters for daily data with 0.5° x 0.625° resolution.
        parameters_3 (str): Parameters for hourly data.
        date_start (str): Starting date for the dataset (from 2001).
        date_end (str): Ending date for the dataset (until 2020).
        community (str): Community of the data archive.
        temp_res_1 (str): Temporal resolution for daily data.
        temp_res_2 (str): Temporal resolution for hourly data.
        output_format (str): Output format.
        user (str): User key.
    """
    nasa_base_url: str
    loc_id: str
    parameters_1: str
    parameters_2: str
    parameters_3: str
    date_start: str
    date_end: str
    community: str
    temp_res_1: str
    temp_res_2: str
    nasa_output_format: str
    user: str

class PVGISParams(BaseModel):
    """
    PVGISParams configuration model.

    This class represents the PVGIS API parameters which are non-editable.

    Attributes:
        base_url (str): Base URL for the PVGIS API.
        output_format (str): Output format.
    """
    pvgis_base_url: str
    pvgis_output_format: str

class ResourceAssessment(BaseModel):
    """
    ResourceAssessment configuration model.

    This class represents the resource assessment parameters for a project,
    capturing location details and various solar and wind energy parameters.

    Attributes:
        res_sources (int): The number of renewable energy sources.
        res_names (List[str]): The names of the renewable energy sources.
        res_nominal_capacity (List[float]): The nominal capacity of the renewable energy sources.
        location (str): The geographical location description.
        lat (float): Latitude of the project location.
        lon (float): Longitude of the project location.
        time_zone (int): Time zone offset from UTC.
        turbine_type (str): Type of wind turbine (e.g., Horizontal Axis, Vertical Axis).
        turbine_model (str): Specific model of the wind turbine.
        drivetrain_efficiency (float): Efficiency of the wind turbine's drivetrain.
        nom_power (int): Nominal power of the solar panel in watts.
        tilt (int): Tilt angle of the solar panel relative to the ground in degrees.
        azim (int): Azimuth angle of the solar panel in degrees.
        ro_ground (float): Ground reflectance factor, a value between 0 and 1.
        k_t (float): Temperature coefficient of the solar panel.
        nmot (int): Nominal Operating Cell Temperature in degrees Celsius.
        t_nmot (int): Ambient temperature at NMOT in degrees Celsius.
        g_nmot (int): Solar irradiance at NMOT in watts per square meter.
    """
    res_sources: int
    res_names: List[str]
    res_nominal_capacity: List[float]
    location: str
    lat: float
    lon: float
    time_zone: int
    turbine_type: str
    turbine_model: str
    drivetrain_efficiency: float
    surface_type: str
    nom_power: int
    tilt: int
    azim: int
    ro_ground: float
    k_T: float
    NMOT: int
    T_NMOT: int
    G_NMOT: int

class ArchetypesParams(BaseModel):
    """
    ArchetypesParams configuration model.

    This class represents the archetype parameters for a project.

    Attributes:
        demand_growth (float): The demand growth rate.
        cooling_period (str): The cooling period.
        h_tier1 (int): The number of households in tier 1.
        h_tier2 (int): The number of households in tier 2.
        h_tier3 (int): The number of households in tier 3.
        h_tier4 (int): The number of households in tier 4.
        h_tier5 (int): The number of households in tier 5.
        schools (int): The number of schools.
        hospital_1 (int): The number of hospitals in tier 1.
        hospital_2 (int): The number of hospitals in tier 2.
        hospital_3 (int): The number of hospitals in tier 3.
        hospital_4 (int): The number of hospitals in tier 4.
        hospital_5 (int): The number of hospitals in tier 5.
    """
    demand_growth : float
    cooling_period : str
    h_tier1 : int
    h_tier2 : int
    h_tier3 : int
    h_tier4 : int
    h_tier5 : int
    schools : int
    hospital_1 : int
    hospital_2 : int
    hospital_3 : int
    hospital_4 : int
    hospital_5 : int

class RenewablesParams(BaseModel):
    """
    RESParams configuration model.

    This class represents the renewable energy source parameters for a project.

    Attributes:
        res_inverter_efficiency (List[float]): The inverter efficiency of the renewable energy sources.
        res_specific_area (Optional[List[float]]): The specific area of the renewable energy sources.
        res_specific_investment_cost (List[float]): The specific investment cost of the renewable energy sources.
        res_specific_om_cost (List[float]): The specific operation and maintenance cost of the renewable energy sources.
        res_lifetime (List[int]): The lifetime of the renewable energy sources.
        res_unit_co2_emission (List[float]): The unit CO2 emission of the renewable energy sources.
        res_existing_capacity (Optional[List[float]]): The existing capacity of the renewable energy sources.
        res_existing_area (Optional[List[float]]): The existing area of the renewable energy sources.
        res_existing_years (Optional[List[int]]): The existing years of the renewable energy sources.
    """

    res_connection_types: List[str]
    res_specific_area: Optional[List[float]]
    res_specific_investment_cost: List[float]
    res_specific_om_cost: List[float]
    res_lifetime: List[int]
    res_unit_co2_emission: List[float]
    res_existing_capacity: Optional[List[float]]
    res_existing_area: Optional[List[float]]
    res_existing_years: Optional[List[int]]
    res_inverter_efficiency: List[float]
    res_inverter_lifetime: List[int]
    res_inverter_nominal_capacity: List[float]
    res_inverter_existing_capacity: List[float]
    res_inverter_existing_years: List[int]
    res_inverter_cost: List[float]

class BatteryParams(BaseModel):
    """
    BatteryParams configuration model.

    This class represents the battery parameters for a project.

    Attributes:
        battery_nominal_capacity (float): Nominal capacity of the battery (Wh).
        battery_specific_investment_cost (float): Specific investment cost of the battery bank (USD/Wh).
        battery_specific_electronic_investment_cost (float): Specific investment cost of non-replaceable parts (electronics) of the battery bank (USD/Wh).
        battery_specific_om_cost (float): Percentage of the total investment spent in operation and management of batteries in each period (%).
        battery_inverter_efficiency_dc_ac (float): Efficiency of the inverter between battery and the AC-Microgrid (%).
        battery_inverter_efficiency_ac_dc (float): Efficiency of the inverter between AC-Microgrid and the battery (%).    
        battery_discharge_battery_efficiency (float): Efficiency of the discharge of the battery (%).
        battery_charge_battery_efficiency (float): Efficiency of the charge of the battery (%).
        battery_initial_soc (float): Initial state of charge of the battery.
        battery_depth_of_discharge (float): Depth of discharge of the battery (%).
        maximum_battery_discharge_time (float): Minimum time of discharge of the battery (hours).
        maximum_battery_charge_time (float): Maximum time of charge of the battery (hours).
        battery_cycles (float): Number of cycles the battery can undergo.
        battery_expected_lifetime (float): Expected lifetime of the battery (years).
        bess_unit_co2_emission (float): CO2 emissions per unit of the battery (kgCO2/Wh).
        battery_existing_capacity (float): Existing capacity of the battery (Wh).
    """
    battery_nominal_capacity: float
    battery_specific_investment_cost: float
    battery_specific_electronic_investment_cost: float
    battery_specific_om_cost: float
    battery_inverter_efficiency_dc_ac: float
    battery_inverter_efficiency_ac_dc: float
    battery_inverter_lifetime: int
    battery_inverter_nominal_capacity: float
    battery_inverter_cost: float
    battery_discharge_battery_efficiency: float
    battery_charge_battery_efficiency: float
    battery_initial_soc: float
    battery_depth_of_discharge: float
    maximum_battery_discharge_time: float
    maximum_battery_charge_time: float
    battery_cycles: int
    battery_expected_lifetime: int
    bess_unit_co2_emission: float
    battery_existing_capacity: Optional[float]
    battery_existing_years: Optional[int]
    battery_existing_inverter_capacity: Optional[float]
    battery_inverter_existing_years: Optional[int]

class GeneratorParams(BaseModel):
    """
    GeneratorParams configuration model.
    
    This class represents the generator parameters for a project.
    
    Attributes:
        gen_types (int): The number of generator types.
        gen_names (List[str]): The names of the generator types.
        gen_nominal_capacity (List[float]): The nominal capacity of the generator types.
        gen_nominal_efficiency (List[float]): The nominal efficiency of the generator types.
        gen_rectifier_efficiency (List[float]): The rectifier efficiency of the generator types.
        gen_rectifier_nominal_capacity (List[float]): The nominal capacity of the rectifier for the generator types.
        gen_rectifier_lifetime (List[int]): The lifetime of the rectifier for the generator types.
        gen_rectifier_cost (List[float]): The cost of the rectifier for the generator types.
        gen_specific_investment_cost (List[float]): The specific investment cost of the generator types.
        gen_specific_om_cost (List[float]): The specific operation and maintenance cost of the generator types.
        gen_lifetime (List[int]): The lifetime of the generator types.
        gen_unit_co2_emission (List[float]): The unit CO2 emission of the generator types.
        gen_existing_capacity (List[float]): The existing capacity of the generator types.
        gen_existing_years (List[int]): The existing years of the generator types.
        fuel_names (List[str]): The names of the fuels used by the generator types.
        fuel_lhv (List[float]): The lower heating value of the fuels used by the generator types.
        fuel_co2_emission (List[float]): The CO2 emission of the fuels used by the generator types.
        max_fuel_consumption (List[float]): The maximum yearly fuel consumption of the generator types.
        partial_load (bool): Indicates if partial load is allowed for the generator types.
        gen_sampled_relative_output (Optional[List[List[float]]]): Sampled relative output of the generator types.
        gen_sampled_efficiency (Optional[List[List[float]]]): Sampled efficiency of the generator types.
        gen_existing_rectifier_capacity (Optional[List[float]]): Existing rectifier capacity of the generator types.
        gen_existing_rectifier_years (Optional[List[int]]): Existing rectifier years of the generator types.
    """
    gen_types: int
    gen_names: List[str]
    gen_nominal_capacity: List[float]
    gen_nominal_efficiency: List[float]
    gen_rectifier_efficiency: List[float]
    gen_rectifier_nominal_capacity: List[float]
    gen_rectifier_lifetime: List[int]
    gen_rectifier_cost: List[float]
    gen_specific_investment_cost: List[float]
    gen_specific_om_cost: List[float]
    gen_lifetime: List[int]
    gen_unit_co2_emission: List[float]
    gen_existing_capacity: List[float]
    gen_existing_years: List[int]
    fuel_names: List[str]
    fuel_lhv: List[float]
    fuel_co2_emission: List[float]
    max_fuel_consumption: List[float]
    partial_load: bool
    gen_sampled_relative_output: Optional[List[List[float]]] = None 
    gen_sampled_efficiency: Optional[List[List[float]]] = None       
    gen_existing_rectifier_capacity: Optional[List[float]] = None
    gen_existing_rectifier_years: Optional[List[int]] = None

class GridParams(BaseModel):
    """
    GridParams configuration model.

    This class represents the grid connection parameters for a project.

    Attributes:
        year_grid_connection (int): Year of grid connection.
        electricity_purchased_cost (float): Cost of purchased electricity from grid (USD/kWh).
        electricity_sold_price (Optional[float]): Price of electricity sold to grid (USD/kWh).
        grid_distance (float): Distance to grid connection point (km).
        grid_connection_cost (float): Cost of grid connection (USD).
        grid_maintenance_cost (float): Annual grid maintenance cost as a fraction of connection cost.
        maximum_grid_power (float): Maximum power that can be drawn from or fed to the grid (W).
        national_grid_specific_co2_emissions (float): CO2 emissions per kWh from the national grid (kgCO2/kWh).
        grid_availability_simulation (Optional[bool]): Indicates if grid availability simulation is enabled.
        grid_average_number_outages (Optional[float]): Average number of grid outages per year.
        grid_average_outage_duration (Optional[float]): Average duration of grid outages (hours).
    """
    year_grid_connection: int
    electricity_purchased_cost: float
    electricity_sold_price: Optional[float]
    grid_distance: float
    grid_connection_cost: float
    grid_maintenance_cost: float
    grid_to_microgrid_efficiency: float
    microgrid_to_grid_efficiency: float
    grid_transformer_nominal_capacity: float
    grid_transformer_cost: float
    maximum_grid_power: float
    national_grid_specific_co2_emissions: float
    grid_availability_simulation: Optional[bool]
    grid_average_number_outages: Optional[float]
    grid_average_outage_duration: Optional[float]

class ProjectParameters(BaseModel):
    """
    Model representing the default values for the project.

    Attributes:
        project_info (ProjectInfo): The project information.
        project_settings (ProjectSettings): The project settings.
        advanced_settings (AdvancedSettings): The advanced settings.
        nasa_power_params (NasaPowerParams): The NASA POWER API parameters.
        resource_assessment (ResourceAssessment): The resource assessment parameters.
        archetypes_params (ArchetypesParams): The archetype parameters.
        renewables_params (RenewablesParams): The renewable energy source parameters.
        grid_params (GridParams): The grid connection parameters.
    """
    # Pydantic configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)
        
    # Parameters
    project_info: ProjectInfo
    project_settings: ProjectSettings
    advanced_settings: AdvancedSettings
    nasa_power_params: NasaPowerParams
    pvgis_params: PVGISParams
    resource_assessment: ResourceAssessment
    archetypes_params: ArchetypesParams
    renewables_params: RenewablesParams
    battery_params: BatteryParams
    generator_params: GeneratorParams
    grid_params: GridParams

    @classmethod
    def instantiate_from_yaml(cls, filepath: str) -> 'ProjectParameters':
        """Instantiate a ProjectParameters object loading parameters from a YAML file."""
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)
    
    def save_to_yaml(self, filepath: str) -> None:
        """Save parameters to a YAML file."""
        with open(filepath, 'w') as file:
            yaml.dump(self.model_dump(), file)
