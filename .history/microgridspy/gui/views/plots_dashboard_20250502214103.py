import streamlit as st
import pandas as pd

from typing import Dict, Any, List
from pathlib import Path
from microgridspy.model.model import Model
from config.path_manager import PathManager
from microgridspy.post_process.cost_calculations import (
    calculate_actualized_investment_cost,
    calculate_actualized_salvage_value,
    calculate_lcoe,
    calculate_grid_costs)
from microgridspy.post_process.energy_calculations import (
    calculate_energy_usage,
    calculate_renewable_penetration,
    calculate_partial_load_indicators)
from microgridspy.post_process.data_retrieval import get_sizing_results, get_conversion_sizing_results
from microgridspy.post_process.plots import (
    costs_pie_chart,
    create_energy_usage_pie_chart,
    dispatch_plot,
    create_sizing_plot
)
from microgridspy.post_process.export_results import save_energy_balance_to_excel, save_plots

DEFAULT_COLORS = {
    'Demand': '#000000',
    'Curtailment': '#FFA500',
    'Battery': '#4CC9F0',
    'Electricity Purchased': '#800080',
    'Electricity Sold': '#008000',
    'Lost Load': '#F21B3F'
}

def initialize_colors(model: Model) -> Dict[str, str]:
    colors = DEFAULT_COLORS.copy()
    for i, res_name in enumerate(model.sets['renewable_sources'].values):
        colors[res_name] = ['#FFFF00', '#FFFFE0', '#FFFACD', '#FAFAD2'][i % 4]
    if model.has_generator:
        for i, gen_name in enumerate(model.sets['generator_types'].values):
            colors[gen_name] = ['#00509D', '#0066CC', '#0077B6', '#0088A3'][i % 4]
    if 'color_dict' not in st.session_state:
        st.session_state.color_dict = colors
    return st.session_state.color_dict

def create_color_customization_section(all_elements: List[str], color_dict: Dict[str, str]) -> None:
    st.write("Customize colors for each technology: click on the color picker to change the color.")
    cols = st.columns(len(all_elements))
    for element, col in zip(all_elements, cols):
        with col:
            default_color = color_dict.get(element, DEFAULT_COLORS.get(element))
            color_dict[element] = st.color_picker(element, key=f"color_{element}", value=default_color)

