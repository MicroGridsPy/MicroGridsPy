import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from typing import Dict

from microgridspy.model.model import Model
from microgridspy.post_process.cost_calculations import get_cost_details
from microgridspy.post_process.data_retrieval import get_sizing_results


import matplotlib.pyplot as plt

def costs_pie_chart(model: Model, optimization_goal: str, color_dict: Dict[str, str]):
    cost_details = get_cost_details(model, optimization_goal)
    actualized = optimization_goal == "NPC"
    suffix = "(Actualized)" if actualized else "(Non-Actualized)"

    total_investment_cost = cost_details[f"Total Investment Cost {suffix}"]
    scenario_total_variable_cost = cost_details[f"Total Variable Cost {suffix}"]
    total_salvage_value = cost_details[f"Total Salvage Value {suffix}"]

    total_cost = total_investment_cost + scenario_total_variable_cost

    # Prepare data for pie chart using color_dict
    pie_data = [
        ("Total Investment Cost", total_investment_cost, color_dict.get("Investment", '#ff9999')),
        ("Total Variable Cost", scenario_total_variable_cost, color_dict.get("Variable", '#66b3ff'))
    ]

    # Calculate percentages for pie chart
    labels, sizes, colors = zip(*[(label, (value / total_cost) * 100, color) for label, value, color in pie_data])

    # Prepare data for bar chart using color_dict
    variable_data = [
        ("Fixed O&M", cost_details[f"Total Fixed O&M Cost {suffix}"], color_dict.get("Fixed O&M", '#ffcc99')),
        ("Battery Replacement", cost_details.get(f"Total Battery Replacement Cost {suffix}", 0), color_dict.get("Battery", '#ff6666')),
        ("Fuel Cost", cost_details.get(f"Total Fuel Cost {suffix}", 0), color_dict.get("Fuel", '#c2c2f0')),
        ("Electricity Cost", cost_details.get(f"Total Electricity Purchased Cost {suffix}", 0), color_dict.get("Electricity Purchased", '#98FB98'))
    ]

    # Filter out zero-cost items
    variable_data = [(label, value, color) for label, value, color in variable_data if value > 0]
    variable_labels, variable_costs, variable_colors = zip(*variable_data) if variable_data else ([], [], [])
    variable_percentages = [cost / scenario_total_variable_cost * 100 for cost in variable_costs] if scenario_total_variable_cost > 0 else []

    # Create the figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1.5, 1]})
    fig.suptitle(f"Cost Breakdown (%) - {optimization_goal}", fontsize=16)

    # Pie chart
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')

    # Add Salvage Value as text
    salvage_percentage = (total_salvage_value / total_cost) * 100
    ax1.text(0, -1.2, f"Salvage Value: {salvage_percentage:.1f}%", ha='center', va='center', fontweight='bold')

    # Bar chart for variable costs breakdown
    if variable_costs:
        y_pos = range(len(variable_labels))
        ax2.barh(y_pos, variable_percentages, align='center', color=variable_colors)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(variable_labels)
        ax2.invert_yaxis()  # Labels read top-to-bottom
        ax2.set_xlabel('Percentage (%)')
        ax2.set_title('Breakdown of Variable Costs')

        # Add percentage values to the end of each bar
        for i, v in enumerate(variable_percentages):
            ax2.text(v, i, f' {v:.1f}%', va='center')
    else:
        ax2.text(0.5, 0.5, "No variable costs", ha='center', va='center')
        ax2.axis('off')

    # Adjust layout
    plt.tight_layout()

    return fig


