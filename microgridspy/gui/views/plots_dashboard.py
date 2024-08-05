import streamlit as st
import pandas as pd

from microgridspy.model.model import Model
from config.path_manager import PathManager
from microgridspy.post_process.cost_calculations import calculate_actualized_investment_cost, calculate_actualized_salvage_value, calculate_lcoe
from microgridspy.post_process.energy_calculations import calculate_energy_usage, calculate_renewable_penetration
from microgridspy.post_process.data_retrieval import get_generator_usage, get_battery_soc, get_renewables_usage
from microgridspy.post_process.plots import(
    create_bar_of_pie_chart, 
    create_energy_usage_pie_chart, 
    create_heatmap, dispatch_plot, 
    create_sizing_plot, 
    format_sizing_table
)
from microgridspy.post_process.export_results import save_results_to_excel, save_plots

# Define default colors
DEFAULT_COLORS = {
    'Demand': '#000000',  # Black
    'Curtailment': '#FFA500',  # Orange
    'Battery': '#ADD8E6',  # Light Blue
    'RES': '#FFFF00',  # Yellow
    'Generator': '#00008B',  # Dark Blue
}

def display_cost_breakdown(model: Model, optimization_goal: str):

    def get_cost(var_name: str):
        value = model.get_solution_variable(var_name)
        return value.values.item() / 1000 if value is not None else 0
    
    currency = st.session_state.get('currency', 'USD')
    
    if optimization_goal == "NPC":
        npc = get_cost("Net Present Cost")
        lcoe = calculate_lcoe(model, 'NPC')
        # Display NPC and LCOE
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Net Present Cost", f"{npc:.2f} k{currency}")
        with col2:
            st.metric("Levelized Cost of Energy (LCOE)", f"{lcoe:.4f} {currency}/kWh")

    elif optimization_goal == "Total Variable Cost":
        total_variable_cost = get_cost("Total Variable Cost")
        lcoe = calculate_lcoe(model, 'Total Variable Cost')
        # Display Total Variable Cost and LCOE
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Variable Cost", f"{total_variable_cost:.2f} k{currency}")
        with col2:
            st.metric("Levelized Variable Cost (LVC)", f"{lcoe:.4f} {currency}/kWh")

    # Display cost details in a table
    st.subheader("Cost Details")
    if optimization_goal == "NPC":
        total_investment_cost = get_cost("Total Investment Cost")
        scenario_total_variable_cost = get_cost("Scenario Total Variable Cost (Actualized)")
        total_fixed_operation_cost = get_cost("Operation and Maintenance Cost (Actualized)")
        total_battery_replacement_cost = get_cost("Battery Replacement Cost (Actualized)") if model.has_battery else 0
        total_fuel_cost = get_cost("Total Fuel Cost (Actualized)") if model.has_generator else 0
        total_salvage_value = get_cost("Salvage Value")
        
        cost_details = {
            "Total Investment Cost (Actualized)": total_investment_cost,
            "Total Variable Cost (Actualized)": scenario_total_variable_cost,
            " - Total Fixed O&M Cost (Actualized)": total_fixed_operation_cost,
            " - Total Battery Replacement Cost (Actualized)": total_battery_replacement_cost,
            " - Total Fuel Cost (Actualized)": total_fuel_cost,
            "Total Salvage Value (Actualized)": total_salvage_value}
        
    elif optimization_goal == "Total Variable Cost":
        total_investment_cost = calculate_actualized_investment_cost(model)
        scenario_total_variable_cost = get_cost("Scenario Total Variable Cost (Non-Actualized)")
        total_fixed_operation_cost = get_cost("Operation and Maintenance Cost (Non-Actualized)")
        total_battery_replacement_cost = get_cost("Battery Replacement Cost (Not Actualized)") if model.has_battery else 0
        total_fuel_cost = get_cost("Total Fuel Cost (Non-Actualized)") if model.has_generator else 0
        total_salvage_value = calculate_actualized_salvage_value(model)

        cost_details = {
            "Total Investment Cost (Actualized)": total_investment_cost,
            "Total Variable Cost (Not Actualized)": scenario_total_variable_cost,
            " - Total Fixed O&M Cost (Not Actualized)": total_fixed_operation_cost,
            " - Total Battery Replacement Cost (Not Actualized)": total_battery_replacement_cost,
            " - Total Fuel Cost (Not Actualized)": total_fuel_cost,
            "Total Salvage Value (Actualized)": total_salvage_value}
    
    # Create a DataFrame for the cost details
    cost_df = pd.DataFrame.from_dict(cost_details, orient='index', columns=[f'Value (k{currency})'])
    cost_df[f'Value (k{currency})'] = cost_df[f'Value (k{currency})'].round(2)
    
    # Display the table
    st.table(cost_df)


