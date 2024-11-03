import streamlit as st
import contextlib
import io
import threading
import time

from pathlib import Path
from datetime import datetime

from microgridspy.model.parameters import ProjectParameters
from microgridspy.model.model import Model
from config.path_manager import PathManager

def datetime_to_str(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def update_nested_settings(settings):
    for field in settings.model_fields:
        if hasattr(settings, field):
            value = getattr(settings, field)
            if isinstance(value, (int, float, str, bool)):
                if field in st.session_state:
                    setattr(settings, field, st.session_state[field])
            elif isinstance(value, datetime):
                if field in st.session_state:
                    setattr(settings, field, datetime_to_str(st.session_state[field]))
            elif isinstance(value, list):
                if field in st.session_state:
                    new_value = st.session_state[field]
                    if isinstance(new_value, list):
                        setattr(settings, field, new_value)
                    else:
                        setattr(settings, field, [new_value])  # Convert single value to list
            elif isinstance(value, dict):
                if field in st.session_state:
                    new_value = st.session_state[field]
                    if isinstance(new_value, dict):
                        current_dict = getattr(settings, field)
                        current_dict.update(new_value)
                        setattr(settings, field, current_dict)
            elif hasattr(value, 'model_fields'):
                if field == 'renewables_params':
                    setattr(settings, field, update_renewable_params(value, settings.resource_assessment.res_sources))
                elif field == 'generator_params':
                    setattr(settings, field, update_generator_params(value, settings.generator_params.gen_types))
                else:
                    setattr(settings, field, update_nested_settings(value))
    return settings

def update_renewable_params(renewables_params, res_sources):
    renewable_fields = [
        'res_existing_area', 'res_existing_capacity', 'res_existing_years',
        'res_inverter_efficiency', 'res_lifetime', 'res_specific_area',
        'res_specific_investment_cost', 'res_specific_om_cost', 'res_unit_co2_emission']
    
    for field in renewable_fields:
        if hasattr(renewables_params, field):
            current_value = getattr(renewables_params, field)
            if isinstance(current_value, list):
                if field in st.session_state:
                    new_value = st.session_state[field]
                    if isinstance(new_value, list):
                        setattr(renewables_params, field, new_value[:res_sources])
                    else:
                        setattr(renewables_params, field, [new_value] * res_sources)
                else:
                    setattr(renewables_params, field, current_value[:res_sources])

    return renewables_params

def update_generator_params(generator_params, gen_types):
    generator_fields = [
        'fuel_co2_emission', 'fuel_lhv', 'fuel_names', 'gen_cost_increase',
        'gen_existing_capacity', 'gen_existing_years', 'gen_lifetime',
        'gen_min_output', 'gen_names', 'gen_nominal_capacity',
        'gen_nominal_efficiency', 'gen_specific_investment_cost',
        'gen_specific_om_cost', 'gen_unit_co2_emission']
    
    for field in generator_fields:
        if hasattr(generator_params, field):
            current_value = getattr(generator_params, field)
            if isinstance(current_value, list):
                if field in st.session_state:
                    new_value = st.session_state[field]
                    if isinstance(new_value, list):
                        setattr(generator_params, field, new_value[:gen_types])
                    else:
                        setattr(generator_params, field, [new_value] * gen_types)
                else:
                    setattr(generator_params, field, current_value[:gen_types])

    return generator_params

def run_model():
    st.title("MiniGrid Optimization Process")
    
    # Get the current project's YAML file path
    project_name: str = st.session_state.get('project_name')
    solver: str = st.session_state.get('solver')
    if not project_name:
        st.error("No project is currently loaded. Please create or load a project first.")
        return

    path_manager: PathManager = PathManager(project_name)
    yaml_filepath: Path = path_manager.PROJECTS_FOLDER_PATH / project_name / f"{project_name}.yaml"
    results_enabled = False
    
    if not yaml_filepath.exists():
        st.error(f"YAML file for project '{project_name}' not found. Please ensure the project is set up correctly.")
        return

    # Load current project parameters
    current_settings = ProjectParameters.instantiate_from_yaml(yaml_filepath)
    
    # Update YAML with current session state
    st.subheader("Update and Save Current Settings")
    st.write("Before running the optimization, you can update and save your current settings to the YAML file.")
    
    if st.button("Update and Save Current Settings"):
        try:
            # Update current_settings with values from session state
            updated_settings = update_nested_settings(current_settings)

            # Save updated settings to YAML
            updated_settings.save_to_yaml(str(yaml_filepath))

            st.success(f"Settings successfully updated and saved to {yaml_filepath}")
        except Exception as e:
            st.error(f"An error occurred while saving settings: {str(e)}")
    
    st.write("---")  # Add a separator

    st.subheader("Optimize the system and Find a solution")
    st.write("""
    This page allows you to run the optimization model
    for your mini-grid project. The model will determine the optimal sizing and dispatch strategy (perfect foresight)
    for your mini-grid components based on the provided parameters.
    
    Click the 'Run Optimization Model' button below to start the process. The solver's output will be displayed in the IDE console.
    """)

    # Run model button
    if st.button("Run Optimization Model"):
        # Reload settings from the updated YAML file
        settings = ProjectParameters.instantiate_from_yaml(str(yaml_filepath))
        st.success("Project parameters loaded successfully.")

        # Initialize the linopy optimization model
        model = Model(settings)
        
        # Create a log file path
        log_file_path = path_manager.PROJECTS_FOLDER_PATH / project_name / f"{project_name}_solver_log.txt"
        
        with st.spinner(f"Optimizing the energy system using {solver}. Please check the IDE console for solver progress..."):
            # Solve the model
            model.solve(solver_name=solver, log_fn=str(log_file_path))
        
        st.success("Optimization completed successfully!")

        # Display the solver log
        if log_file_path.exists():
            with open(log_file_path, 'r') as log_file:
                solver_log = log_file.read()
            st.text_area("Solver Log", solver_log, height=300)
        else:
            st.warning("Solver log file not found.")

        # Store results in session state
        st.session_state.model = model
        results_enabled = True

    st.write("---")  # Add a separator

    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Grid Connection"
            st.rerun()
    with col2:
        if st.button("View Results", disabled=not results_enabled):
            st.session_state.page = "Results"
            st.rerun()