def create_sizing_plot(model: Model, color_dict: dict, sizing_df: pd.DataFrame):
    """
    Create a plot to visualize the sizing of renewable sources, generators, and battery bank.
    Uses two y-axes for kW and kWh. If there's capacity expansion, it will show the additional capacity for each investment step.
    For brownfield scenarios, existing capacities are included.
    Capacities are rounded to whole numbers.
    """
    
    # Extract data from sizing_df
    categories = sizing_df['Component'].tolist()
    existing_capacities = sizing_df['Existing'].astype(int).values
    capacity_units = [cat.split('(')[-1].strip(')') for cat in categories]  # Extract units (kW or kWh)
    
    # Extract capacity values for each step
    capacities = sizing_df.iloc[:, 2:].astype(int).values  # Step capacities, converted to integer

    # Determine if the model is brownfield
    is_brownfield = model.get_settings('brownfield', advanced=True)
    num_steps = capacities.shape[1]  # Number of steps

    # Assign colors from the color dictionary
    colors = [color_dict.get(cat.split(' (')[0], '#000000') for cat in categories]  # Default to black if not found

    # Create plot with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    # Split components by units: kW and kWh
    kw_mask = np.array(capacity_units) == 'kW'
    kwh_mask = np.array(capacity_units) == 'kWh'

    def plot_bars(ax, mask, label):
        selected_categories = np.array(categories)[mask]
        selected_capacities = capacities[mask]
        selected_existing = existing_capacities[mask]
        selected_colors = np.array(colors)[mask]

        if len(selected_categories) == 0:
            return []  # No components to plot

        # Plot existing capacities if brownfield
        if is_brownfield:
            bars = ax.bar(selected_categories, selected_existing, color=selected_colors, alpha=0.5, label='Existing')
            bottom = selected_existing
        else:
            bottom = None

        # Plot capacities for each step
        bars = ax.bar(selected_categories, selected_capacities[:, 0], color=selected_colors, bottom=bottom)
        if num_steps > 1:
            bottom = selected_capacities[:, 0] if bottom is None else bottom + selected_capacities[:, 0]
            for step in range(1, num_steps):
                expansion = selected_capacities[:, step] - selected_capacities[:, step - 1]
                ax.bar(selected_categories, expansion, bottom=bottom, color=selected_colors, alpha=0.5, 
                       label=f'Step {step + 1}')
                bottom += expansion
        return bars

    # Plot components in kW and kWh
    kw_bars = plot_bars(ax1, kw_mask, 'kW')
    kwh_bars = plot_bars(ax2, kwh_mask, 'kWh')

    # Customize the plot
    ax1.set_ylabel('Capacity (kW)')
    ax2.set_ylabel('Capacity (kWh)')
    plt.title('System Sizing')

    # Add value labels on the bars
    def add_labels(ax, bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:  # Only label non-zero bars
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{int(height)}',  # Display as integer
                        ha='center', va='bottom')

    add_labels(ax1, kw_bars)
    add_labels(ax2, kwh_bars)

    # Add legend if there are expansions or existing capacities
    if num_steps > 1 or is_brownfield:
        ax1.legend(title='Capacity Breakdown')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig

def dispatch_plot(model: Model, scenario: int, year: int, day: int, color_dict: dict):
    """Plot the energy balance for a given day and year, including grid interactions and curtailment."""
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow') if model.has_battery else None
    battery_outflow = model.get_solution_variable('Battery Outflow') if model.has_battery else None
    generator_production = model.get_solution_variable('Generator Energy Production') if model.has_generator else None
    energy_from_grid = model.get_solution_variable('Energy from Grid') if model.has_grid_connection else None
    energy_to_grid = model.get_solution_variable('Energy to Grid') if model.has_grid_connection and model.get_settings('grid_connection_type', advanced=True) == 1 else None
    lost_load = model.get_solution_variable('Lost Load') if model.get_settings('lost_load_fraction') > 0.0 else None

    start_idx = day * 24
    end_idx = (day + 1) * 24

    steps = model.sets['steps'].values
    years = model.sets['years'].values
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    year_to_step = {year: step for year, step in years_steps_tuples}
    step = year_to_step[year]

    daily_demand = demand.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
    daily_battery_inflow = battery_inflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_inflow is not None else np.zeros_like(daily_demand)
    daily_battery_outflow = battery_outflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_outflow is not None else np.zeros_like(daily_demand)
    daily_energy_from_grid = energy_from_grid.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if energy_from_grid is not None else np.zeros_like(daily_demand)
    daily_energy_to_grid = energy_to_grid.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if energy_to_grid is not None else np.zeros_like(daily_demand)
    daily_lost_load = lost_load.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if lost_load is not None else np.zeros_like(daily_demand)
    daily_total_curtailment = curtailment.sum('renewable_sources').isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)

    fig, ax = plt.subplots(figsize=(20, 12))

    x = range(24)
    cumulative_outflow = np.zeros(24)
    cumulative_inflow = np.zeros(24)

    # Plot actual renewable energy production for each source
    renewable_sources = model.sets['renewable_sources'].values
    for source in renewable_sources:
        daily_source_production = res_production.sel(renewable_sources=source, steps=step).isel(scenarios=scenario)[start_idx:end_idx] / 1000
        daily_source_curtailment = curtailment.sel(renewable_sources=source).isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)
        daily_actual_production = daily_source_production - daily_source_curtailment
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_actual_production, 
                        label=f'{source} Actual Production', color=color_dict.get(source), alpha=0.5)
        cumulative_outflow += daily_actual_production

    # Plot battery charging and discharging
    ax.fill_between(x, -cumulative_inflow, -(cumulative_inflow+daily_battery_inflow), label='Battery Charging', 
                    color=color_dict.get('Battery'), alpha=0.5)
    cumulative_inflow += daily_battery_inflow
    ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_battery_outflow, 
                    label='Battery Discharging', color=color_dict.get('Battery'), alpha=0.5)
    cumulative_outflow += daily_battery_outflow

    # Plot generator production for each type
    if generator_production is not None:
        generator_types = generator_production.coords['generator_types'].values
        for gen_type in generator_types:
            daily_gen_production = generator_production.sel(generator_types=gen_type).isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000
            ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_gen_production, 
                            label=f'{gen_type} Production', color=color_dict.get(gen_type), alpha=0.5)
            cumulative_outflow += daily_gen_production

    # Plot energy from grid
    if energy_from_grid is not None:
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_energy_from_grid, 
                        label='Energy from Grid', color=color_dict.get('Electricity Purchased'), alpha=0.5)
        cumulative_outflow += daily_energy_from_grid

    # Plot lost load
    if lost_load is not None:
        ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_lost_load, label='Lost Load', 
                        color=color_dict.get('Lost Load'), alpha=0.5)
        cumulative_outflow += daily_lost_load

    # Plot energy to grid (as negative values)
    if energy_to_grid is not None:
        ax.fill_between(x, -cumulative_inflow, -(cumulative_inflow+daily_energy_to_grid), label='Energy to Grid', 
                        color=color_dict.get('Electricity Sold'), alpha=0.5)
        cumulative_inflow += daily_energy_to_grid

    # Plot demand
    ax.plot(x, daily_demand, label='Demand', color=color_dict.get('Demand', 'black'), linewidth=2)

    # Plot curtailment on top of demand
    ax.fill_between(x, cumulative_outflow, cumulative_outflow + daily_total_curtailment, 
                    label='Curtailment', color=color_dict.get('Curtailment'), alpha=0.5)

    ax.set_xlabel('Hours')
    ax.set_ylabel('Energy (kWh)')
    ax.set_title(f'Energy Balance - Year {year + 1}, Day {day + 1}')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    
    # Adjust y-axis to show negative values if energy is sold to the grid
    y_min = min(ax.get_ylim()[0], -daily_energy_to_grid.max() if energy_to_grid is not None else 0)
    y_max = max(ax.get_ylim()[1], (daily_demand + daily_total_curtailment).max())
    ax.set_ylim(bottom=y_min, top=y_max)

    return fig

def create_energy_usage_pie_chart(energy_usage: dict, model: Model, res_names, color_dict, gen_names=None):
    """Create a pie chart of energy usage percentages with a legend and external labels."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Dynamically create color mapping and usage data
    color_mapping = {}
    usage_data = {}
    
    # Add renewable sources
    for res in res_names:
        color_mapping[f"{res} Usage"] = res
        usage_data[f"{res} Usage"] = energy_usage.get(f"{res} Usage", 0)

    # Add Battery
    if model.has_battery:
        color_mapping["Battery Usage"] = "Battery"
        usage_data["Battery Usage"] = energy_usage.get("Battery Usage", 0)
    
    # Add generators
    if model.has_generator:
        for gen in gen_names:
            color_mapping[f"{gen} Usage"] = gen
            usage_data[f"{gen} Usage"] = energy_usage.get(f"{gen} Usage", 0)

    if model.has_grid_connection:
        color_mapping["Grid Usage"] = "Electricity Purchased"
        usage_data["Grid Usage"] = energy_usage.get("Grid Usage", 0)

    # Remove zero values
    usage_data = {k: v for k, v in usage_data.items() if v > 0}
    
    # Get colors based on the mapping
    colors = [color_dict.get(color_mapping.get(k, k)) for k in usage_data.keys()]
    
    wedges, texts, autotexts = ax.pie(usage_data.values(), 
                                      colors=colors,
                                      autopct=lambda pct: f'{pct:.1f}%',
                                      pctdistance=0.8,
                                      wedgeprops=dict(width=0.5))
    
    # Add labels outside the pie chart
    ax.legend(wedges, usage_data.keys(),
              title="Energy Usage",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))
    
    ax.set_title('Average Energy Usage by Technology')
    
    # Remove bold formatting from percentage labels
    plt.setp(autotexts, weight="normal", size=8)
    
    plt.tight_layout()
    
    return fig