def plots_dashboard():
    fig: dict = {}
    st.title("Results Dashboard")

    if 'model' not in st.session_state:
        st.warning("Please run the optimization model first.")
        return

    model: Model = st.session_state.model
    currency = st.session_state.get('currency', 'USD')
    project_name = st.session_state.get('project_name')

    # Load selected Pareto solution if available
    if 'selected_solution_index' in st.session_state and 'multiobjective_solutions' in st.session_state:
        selected_index = st.session_state.selected_solution_index
        model.solution = st.session_state.multiobjective_solutions[selected_index]

    # Optional selector for Pareto exploration
    if 'pareto_front' in st.session_state and 'multiobjective_solutions' in st.session_state:
        st.subheader("Explore Other Pareto Solutions")
        co2_vals, npc_vals = zip(*st.session_state.pareto_front)
        selected_index = st.selectbox(
            "Select a solution to visualize",
            range(len(st.session_state.pareto_front)),
            format_func=lambda x: f"Solution {x + 1}: CO₂ = {co2_vals[x]/1000:.2f} t, NPC = {npc_vals[x]/1000:.2f} k{currency}",
            index=st.session_state.get('selected_solution_index', 0),
            key="dashboard_solution_selector"
        )
        st.session_state.selected_solution_index = selected_index
        model.solution = st.session_state.multiobjective_solutions[selected_index]

    color_dict = initialize_colors(model)

    st.header("Cost Breakdown")
    optimization_goal = 'NPC' if model.get_settings('optimization_goal') == 0 else 'Total Variable Cost'
    actualized = optimization_goal == "NPC"

    main_cost = (
        model.get_solution_variable('Net Present Cost').values.item()
        if actualized else
        model.get_solution_variable('Total Variable Cost').values.item())

    col1, col2 = st.columns(2)
    with col1:
        st.metric(optimization_goal, f"{main_cost / 1000:.2f} k{currency}")
    with col2:
        lcoe = calculate_lcoe(model, optimization_goal)
        lcoe_label = "Levelized Cost of Energy (LCOE)" if actualized else "Levelized Variable Cost (LVC)"
        st.metric(lcoe_label, f"{lcoe:.4f} {currency}/kWh")

    st.subheader("Cost Details")
    from microgridspy.post_process.cost_calculations import costs_breakdown
    costs_df = costs_breakdown(model, optimization_goal)
    st.table(costs_df)
    fig['Cost Breakdown Pie'] = costs_pie_chart(model, optimization_goal, color_dict)
    st.pyplot(fig['Cost Breakdown Pie'])

    st.header("Sizing and Dispatch")
    all_elements = ["Demand", "Curtailment"] + list(model.sets['renewable_sources'].values)
    if model.has_battery:
        all_elements.append("Battery")
    if model.has_generator:
        all_elements.extend(list(model.sets['generator_types'].values))
    if model.has_grid_connection:
        all_elements.append("Electricity Purchased")
        if model.get_settings('grid_connection_type', advanced=True) == 1:
            all_elements.append("Electricity Sold")
    if model.get_settings('lost_load_fraction') > 0.0:
        all_elements.append("Lost Load")
    create_color_customization_section(all_elements, color_dict)

    st.header("Mini-Grid Sizing")
    sizing_df = get_sizing_results(model)
    fig['Sizing'] = create_sizing_plot(model, color_dict, sizing_df)
    st.pyplot(fig['Sizing'])
    st.table(sizing_df)

    try:
        conversion_sizing_df = get_conversion_sizing_results(model)
        st.write("Conversion Sizing Results")
        st.table(conversion_sizing_df)
    except:
        conversion_sizing_df = None
        st.write("No conversion sizing results available.")

    st.header("Energy Usage Visualization")
    years = [int(year) for year in model.sets['years']]
    selected_year = st.slider("Select Year for Dispatch Plot", min_value=min(years), max_value=max(years), value=min(years))
    selected_day = st.slider("Select Day", 0, 364, 0, key="day_slider")
    dispatch_fig = dispatch_plot(model, scenario=0, year=years.index(selected_year), day=selected_day, color_dict=color_dict)
    fig['Dispatch Plot'] = dispatch_fig
    st.pyplot(dispatch_fig)

    st.subheader("Average Energy Usage")
    energy_usage = calculate_energy_usage(model)
    renewable_penetration = calculate_renewable_penetration(model)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Yearly Curtailment", f"{energy_usage['Curtailment']:.2f}%")
    with col2:
        st.metric("Average Yearly Renewable Penetration", f"{renewable_penetration:.2f}%")
    pie = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, color_dict, st.session_state.gen_names if model.has_generator else None)
    fig['Energy Usage Pie Chart'] = pie
    st.pyplot(pie)

    if model.has_generator:
        fuel = model.get_solution_variable('Generator Fuel Consumption').sum().item()
        co2 = model.get_solution_variable('Fuel Emissions').sum().item()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Fuel Total Consumption", f"{fuel:.2f} liters")
        with col2:
            st.metric("Fuel Total Emission", f"{co2:.2f} kgCO₂")
        if st.session_state.get('partial_load'):
            avg_lf, avg_eff = calculate_partial_load_indicators(model)
            st.markdown("**Generator Partial Load Indicators**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Generator Load Factor", f"{avg_lf:.2f} %")
            with col2:
                st.metric("Average Generator Efficiency", f"{avg_eff:.2f} kWh/liter")

    st.header("Export Results")
    st.write("Click the buttons below to export the full results to Excel or save the current plots.")
    export_results(project_name, model, costs_df, sizing_df, conversion_sizing_df, fig)

    st.write("---")
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Back"):
            st.session_state.page = "Optimization"
            st.rerun()
    with col2:
        if st.button("Next"):
            st.session_state.page = "Project Profitability"
            st.rerun()
