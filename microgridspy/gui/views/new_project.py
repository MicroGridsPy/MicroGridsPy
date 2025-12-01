import streamlit as st
import shutil
from pathlib import Path
from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters
from microgridspy.gui.utils import initialize_session_state
from microgridspy.gui.views.resource_page import resource_assessment
from microgridspy.gui.views.settings_page import settings_page
from microgridspy.gui.views.advanced_settings import advanced_settings
from microgridspy.gui.views.demand_page import demand_assessment
from microgridspy.gui.views.renewables_page import renewables_technology
from microgridspy.gui.views.battery_page import battery_technology
from microgridspy.gui.views.generator_page import generator_technology

def copy_project_inputs_to_default(project_inputs_folder: Path, default_inputs_folder: Path) -> None:
    """
    Copy CSV files from project inputs folder to default inputs folder, overwriting existing files.
    
    Args:
        project_inputs_folder: Path to the project's inputs folder
        default_inputs_folder: Path to the default inputs folder
    """
    try:
        if not project_inputs_folder.exists():
            return
            
        default_inputs_folder.mkdir(parents=True, exist_ok=True)
        
        files_copied = 0
        for item in project_inputs_folder.iterdir():
            if item.is_file() and item.suffix == '.csv':
                dst_file = default_inputs_folder / item.name
                shutil.copy2(item, dst_file)
                files_copied += 1
            elif item.is_dir():
                # Recurse into subdirectories
                copy_project_inputs_to_default(item, default_inputs_folder / item.name)
        
        if files_copied > 0:
            st.info(f"Copied {files_copied} CSV files from project to default inputs folder.")
    except Exception as e:
        st.warning(f"Could not copy some files: {str(e)}")


def load_image(image_path):
    """Load an image from the images folder."""
    return str(PathManager.IMAGES_PATH / image_path)

def create_new_project(project_name):
    """Create a new project with the given name and description."""
    path_manager = PathManager(project_name)
    project_folder = path_manager.PROJECTS_FOLDER_PATH / project_name
    
    if project_folder.exists():
        st.error(f"A project with the name '{project_name}' already exists. Please choose a different name.")
        return False
    
    project_folder.mkdir(parents=True, exist_ok=True)
    
    # Create subfolders for inputs
    project_folder.mkdir(exist_ok=True)
    (project_folder / "inputs").mkdir(exist_ok=True)
    (project_folder / "results").mkdir(exist_ok=True)
    
    # Instantiate the default values and save in session state
    st.session_state.path_manager = path_manager
    st.session_state.default_values = ProjectParameters.instantiate_from_yaml(PathManager.DEFAULT_YAML_FILE_PATH)
    
    # Create a YAML file for the project with default values
    yaml_file_path = project_folder / f"{project_name}.yaml"
    st.session_state.default_values.save_to_yaml(yaml_file_path)
    
    return True

def load_existing_project(uploaded_file):
    """Load an existing project configuration file."""
    try:
        project_name = Path(uploaded_file.name).stem
        path_manager = PathManager(project_name)
        project_folder = path_manager.PROJECTS_FOLDER_PATH / project_name
        
        if not project_folder.exists():
            # Create subfolders for inputs
            project_folder.mkdir(parents=True, exist_ok=True)
            (project_folder / "demand").mkdir(exist_ok=True)
            (project_folder / "resource").mkdir(exist_ok=True)
            (project_folder / "technology characterization").mkdir(exist_ok=True)
            (project_folder / "grid").mkdir(exist_ok=True)
        
        # Save the uploaded file to the project folder
        yaml_file_path = project_folder / f"{project_name}.yaml"
        with open(yaml_file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        st.session_state.project_name = project_name
        st.session_state.path_manager = path_manager
        st.session_state.default_values = ProjectParameters.instantiate_from_yaml(yaml_file_path)
        return True
    except Exception as e:
        st.error(f"Failed to load configuration: {e}")
        return False

def new_project():
    """Streamlit page for creating a new project or loading existing configuration files."""
    # Set the page title
    st.title("Welcome to MicroGridsPy!")
    
    # Display the project overview
    st.markdown(
        """
        <div style='text-align: justify;'>
            MicroGridsPy is an analytical <b>energy system model</b> designed to 
            <i>optimize the size and dispatch</i> of energy in village-scale mini-grids 
            in remote areas. It implements a <i>two-stage stochastic optimization</i> 
            for a <b>detailed techno-economic characterization</b> of generation and 
            storage technologies, aiming to <b>minimize NPC or O&M costs</b> over the 
            project's lifespan. The latest version includes <b>advanced features</b> like 
            <i>Multi-Year Capacity-Expansion Formulation</i>, <i>MILP Formulation</i>, 
            <i>Multi-Objective and Multi-Scenario Optimization</i>.
        </div>
        """,
        unsafe_allow_html=True)
    
    # st.image(load_image("model_overview.png"), width='stretch', caption="Model Overview")
    
    # Create a new project
    st.subheader("Create a New Project")
    st.write("Enter the details below to create a new project.")
    project_name = st.text_input("Project Name", key="new_project_name")
    # Store the project name in session state
    st.session_state.project_name = project_name
    st.session_state.project_description = st.text_area("Project Description", key="new_project_description")
    
    if st.button("Create Project"):
        if project_name:
            if create_new_project(project_name):
                st.success(f"Project '{project_name}' created successfully!")
                st.session_state.page = "Project Settings"
                st.session_state.new_project_completed = True
                st.rerun()
        else:
            st.error("Project name cannot be empty. Please enter a valid project name.")
    
    # Load an existing project
    st.subheader("Load an Existing Project")
    st.write("Upload an existing project configuration file (YAML format) to load the project.")
    
    copy_inputs_checkbox = st.checkbox(
        "Copy project CSV files to default inputs folder",
        value=False,
        help="When enabled, CSV files from the project's inputs folder will be copied to the default inputs folder, overwriting existing files."
    )
    
    uploaded_file = st.file_uploader("Choose a YAML file", type="yaml")
    if uploaded_file is not None:
        if load_existing_project(uploaded_file):
            initialize_session_state(st.session_state.default_values, 'advanced_settings')
            initialize_session_state(st.session_state.default_values, 'archetypes_params')
            initialize_session_state(st.session_state.default_values, 'battery_params')
            initialize_session_state(st.session_state.default_values, 'generator_params')
            initialize_session_state(st.session_state.default_values, 'grid_params')
            initialize_session_state(st.session_state.default_values, 'nasa_power_params')
            initialize_session_state(st.session_state.default_values, 'project_info')
            initialize_session_state(st.session_state.default_values, 'project_settings')
            initialize_session_state(st.session_state.default_values, 'pvgis_params')
            initialize_session_state(st.session_state.default_values, 'renewables_params')
            initialize_session_state(st.session_state.default_values, 'resource_assessment')

            # Copy CSV files if checkbox is enabled
            if copy_inputs_checkbox:
                project_inputs = st.session_state.path_manager.PROJECTS_FOLDER_PATH / st.session_state.project_name / "inputs"
                default_inputs = PathManager.INPUTS_FOLDER_PATH
                copy_project_inputs_to_default(project_inputs, default_inputs)
            
            st.success(f"Project '{st.session_state.project_name}' loaded successfully!")
            st.session_state.page = "Project Settings"
            st.session_state.new_project_completed = True
            st.rerun()