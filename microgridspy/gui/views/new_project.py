"""
This module serves as the first page of a Streamlit application for data input 
in MicroGridsPy. It provides a modern graphic interface for users to create a new 
project or load an existing project configuration file. The module initializes 
session state variables, manages user inputs, validates project names, and handles 
file uploads.
"""

from pathlib import Path

import streamlit as st

from config.path_manager import PathManager
from microgridspy.model.parameters import ProjectParameters


def initialize_session_state():
    """Initialize session state variables."""
    if 'show_project_name_input' not in st.session_state:
        st.session_state.show_project_name_input = False
    if 'new_project_completed' not in st.session_state:
        st.session_state.new_project_completed = False
    if 'path_manager' not in st.session_state:
        st.session_state.path_manager = None
    if 'project_name' not in st.session_state:
        st.session_state.project_name = None
    if 'project_description' not in st.session_state:
        st.session_state.project_description = None
    if 'default_values' not in st.session_state:
        st.session_state.default_values = None
    if 'page' not in st.session_state:
        st.session_state.page = "NewProject"


def new_project() -> None:
    """
    Initial page for loading or creating projects.

    This function displays the initial interface for the user to either create a
    new project or load an existing project configuration file. It manages the
    user inputs, validates the project name, and handles the file upload for
    loading an existing project.
    """
    st.title("Welcome to MicroGridsPy!")
    st.markdown("""
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
        """, unsafe_allow_html=True)
    image_path = PathManager.IMAGES_PATH / "model_overview.png"
    st.image(str(image_path), use_column_width=True, caption="Model Overview")

    # Initialize session state variables
    initialize_session_state()

    # Create a new project
    st.subheader("Create a New Project")
    st.write(
        "Click the button below to create a new project. You will be prompted to "
        "enter a project name and description.")

    if st.button("Create New Project"):
        st.session_state.show_project_name_input = True

    if st.session_state.show_project_name_input:
        project_name = st.text_input(
            "Enter the name of the new project:", value=st.session_state.project_name or "")
        project_description = st.text_area(
            "Enter a brief description for the new project:", 
            value=st.session_state.project_description or "")
        
        if st.button("Submit Project Name"):
            if project_name:
                # Check if project directory already exists
                path_manager = PathManager(project_name)
                if not path_manager.get_project_path(project_name).exists():
                    st.session_state.path_manager = path_manager
                    # Initialize default values for the new project
                    st.session_state.default_values = ProjectParameters.instantiate_from_yaml(
                        PathManager.DEFAULT_YAML_FILE_PATH)
                    st.session_state.default_values.project_info.project_name = project_name
                    st.session_state.default_values.project_info.project_description = project_description
                    st.session_state.new_project_completed = True
                    st.session_state.page = "Project Settings"
                    
                    # Save default values to YAML file
                    filepath = path_manager.get_project_path(project_name)
                    st.session_state.default_values.save_to_yaml(filepath)
                    st.rerun()
                else:
                    st.error(f"A project with the name '{project_name}' already exists. Please choose a different name.")
            else:
                st.error("Project name cannot be empty. Please enter a valid project name.")

    # Load an existing project
    st.subheader("Load an Existing Project")
    st.write("Upload an existing project configuration file (YAML format) to load the project.")
    
    uploaded_file = st.file_uploader("Choose a YAML file", type="yaml")
    if uploaded_file is not None:
        try:
            # Load the uploaded YAML file
            project_name = Path(uploaded_file.name).stem
            path_manager = PathManager(project_name)
            file_path = path_manager.get_project_path(project_name)
            
            # Store session state variables
            st.session_state.project_name = project_name
            st.session_state.path_manager = path_manager
            st.session_state.default_values = ProjectParameters.instantiate_from_yaml(file_path)
            st.session_state.new_project_completed = True
            st.success(f"Project '{project_name}' loaded successfully!")
            st.session_state.page = "Project Settings"
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load configuration: {e}")
