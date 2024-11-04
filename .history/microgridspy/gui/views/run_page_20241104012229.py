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


# Main function to run the model
def run_model():
    st.title("MiniGrid Optimization Process")

    # Load the project settings and necessary data
    project_name = st.session_state.get('project_name')
    solver = st.session_state.get('solver')
    pareto_points = st.session_state.get('pareto_points', 10)

    if not project_name:
        st.error("No project is currently loaded. Please create or load a project first.")
        return

    path_manager = PathManager(project_name)
    yaml_filepath = path_manager.PROJECTS_FOLDER_PATH / project_name / f"{project_name}.yaml"

    if not yaml_filepath.exists():
        st.error(f"YAML file for project '{project_name}' not found. Please ensure the project is set up correctly.")
        return

    # Load current project parameters
    current_settings = ProjectParameters.instantiate_from_yaml(yaml_filepath)
    print("Parameters loaded successfully")
    
    # UI for updating and saving settings
    st.subheader("Update and Save Current Settings")
    if st.button("Update and Save Current Settings"):
        try:
            updated_settings = update_nested_settings(current_settings)
            updated_settings.save_to_yaml(str(yaml_filepath))
            st.success(f"Settings successfully updated and saved to {yaml_filepath}")
        except Exception as e:
            st.error(f"An error occurred while saving settings: {str(e)}")

    st.write("---")

    st.subheader("Optimize the System and Find a Solution")
    currency = st.session_state.get('currency', 'USD')

    # Check if the model has been solved already (avoid recomputation)
    if 'model' not in st.session_state:
        st.session_state.model = None

    if 'multiobjective_optimization' in st.session_state and st.session_state.multiobjective_optimization:
        if st.button("Run Multi-Objective Optimization"):
            # Initialize the model
            model = Model(current_settings)
            with st.spinner("Generating Pareto front..."):
                pareto_front, multiobjective_solutions = model.solve_multi_objective(num_points=pareto_points)
            
            st.session_state.pareto_front = pareto_front
            st.session_state.multiobjective_solutions = multiobjective_solutions
            st.session_state.model = model
            st.success("Multi-objective optimization completed successfully!")

            st.write("### Pareto Front Plot")
            co2_values, npc_values = zip(*st.session_state.pareto_front)
            fig, ax = plt.subplots()
            ax.plot(npc_values, co2_values, 'o-', color='blue', label='Pareto Optimal Front')
            ax.set_xlabel(f"Net Present Cost [{currency}]")
            ax.set_ylabel("CO₂ Emissions [CO₂]")
            ax.set_title("Pareto Front: Trade-off between CO₂ Emissions and NPC")
            ax.legend()
            st.pyplot(fig)

            # Display Pareto front data
            st.write("### Pareto Front Data")
            pareto_front_df = pd.DataFrame(st.session_state.pareto_front, columns=["CO₂ Emissions", "Net Present Cost"])
            st.dataframe(pareto_front_df)

            # Allow user to select a solution from the Pareto front without re-running the whole app
            selected_index = st.selectbox(
                "Select a solution to explore",
                range(len(st.session_state.pareto_front)),
                format_func=lambda x: f"Solution {x + 1}: CO₂ = {co2_values[x]}, NPC = {npc_values[x]}",
                key='selected_solution_index')

            # Store the selected solution for later use
            st.session_state.model.solution = st.session_state.multiobjective_solutions[selected_index]
            model.solution = st.session_state.model.solution

    else:
        if st.button("Run Single-Objective Optimization"):
            model = Model(current_settings)
            with st.spinner(f"Optimizing for a single objective using {solver}..."):
                model.solve_single_objective()
            st.session_state.model = model
            st.success("Single-objective optimization completed successfully!")

    st.write("---")

    # Navigation buttons
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Grid Connection"
            st.rerun()
    with col2:
        if st.button("View Results", disabled=st.session_state.model is None):
            st.session_state.page = "Results"
            st.rerun()