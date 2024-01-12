=========================
Model Structure
=========================

The ``Model`` directory forms the core of the MicroGridsPy application for developers. It contains a set of Python modules that together constitute the architecture of the Pyomo optimization model. Each module is specialized to handle different aspects of the optimization process. Below is a concise overview of each file within the ``Model`` folder:

- ``__pycache__``: A directory that holds the bytecode compiled Python files, which are used to speed up module loading. This directory is automatically generated and should not be altered manually.

- ``Constraints.py``: This file defines the constraints of the optimization problem, ensuring that the solutions conform to the predefined logical and mathematical rules.

- ``Demand.py``: Manages the demand simulation advanced features thorugh build-in demand archetypes.

- ``Grid_Availability.py``: This module generates the electrical grid's availability matrix, crucial for planning around periods when the grid is not operational.

- ``Initialize.py``: Prepares the initial settings and variables necessary for the model, setting the stage for the optimization process.

- ``MicroGrids.py``: Acts as the primary script for developers to run the model, invoking the necessary modules and coordinating the execution flow.

- ``Model_Creation.py``: Entrusted with assembling the model instance, defining the structural elements, and populating initial set, parameters and variables.

- ``Model_Resolution.py``: Dedicated to the resolution of the optimization model, it triggers the solver and oversees the entire solution procedure.

- ``Plots.py``: A utility module aimed at creating graphical representations of the model's outputs.

- ``RE_calculation.py``: Calculates the production of renewable energy, downloading and processing the time series data for sources like wind and solar from the NASA POWER project website. 

- ``Results.py``: Manages the formatting and storage of the model's outcomes, preparing them for analysis or reporting purposes.

- ``tmpjvcss8hv.pyomo.lp``: An intermediary file that represents the linear programming formulation of the model, useful for debugging or in-depth examination by developers.

In the forthcoming sections, we will explore in detail the functionalities and significance of each module, offering insights into their contributions to the model's optimization mechanism.

Model Creation Module
=====================

The ``Model_Creation`` module is where the MicroGridsPy's model components are defined and structured. It lays down the framework of parameters, sets, and variables, which are crucial for the optimization process.

Parameters
----------

The module begins by importing necessary Pyomo classes and initialization functions from an external ``Initialize.py`` module:

.. code-block:: python

    from pyomo.environ import Param, RangeSet, Any, NonNegativeReals, NonNegativeIntegers, Var, Set, Reals, Binary
    from Initialize import *

The ``Model_Creation`` function then initializes a series of parameters. Parameters in Pyomo are symbolic representations of values that define the characteristics of the optimization model. They can be mutable or immutable and can be indexed to represent arrays of parameters.

.. code-block:: python

    def Model_Creation(model):
        #%% PARAMETERS
        ############## 

        # RES Time Series Estimation parameters
        model.base_URL= Param(within=Any)
        model.loc_id = Param(within=Any)
        # ...
        # Several other parameters follow here

        # Project parameters
        model.Periods = Param(within=NonNegativeIntegers)
        # ...
        # Additional project parameters follow

Sets
----

After defining parameters, the module creates several sets. Sets are collections of objects, often numbers or strings, that index the model's variables and constraints. For instance, the `periods` set ranges from 1 to the number of periods in each year:

.. code-block:: python

    #%% Sets
    #########

    model.periods = RangeSet(1, model.Periods)
    # ... additional sets follow

Variables
---------

Variables represent the decision variables of the optimization problem. In this module, variables are defined for each component of the energy system, such as the units of renewable energy sources (RES), the energy production from RES, the state of charge (SOC) for batteries, and the energy produced by diesel generators.

.. code-block:: python

    #%% VARIABLES
    #############

    # Variables associated with the RES
    model.RES_Units = Var(model.steps, model.renewable_sources, within=NonNegativeReals)
    # ... additional variables follow

Example Usage
-------------

Here's an example of how a developer might utilize this module to set up an optimization model for a mini-grid:

.. code-block:: python

    from pyomo.environ import ConcreteModel
    from Model_Creation import Model_Creation

    # Create a Pyomo model instance
    model = ConcreteModel()

    # Call the Model_Creation function to set up the model
    Model_Creation(model)

    # The model is now ready to be populated with data and solved.

