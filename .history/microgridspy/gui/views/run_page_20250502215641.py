import shutil
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

def copy_missing_files(src_folder: str, dst_folder: str) -> None:
    """
    Copy missing files from src_folder to dst_folder without overwriting existing files.

    Args:
        src_folder (str): Path to the source folder.
        dst_folder (str): Path to the destination folder.

    Raises:
        FileNotFoundError: If the source folder does not exist.
        ValueError: If the source and destination folders are the same.
        Exception: For other unexpected errors.
    """
    try:
        src = Path(src_folder)
        dst = Path(dst_folder)

        if not src.exists() or not src.is_dir():
            raise FileNotFoundError(f"Source folder does not exist: {src}")
        if src.resolve() == dst.resolve():
            raise ValueError("Source and destination folders must be different.")

        dst.mkdir(parents=True, exist_ok=True)  # Create destination if it doesn't exist

        files_copied = 0
        for item in src.iterdir():
            dst_file = dst / item.name
            if item.is_file():
                if not dst_file.exists():
                    shutil.copy2(item, dst_file)
                    files_copied += 1
            elif item.is_dir():
                # If the item is a directory, recurse
                copy_missing_files(item, dst_file)

        if files_copied > 0:
            print(f"Copied {files_copied} missing files from '{src}' to '{dst}'.")
        else:
            print(f"No new files needed to be copied from '{src}' to '{dst}'.")

    except Exception as e:
        raise Exception(f"An error occurred during copying: {e}")



def update_renewable_params(renewables_params, res_sources):
    renewable_fields = [
        'res_existing_area', 'res_existing_capacity', 'res_existing_years', 'res_connection_types',
        'res_inverter_nominal_capacity','res_inverter_efficiency', 'res_lifetime', 'res_specific_area',
        'res_specific_investment_cost', 'res_specific_om_cost', 'res_inverter_cost', 'res_inverter_lifetime', 
        'res_inverter_existing_capacity', 'res_inverter_existing_years', 'res_unit_co2_emission']
    
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
        'gen_specific_om_cost', 'gen_unit_co2_emission', 'gen_rectifier_efficiency',
        'gen_rectifier_nominal_capacity', 'gen_rectifier_cost', 'gen_rectifier_lifetime', 
        'gen_existing_rectifier_capacity','gen_existing_rectifier_years',
        'gen_sampled_relative_output', 'gen_sampled_efficiency'  # No 'partial_load' here
    ]

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

    # ⚡ Handle partial_load separately (because it's a bool)
    if hasattr(generator_params, 'partial_load'):
        if 'partial_load' in st.session_state:
            generator_params.partial_load = st.session_state['partial_load']
            
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

    # Check if the model has been solved already (avoid recomputation)
    if 'model' not in st.session_state:
        st.session_state.model = None

    # Multi-objective optimization workflow
    if st.session_state.get('multiobjective_optimization', False):
        if st.button("Run Multi-Objective Optimization"):
            # Update and save settings
            try:
                updated_settings = update_nested_settings(current_settings)
                updated_settings.save_to_yaml(str(yaml_filepath))
                inputs_folder = PathManager.INPUTS_FOLDER_PATH  
                project_inputs_folder = path_manager.PROJECTS_FOLDER_PATH / project_name / "inputs"
                copy_missing_files(inputs_folder, project_inputs_folder)
            except Exception as e:
                st.error(f"An error occurred while saving settings and inputs: {str(e)}")

            # Initialize model and solve
            model = Model(current_settings)
            with st.spinner("Generating Pareto front..."):
                pareto_front, multiobjective_solutions = model.solve_multi_objective(
                    num_points=st.session_state.pareto_points,
                    solver=solver,
                    problem_fn=lp_path,
                    log_path=log_path
                )
            st.session_state.pareto_front = pareto_front
            st.session_state.multiobjective_solutions = multiobjective_solutions
            st.session_state.model = model
            st.session_state.selected_solution_index = 0
            st.success("Multi-objective optimization completed successfully!")

    # Always show the Pareto front and dropdown if results exist
    if 'pareto_front' in st.session_state and 'multiobjective_solutions' in st.session_state:
        co2_values, npc_values = zip(*st.session_state.pareto_front)

        # Create a pareto front plot
        fig, ax = plt.subplots()
        ax.plot(npc_values, co2_values, 'o-', color='blue', label='Pareto Optimal Front')
        ax.set_xlabel(f"Net Present Cost [{currency}]")
        ax.set_ylabel("CO₂ Emissions [CO₂]")
        ax.set_title("Pareto Front: Trade-off between CO₂ Emissions and NPC")
        ax.legend()
        st.pyplot(fig)
    else:
        if st.button("Run Single-Objective Optimization"):
            # Update and save the settings
            try:
                updated_settings = update_nested_settings(current_settings)
                updated_settings.save_to_yaml(str(yaml_filepath))
                # Copy the inputs folder to the project folder
                inputs_folder = PathManager.INPUTS_FOLDER_PATH  
                project_inputs_folder = path_manager.PROJECTS_FOLDER_PATH / project_name / "inputs"
                copy_missing_files(inputs_folder, project_inputs_folder)
            except Exception as e:
                st.error(f"An error occurred while saving settings: {str(e)}")

            # Initialize the model
            model = Model(current_settings)

            # Run the single-objective optimization
            with st.spinner(f"Optimizing for a single objective using {solver}..."):
                solution = model.solve_single_objective(solver=solver, problem_fn=lp_path, log_path=log_path)
            st.session_state.model = model
            model.solution = solution
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