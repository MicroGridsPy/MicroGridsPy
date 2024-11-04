import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

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
    pareto_points: int = st.session_state.get('pareto_points', 10)
    
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

    st.subheader("Optimize the System and Find a Solution")
    st.write("""
    This page allows you to run the optimization model for your mini-grid project.
    You can either run a single-objective optimization or generate a Pareto front for a multi-objective analysis.
    """)
    currency = st.session_state.get('currency', 'USD')
    # Initialize the linopy optimization model
    model = None
    # Reload settings from the updated YAML file
    settings = ProjectParameters.instantiate_from_yaml(str(yaml_filepath))

    if st.session_state.get('multiobjective_optimization', False):

        if st.button("Run Multi-Objective Optimization"):
            # Initialize the model
            model = Model(settings)
            
            # Solve the multi-objective optimization
            with st.spinner("Generating Pareto front..."):
                pareto_front, multiobjective_solutions = model.solve_multi_objective(num_points=pareto_points)
            
            st.success("Multi-objective optimization completed successfully!")

            # Plot the Pareto front
            st.write("### Pareto Front Plot")
            co2_values, npc_values = zip(*pareto_front)
            fig, ax = plt.subplots()
            ax.plot(npc_values / 1000, co2_values / 1000, 'o-', color='blue', label='Pareto Optimal Front')
            ax.set_xlabel(f"Net Present Cost [k{currency}]")
            ax.set_ylabel("CO₂ Emissions [tCO₂]")
            ax.set_title("Pareto Front: Trade-off between CO₂ Emissions and NPC")
            ax.legend()
            st.pyplot(fig)

            # Display Pareto front data
            st.write("### Pareto Front Data")
            pareto_front_df = pd.DataFrame(pareto_front, columns=["CO₂ Emissions", "Net Present Cost"])
            st.dataframe(pareto_front_df)

            # Allow user to select a solution from the Pareto front
            selected_index = st.selectbox("Select a solution to explore", range(len(pareto_front)),
                                        format_func=lambda x: f"Solution {x + 1}: CO₂ = {co2_values[x]}, NPC = {npc_values[x]}")
            
            # Store the selected solution
            selected_solution = multiobjective_solutions[selected_index]
            model.solution = selected_solution
            results_enabled = True

    else:
        if st.button("Run Single-Objective Optimization"):
            # Initialize the model
            model = Model(settings)
            
            # Create a log file path
            log_file_path = path_manager.PROJECTS_FOLDER_PATH / project_name / f"{project_name}_solver_log.txt"
            
            with st.spinner(f"Optimizing for a single objective using {solver}..."):
                # Solve the model
                solution = model.solve_single_objective()
            
            st.success("Single-objective optimization completed successfully!")
            model.solution = solution
            results_enabled = True

    # Display the solver log if available
    if model:
        log_file_path = path_manager.PROJECTS_FOLDER_PATH / project_name / f"{project_name}_solver_log.txt"
        if log_file_path.exists():
            with open(log_file_path, 'r') as log_file:
                solver_log = log_file.read()
            st.text_area("Solver Log", solver_log, height=300)
        else:
            st.warning("Solver log file not found.")

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