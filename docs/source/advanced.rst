=========================
Advanced Features
=========================

MicroGridsPy allows the user to choose different advanced features embedded into the model. These are designed to elevate the energy modelling by addressing evolving challenges of mini-grid system components and optimization.

Capacity Expansion
---------------------------------

In the context of a capacity expansion formulation, the model considers the option of adding more capacity to a system in a step-by-step manner over a defined time horizon. This approach is driven by the idea of strategically expanding the installed capacity of various components, such as power generation units or storage, to manage costs effectively, especially during the initial years when lower energy demand is anticipated.

The multi-year formulation is a crucial prerequisite for implementing a capacity expansion concept. This approach enables the postponement of installing certain components' capacity, such as PV modules or battery banks, to later years based on the evolution of electricity demand. This flexibility helps avoid incurring large initial capital costs. Consequently, O&M costs become proportional to the actual capacity installed and utilized each year.

.. tip::

   **Multi-Year Formulation and Capacity Expansion in the model**: This approach drops the old consideration about the yearly demand for project lifetime which was the same and equal to a typical year of consumption for the study area. For this new concept, all the model constraints are estimated at each time step (t) of every year (yt) along the mini-grid lifetime. Thus, all equations involving time-dependent variables must be thus verified at all time steps (yt,t) of the optimization horizon.
   The variables associated with component capacity are determined by decision steps (ut) within the time horizon. The user defines the number of decision steps, essentially dividing the time horizon. This user-defined parameter governs how finely the model considers the progression of time, allowing for a strategic and step-by-step approach to capacity expansion based on the evolving electricity demand.

**Parameters**

The following table provides a detailed overview of the parameters used in the Capacity Expansion formulation.


.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter Name
     - Unit
     - Description
   * - Step Duration
     - [years]
     - Duration of each investment decision step in which the project lifetime will be split
   * - Minimum Last Step Duration
     - [years]
     - Minimum duration of the last investment decision step, in case of non-homogeneous divisions of the project lifetime

-----------------------------------------------------------------------------------------

Weighted Average Cost of Capital
---------------------------------

The financial modeling approach introduced in [1] aims to go beyond traditional energy modeling by incorporating the Weighted Average Cost of Capital (WACC) in place of the standard discount rate. The WACC represents the average cost of capital based on the project's financing structure and is defined as the minimum return that would make the investment profitable.

**Financing Mini-Grids in Africa**

The mini-grid sector in sub-Saharan Africa, although a cost-effective solution for high-tier energy services, faces challenges such as market fragmentation and perceived investment risks, leading to high capital costs. Traditional financing relies heavily on government funding with minimal private sector involvement. The immaturity of the mini-grid market in Africa is reflected by the typical structure of financing these systems. Traditional financing of power projects, including plans for off-grid electrification, usually sees the participation of the national government, through its national energy ministry or agency, as the major funder. The main source of the investment usually comes from the governmental development budget or from aided borrowing by multilateral and bilateral development agencies. In the current situation, the participation of the private sector is therefore very limited: it is involved in the stages of construction and first running of the power plant, but the property (and the associated risk of investment) is still owned by a national public utility, in most of the cases. In general, two types of financing can be employed in the mini-grid market for structuring a new investment:

* **Debt Financing**: Involves borrowing capital with the obligation of repayment at a high-interest rate, often unattractive due to high perceived risks 
  in the mini-grid market.
* **Equity Financing**: Involves investment from the developer's own capital or project promoters and is characterized by high returns on investment due to 
  the high-risk nature of mini-grid projects.

These financial parameters are used to calculate the Weighted Average Cost of Capital (WACC), including the costs of equity and debt, the corporate tax rate, and the proportions of equity and debt in the total investment.

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    V = D + E \quad (2)

.. raw:: html

    </div>


.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    L = \frac{D}{E} \quad (3)

.. raw:: html

    </div>

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    WACC = \frac{R_D \cdot (1 - t)}{1 + L} + \frac{R_E}{1 + L} \quad (4)

.. raw:: html

    </div>
    



It is worth noticing that being the leverage L in a [0; +infinite) domain, WACC varies depending on the parameters above mentioned, and can be 
qualitatively depicted as:

.. figure:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/wacc.png?raw=true
     :width: 700
     :align: center

     WACC as function of the leverage, for different values of return on equity and return on debt [1].

  
In general, the higher the equity E is invested in a project, the less risk is perceived by new lenders and the 
more the cost of borrowing external capitals can reduce over the time, pushing for an increase of D. 
Consequently, as the above graphs reflect, the WACC can be minimized by:

* Maximizing the level of equity E (i.e., minimizing L) in the case that the rate of return on debt (RD)
  discounted of taxes (t) results greater than the rate of return on equity (RE); or
* Maximizing the level of debt D (i.e., maximizing L) in the case that the rate of return on equity (RE)
  results greater than the rate of return on debt (RD) discounted of taxes (t).