def get_sizing_results(model: Model):
    sizing = {}
    
    res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables')
    res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
    if res_units is not None:
        for source in res_units.renewable_sources.values:
            capacities = res_units.sel(renewable_sources=source).values * res_nominal_capacity.sel(renewable_sources=source).values
            sizing[source] = [f"{capacity / 1000:.2f}" for capacity in capacities]
    
    if model.has_battery:
        bat_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries')
        if bat_units is not None:
            battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
            capacities = bat_units.values * battery_nominal_capacity.values
            sizing["Battery Bank"] = [f"{capacity / 1000:.2f}" for capacity in capacities]

    if model.has_generator:
        gen_units = model.get_solution_variable('Unit of Nominal Capacity for Generators')
        if gen_units is not None:
            for gen_type in gen_units.generator_types.values:
                capacities = gen_units.sel(generator_types=gen_type).values * model.parameters['GENERATOR_NOMINAL_CAPACITY'].sel(generator_types=gen_type).values
                sizing[gen_type] = [f"{capacity / 1000:.2f}" for capacity in capacities]
    
    return sizing

def plots_dashboard():
    """Create the results dashboard with cost breakdown, sizing results, and additional visualizations."""
    # Initialize dict to store plot figures
    fig: dict = {}

    st.title("Results Dashboard")

    if 'model' not in st.session_state:
        st.warning("Please run the optimization model first.")
        return
    else:
        # Get the results from the model
        model = st.session_state.model

    # Cost breakdown
    st.header("Cost Breakdown")
    # Optimization goal: NPC
    if model.get_settings('optimization_goal') == 0:
        display_cost_breakdown(model, 'NPC')
        # Create and display the bar of pie chart
        cost_breakdown_fig = create_bar_of_pie_chart(model, 'NPC')
        fig['Cost Breakdown Bar of Pie Chart'] = cost_breakdown_fig
        st.pyplot(cost_breakdown_fig)
    # Optimization goal: Total Variable Cost
    else:
        display_cost_breakdown(model, 'Total Variable Cost')
        # Create and display the bar of pie chart
        cost_breakdown_fig = create_bar_of_pie_chart(model, 'Total Variable Cost')
        fig['Cost Breakdown Bar of Pie Chart'] = cost_breakdown_fig
        st.pyplot(cost_breakdown_fig)

    st.write("---")  # Add a separator

    # Sizing and Dispatch
    st.header("Sizing and Dispatch")

    # Color customization section
    st.write("Customize colors for each technology: click on the color picker to change the color.")
    
    if 'color_dict' not in st.session_state:
        st.session_state.color_dict = DEFAULT_COLORS.copy()

    res_names = st.session_state.res_names
    gen_names = st.session_state.gen_names

    for res in res_names:
        if res not in st.session_state.color_dict:
            st.session_state.color_dict[res] = DEFAULT_COLORS['RES']
    for gen in gen_names:
        if gen not in st.session_state.color_dict:
            st.session_state.color_dict[gen] = DEFAULT_COLORS['Generator']

    # Create a single line of color pickers
    all_elements = ["Demand", "Curtailment", "Battery"] + res_names + gen_names
    num_columns = len(all_elements)
    cols = st.columns(num_columns)

    for i, element in enumerate(all_elements):
        with cols[i]:
            st.session_state.color_dict[element] = st.color_picker(
                element,
                key=f"color_{element}",
                value=st.session_state.color_dict[element])

    # Sizing results
    st.header("Mini-Grid Sizing")
    
    # Create and display the sizing plot
    sizing_fig, categories, capacities, capacity_units = create_sizing_plot(model, st.session_state.color_dict)
    fig['System Sizing'] = sizing_fig
    st.pyplot(sizing_fig)
    
    # Display sizing results in a formatted table
    sizing_df = format_sizing_table(categories, capacities, capacity_units)
    st.table(sizing_df)

    # Create a dictionary of installed capacities
    installed_capacities = {cat: cap.sum() for cat, cap in zip(categories, capacities)}

    st.write("---")  # Add a separator

    # Energy Balance Visualization
    st.header("Energy Usage Visualization")

    # Convert years to integers if they're not already
    years = [int(year) for year in model.sets['years']]
    min_year = min(years)
    max_year = max(years)

    # Energy Balance Visualization
    st.subheader("Dispatch Plot")

    selected_year = st.slider("Select Year for Dispatch Plot", 
                        min_value=min_year,
                        max_value=max_year,
                        value=min_year)
    selected_year_index = years.index(selected_year)
    selected_day = st.slider("Select Day", 0, 364, 0, key="day_slider")

    dispatch_fig = dispatch_plot(model, scenario=0, year=selected_year_index, day=selected_day, color_dict=st.session_state.color_dict)
    fig['Dispatch Plot'] = dispatch_fig
    st.pyplot(dispatch_fig)

    # Energy Usage and Curtailment
    st.subheader("Average Energy Usage")
    
    energy_usage = calculate_energy_usage(model)
    renewable_penetration = calculate_renewable_penetration(model)
    
    # Display Curtailment and Renewable Penetration as metrics side by side
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Curtailment", f"{energy_usage['Curtailment']:.2f}%")
    with col2:
        st.metric("Renewable Penetration", f"{renewable_penetration:.2f}%")
    
    # Create and display pie chart
    energy_usage_fig = create_energy_usage_pie_chart(energy_usage, model, st.session_state.res_names, st.session_state.gen_names, st.session_state.color_dict)
    fig['Energy Usage Pie Chart'] = energy_usage_fig
    st.pyplot(energy_usage_fig)

    # Renewables Usage 
    st.subheader("Renewables Usage")
    res_sources = model.get_solution_variable('Energy Production by Renewables').coords['renewable_sources'].values
    available_res = [res for res in res_sources if installed_capacities.get(res, 0) > 0]
    
    if available_res:
        selected_res = st.selectbox("Select Renewable Sources", available_res)
        res_usage = get_renewables_usage(model, selected_res)
        if not res_usage.empty:
            res_usage.index = pd.date_range(start=f"{min_year}-01-01", periods=len(res_usage), freq='H')
            selected_year = st.slider("Select Year for Renewable Usage", 
                                      min_value=min_year,
                                      max_value=max_year,
                                      value=min_year)
            res_heatmap = create_heatmap(res_usage, f'{selected_res} Usage', selected_year, st.session_state.color_dict[selected_res])
            fig['Renewables Usage Heatmap'] = res_heatmap
            st.pyplot(res_heatmap)
    else:
        st.warning("No renewable sources with installed capacity.")
    
    # Battery State of Charge (if applicable)
    if model.has_battery and installed_capacities.get("Battery Bank", 0) > 0:
        st.subheader("Battery State of Charge")
        soc_data = get_battery_soc(model)
        if not soc_data.empty:
            soc_data.index = pd.date_range(start=f"{min_year}-01-01", periods=len(soc_data), freq='H')
            selected_year_battery = st.slider("Select Year for Battery SoC", 
                                              min_value=min_year,
                                              max_value=max_year,
                                              value=min_year)
            battery_soc_heatmap = create_heatmap(soc_data, 'Battery State of Charge', selected_year_battery, st.session_state.color_dict['Battery'])
            fig['Battery SoC Heatmap'] = battery_soc_heatmap
            st.pyplot(battery_soc_heatmap)
    elif model.has_battery:
        st.warning("Battery is present in the model but has no installed capacity.")

    # Generator Usage (if applicable)
    if model.has_generator:
        st.subheader("Generator Usage")
        gen_types = model.get_solution_variable('Generator Energy Production').coords['generator_types'].values
        available_gens = [gen for gen in gen_types if installed_capacities.get(gen, 0) > 0]
        
        if available_gens:
            selected_gen = st.selectbox("Select Generator Type", available_gens)
            gen_usage = get_generator_usage(model, selected_gen)
            if not gen_usage.empty:
                gen_usage.index = pd.date_range(start=f"{min_year}-01-01", periods=len(gen_usage), freq='H')
                selected_year = st.slider("Select Year for Generator Usage", 
                                          min_value=min_year,
                                          max_value=max_year,
                                          value=min_year)
                generator_heatmap = create_heatmap(gen_usage, f'{selected_gen} Usage', selected_year, st.session_state.color_dict[selected_gen])
                fig['Generator Usage Heatmap'] = generator_heatmap
                st.pyplot(generator_heatmap)
        else:
            st.warning("No generators with installed capacity.")

    st.write("---")  # Add a separator

    # Export results
    st.header("Export Results")
    st.write("Save results and plots within the results folder.")
    excel_filepath = PathManager.RESULTS_FOLDER_PATH
    plots_filepath = PathManager.RESULTS_FOLDER_PATH / "Plots"
    plots_filepath.mkdir(exist_ok=True)
    
    if st.button("Export Results"):
        with st.spinner("Exporting results..."):
            save_results_to_excel(model, excel_filepath)
        st.success(f"Results exported successfully to {excel_filepath}")

    if st.button("Save Plots"):
        with st.spinner("Saving current plots..."):
            save_plots(plots_filepath, fig)
        st.success(f"Plots saved successfully to {plots_filepath}")
