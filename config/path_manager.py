"""
This module provides the PathManager class for managing paths related to project configurations in the MicroGridsPy application.
It includes paths for default and project configurations, inputs, archetypes, assets, documentation, GitHub repository, and contact email.
"""

from pathlib import Path

class PathManager:
    """
    Class to manage the paths for project configurations.
    """
    # Define the root path
    ROOT_PATH: Path = Path(__file__).resolve().parent.parent

    # Define paths for default and project configurations
    CONFIG_FOLDER_PATH: Path = ROOT_PATH / 'config'
    PROJECTS_FOLDER_PATH: Path = ROOT_PATH / 'projects'
    DEFAULT_YAML_FILE_PATH: Path = CONFIG_FOLDER_PATH / 'default.yaml'
    POWER_CURVE_FILE_PATH: Path = CONFIG_FOLDER_PATH / 'Wind Turbine Power Curves.xlsx'

    # Define inputs path
    INPUTS_FOLDER_PATH: Path = ROOT_PATH / 'microgridspy' / 'inputs'
    RESULTS_FOLDER_PATH: Path = ROOT_PATH / 'microgridspy' / 'results'
    DEMAND_FOLDER_PATH: Path = INPUTS_FOLDER_PATH / 'demand files'
    AGGREGATED_DEMAND_FILE_PATH: Path = DEMAND_FOLDER_PATH / 'Aggregated Demand.csv'
    RESOURCE_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'Resources Availability.csv'
    TEMPERATURE_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'Temperature.csv'
    FUEL_SPECIFIC_COST_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'Fuel Specific Cost.csv'
    RES_COST_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'RES Cost.csv'
    BATTERY_COST_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'Battery Cost.csv'
    GRID_AVAILABILITY_FILE_PATH: Path = INPUTS_FOLDER_PATH / 'Grid Availability.csv'

    # Define paths for archetypes folder
    ARCHETYPES_FOLDER_PATH: Path = ROOT_PATH / 'microgridspy' / 'utils' / 'demand_archetypes'

    # Define paths for grid routing
    SHAPEFILE_PATH = ROOT_PATH / 'microgridspy' / 'grid_routing' / 'files'

    # Define paths for assets
    IMAGES_PATH: Path = ROOT_PATH / 'microgridspy'/ 'gui' / 'assets' / 'images'
    ICONS_PATH: Path = ROOT_PATH / 'microgridspy'/ 'gui' / 'assets' / 'icons'

    # Define the URL for documentation and GitHub repository
    DOCS_URL: str = "https://microgridspy-documentation.readthedocs.io/en/latest/index.html"
    GITHUB_URL: str = "https://github.com/SESAM-Polimi/MicroGridsPy-SESAM"

    # Define the contact email
    MAIL_CONTACT: str = "alessandro.onori@polimi.it"

    def __init__(self, project_name: str = "default"):
        self.project_name = project_name
        self.project_file_path = self.get_project_path(project_name)

        # Ensure the projects directory exists
        self.PROJECTS_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_name: str) -> Path:
        """Get the full path to a project file."""
        return self.PROJECTS_FOLDER_PATH / f"{project_name}.yaml"

    def set_project_path(self, project_name: str) -> None:
        """Set the project path based on the provided project name."""
        self.project_name = project_name
        self.project_file_path = self.get_project_path(project_name)