Finally, it is worth mentioning that the figures of RD and RE strongly depend on the 
financing structure adopted for the project. As will be advanced in the following sections, a structure built with 
a project finance approach can help in maximizing the leverage while keeping the return on debt low, if the 
solidity of future cash flows is assumed [11].

**Parameters**

The following table provides a detailed overview of the parameters used in the WACC (Weighted Average Cost of Capital) calculation.


.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter Name
     - Unit
     - Description
   * - cost_of_equity
     - [%] (0-1)
     - Cost of equity (i.e., the return required by the equity shareholders)
   * - cost_of_debt
     - [%] (0-1)
     - Cost of debt (i.e., the interest rate)
   * - tax
     - [%] (0-1)
     - Corporate tax deduction (debt is assumed as tax deducible)
   * - equity_share
     - [%] (0-1)
     - Total level of equity as a proportion of the total capital
   * - debt_share
     - [%] (0-1)
     - Total level of debt as a proportion of the total capital

-----------------------------------------------------------------------------------------

Multi-Objective Optimization
--------------------------------
The design of a reliable and appropriate off-grid energy system is usually critical. 
The energy needs of people who are susceptible to the uncertainty of possible energy consumption evolution through time must be considered, 
taking into consideration the site-specific characteristics of each target community.

In this field, energy system models can play a pivotal role in guiding informed policy decisions trying to capture the complexities related to the 
time-evolving boundary conditions, comparing alternative energy system configurations and energy mix combinations to find the optimal solution. 
One of the challenges identified in the current state-of-the-art microgrid optimal sizing tools is that the Net Present Cost alone is not a sufficient decision parameter in energy system sizing [2]

Most optimization tools are focused on single-objective optimization that does not allow to capture the complexity of an intervention of rural electrification. 
A multi-objective two-stage stochastic approach is presented by Gou et al. [3]. The goals are to minimize the net present cost (NPC) and the pollutants emission using chance-constrained programming and a genetic algorithm as optimization techniques. 
Multi-objective optimization could be a solution to address economic, social and environmental objectives by evaluating different trade-off between these criteria, especially in the rural electrification sector where different stakeholders 
(companies, public institutions, NGOs) with different priorities are involved. This is crucial in this type of projects given the multiplicity of impacts on the community involved and the interconnection between them. 
The result of multi-objective optimization would be a Pareto frontier providing the decision maker with a more comprehensive view of the possible alternatives and allowing him to take more informed decisions. 
Exceptions to this are represented by Dufo-Lopez [4] that included a multi objective optimization on NPC, HDI and Job Creation and Petrelli [5] that optimizes on NPC, LCA emissions, Land Use and Job Creation.

**Parameters**

The following table provides a detailed overview of the parameters used in the Multi-Objective Optimization mode:

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - Multiobjective_Optimization
     - Optimization of NPC or Operation cost and CO2 emissions
     - It allows to switch between a costs-oriented optimization and a cost and emissions optimization
   * - Plot Max Cost
     - Pareto curve has to include the point at maxNPC/maxOperationCost
     - It allows to shows a specific point on the Pareto curve for multi-objective optimization
   * - Pareto points
     - [-]
     - It allows to specify the Pareto curve points to be analysed during optimization
   * - Pareto solution
     - [-]
     - It allows to specify the Multi-Objective optimization solution to be displayed

----------------------------------------------------------------------------------------------

Multi-Scenario Optimization
------------------------------

**Parameters**

The following table provides a detailed overview of the parameters used in the Multi-Scenario Optimization mode:

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - Scenarios
     - [-]
     - Number of scenarios to consider within the optimisation
   * - Scenario_Weight
     - [%] (0-1)
     - Occurrence probability of each scenario (between 0 and 1)

-------------------------------------------------------------------------


RES Time Series Estimation
-----------------------------
Renewable Energy Sources (RES) time series estimation in MicroGridsPy is an essential process for modeling and simulation of solar PV and wind turbine generation. This section outlines the key parameters and equations used for accurately estimating the energy production from these renewable sources.

**Solar PV generation**

The energy production from solar PV is influenced by various factors including the temperature on the PV cell, calculated as follows:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>
    
.. raw:: html

    <div class="equation-container">

.. math::

    T^{PV} = T^{amb} + \frac{NOCT-20}{800} \times I^{T,\beta}

.. raw:: html

    </div>


where T is the temperature NOCT is the Nominal Operating Cell Temperature, and I is the incident solar radiation.

**Wind turbine generation**

Wind turbine generation is modeled considering factors like turbine type, efficiency, and wind speed. The power output from a wind turbine, given a specific wind speed, is calculated based on the turbine's power curve.

**Parameters**

