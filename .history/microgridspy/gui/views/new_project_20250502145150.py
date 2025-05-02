import streamlit as st
from pathlib import Path
from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters

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
    
    st.image(load_image("model_overview.png"), container_width=True, caption="Model Overview")
    
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
    uploaded_file = st.file_uploader("Choose a YAML file", type="yaml")
    if uploaded_file is not None:
        if load_existing_project(uploaded_file):
            st.success(f"Project '{st.session_state.project_name}' loaded successfully!")
            st.session_state.page = "Project Settings"
            st.session_state.new_project_completed = True
            st.rerun()