Insights
---------

The ``Model_Creation`` encapsulates the essence of the system being modeled, from the estimation of renewable energy production and demand to the detailed configurations of the project itself.
By structuring the model in this way, MicroGridsPy ensures that the optimization framework is robust, extendable, and maintainable. It also encapsulates complex optimization features like multi-objective optimization and MILP formulations, making it a powerful tool for energy system optimization.


Initialization Module
=====================

The ``Initialize`` module in MicroGridsPy sets the stage for the entire optimization model. It is responsible for parsing input data, initializing model parameters, defining sets, and creating the initial conditions required for the optimization process to commence.

Parsing Input Data
------------------

Input data is parsed from various CSV files and the Parameters.dat file, which include essential data such as scenarios, periods, years, and generator types.

.. code-block:: python

    # Example of parsing Scenarios, Periods, Years from Parameters.dat
    n_scenarios = int((re.findall('\d+',Data_import[i])[0]))
    n_years = int((re.findall('\d+',Data_import[i])[0]))
    n_periods = int((re.findall('\d+',Data_import[i])[0]))
    # ... and more

Initializing Parameters
-----------------------

Parameters are defined using the parsed data. These parameters serve as constants throughout the model and influence the optimization's behavior and outcomes.

.. code-block:: python

    # Example of defining parameters for Scenarios and Periods
    scenario = [i for i in range(1,n_scenarios+1)]
    period = [i for i in range(1,n_periods+1)]
    # ... and more

Defining Investment Steps
-------------------------

The module calculates the number of investment steps and assigns each year to its corresponding step. This is crucial for models that incorporate multi-year capacity expansion.

.. code-block:: python

    def Initialize_Upgrades_Number(model):
        # ... logic to determine the number of upgrades
        return int(n_upgrades)

Creating Multi-Indexed DataFrames
---------------------------------

Multi-indexed DataFrames are created for time-series data such as demand and renewable energy output. These DataFrames facilitate the handling of time-dependent data in the model.

.. code-block:: python

    # Example of creating a Multi-indexed DataFrame for Energy Demand
    frame = [scenario,year,period]
    index = pd.MultiIndex.from_product(frame, names=['scenario','year','period'])
    Energy_Demand.index = index
    # ... and more

Setting Up Initialization Functions
-----------------------------------

Initialization functions are defined for various model components such as demand, renewable energy production, and grid availability. These functions are used during the model creation phase to populate the model with data.

.. code-block:: python

    def Initialize_Demand(model, s, y, t):
        return float(Energy_Demand[0][(s,y,t)])

    # ... more initialization functions

Grid Connection and Availability
--------------------------------

The module also deals with the grid connection, including setting up parameters for grid investment costs, operation, and maintenance costs, as well as determining grid availability.

.. code-block:: python

    if Grid_Availability_Simulation:
        grid_avail(average_n_outages, average_outage_duration, n_years, year_grid_connection,n_scenarios, n_periods)
    # ... and more



The ``Initialize`` module provides a comprehensive setup for the optimization model, ensuring that all necessary data is loaded and parameters are set before the optimization begins. It acts as the preparatory stage, converting raw data into a structured format that the model can interpret and utilize. This module underscores the importance of initial conditions in the optimization process and ensures that the model's execution is based on accurate and up-to-date information.

Demand Module
=================

The ``Demand`` module is tasked with the generation of load curves for the MicroGridsPy model. It leverages a data-driven approach, utilizing predefined archetypes that reflect the energy consumption patterns of different household tiers and service structures.

Importing Data
--------------

Data importation is the first step in the load curve generation process. The module reads key parameters such as latitude, cooling periods, and household tiers from a `Parameters.dat` file. These parameters are crucial for selecting the correct archetype for demand calculation.

.. code-block:: python

    # Example of how the latitude parameter is used to determine the geographical zone archetype
    if "param: lat" in value:
        lat = (value[value.index('=')+1:value.index(';')])
        # ... rest of the code
        if  10 <= lat <=20:
            F = 'F1'
        # ... other conditions

Demand Calculation
------------------

With the parameters set, the `demand_calculation` function computes the demand for each household tier and service. It aggregates hourly loads according to the defined periods to align with the model's time resolution.

