import streamlit as st
import pandas as pd

from microgridspy.gui.utils import initialize_session_state

def display_timeline(time_horizon, step_duration):
    """Display project timeline as a table."""
    num_steps = time_horizon // step_duration
    min_step_duration = time_horizon - step_duration * num_steps
    
    step_durations = [step_duration] * num_steps
    if min_step_duration > 0:
        step_durations.append(min_step_duration)
        num_steps += 1

    timeline_data = {
        "Step": [f"Investment Step {i + 1}" for i in range(num_steps)],
        "Duration [Years]": step_durations} 
    
    df_timeline = pd.DataFrame(timeline_data)
    st.table(df_timeline)

def advanced_settings():
    """Streamlit page for configuring advanced settings."""
    # Page title and description
    st.title("Advanced Settings")
    st.write("Configure detailed model parameters and optimization options for your project.")

    initialize_session_state(st.session_state.default_values, 'advanced_settings')

    with st.expander("🧮 Model Formulation", expanded=False):
        milp_options = ["Linear Programming (LP)", "Mixed-Integer Linear Programming (MILP)"]
        milp_index = 1 if st.session_state.milp_formulation else 0
        milp_choice = st.selectbox(
            "Optimization Formulation:",
            options=milp_options,
            index=milp_index,
            help="Choose between LP and MILP formulation. MILP allows for more realistic technology representation but may increase computational effort.")
        
        st.session_state.milp_formulation = milp_choice == "Mixed-Integer Linear Programming (MILP)"
        
        if st.session_state.milp_formulation:
            st.session_state.unit_commitment = st.checkbox(
                "Enable Unit Commitment Approach", 
                value=st.session_state.unit_commitment,
                help="Restrict sizing variables to units of nominal capacity for each technology. It allows for more realistic technology representation but may increase computational effort.")
        
        project_type_options = ["Greenfield", "Brownfield"]
        project_type_index = 1 if st.session_state.brownfield else 0
        project_type_choice = st.selectbox(
            "Project Type:",
            options=project_type_options,
            index=project_type_index,
            help="Choose Greenfield for entirely new projects or Brownfield if considering existing capacity installed for the case study.")
        
        st.session_state.brownfield = project_type_choice == "Brownfield"

        st.session_state.capacity_expansion = st.checkbox(
            "Activate Capacity Expansion", 
            value=st.session_state.capacity_expansion,
            help="Enable to allow system capacity to increase over time through discrete investment steps.")

        if st.session_state.capacity_expansion:
            st.session_state.step_duration = st.slider(
                "Duration of each Investment Step [Years]:", 
                min_value=1, max_value=st.session_state.time_horizon,
                value=st.session_state.step_duration,
                help="Set the interval between potential capacity expansions. Shorter intervals allow more frequent upgrades but increase computational load.")
            
            display_timeline(st.session_state.time_horizon, st.session_state.step_duration)


    with st.expander("⚡ Grid Connection", expanded=False):
        st.session_state.grid_connection = st.checkbox(
            "Simulate Grid Connection", 
            value=st.session_state.grid_connection,
            help="Include national grid connection in the model. This affects energy balance and can impact system economics significantly.")
        
        if st.session_state.grid_connection:
            st.session_state.grid_availability_simulation = st.checkbox(
                "Enable Grid Availability Simulation", 
                value=st.session_state.grid_availability_simulation,
                help="Model intermittent grid availability. This is crucial for areas with unreliable grid supply.")
            
            grid_connection_type = st.radio(
                "Grid Connection Type:", 
                options=["Purchase Only", "Purchase/Sell"],
                index=st.session_state.grid_connection_type,
                help="Choose whether the system can only buy from the grid or both buy and sell. Selling capability can significantly affect system economics.")
            
            st.session_state.grid_connection_type = 0 if grid_connection_type == "Purchase Only" else 1

    with st.expander("📈 Weighted Average Cost of Capital Calculation", expanded=False):
        st.session_state.wacc_calculation = st.checkbox(
            "Enable WACC Calculation", 
            value=st.session_state.wacc_calculation,
            help="Activate to calculate the Weighted Average Cost of Capital. This provides a more accurate discount rate for financial calculations.")
        
        if st.session_state.wacc_calculation:
            st.session_state.cost_of_equity = st.number_input(
                "Cost of Equity [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.cost_of_equity * 100,
                help="Expected return on equity investment. Higher values indicate higher risk or expected returns.")
            st.session_state.cost_of_equity /= 100 
            
            st.session_state.cost_of_debt = st.number_input(
                "Cost of Debt [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.cost_of_debt * 100,
                help="Interest rate on project debt. This is typically lower than the cost of equity.")
            st.session_state.cost_of_debt /= 100  
            
            st.session_state.tax = st.number_input(
                "Corporate Tax Rate [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.tax * 100,
                help="Applicable corporate tax rate. This affects the after-tax cost of debt.")
            st.session_state.tax /= 100  
            
            st.session_state.equity_share = st.number_input(
                "Equity Share [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.equity_share * 100,
                help="Percentage of project financed through equity. Must sum to 100% with debt share.")
            st.session_state.equity_share /= 100  
            
            st.session_state.debt_share = st.number_input(
                "Debt Share [%]:", 
                min_value=0.0, max_value=100.0,
                value=st.session_state.debt_share * 100,
                help="Percentage of project financed through debt. Must sum to 100% with equity share.")
            st.session_state.debt_share /= 100  

    with st.expander("🎯 Multi-Objective Optimization", expanded=False):
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

    with st.expander("🔀 Multi-Scenario Optimization", expanded=False):
        st.session_state.multi_scenario_optimization = st.checkbox(
            "Enable Multi-Scenario Optimization", 
            value=st.session_state.multi_scenario_optimization,
            help="Optimize across multiple scenarios of demand and renewable resource availability. This accounts for uncertainty in long-term projections.")
        
        if st.session_state.multi_scenario_optimization:
            st.session_state.num_scenarios = st.number_input(
                "Number of Scenarios:", 
                min_value=2, 
                value=st.session_state.num_scenarios,
                help="Set the number of scenarios to consider. More scenarios capture more uncertainty but increase computational requirements.")
            
            scenario_weights = []
            for i in range(st.session_state.num_scenarios):
                weight = st.number_input(
                    f"Scenario {i+1} Weight [%]:", 
                    min_value=0.0, max_value=100.0,
                    value=st.session_state.scenario_weights[i] * 100 if i < len(st.session_state.scenario_weights) else 100.0 / st.session_state.num_scenarios,
                    key=f"scenario_weight_{i}",
                    help=f"Assign probability or importance to Scenario {i+1}. Weights should sum to 100% across all scenarios.")
                scenario_weights.append(weight / 100)  
            st.session_state.scenario_weights = scenario_weights

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