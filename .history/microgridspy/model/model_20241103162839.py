from typing import Optional, Dict

import xarray as xr
import linopy

from config.solver_settings import get_gurobi_settings
from microgridspy.model.parameters import ProjectParameters
from microgridspy.model.initialize import (
    initialize_sets, 
    initialize_demand, 
    initialize_resource, 
    initialize_temperature,
    initialize_grid_availability,
    initialize_project_parameters, 
    initialize_res_parameters, 
    initialize_battery_parameters,
    initialize_generator_parameters,
    initialize_grid_parameters)
from microgridspy.model.variables import (
    add_project_variables, 
    add_res_variables,
    add_lost_load_variables,
    add_battery_variables,
    add_generator_variables,
    add_grid_variables)
from microgridspy.model.constraints.project_costs import add_cost_calculation_constraints
from microgridspy.model.constraints.energy_balance import add_energy_balance_constraints
from microgridspy.model.constraints.res_constraints import add_res_constraints
from microgridspy.model.constraints.battery_constraints import add_battery_constraints
from microgridspy.model.constraints.generator_constraints import add_generator_constraints
from microgridspy.model.constraints.grid_constraints import add_grid_constraints
from microgridspy.model.objectives import add_objectives

# Define the Model class
class Model:
    def __init__(self, settings: ProjectParameters) -> None:
        """Initialize the Model class."""
        # Store project parameters for settings and user inputs
        self.settings: ProjectParameters = settings
        
        # Define system components
        self.has_battery: bool = settings.project_settings.system_configuration in [0, 1]
        self.has_generator: bool = settings.project_settings.system_configuration in [0, 2]
        self.has_grid_connection: bool = settings.advanced_settings.grid_connection
        
        # Initialize linopy model
        self.model = linopy.Model()
        self.sets: xr.Dataset = xr.Dataset()
        self.time_series: xr.Dataset = xr.Dataset()
        self.parameters: xr.Dataset = xr.Dataset()
        self.variables: Dict[str, linopy.Variable] = {}
        self.solution = None
        
        print("Model initialized.")

    def _initialize_sets(self) -> None:
        """Definition of sets (or dimensions)."""
        self.sets: xr.Dataset = initialize_sets(self.settings, self.has_generator)
        print("Sets initialized successfully.")

    def _initialize_time_series(self) -> None:
        """Load and initialize time series data."""
        self.demand: xr.DataArray = initialize_demand(self.sets)
        self.resource: xr.DataArray = initialize_resource(self.sets)
        self.temperature: xr.DataArray = initialize_temperature(self.sets)

        # Combine time series data into a single xr.Dataset
        self.time_series: xr.Dataset = xr.merge([self.demand.to_dataset(name='DEMAND'),
                                                 self.resource.to_dataset(name='RESOURCE'),
                                                 self.temperature.to_dataset(name='TEMPERATURE'),])
        if self.has_grid_connection:
            self.grid_availability: xr.DataArray = initialize_grid_availability(self.sets)
            self.time_series = xr.merge([self.time_series, self.grid_availability.to_dataset(name='GRID_AVAILABILITY')])
        
        print("Time series data loaded and initialized successfully.")

    def _initialize_parameters(self) -> None:
        """Initialize the model parameters."""
        self.project_parameters: xr.Dataset = initialize_project_parameters(self.settings, self.sets)
        self.res_parameters: xr.Dataset = initialize_res_parameters(self.settings, self.sets)

        # Combine parameters into a single xr.Dataset
        self.parameters: xr.Dataset = xr.merge([self.time_series,self.project_parameters, self.res_parameters])
        
        if self.has_battery:
            self.battery_parameters: xr.Dataset = initialize_battery_parameters(self.settings, self.time_series, self.sets)
            self.parameters = xr.merge([self.parameters, self.battery_parameters])

        if self.has_generator:
            self.generator_parameters: xr.Dataset = initialize_generator_parameters(self.settings, self.sets)
            self.parameters = xr.merge([self.parameters, self.generator_parameters])

        if self.has_grid_connection:
            self.grid_parameters: xr.Dataset = initialize_grid_parameters(self.settings, self.sets)
            self.parameters = xr.merge([self.parameters, self.grid_parameters])
        
        print("Parameters initialized successfully.")

    def _add_variables(self) -> None:       
        """Add variables to the model."""
        self.project_variables: Dict[str, linopy.Variable] = add_project_variables(self.model, self.settings, self.sets)
        self.res_variables: Dict[str, linopy.Variable] = add_res_variables(self.model, self.settings, self.sets)
        self.variables: Dict[str, linopy.Variable] = {**self.project_variables, **self.res_variables}

        if self.has_battery:
            self.battery_variables: Dict[str, linopy.Variable] = add_battery_variables(self.model, self.settings, self.sets)
            self.variables.update(self.battery_variables)

        if self.has_generator:
            self.generator_variables: Dict[str, linopy.Variable] = add_generator_variables(self.model, self.settings, self.sets)
            self.variables.update(self.generator_variables)

        if self.has_grid_connection:
            self.grid_variables: Dict[str, linopy.Variable] = add_grid_variables(self.model, self.settings, self.sets)
            self.variables.update(self.grid_variables)

        if self.settings.project_settings.lost_load_fraction > 0:
            self.lost_load_variables: Dict[str, linopy.Variable] = add_lost_load_variables(self.model, self.settings, self.sets)
            self.variables.update(self.lost_load_variables)

        print("Variables added to the model successfully.")

    def _add_constraints(self) -> None:
        """Add constraints to the model."""
        add_res_constraints(self.model, self.settings, self.sets, self.parameters, self.variables)
        add_cost_calculation_constraints(self.model, self.settings, self.sets, self.parameters, self.variables, self.has_battery, self.has_generator, self.has_grid_connection)
        add_energy_balance_constraints(self.model, self.settings, self.sets, self.parameters, self.variables, self.has_battery, self.has_generator, self.has_grid_connection)
        
        if self.has_battery:
            add_battery_constraints(self.model, self.settings, self.sets, self.parameters, self.variables)

        if self.has_generator:
            add_generator_constraints(self.model, self.settings, self.sets, self.parameters, self.variables)

        if self.has_grid_connection:
            add_grid_constraints(self.model, self.settings, self.sets, self.parameters, self.variables)
        
        print("Constraints added to the model successfully.")

    def _add_objectives(self) -> None:
        """Add objectives to the model."""
        add_objectives(self.model, self.settings, self.sets, self.parameters, self.variables)

        print("Objectives added to the model successfully.")

    def _build(self) -> None:
        self._initialize_sets()
        self._initialize_time_series()
        self._initialize_parameters()
        self._add_variables()
        self._add_constraints()
        self._add_objectives()

    def solve(self, solver_name:  Optional[str] = None, lp_path: Optional[str] = None, io_api: str = "lp", log_fn: str = ""):
        """Solve the model using the specified solver."""
        # Build the model
        self._build()

        # Choose the solver
        if solver_name is None or solver_name not in linopy.available_solvers:
            solver: str = linopy.available_solvers[0]
            print(f"No solver specified. Using default solver: {solver}.")
        elif solver_name not in linopy.available_solvers:
            print(f"Solver {solver_name} not available. Choose from {linopy.available_solvers}.")
            return False
        else:
            solver: str = solver_name
            print(f"Using solver: {solver}.")

        if lp_path:
            self.model.to_file(lp_path)

        # Set specific Gurobi options
        solver_options = {}
        if solver == 'gurobi':
            solver_options = get_gurobi_settings(self.settings.advanced_settings.milp_formulation)

        # Solve the model
        print(f"Solving the model using {solver}...")
        self.model.solve(solver_name=solver, io_api=io_api, log_fn=log_fn, **solver_options)

        # Store the solution
        self.solution = self.model.solution

        return True
    
    def get_settings(self, setting_name: str, advanced: bool = False):
        settings = self.settings.advanced_settings if advanced else self.settings.project_settings
        return getattr(settings, setting_name)
    
    def get_solution_variable(self, variable_name: str) -> xr.DataArray:
        if self.solution is None:
            raise ValueError("Model has not been solved yet.")
        variable = self.solution.get(variable_name)
        if variable is None:
            raise ValueError(f"Variable '{variable_name}' not found in the solution.")
        return variable