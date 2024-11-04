import xarray as xr
import linopy
from linopy import Model
from microgridspy.model.parameters import ProjectParameters
from typing import Dict

def add_objectives(model: Model, settings: ProjectParameters, sets: xr.Dataset, param: xr.Dataset, var: Dict[str, linopy.Variable]) -> None:
    """
    Define and add objective functions to the Linopy model based on project parameters.

    Args:
        model (Model): The Linopy model instance.
        settings (ProjectParameters): The project parameters settings instance.
        sets (xr.Dataset): The sets dataset.
        params (xr.Dataset): The parameters dataset.
        variables (Dict[str, linopy.Variable]): The variables dictionary.
    """
    # Define the objective functions
    if settings.project_settings.optimization_goal == 0:
        # Net Present Cost Objective
        objective = (var["scenario_net_present_cost"] * param['SCENARIO_WEIGHTS']).sum('scenarios')
        model.add_objective(objective)
    else:
        # Total Variable Cost Objective
        objective = (var["total_scenario_variable_cost_nonact"] * param['SCENARIO_WEIGHTS']).sum('scenarios')
        model.add_objective(objective)