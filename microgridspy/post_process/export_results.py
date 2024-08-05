import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from typing import Dict

from microgridspy.model.model import Model

def save_results_to_excel(model: Model, base_filepath: Path) -> None:
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
    step_duration = model.settings.advanced_settings.step_duration
    years_steps_tuples = [(years[i], steps[i // step_duration]) for i in range(len(years))]

    for scenario in range(demand.sizes['scenarios']):
        filepath = base_filepath / f"Energy Balance - Scenario {scenario + 1}.xlsx"
        with pd.ExcelWriter(filepath) as writer:
            for year in range(len(years)):
                step = years_steps_tuples[year][1]
                data = {'Demand (kWh)': (demand.isel(years=year, scenarios=scenario).values) / 1000}
                
                # Add specific production for each renewable source
                for source in res_production.coords['renewable_sources'].values:
                    source_production = res_production.isel(scenarios=scenario).sel(steps=step, renewable_sources=source).values / 1000
                    source_curtailment = curtailment.isel(scenarios=scenario).sel(years=year + start_year, renewable_sources=source).values / 1000 if curtailment is not None else 0
                    data[f'{source} Total Production (kWh)'] = source_production
                    data[f'{source} Curtailment (kWh)'] = source_curtailment
                    data[f'{source} Actual Production (kWh)'] = source_production - source_curtailment

                data['Battery Outflow (kWh)'] = (battery_outflow.isel(scenarios=scenario).sel(years=year + start_year).values) / 1000 if battery_outflow is not None else None
                data['Battery Inflow (kWh)'] = (battery_inflow.isel(scenarios=scenario).sel(years=year + start_year).values) / 1000 if battery_inflow is not None else None
                data['Battery State of Charge (%)'] = ((state_of_charge.isel(scenarios=scenario).sel(years=year + start_year).values)) / (battery_units.sel(steps=step).values * battery_nominal_capacity.values) * 100 if state_of_charge is not None else None
                
                if generator_production is not None:
                    for gen_type in generator_production.coords['generator_types'].values:
                        data[f'{gen_type} Production (kWh)'] = generator_production.isel(scenarios=scenario).sel(years=year + start_year, generator_types=gen_type).values / 1000

                df = pd.DataFrame(data)
                df = df.round(2)  # Round all numerical values to 2 decimal places
                df.to_excel(writer, sheet_name=f'Year {year + 1}', index=False)

def save_plots(plots_filepath: Path, figures: Dict[str, plt.Figure]):
    """
    Save all plots generated in the dashboard to separate files.

    Args:
    model (Model): The model object containing all the data.
    plots_filepath (Path): The directory path where plots should be saved.
    figures (Dict[str, plt.Figure]): A dictionary containing all the generated figures.
    """

    for plot_name, fig in figures.items():
        # Clean the plot name to use as a filename
        filename = "".join(x for x in plot_name if x.isalnum() or x in [' ', '_']).rstrip()
        filename = filename.replace(' ', '_') + '.png'
        
        # Save the figure
        fig.savefig(plots_filepath / filename, dpi=300, bbox_inches='tight')
        plt.close(fig)  # Close the figure to free up memory

    print(f"All plots saved successfully to {plots_filepath}")