import pandas as pd
import numpy as np
from pathlib import Path
from microgridspy.model.parameters import ProjectParameters
from microgridspy.model.model import Model
import matplotlib.pyplot as plt
from config.path_manager import PathManager

def calculate_lcoe(model: Model) -> float:
    """
    Calculate the Levelized Cost of Energy (LCOE) based on the model results.
    """
    net_present_cost = model.get_solution_variable('Net Present Cost').values.item()  # USD
    demand = model.parameters['DEMAND'] / 1000  # Convert to kW
    discount_rate = model.parameters['DISCOUNT_RATE'].values.item()
    num_years = len(demand.coords['years'])
    project_years = range(num_years)

    pv_demand = sum(demand.isel(years=year-1, scenarios=0).sum().values / ((1 + discount_rate) ** year) for year in project_years)

    lcoe = net_present_cost / pv_demand
    return lcoe

def print_solution_results(model: Model):
    print("\nCosts Results:")
    
    def print_cost(name: str, var_name: str):
        value = model.get_solution_variable(var_name)
        if value is not None:
            print(f"{name}: {value.values.item() / 1000:.2f} kUSD")
    
    print_cost("Net Present Cost", "Net Present Cost")
    print_cost("Total Actualized Investment Cost", "Total Investment Cost")
    print_cost("Total Actualized Variable Cost", "Scenario Total Variable Cost (Actualized)")
    print_cost(" - Total Actualized Fixed O&M Cost", "Operation and Maintenance Cost (Actualized)")
    
    if model.has_battery:
        print_cost(" - Total Actualized Battery Replacement Cost", "Battery Replacement Cost (Actualized)")

    if model.has_generator:
        print_cost(" - Total Actualized Fuel Cost", "Total Fuel Cost (Actualized)")
    
    print_cost("Salvage Value", "Salvage Value")

    # Calculate and print LCOE
    lcoe = calculate_lcoe(model)
    print(f"LCOE (NPC/Demand): {lcoe:.4f} USD/kW")
    
    # Print sizing
    print("\nMini-Grid Sizing:")
    res_units = model.get_solution_variable('Unit of Nominal Capacity for Renewables')
    res_nominal_capacity = model.parameters['RES_NOMINAL_CAPACITY']
    if res_units is not None:
        for source in res_units.renewable_sources.values:
            capacities = res_units.sel(renewable_sources=source).values * res_nominal_capacity.sel(renewable_sources=source).values
            previous_capacity = 0
            for step, capacity in zip(res_units.steps.values, capacities):
                additional_capacity = capacity - previous_capacity
                print(f"{source} (Step {step}): {additional_capacity / 1000:.2f} kW, {capacity / 1000:.2f} kW (Total)")
                previous_capacity = capacity
    
    if model.has_battery:
        bat_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries')
        if bat_units is not None:
            battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
            capacities = bat_units.values * battery_nominal_capacity.values
            previous_capacity = 0
            for step, capacity in zip(bat_units.steps.values, capacities):
                additional_capacity = capacity - previous_capacity
                print(f"Battery Bank (Step {step}): {additional_capacity / 1000:.2f} kWh, {capacity / 1000:.2f} kWh (Total)")
                previous_capacity = capacity

    if model.has_generator:
        gen_units = model.get_solution_variable('Unit of Nominal Capacity for Generators')
        if gen_units is not None:
            for gen_type in gen_units.generator_types.values:
                capacities = gen_units.sel(generator_types=gen_type).values * model.parameters['GENERATOR_NOMINAL_CAPACITY'].sel(generator_types=gen_type).values
                previous_capacity = 0
                for step, capacity in zip(gen_units.steps.values, capacities):
                    additional_capacity = capacity - previous_capacity
                    print(f"{gen_type} (Step {step}): {additional_capacity / 1000:.2f} kW, {capacity / 1000:.2f} kW (Total)")
                    previous_capacity = capacity

    demand = model.parameters['DEMAND']
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    total_renewable_production = model.get_solution_variable('Energy Production by Renewables')
    battery_outflow = model.get_solution_variable('Battery Outflow')
    battery_inflow = model.get_solution_variable('Battery Inflow')
    generator_energy_production = model.get_solution_variable('Generator Energy Production')

    years = demand.coords['years'].values
    steps = total_renewable_production.coords['steps'].values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]

    yearly_battery_usage = []
    yearly_generator_usage = []
    yearly_pv_usage = []
    yearly_curtailment_percentage = []

    for year in years:
        step = years_steps_tuples[year - years[0]][1]
        
        yearly_demand = demand.sel(years=year).sum().values.item()
        yearly_renewable_production = total_renewable_production.sel(steps=step).sum().values.item()
        yearly_curtailment = curtailment.sel(years=year).sum().values.item() if curtailment is not None else 0

        yearly_battery_in = battery_inflow.sel(years=year).sum().values.item() if battery_inflow is not None else 0
        yearly_generator_production = generator_energy_production.sel(years=year).sum().values.item() if generator_energy_production is not None else 0
        
        yearly_pv_used = yearly_renewable_production - yearly_curtailment - yearly_battery_in
        yearly_pv_usage.append((yearly_pv_used / yearly_demand) * 100)

        if yearly_generator_production is not None:
            yearly_generator_usage.append((yearly_generator_production / yearly_demand) * 100)

        if battery_outflow is not None:
            yearly_battery_out = battery_outflow.sel(years=year).sum().values.item()
            yearly_battery_usage.append((yearly_battery_out / yearly_demand) * 100)

        if yearly_renewable_production > 0:
            yearly_curtailment_percentage.append((yearly_curtailment / yearly_renewable_production) * 100)
        else:
            yearly_curtailment_percentage.append(0)

    if battery_outflow is not None:
        average_battery_usage = sum(yearly_battery_usage) / len(yearly_battery_usage)
        print(f"\nAverage Battery Usage over Demand: {average_battery_usage:.2f}%")

    if generator_energy_production is not None:
        average_generator_usage = sum(yearly_generator_usage) / len(yearly_generator_usage)
        print(f"Average Generator Usage over Demand: {average_generator_usage:.2f}%")

    average_pv_usage = sum(yearly_pv_usage) / len(yearly_pv_usage)
    print(f"Average PV Usage over Demand: {average_pv_usage:.2f}%")

    average_curtailment_percentage = sum(yearly_curtailment_percentage) / len(yearly_curtailment_percentage)
    print(f"Average Curtailment over Total Energy Production: {average_curtailment_percentage:.2f}%")