.. code-block:: python

    # Code snippet showing the aggregation of load data
    def aggregate_load(load_data, periods):
        # ... aggregation logic
        return aggregated_load

Household and Service Classes
-----------------------------

Two classes, `household` and `service`, encapsulate the logic for calculating the load demands for households and services respectively. These classes take the number of entities and their respective archetypes to output the demand.

.. code-block:: python

    class household:
        # ... class methods
        def load_demand(self, h_load):
            load = self.number/100 * h_load
            return load

    class service:
        # ... class methods

Load Profile Generation
-----------------------

The module generates a load profile for the specified number of years by combining the demand from all households and services. It accounts for annual demand growth to reflect the changes over the project's lifespan.

.. code-block:: python

    # Example of how load profiles are generated and grown annually
    for column in load_total:
        if column == 0:
            continue
        else: 
            load_total[column] = load_total[column-1]*(1+demand_growth/100)

Exporting Results
-----------------

Once the load curves are computed, the `excel_export` function exports the data to a CSV file, which will be used as input for the optimization model.

.. code-block:: python

    # Exporting the DataFrame to a CSV file
    def excel_export(load, years):
        # ... export logic

Execution
---------

The module concludes with the `demand_generation` function, which executes the demand calculation and exports the final load curves. This function also prints out the time taken to perform the calculations.

.. code-block:: python

    def demand_generation():
        # ... generation logic
        print("Load demand calculation started...")
        # ... more logic
        print('\n\nLoad demand calculation completed...')

Module Execution
----------------

The `Demand.py` module can be run as a standalone script to generate demand profiles. However, in the context of MicroGridsPy, it is typically called during the model setup phase.

Insights
--------

The demand generation process within MicroGridsPy is a sophisticated sequence that simulates realistic energy consumption patterns based on various factors. This module's output provides a crucial input for the optimization model, enabling it to make informed decisions about energy resource allocation and system design.

RES Time Series Estimation Module
=================================

Introduction
------------
The RES Time Series Estimation module is a core component of the MicroGridsPy framework. It is designed to accurately estimate solar and wind energy potential using data from NASA's POWER API. This module processes and interpolates the collected data to create a representative Typical Meteorological Year (TMY) for energy modeling.

Data Collection and URL Generation
----------------------------------
The module starts by importing necessary parameters, including geographical coordinates and technological specifications. It constructs URLs for accessing NASA's POWER API data, tailored for both daily and hourly resolutions.

.. code-block:: python

    # Sample function to create API URLs
    def URL_creation_d(Data_import):
        # Logic to construct daily and hourly data URLs
        return URL_1, URL_2

Data Processing and Interpolation
---------------------------------
After data retrieval, the module processes the JSON responses. Bilinear interpolation is applied to estimate relevant daily and hourly parameters such as temperature, wind speed, and solar irradiance.

.. code-block:: python

    # Function for data processing and interpolation
    def data_2D_interpolation(jsdata, ...):
        # Bilinear interpolation logic for daily and hourly data
        return param_daily_interp, param_hourly_interp

Typical Meteorological Year (TMY) Calculation
---------------------------------------------
One of the module's key functions is to compute a TMY, using statistical methods to select the most representative year from the historical data.

.. code-block:: python

    # Function to determine the TMY
    def typical_year_daily(param_daily, ...):
        # Statistical analysis for TMY calculation
        return best_years, param_typical_daily

RES Calculation Module
------------------------
The module calculates the potential energy supply from solar and wind resources. It includes specific algorithms to determine solar irradiation on tilted surfaces and to estimate wind turbine electricity production.

.. code-block:: python

    # Solar energy calculation function
    def hourly_solar(H_day, lat, ...):
        # Solar irradiation estimation logic

    # Wind energy production function
    def P_turb(power_curve, ...):
        # Wind turbine energy calculation logic

Data Export
-----------
The final step involves aggregating the estimated data and exporting it to CSV format for further analysis and optimization within MicroGridsPy.

.. code-block:: python

    # Function for data export
    def export(energy_PV, ...):
        # Data aggregation and export logic


Insights
----------
The `RE_calculation.py` module exemplifies the comprehensive approach of MicroGridsPy in modeling renewable energy systems. Its accurate data processing and analysis capabilities are pivotal in optimizing microgrid solutions.
