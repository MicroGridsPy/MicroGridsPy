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
    currency = st.session_state.get('currency', 'USD')

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
    
    # UI for updating and saving settings
    st.subheader("Update and Save Current Settings")
    st.write("Save project parameter for later use. This helps to keep updated project settings in the parameter YAML file within the project folder.")
    if st.button("Update and Save Current Settings"):
        try:
            updated_settings = update_nested_settings(current_settings)
            updated_settings.save_to_yaml(str(yaml_filepath))
            st.success(f"Settings successfully updated and saved to {yaml_filepath}")
        except Exception as e:
            st.error(f"An error occurred while saving settings: {str(e)}")

    st.write("---")

    st.subheader("Optimize the System and Find a Solution")
    st.write("""
        Choose your solver and run the optimization process. 
        Before proceeding, ensure that the selected solver is properly installed and available on your laptop.
        
        - **Gurobi**: A commercial solver known for its efficiency with mixed-integer linear programming (MILP) problems. 
        Make sure you have installed Gurobi and have a valid license configured. If you select Gurobi, the optimization 
        process will only run if the solver is accessible and correctly set up in your environment.
        
        - **HiGHS**: An open-source solver that comes pre-installed with the MicroGridsPy environment. If you're unsure about 
        solver setup or don't have a specific preference, HiGHS is a reliable default option. It's already configured 
        and ready to use for most linear optimization problems.""")

    # Dropdown for solver selection
    solver = st.selectbox("Select a Solver", ["gurobi", "highs"], key="solver")

    # Option to provide a different LP path
    st.write("""
             By default, the model will NOT save the LP representation and the log file, but you can specify a path 
             if needed. If you opt to use a custom path, make sure the directory exists and is writable.""")
    
    # Custom LP and log file paths
    use_lp_path = st.checkbox("Provide a custom LP file path")
    if use_lp_path: 
        st.write("Specify a custom path to the file (.lp) for problem LP representation:")
        lp_path = st.text_input("Custom LP File Path", value="")
        if Path(lp_path).suffix != ".lp": 
            st.error("File path not valid. The file should have a .lp extension.")
    else:
        lp_path = None
    
    use_log_path = st.checkbox("Provide a custom Log file path")
    if use_log_path:
        st.write("Specify a custom path to the file (.log) for logging the solver's output:")
        log_path = st.text_input("Custom Log File Path", value="")
        if Path(log_path).suffix != ".log": 
            st.error("File path not valid. The log file should have a .log extension.")           
    else:
        log_path = None

    st.write("---")
    st.write("""
    ### Choosing Between Single-Objective and Multi-Objective Optimization
    
    Selecting an optimization approach depends on your project goals:
    
    - **Single-Objective Optimization**: If the main priority is cost minimization, without specific trade-offs against other criteria, choose the single-objective option. This approach will optimize solely for total costs, making it ideal when budget constraints are the primary concern and emissions are either regulated separately or not a primary focus.

    - **Multi-Objective Optimization**: If balancing multiple criteria, such as costs and emissions, is essential, select the multi-objective option. This approach generates a Pareto front, allowing you to evaluate trade-offs between objectives and select configurations that balance costs with environmental impact. Multi-objective optimization is useful for projects aiming to meet economic and sustainability targets simultaneously.
    
    """)

    # Check if the model has been solved already (avoid recomputation)
    if 'model' not in st.session_state:
        st.session_state.model = None
    with st.expander("🎯 Single-Objective Optimization", expanded=False):
        if st.button("Run Single-Objective Optimization"):
            st.session_state.multiobjective_optimization = False
            try:
                updated_settings = update_nested_settings(current_settings)
                updated_settings.save_to_yaml(str(yaml_filepath))
                st.success(f"Settings successfully updated and saved to {yaml_filepath}")
            except Exception as e:
                st.error(f"An error occurred while saving settings: {str(e)}")
            model = Model(current_settings)
            with st.spinner(f"Optimizing for a single objective using {solver}..."):
                solution = model.solve_single_objective(solver=solver, problem_fn=lp_path, log_path=log_path)
            st.session_state.model = model
            model.solution = solution
            st.success("Single-objective optimization completed successfully!")

    with st.expander("⚖️ Multi-Objective Optimization", expanded=False):
        st.session_state.multiobjective_optimization = st.checkbox(
            "Enable Multi-Objective Optimization", 
            value=st.session_state.multiobjective_optimization,
            help="Optimize for both cost and CO2 emissions. This provides a range of solutions with different trade-offs.")
        
        if st.session_state.multiobjective_optimization:
            st.session_state.pareto_points = st.number_input(
                "Number of Pareto Curve Points:", 
                min_value=2, 
                value=st.session_state.pareto_points,
                help="Specify the number of solutions to generate along the Pareto front. More points provide a more detailed trade-off curve but increase computation time.")

            if st.button("Run Multi-Objective Optimization"):
                try:
                    updated_settings = update_nested_settings(current_settings)
                    updated_settings.save_to_yaml(str(yaml_filepath))
                    st.success(f"Settings successfully updated and saved to {yaml_filepath}")
                except Exception as e:
                    st.error(f"An error occurred while saving settings: {str(e)}")
                # Initialize the model
                model = Model(current_settings)
                with st.spinner("Generating Pareto front..."):
                    pareto_front, multiobjective_solutions = model.solve_multi_objective(num_points=st.session_state.pareto_points, 
                                                                                        solver=solver,
                                                                                        problem_fn=lp_path, 
                                                                                        log_path=log_path)
                
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