def plot_energy_balance(model: Model, scenario: int, year: int, day: int):
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow')
    battery_outflow = model.get_solution_variable('Battery Outflow')
    generator_production = model.get_solution_variable('Generator Energy Production')
    curtailment = model.get_solution_variable('Curtailment by Renewables')

    # Calculate the start and end indices for the selected day
    start_idx = day * 24
    end_idx = (day + 1) * 24

    # Ensure the year is within the range of available data
    if year < 0 or year >= len(demand.coords['years']):
        raise ValueError("Year out of range")

    # Mapping steps to years
    steps = res_production.coords['steps'].values
    years = demand.coords['years'].values
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i] - years[0], steps[i // step_duration]) for i in range(len(years))]
    year_to_step = {year: step for year, step in years_steps_tuples}
    step = year_to_step[year]

    daily_demand = demand.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000  # Convert to kW
    daily_battery_inflow = battery_inflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_inflow is not None else np.zeros_like(daily_demand)
    daily_battery_outflow = battery_outflow.isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if battery_outflow is not None else np.zeros_like(daily_demand)
    daily_generator_production = generator_production.isel(years=year, scenarios=scenario)[start_idx:end_idx].sum('generator_types') / 1000 if generator_production is not None else np.zeros_like(daily_demand)

    daily_curtailment = curtailment.sum('renewable_sources').isel(years=year, scenarios=scenario)[start_idx:end_idx] / 1000 if curtailment is not None else np.zeros_like(daily_demand)

    plt.figure(figsize=(12, 6))

    x = range(24)
    battery_discharge = daily_battery_outflow
    battery_charge = -daily_battery_inflow  # Negative for charging
    generator_production = daily_generator_production
    curtail = daily_curtailment

    # Calculate energy used (res_production - curtailment - battery_inflow)
    daily_energy_used = (res_production.sel(steps=step).isel(scenarios=scenario) - curtailment.isel(years=year,scenarios=scenario) - battery_inflow.isel(years=year,scenarios=scenario))[start_idx:end_idx].sum('renewable_sources') / 1000

    # Plotting the renewable energy used
    plt.fill_between(x, 0, daily_energy_used, label='Renewable Energy Used', color='yellow', alpha=0.5)

    # Plot curtailment
    plt.fill_between(x, daily_energy_used, daily_energy_used + curtail, label='Curtailment', color='orange', alpha=0.5)

    # Plot battery charging (negative values)
    plt.fill_between(x, 0, battery_charge, label='Battery Charging', color='lightblue', alpha=0.5)

    # Plot battery discharging
    plt.fill_between(x, daily_energy_used, daily_energy_used + battery_discharge, label='Battery Discharging', color='lightblue', alpha=0.5)

    # Plot generator production
    plt.fill_between(x, daily_energy_used, daily_energy_used + battery_discharge + generator_production, label='Generator Production', color='blue', alpha=0.5)

    # Plot demand line
    plt.plot(x, daily_demand, label='Demand', color='black', linewidth=2)

    plt.xlabel('Hours')
    plt.ylabel('Energy (kWh)')
    plt.title(f'Energy Balance - Year {year + 1}, Day {day + 1}')
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def save_results_to_excel(model: Model, base_filepath: Path):
    demand = model.parameters['DEMAND']
    res_production = model.get_solution_variable('Energy Production by Renewables')
    battery_inflow = model.get_solution_variable('Battery Inflow')
    battery_outflow = model.get_solution_variable('Battery Outflow')
    state_of_charge = model.get_solution_variable('Battery State of Charge')
    battery_units = model.get_solution_variable('Unit of Nominal Capacity for Batteries')
    if battery_units is not None:
        battery_nominal_capacity = model.parameters['BATTERY_NOMINAL_CAPACITY']
    curtailment = model.get_solution_variable('Curtailment by Renewables')
    generator_production = model.get_solution_variable('Generator Energy Production')

    # Mapping steps to years
    steps = res_production.coords['steps'].values
    years = demand.coords['years'].values
    start_year = years[0]
    step_duration = settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i], steps[i // step_duration]) for i in range(len(years))]

    for scenario in range(demand.sizes['scenarios']):
        filepath = base_filepath / f"Energy Balance - Scenario {scenario + 1}.xlsx"
        with pd.ExcelWriter(filepath) as writer:
            for year in range(len(years)):
                step = years_steps_tuples[year][1]

                data = {'Demand (kWh)': (demand.isel(years=year, scenarios=scenario).values) / 1000}
                data['Total Renewable Production (kWh)'] = res_production.isel(scenarios=scenario).sel(steps=step).sum('renewable_sources').values / 1000
                data[f'Curtailment (kWh)'] = curtailment.isel(scenarios=scenario).sel(years=year + start_year).sum('renewable_sources').values / 1000 if curtailment is not None else 0
                data['Battery Outflow (kWh)'] = (battery_outflow.isel(scenarios=scenario).sel(years=year + start_year).values) / 1000 if battery_outflow is not None else None
                data['Battery Inflow (kWh)'] = (battery_inflow.isel(scenarios=scenario).sel(years=year + start_year).values) / 1000 if battery_inflow is not None else None
                data['Battery State of Charge (%)'] = ((state_of_charge.isel(scenarios=scenario).sel(years=year + start_year).values)) / (battery_units.sel(steps=step).values * battery_nominal_capacity.values) * 100 if state_of_charge is not None else None
                data['Generator Production (kWh)'] = generator_production.isel(scenarios=scenario).sel(years=year + start_year).sum('generator_types').values / 1000 if generator_production is not None else None

                df = pd.DataFrame(data)
                df = df.round(2)  # Round all numerical values to 2 decimal places
                df.to_excel(writer, sheet_name=f'Year {year + 1}', index=False)
        print(f"Results saved to {filepath}")



if __name__ == "__main__":
    # Load project parameters
    yaml_filepath = PathManager.DEFAULT_YAML_FILE_PATH
    settings = ProjectParameters.instantiate_from_yaml(yaml_filepath)
    print("Project parameters loaded successfully.")

    # Initialize and solve the model
    model = Model(settings)
    
    model.solve(solver="gurobi")

    # Print solution results
    print_solution_results(model)
    plot_energy_balance(model, scenario=0, year=0, day=0)

    # Save results to Excel
    excel_filepath = PathManager.RESULTS_FOLDER_PATH
    save_results_to_excel(model, excel_filepath)
