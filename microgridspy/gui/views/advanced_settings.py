"""
This module provides the advanced settings page for the MicroGridsPy Streamlit application. 
It allows users to configure detailed model parameters and optimization options for their project. 
Users can adjust advanced parameters, validate inputs using Pydantic, and update the state accordingly.
"""

import streamlit as st
import pandas as pd

from microgridspy.model.parameters import ProjectParameters


def initialize_session_state(default_values: ProjectParameters) -> None:
    """Initialize session state variables for advanced settings."""
    advanced_settings = default_values.advanced_settings
    session_state_defaults = {
        'capacity_expansion': advanced_settings.capacity_expansion,
        'step_duration': advanced_settings.step_duration,
        'num_steps': advanced_settings.num_steps,
        'min_step_duration': advanced_settings.min_step_duration,
        'milp_formulation': advanced_settings.milp_formulation,
        'unit_commitment': advanced_settings.unit_commitment,
        'brownfield': advanced_settings.brownfield,
        'grid_connection': advanced_settings.grid_connection,
        'grid_availability_simulation': advanced_settings.grid_availability_simulation,
        'grid_connection_type': advanced_settings.grid_connection_type,
        'wacc_calculation': advanced_settings.wacc_calculation,
        'cost_of_equity': advanced_settings.cost_of_equity,
        'cost_of_debt': advanced_settings.cost_of_debt,
        'tax': advanced_settings.tax,
        'equity_share': advanced_settings.equity_share,
        'debt_share': advanced_settings.debt_share,
        'multiobjective_optimization': advanced_settings.multiobjective_optimization,
        'pareto_points': advanced_settings.pareto_points,
        'multi_scenario_optimization': advanced_settings.multi_scenario_optimization,
        'num_scenarios': advanced_settings.num_scenarios,
        'scenario_weights': advanced_settings.scenario_weights,
    }

    for key, value in session_state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def advanced_settings() -> None:
    """
    Advanced Settings Page for configuring detailed model parameters.

    This function displays an advanced configuration settings page for the user to update various
    advanced parameters related to the project's optimization and modeling. It captures user inputs,
    validates them using Pydantic, and updates the state accordingly.
    """
    st.title("Advanced Settings")
    st.write(
        "This page allows you to configure advanced settings for your project, including detailed "
        "model parameters and optimization options. Adjust these settings to fine-tune the behavior "
        "and performance of your model."
    )

    # Initialize session state variables
    initialize_session_state(st.session_state.default_values)

    # Advanced Modeling Options
    st.subheader("Advanced Modeling Options")
    st.write("Configure additional advanced parameters to enhance the detail and accuracy of your project model.")

    with st.expander("🧮 Model Formulation"):
        # Introduction for MILP Formulation
        st.write(
            "The MILP (Mixed-Integer Linear Programming) formulation allows for the inclusion of binary variables within the optimization model, "
            "which can make the representation of certain technologies, such as batteries, more realistic." 
            "However, it may increase the computational effort required for solving the model.")
        
        st.session_state.milp_formulation = st.checkbox(
            "MILP Formulation", value=st.session_state.milp_formulation)
        
        # Additional selection for Unit Commitment if MILP Formulation is enabled
        if st.session_state.milp_formulation:
            # Introduction for Unit Commitment Approach
            st.write(
                "The unit commitment approach restricts the sizing variables to integer values, ensuring that component sizes are selected in terms of units of nominal capacity. "
                "This approach is useful for representing start-up and shut-down decisions in generation units."
                "However, it significantly increases the computational complexity of the optimization problem.")
            
            st.session_state.unit_commitment = st.checkbox(
                "Enable Unit Commitment Approach", value=st.session_state.unit_commitment)
        
        st.write(
            "Select this option if you want to consider existing capacity installed for brownfield projects.")
        
        st.session_state.brownfield = st.checkbox(
            "Select for Brownfield project", value=st.session_state.brownfield)

        st.write(
            "Enable this option to allow the capacity of the system to expand over time. This will enable "
            "fields for specifying the duration of each investment decision step and the minimum last step duration.")
        
        st.session_state.capacity_expansion = st.checkbox(
            "Activate Capacity Expansion", value=st.session_state.capacity_expansion)

        if st.session_state.capacity_expansion:
            st.session_state.step_duration = st.slider(
                "Duration of each Investment Step over the project timeline:", min_value=1, max_value=st.session_state.get("time_horizon"),
                value=st.session_state.get('step_duration', 1),
                help="Specify the duration of each investment step in years.")
            
            st.session_state.num_steps = st.session_state.get("time_horizon") // st.session_state.step_duration
            st.session_state.min_step_duration = st.session_state.get("time_horizon") - st.session_state.step_duration * st.session_state.num_steps

            step_durations = [st.session_state.step_duration] * st.session_state.num_steps
            if st.session_state.min_step_duration > 0:
                step_durations.append(st.session_state.min_step_duration)
                st.session_state.num_steps += 1

            st.markdown("**Project Timeline with Investment Steps**")

            # Display the project timeline as a table
            timeline_data = {
                "Step": [f"Investment Step {i + 1}" for i in range(st.session_state.num_steps)],
                "Duration [Years]": step_durations}
            df_timeline = pd.DataFrame(timeline_data)
            st.table(df_timeline)

    with st.expander("⚡ Grid Connection", expanded=False):
        st.write(
            "Enable this option to simulate a grid connection. This will enable fields for simulating grid availability "
            "and specifying the type of grid connection.")
        
        st.session_state.grid_connection = st.checkbox(
            "Simulate Grid Connection", value=st.session_state.grid_connection,
            help="Simulate grid connection during project lifetime.")
        
        if st.session_state.grid_connection:
            st.session_state.grid_availability_simulation = st.checkbox(
                "Enable Grid Availability Simulation", value=st.session_state.grid_availability_simulation,
                help="Simulate grid availability matrix.")
            
            grid_connection_type = st.radio(
                "Grid Connection Type:", options=["Purchase Only", "Purchase/Sell"],
                index=0 if st.session_state.grid_connection_type == 0 else 1,
                help="Specify if the grid connection is for purchasing only or both purchasing and selling.")
            
            st.session_state.grid_connection_type = 0 if grid_connection_type == "Purchase Only" else 1

    with st.expander("📈 Weighted Average Cost of Capital Calculation", expanded=False):
        st.write(
            "Enable this option to calculate the Weighted Average Cost of Capital (WACC). This will enable fields for "
            "specifying the cost of equity, cost of debt, tax, equity share, and debt share.")
        
        st.session_state.wacc_calculation = st.checkbox(
            "Enable WACC Calculation", value=st.session_state.wacc_calculation,
            help="Enable Weighted Average Cost of Capital (WACC) calculation.")
        
        if st.session_state.wacc_calculation:
            st.session_state.cost_of_equity = st.number_input(
                "Cost of Equity:", min_value=0.0, value=st.session_state.cost_of_equity,
                help="Cost of equity (i.e., the return required by the equity shareholders).")
            
            st.session_state.cost_of_debt = st.number_input(
                "Cost of Debt:", min_value=0.0, value=st.session_state.cost_of_debt,
                help="Cost of debt (i.e., the interest rate).")
            
            st.session_state.tax = st.number_input(
                "Tax:", min_value=0.0, value=st.session_state.tax,
                help="Corporate tax deduction (debt is assumed as tax deductible).")
            
            st.session_state.equity_share = st.number_input(
                "Equity Share:", min_value=0.0, max_value=1.0, value=st.session_state.equity_share,
                help="Total level of equity.")
            
            st.session_state.debt_share = st.number_input(
                "Debt Share:", min_value=0.0, max_value=1.0, value=st.session_state.debt_share,
                help="Total level of debt.")

    # Advanced Optimization Configuration
    st.subheader("Advanced Optimization Configuration")
    st.write("Fine-tune optimization settings for your project to achieve more specific outcomes.")

    with st.expander("🎯 Multi-Objective Optimization", expanded=False):
        st.write(
            "Enable this option to perform multi-objective optimization. This will enable fields for specifying the plot max "
            "cost, Pareto points, and Pareto solution."
        )
        st.session_state.multiobjective_optimization = st.checkbox(
            "Enable Multi-Objective Optimization", value=st.session_state.multiobjective_optimization,
            help="Optimization of NPC/operation cost and CO2 emissions."
        )
        if st.session_state.multiobjective_optimization:
            st.session_state.pareto_points = st.number_input(
                "Number of Pareto curve points to be analyzed during optimization:", min_value=1, value=st.session_state.pareto_points,
                help="Number of Pareto curve points to be analyzed during optimization from minimum emissions (and free costs) to minimum costs (and free emissions)."
            )

    with st.expander("🔀 Multi-Scenario Optimization", expanded=False):
        st.write(
            "Enable this option to perform multi-scenario optimization. This will enable fields for specifying the number "
            "of scenarios and their respective weights."
        )
        st.session_state.multi_scenario_optimization = st.checkbox(
            "Enable Multi-Scenario Optimization", value=st.session_state.multi_scenario_optimization,
            help="Simulate different scenarios of demand and RES time series."
        )
        if st.session_state.multi_scenario_optimization:
            st.session_state.num_scenarios = st.number_input(
                "Number of Scenarios:", min_value=1, value=st.session_state.num_scenarios,
                help="Number of scenarios to simulate."
            )
            for i in range(st.session_state.num_scenarios):
                st.session_state[f"scenario_weight_{i}"] = st.number_input(
                    f"Scenario {i+1} weight:", min_value=0.0, max_value=1.0,
                    value=st.session_state.get(f"scenario_weight_{i}", 1.0),
                    help=f"Weight for scenario {i+1}."
                )

    # Navigation buttons
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Project Settings"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Resource Assessment"
            st.rerun()