RES parameters for production time series estimation in MicroGridsPy:

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - lat
     - [-° -' -"] (e.g. 'xx xx xx')
     - latitude  [N positive, S negative]
   * - lon
     - [-° -' -"] (e.g. 'xx xx xx')
     - longitude [E positive, O negative]
   * - time_zone
     - (-) (e.g. +2)
     - UTC time zone 
   * - nom_power
     - Power (e.g. W)
     - Solar module nominal power 	
   * - tilt
     - °
     - tilt angle 
   * - azim
     - °
     - azimuth angle [0° south facing, 180° north facing]
   * - ro_ground
     - (-)
     - ground reflectivity  
   * - k_T
     - (e.g. %/°C)
     - power variation coefficient with temperature 
   * - NMOT
     - (e.g. °C)
     - Nominal Module Operating Temperature 
   * - T_NMOT
     - (e.g. °C)
     - Ambient temperature of NMOT conditions
   * - G_NMOT
     - (e.g. W/m^2)
     - Irradiance in NMOT conditions 
   * - turbine_type
     - (e.g. 'HA' or 'VA')
     - Horizontal Axis/Vertical Axis
   * - turbine_model
     - (e.g. 'NPS100c-21')
     - model name of the turbine (turbine data and power curve selected in XXX.csv)
   * - drivetrain_efficiency
     - % (0-1)
     - Average efficiency of turbine drivetrain (gearbox,generator,brake)


RES parameters which are non-editable. Advanced parameters used for developers:

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - base_URL
     - 'https://power.larc.nasa.gov/api/temporal/'
     - URL base for API 
   * - loc_id
     - 'point'
     - Spatial resolution
   * - parameters_1
     - 'ALLSKY_SFC_SW_DWN'
     - Parameters of daily data with resolution of 1° x 1°
   * - parameters_2
     - 'T2MWET, T2M, WS50M'
     - Parameters of daily data with resolution of 0.5° x 0.625°
   * - parameters_3
     - 'WS50M, WS2M,WD50M, T2M'
     - parameters of hourly data
   * - date_start
     - '20150101'
     - Starting date for dataset (from 2001)
   * - date_end
     - '20201231'
     - Ending date for dataset (until 2020)
   * - community
     - 'RE'
     - Community of data archive
   * - temp_res_1
     - 'daily'
     - Temporal resolution for daily data
   * - temp_res_2
     - 'hourly'
     - Temporal resolution for hourly data
   * - output_format
     - 'JSON'
     - Output format
   * - user
     - 'anonymous'
     - User key

-----------------------------------------------------------------------

Load Demand Estimation
------------------------
MicroGridsPy's Load Demand Estimation feature, as detailed in [12], employs a unique approach by categorizing rural energy users into specific archetypes based on factors such as location, socio-economic status, and facility type. 
For example, it differentiates between residential users, schools, and health centers, recognizing the varied energy usage patterns of each group. 
This allows for more accurate and tailored predictions of energy demand, crucial for effective planning and management of microgrids in Sub-Saharan Africa. 
The model addresses regional differences by adjusting for latitude and climate variations, ensuring relevance and adaptability to diverse rural environments.

The methodology utilizes three primary parameters: Wealth Tier, Latitude, and Number of Cooling Days, to create user archetypes for households, schools, and health centers. These archetypes consider variations in appliance usage, climate impacts on energy demand, and geographic differences. 
This approach results in 100 (5×5×4) archetypes of household users, characterized by different set of appliances (wealth parameter), seasonal variations in the time of use of the appliances (latitude parameter) and different seasonal use of ambient cooling devices (climate zone parameter). 
The methodology is adept at capturing variations in energy usage without needing extensive field surveys, making it suitable for diverse geographic and socio-economic contexts.

Five Health Facilities archetypical loads based on the kind of Health Centre and 1 archetypical load for a rural primary school. Such user classes are then used to feed the bottom-up stochastic load curve generator model RAMP and built up into the community load following:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    P_{total} = \sum_{i} N_{i,j,k} \times P_{i,j,k} + N_{health} \times P_{health} + N_{school} \times P_{school}

.. raw:: html

    </div>


where:

* P  is the total load of the designed village
* N is the number of households in wealth tier i, climate zone j and latitude k

**Parameters**

The archetypesload curves are located into the 'Demand_Archetypes' folder and the related parameters are listed below:

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter Name
     - Unit
     - Description
   * - demand_growth
     - [%]
     - Yearly expected average variation of the demand
   * - cooling_period
     - Text
     - Cooling period (NC = No Cooling; AY = All Year; OM = Oct-Mar; AS = Apr-Sept)
   * - h_tier1
     - [-]
     - Number of households in wealth tier 1
   * - h_tier2
     - [-]
     - Number of households in wealth tier 2
   * - h_tier3
     - [-]
     - Number of households in wealth tier 3
   * - h_tier4
     - [-]
     - Number of households in wealth tier 4
   * - h_tier5
     - [-]
     - Number of households in wealth tier 5
   * - schools
     - [-]
     - Number of schools
   * - hospital_1
     - [-]
     - Number of hospitals of type 1
   * - hospital_2
     - [-]
     - Number of hospitals of type 2
   * - hospital_3
     - [-]
     - Number of hospitals of type 3
   * - hospital_4
     - [-]
     - Number of hospitals of type 4
   * - hospital_5
     - [-]
     - Number of hospitals of type 5

-----------------------------------------------------------------------------------

MILP Formulation
---------------------

This section outlines the MILP formulation used in the model, which includes an integrated unit commitment approach to determine the optimal operation schedule of technologies units.

The MILP optimization variables are integers, reflecting the discrete nature of the decision-making process in committing generator units. Capacity is now a parameter, indicative of fixed attributes of the system components.

.. code-block:: python

    # Example MILP Formulation in Python
    model.Generator_Units = Var(model.steps, 
                                model.generator_types,
                                within=NonNegativeIntegers)                # Total number of generators
    model.Generator_Nominal_Capacity_milp = Param(model.generator_types,
                                                  within=NonNegativeReals)  # Capacity as a parameter

The Mixed-Integer Linear Programming (MILP) Formulation in energy system modeling is a sophisticated approach that offers a balance between computational tractability and model fidelity. 
This formulation is beneficial because it allows for the precise scheduling of discrete operational decisions, such as the commitment of generation units, which is more aligned with real-world operations. 
It can accurately approximate non-linear behaviors, such as start-up costs and minimum up/down time constraints, which are essential for representing the operational characteristics of power generation units.

However, there are trade-offs to consider. MILP problems are more complex and computationally intensive than their Linear Programming (LP) counterparts, potentially leading to longer solution times. 
This can be particularly challenging when dealing with large-scale systems or when multiple scenarios are being evaluated.
Additionally, the need for high-quality, site-specific data to characterize the operational profile of components like diesel generators can be a barrier, as this data may not always be readily available.

**Parameters**

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - Battery_Nominal_Capacity_Milp
     - Energy (e.g. Wh)
     - Nominal Capacity of each battery
   * - Generator_Nominal_Capacity_milp 
     - Power (e.g. W)
     - Nominal capacity of each generator

---------------------------------------------------------------------------


Generator Partial Load Effect
-------------------------------
In the present section, the focus is set on the generator models which often neglect decreased part-load efficiencies or minimum load constraints which can lead to significantly overestimated performance and therefore biased system planning. The model is therefore modified to consider more complex operating characteristics of a genset operating in partial load. A diesel genset optimally optimises efficiency in a fixed optimal power output. A reduction in power output results in a reduction in the efficiency. This effect has a non-linear behaviour, although diesel generators are often modelled with constant efficiency due to the limitations of the LP formulation. The MILP approach allows many ways to model these effects: a specific set of equations affecting the total operation costs of the energy produced by the generator has been implemented following the example of Balderrama et al. [6]. This formulation is relatively simple to implement, as it does not disrupt the structure of the entire model in terms of equations, it requires few parameters with an advantage in terms of computational effort, but it is closely linked to costs and not directly to the efficiency value leading to some limitations in case of null operation cost. For comparison, the partial load effect formulation is compared to the original LP model. This is further explained in the following figures.

.. raw:: html

    <div style="display: flex; justify-content: center; align-items: center;">
        <img src="https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Partial%20load%201.png?raw=true" width="350" style="margin-right: 10px;"/>
        <img src="https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Partial%20Load%202.jpg?raw=true" width="350" />
    </div>



In the LP formulation, the generator can freely vary its output between 0 and 100% without any penalization for partial load. The only limitation is therefore the maximum capacity of the unit. The slope of the cost curve for the generator system (a_LP), representing the marginal cost, is calculated as shown in equation (1.1) from the price of the fuel (p_fuel), the low heating value of the fuel (〖LHV〗_(fuel ) and the efficiency of the genset (η_gen). To not exceed the generator nominal capacity C, equation (1.2) is necessary, where E(s,t) is the energy output of the genset and Δt_p the hourly timestep. Finally, the total operation cost of the generator in the period t of scenario s (Cost(s,t))is calculated with equation (1.3).

The slope of the cost curve for the generator system, representing the marginal cost, is given by:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    a_{LP} = \frac{p_{fuel}}{LHV_{fuel} \cdot \eta_{gen}} \quad (1.1)

.. raw:: html

    </div>

The constraint to prevent the generator from exceeding its nominal capacity \( C \) is given by:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    C \cdot \Delta t_p \geq E(s, t) \quad \forall s, t \quad (1.2)

.. raw:: html

    </div>

The total operation cost of the generator for a period \( t \) and scenario \( s \) is represented as:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    Cost(s, t) = E(s, t) \cdot a_{LP} \quad \forall s, t \quad (1.3)

.. raw:: html

    </div>


In an isolated system, typically a predetermined number of diesel generators are coordinated to fulfil the fluctuating energy demands. To accurately represent this scenario, as well as account for the part load effect in each generator, the optimization approach is modified to a MILP (Mixed-Integer Linear Programming) formulation. The cost, denoted as Cost and calculated using equation (1.4), considers various factors including the number of generators operating at full load (N_full), the energy output of generators operating at part load (E_part), the slope of the cost curve for part load generators (α_MILP) as defined in equation (1.5), and the origin of the cost curve for part load generators (Cost_part). In this study, the value of Cost_part is determined as a percentage (p_gen) of the total operational cost of the generator system at full load, as elaborated in equation (1.6). Lastly, the binary variable B determines whether a generator operates in part load at a given time t.

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    Cost = N_{\text{full}} \cdot C \cdot a_{LP} \cdot \Delta t_p + E_{\text{part}} \cdot a_{MILP} + Cost_{\text{part}} \cdot B \quad \forall s, t \quad (1.4)

.. raw:: html

    </div>

The slope of the cost curve for part load generators is described as follows:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    a_{MILP} = \frac{C \cdot a_{LP} \cdot \Delta t_p - Cost_{\text{part}}}{C_{\text{gen}} \cdot \Delta t_p} \quad (1.5)

.. raw:: html

    </div>

The origin of the cost curve for part load generators, represented as a percentage of full load operational costs, is given by:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    Cost_{\text{part}} = C \cdot a_{LP} \cdot p_{\text{gen}} \cdot \Delta t_p \quad (1.6)

.. raw:: html

    </div>


The minimum and maximum energy output of the generator in partial load is limited as shown in (1.7), where 𝑀𝑖𝑛𝑝𝑎𝑟𝑡 is the minimum percentage of energy output for the generator in part load. In addition, 𝑁 is the number of gensets and is determined with the last equation. It is important to note that during the MILP optimization 𝐶 is defined as a parameter and 𝑁 is the variable to optimize.

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    C \cdot \text{Min}_{\text{part}} \cdot B[s, t] \cdot \Delta t_p \leq E_{\text{part}}(s, t) \leq C \cdot B[s, t] \cdot \Delta t_p \quad \forall s, t \quad (1.7)

.. raw:: html

    </div>

The energy output of the genset, comprising full load and part load outputs, is expressed as:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>


.. raw:: html

    <div class="equation-container">

.. math::

    E[s, t] = N_{\text{full}} \cdot C \cdot \Delta t_p + E_{\text{part}} 

.. raw:: html

    </div>

The total energy output is limited by the number of gensets available:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

  
.. raw:: html

    <div class="equation-container">

.. math::

    E[s, t] \leq C \cdot N \cdot \Delta t_p \quad \forall s, t 

.. raw:: html

    </div>

**Parameters**

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - Generator_Min_output 
     - [%] (0-1)
     - Minimum percentage of energy output for the generator in part load 
   * - Generator_Nominal_Capacity_milp 
     - Power (e.g. W)
     - Nominal capacity of each generator       
   * - Generator_pgen 
     - [%] (0-1)
     - Percentage of the total operation cost of the generator system at full load 

--------------------------------------------------------------------------------------------------

Variable Fuel Cost
-----------------------------
MicroGridsPy introduces a valuable addition to model dynamic changes in fuel prices, a pivotal factor in the operational economics of mini-grid systems, especially those reliant on fossil fuels. 
Fuel costs in developing countries are notably higher due to transportation expenses and lack of infrastructure. For example, in remote areas, fuel can cost up to 20-30% more than the national average. Moreover, fuel price subsidies, often used by governments to stabilize prices, can be unpredictable and subject to sudden changes, further complicating cost projections.

This feature offers two methods to integrate fuel price variations into the model:

1. **Linear Change Model:** Set a starting fuel cost and a linear change rate for a straightforward projection of fuel costs over the project's lifespan. The change rate can be zero, indicating stable fuel prices.

2. **CSV File Import:** For more complex fuel price variations, import a CSV file with specific fuel cost values for each year of the project's timeline. 

**Parameters**

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter Name
     - Unit
     - Description
   * - Fuel_Specific_Start_Cost
     - [Currency/Unit]
     - Initial cost of fuel at the start of the project.
   * - Fuel_Specific_Cost_Rate
     - [Currency/Unit/Year]
     - Annual rate of change in fuel cost (can be zero).

The equation for the linear change in fuel cost is as follows:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    Fuel\_Cost_y = Fuel\_Cost_{\text{Start}} + y \times Fuel\_Cost_{\text{Change Rate}} 

.. raw:: html

    </div>


where \( Fuel\_Cost_y \) is the fuel cost in year \( y \), \( Fuel\_Cost_{\text{Start}} \) is the initial cost, and \( Fuel\_Cost_{\text{Change Rate}} \) is the yearly rate of change. This feature allows for enhanced flexibility and realism in financial analyses of mini-grid systems.

The integration of this feature may substantially influences the model's outcomes, particularly for operational costs, system design, and financial assessments, aligning it more closely with real-world scenarios in regions like rural Africa where fuel prices are highly volatile. This feature enhances the accuracy of operational expense estimation over the project's lifetime, crucial for effective budgeting and financial planning, and makes the model sensitive to fuel price changes, reflecting their true impact on mini-grid system costs. In terms of system design and optimization, variable fuel costs can influence the selection of technology, potentially making renewable sources more cost-effective as fuel prices rise. This may lead the model to prefer solutions with greater storage capacity or increased renewable energy integration to mitigate fuel price risks. For financial viability and investment decisions, the feature facilitates long-term financial planning by offering realistic fuel expense projections and enables comprehensive risk assessment considering fuel price volatility. Additionally, it allows for the analysis of the impact of fuel subsidies or taxes on project economics, providing valuable insights for policy-making. Overall, this feature significantly enhances MicroGridsPy's ability to simulate and evaluate energy systems under realistic economic conditions, especially in the context of rural electrification in developing countries where fuel price fluctuations are a major concern.

National Grid Connection
---------------------------

Mini-grid systems have been evolving through the years and newest generations (i.e., 3rd and 4th generation) present the possibility for connecting to the main electricity grid. The option to connect the system to the national grid is a feature embedded into the model where this can buy or sell electricity to the grid. For a realistic operation, the grid availability is also estimated based on grid power outages modelling.

**Parameters**

Parameters here govern the potential connection to the national grid, including costs, distances, pricing for energy sold to or purchased from the grid, and reliability metrics.


.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - Year_Grid_Connection 
     - (-)
     - Year at which the mini-grid is connected to the national grid (starting from 1)     
   * - Grid_Sold_El_Price 
     - (e.g. USD/kWh)
     - Price at which electricity is sold to the grid
   * - Grid_Purchased_El_Price 
     - (e.g. USD/kWh)
     - Price at which electricity is purchased from the grid 
   * - Grid_Distance 
     - (e.g. km)
     - Distance from grid connection point 
   * - Grid_Connection_Cost 
     - (e.g. USD/km)
     - Investment cost of grid connection, i.e. extension of power line + transformer costs 
   * - Grid_Maintenance_Cost 
     - (-)
     - O&M cost for maintenance of the power line and transformer as a fraction of investment cost
   * - Maximum_Grid_Power 
     - (e.g. kW)
     - Maximum active power that can be injected/withdrawn to/from the grid 
   * - Grid_Average_Number_Outages 
     - (-)
     - Average number of outages in the national grid in a year (0 to simulate ideal power grid)
   * - Grid_Average_Outage_Duration 
     - minutes
     - Average duration of an outage (0 to simulate ideal power grid)
   * - National_Grid_Specific_CO2_emissions 
     - (e.g. kgCO2/kWh)
     - Specific CO2 emissions by the considered national grid

Regarding the **energy constraint** on this component, the maximum possible energy exchange is directly related to the maximum active power that can be injected or withdrawn to or from the grid.

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    E_{\text{grid}}(s,yt,t) \leq P_{\text{max grid}} * 1000

.. raw:: html

    </div>


- **Grid Availability**

The reliability of a national grid's electricity supply refers to the consistent and uninterrupted availability of electrical power to consumers. It is influenced by factors such as effective maintenance, weather resilience, robust infrastructure, adequate capacity planning, and preparedness for natural disasters. The grid availability estimation introduced in [8] is implemented in the model. This feature allows for a better characterization of the national grid "potential". 

* **In the model**: This estimation results in a **Grid Availability.csv** which has as many numbered columns (excluding the rows labels) as the total years of the project and as many rows (excluding the columns headers) as the periods in which one year is divided (e.g. 1-hour time resolution leads to 8760 rows). These are composed of binary numbers (i.e., '0' or '1') meaning:

- When the mini-grid isn't yet grid-connected:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>


.. raw:: html

    <div class="equation-container">

.. math::

    G_{\text{yt,t}} = 0

.. raw:: html

    </div>



- After grid-connection:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>


.. raw:: html

    <div class="equation-container">

.. math::

    G_{\text{yt,t}} = 0 ; \text{if grid outage}

.. raw:: html

    </div>

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    G_{\text{yt,t}} = 1 ; \text{if grid availability}

.. raw:: html

    </div>
  


.. image:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/GRID%20availability.png?raw=true
     :width: 500
     :align: center


------------------------------------------------------------------------------------------------------------------------------------


Brownfield
----------------------

The feature for brownfield investment introduced in [8], enables the optimization of mini-grids by considering technologies that were previously installed by others in the field. The model can now factor in existing components from previous installations when determining the most efficient and effective way to optimize the microgrid.

.. tip::

   **In the model**: Regarding the constrainst related to **energy production** of each component at the first investment decision step (ut = 1) the energy yield has to be equal or higher than the energy produced by the capacity already installed on the field. 

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    C_{\text{x}}(ut = 1) \geq C_{\text{x}}(inst)

.. raw:: html

    </div>

Some of the related system **cost** such as the investment for RES, battery bank and back-up generators and salvage value for RES and back-up generators, also suffer a slight modification so the already existing units aren't accounted in these calculation. Thus, at the cost of each technology at the first investment decision step is equal to the investment cost due to the total capacity installed in the first step minus the investment cost of the capacity already connected to the microgrid. In the equation shown previously the units section is changed into:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

    Units_{\text{x}}(ut = 1) - Units_{\text{x}}(inst)

.. raw:: html

    </div>

**Parameters**

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - RES_capacity
     - Power (e.g. W)
     - Existing RES nominal capacity
   * - RES_years
     - [years]
     - How many years ago the component was installed 
   * - Battery_capacity
     - Energy (e.g. Wh)
     - Existing Battery capacity
   * - Generator_capacity 
     - Power (e.g. W)
     - Existing Generator capacity
   * - GEN_years 
     - [years]
     - How many years ago the component was installed 


Battery Bank Degradation 
----------------------------

.. warning::

    The following functionalities regarding Battery Bank Degradation are currently a work in progress and not yet fully implemented in the model.


The battery performance isn’t constant over time due to capacity and power fade as the battery is exposed to degradation processes while in both operation and storage mode. Calendar aging results from the degradation while the battery is in storage mode. Whereas cycle aging corresponds to the degradation caused by cyclic operation. The capacity fade refers to the reduction of available capacity. The battery status is provided by the State of Health (SOH) indicator. When the SOH reaches a certain threshold, the battery reached its End of Life (EOL). Temperature, State of Charge (SOC) and Depth of Discharge (DOD), are just some of the stress factors leading to degradation.

.. raw:: html

    <div style="display: flex; justify-content: center; align-items: center;">
        <img src="https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/SOH_temperature.png?raw=true" width="350" style="margin-right: 10px;"/>
        <img src="https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/SOH_DOD.png?raw=true" width="350" />
    </div>


Understanding and estimating the battery behaviour and related parameters during operation is key to improving capacity usage and cycling techniques, and, hence, inform battery modelling accordingly. A complete battery modelling is based on the estimation of operating conditions (i.e., SOC) and the estimation of battery lifetime expectancy (i.e., SOH) at any given moment of battery operation and lifetime. Battery models can be divided into four major groups: analytical, stochastic, electrical and electrochemical models. The most basic models just portray the energy balance which simplifies the behaviour of the battery. Other models reproduce the electrical characteristics during its operation or the chemical reactions, adding more accuracy but also complexity to the methodology. To achieve a complete battery model capable of determining battery related parameters through operation and even lifetime, the aging components must be accounted for in the methodology. 

A degradation model was developed and introduced into the model to account for the battery bank capacity fade. This methodology can be applied for batteries of the following chemistries: Lithium LFP and NMC, and Lead Acid. 

.. image:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/SOH_battery_chemistry.png?raw=true
     :width: 400
     :align: center


The model has the following algorithm:

 - **1.**	For the selected battery technology, the α and β coefficients are calculated using the ambient temperature, in the time step (t), and the DOD which is a fixed value for the simulation. 
 - **2.**	The previous outputs are used in the proposed degradation model. Here, the current battery capacity is calculated. 
 - **3.**	The previous parameters are used in the next time step (t+1), so they’re updated.


* **α and β coefficients**

In initialize, the coefficients alpha and beta are firstly estimated by the following equation, where c and d are specific parameters for each chemistry:

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

   \alpha_{hour} = c_{1} \times y^{3} + c_{2} \times y^{2} + c_{3} \times y + c_{4} 

.. raw:: html

    </div>

.. raw:: html

.. math::

    y = \frac{T_{amb}}{10}

.. raw:: html


- **For Li-ion chemistry**

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

   \beta_{hour} = d_{1} \times y^{3} + d_{2} \times y^{2} + d_{3} \times y + d_{4} 

.. raw:: html

    </div>

.. raw:: html

.. math::

    y = \frac{T_{amb}}{10}

.. raw:: html



- **For Lead Acid chemistry**

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

   \beta_{hour} = d_{1} \times z^{3} + d_{2} \times z^{2} + d_{3} \times z + d_{4} 

.. raw:: html

    </div>

.. raw:: html

.. math::

    z = \frac{DOD-20}{10}

.. raw:: html



* **Current capacity**
The following function estimates the current battery bank capacity (energy constraint in the model). Based on the previous bank capacity, initial bank capacity and hourly power exchange.

.. raw:: html

    <style>
    .equation-container {
        width: 100%;
        display: block;
    }
    </style>

.. raw:: html

    <div class="equation-container">

.. math::

   E^{DB}_t = E^{DB}_{t-1} - \alpha \times E^{B} - \beta \times P^{BE}_t

.. raw:: html

    </div>


* **Results**
The **current battery bank capacity** is exported in the **time-series** for each time step.

* **Replacement**

Regarding the battery replacement, a new approach is introduced when the model accounts for degradation. The replacement principle shifts from cycle life to a SOH base. The concept is based on the replacement of the battery bank capacity, switching to a system with 100% SOH, and related substitution costs. The iterative replacement is based on the procedure conducted in [10]. This method consists of 4 steps described in the following Algorithm:


 - **1.**	The optimization model is run for the desired scenario. 

 - **2.**	The model outputs are analysed. The battery bank replacement year is chosen based on the BESS SOH time-series results. It’s preferential to replace the battery at the EOL.

 - **3.**	The iterative replacement switch is chosen in MGPy. The replacement year is the single necessary input for this procedure. The replacement occurs in the first time step of the referred year. The simulation is repeated for the same scenario (as in step 1). 


**Main considerations:**

 - **1.** The SOC is now constrained by the SOH of the bank thus overtime the SOC no longer can reach 100%
 - **2.** This has a direct impact on the energy balance of the model, and more batteries need to be installed to overcome this fade.
 - **3.** At the moment, this feature does not work with capacity expansion. When considering a battery bank, all batteries should be the same in terms of type, model, capacity and age. When adding new batteries at different investment steps can impact the performance of the bank and overall degradation of the batteries. Now the model installs all needed units at the beginning of the project. 
 - **4.** In the case of brownfield: 
        * If we consider existing battery units, the model won't install new units. With this input, the current SOH for these batteries is also considered and the degradation model will start from that specific capacity.
        * If no previous batteries are present, the model will proceed with the same methodology as the greenfield approach.
 - **5.** A option for battery bank replacement is integrated in the model when the degradation feature is activated. 


References
----------------------
.. [1] Giacomo Crevani, Castro Soares, Emanuela Colombo, “Modelling Financing Schemes for Energy System Planning: A Mini-Grid Case Study”, ECOS 2023, pp. 
       1958-1969
.. [2] B. Akbas, A.S. Kocaman, D. Nock, P.A. Trotter, Rural electrification: an overview of optimization methods, Renew. Sustain. Energy Rev., 156 (2022)
.. [3] L. Guo, W. Liu, B. Jiao, B. Hong, C. Wang, "Multi-objective stochastic optimal planning method for stand-alone microgrid system", IET Generation
       Transm Distrib, 8 (7) (2014), pp. 1263-1273
.. [4] R. Dufo-López, I.R. Cristóbal-Monreal, J.M. Yusta, Optimisation of PV-wind-diesel-battery stand-alone systems to minimise cost and maximise human 
       development index and job creation, Renew. Energy, 94 (2016), pp. 280-293
.. [5] M. Petrelli, D. Fioriti, A. Berizzi, C. Bovo, D. Poli, A novel multi-objective method with online Pareto pruning for multi-year optimization of 
       rural microgrids, Appl. Energy, 299 (2021)
.. [6] S. L. Balderrama Subieta, W. Canedo, V. Lemort, and S. Quoilin, Impact of Diesel generator limitations in the robust sizing of isolated hybrid 
       Microgrids including PV and batteries, in 30th International Conference on Efficiency, Cost, Optimization, Simulation and Environmental Impact of 
       Energy Systems, 2017
.. [7] Nicolò Stevanato, Francesco Lombardi, Giulia Guidicini, Lorenzo Rinaldi, Sergio L. Balderrama, Matija Pavičević, Sylvain Quoilin, Emanuela Colombo, 
       "Long- term sizing of rural microgrids: Accounting for load evolution through multi-step investment plan and stochastic optimization", Energy for 
       Sustainable Development 2020, 58, pp. 16-29
.. [8] Nicolò Stevanato, Gianluca Pellecchia, Ivan Sangiorgio, Diana Shendrikova, Castro Antonio Soares, Riccardo Mereu, Emanuela Colombo, "Planning third 
       generation minigrids: Multi-objective optimization and brownfield investment approaches in modelling village-scale on-grid and off-grid energy systems", 
       Renewable and Sustainable Energy Transition 2023, 3, 100053
.. [9] J.M. Bright, C.J. Smith, P.G. Taylor, R. Crook, Stochastic generation of synthetic minutely irradiance time series derived from mean hourly weather                 observation data, Solar Energy, Volume 115, 2015, pp. 229-242,
.. [10] Petrelli, M.; Fioriti, D.; Berizzi, A.; Poli, D. “Multi-Year Planning of a Rural Microgrid Considering Storage Degradation.” IEEE Transactions on Power             Systems 2021, 36, 1459–1469
.. [11] Baker R, Benoit P. How project finance can advance the clean energy transition in developing countries. 
        Oxford Institute for Energy Studies; 2022
.. [12] N. Stevanato, I. Sangiorgio, R. Mereu and E. Colombo, "Archetypes of Rural Users in Sub-Saharan Africa for Load Demand Estimation," 
        2023 IEEE PES/IAS PowerAfrica, Marrakech, Morocco, 2023, pp. 1-5, doi: 10.1109/PowerAfrica57932.2023.10363287.