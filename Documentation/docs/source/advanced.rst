Advanced Features
=========================

MicroGridsPy allows the user to choose different advanced features embedded into the model. These are designed to elevate the energy modelling by addressing evolving challenges of mini-grid system components and optimization.

.. role:: raw-html(raw)
    :format: html

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

    <div class="equation-container">

.. math::

    L = \frac{D}{E} \quad (3)

.. raw:: html

    </div>

.. raw:: html

    <div class="equation-container">

.. math::

    WACC = \frac{R_D \cdot (1 - t)}{1 + L} + \frac{R_E}{1 + L} \quad (4)

.. raw:: html

    </div>


Multi-Objective Optimization
--------------------------------
The design of a reliable and appropriate off-grid energy system is usually critical. The energy needs of people who are susceptible to the uncertainty of possible energy consumption evolution through time must be considered, taking into consideration the site-specific characteristics of each target community.

In this field, energy system models can play a pivotal role in guiding informed policy decisions trying to capture the complexities related to the time-evolving boundary conditions, comparing alternative energy system configurations and energy mix combinations to find the optimal solution. One of the challenges identified in the current state-of-the-art microgrid optimal sizing tools is that the Net Present Cost alone is not a sufficient decision parameter in energy system sizing [2]

Most optimization tools are focused on single-objective optimization that does not allow to capture the complexity of an intervention of rural electrification. A multi-objective two-stage stochastic approach is presented by Gou et al. [3]. The goals are to minimize the net present cost (NPC) and the pollutants emission using chance-constrained programming and a genetic algorithm as optimization techniques. Multi-objective optimization could be a solution to address economic, social and environmental objectives by evaluating different trade-off between these criteria, especially in the rural electrification sector where different stakeholders (companies, public institutions, NGOs) with different priorities are involved. This is crucial in this type of projects given the multiplicity of impacts on the community involved and the interconnection between them. The result of multi-objective optimization would be a Pareto frontier providing the decision maker with a more comprehensive view of the possible alternatives and allowing him to take more informed decisions. Exceptions to this are represented by Dufo-Lopez [4] that included a multi objective optimization on NPC, HDI and Job Creation and Petrelli [5] that optimizes on NPC, LCA emissions, Land Use and Job Creation.


RES Time Series Estimation
-----------------------------
- **Solar PV generation**


temperature on the PV cell

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

- **Wind turbine generation**


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



Load Demand Estimation
------------------------

Using the advanced features integrated into MicroGridsPy which allows to use built-in archetypes referring to rural villages in Sub-Saharan Africa at different latitudes. These are composed of different types of end-users like households according to the wealth tier (i.e., from 1 to 5), hospitals with the same wealth scale and schools. The possibility for demand growth and specific cooling period are also integrated within this feature. The following parameters present in **Parameters.dat** define all the possible demand archetypes within the current model.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter name
     - Unit
     - Description
   * - demand_growth
     - % (0-1)
     - yearly expected average percentage variation of the demand [%]
   * - cooling_period
     - ('NC' = No Cooling; 'AY' = All Year etc.)
     - Cooling period 
   * - h_tier1
     - (-)
     - number of households in the wealth tier 1
   * - h_tier2
     - (-)
     - number of households in the wealth tier 2
   * - h_tier3
     - (-)
     - number of households in the wealth tier 3
   * - h_tier4
     - (-)
     - number of households in the wealth tier 4
   * - h_tier5
     - (-)
     - number of households in the wealth tier 5
   * - schools
     - (-)
     - number of schools
   * - hospital_1
     - (-)
     - number of hospitals of type 1
   * - hospital_2
     - (-)
     - number of hospitals of type 2
   * - hospital_3
     - (-)
     - number of hospitals of type 3
   * - hospital_4
     - (-)
     - number of hospitals of type 4
   * - hospital_5
     - (-)
     - number of hospitals of type 5


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

    <div class="equation-container">

.. math::

    C \cdot \Delta t_p \geq E(s, t) \quad \forall s, t \quad (1.2)

.. raw:: html

    </div>

The total operation cost of the generator for a period \( t \) and scenario \( s \) is represented as:

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

    <div class="equation-container">

.. math::

    a_{MILP} = \frac{C \cdot a_{LP} \cdot \Delta t_p - Cost_{\text{part}}}{C_{\text{gen}} \cdot \Delta t_p} \quad (1.5)

.. raw:: html

    </div>

The origin of the cost curve for part load generators, represented as a percentage of full load operational costs, is given by:

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

    <div class="equation-container">

.. math::

    E[s, t] = N_{\text{full}} \cdot C \cdot \Delta t_p + E_{\text{part}} 

.. raw:: html

    </div>

The total energy output is limited by the number of gensets available:

.. raw:: html

    <div class="equation-container">

.. math::

    E[s, t] \leq C \cdot N \cdot \Delta t_p \quad \forall s, t 

.. raw:: html

    </div>

Variable Fuel Cost
-----------------------------
MicroGridsPy introduces a valuable addition to model dynamic changes in fuel prices, a pivotal factor in the operational economics of mini-grid systems, especially those reliant on fossil fuels. 
Fuel costs in developing countries are notably higher due to transportation expenses and lack of infrastructure. For example, in remote areas, fuel can cost up to 20-30% more than the national average. Moreover, fuel price subsidies, often used by governments to stabilize prices, can be unpredictable and subject to sudden changes, further complicating cost projections.

This feature offers two methods to integrate fuel price variations into the model:

1. **Linear Change Model:** Set a starting fuel cost and a linear change rate for a straightforward projection of fuel costs over the project's lifespan. The change rate can be zero, indicating stable fuel prices.

2. **CSV File Import:** For more complex fuel price variations, import a CSV file with specific fuel cost values for each year of the project's timeline. 

**Parameters for Variable Fuel Cost**

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

.. math::

    Fuel\_Cost_y = Fuel\_Cost_{\text{Start}} + y \times Fuel\_Cost_{\text{Change Rate}}

Where \( Fuel\_Cost_y \) is the fuel cost in year \( y \), \( Fuel\_Cost_{\text{Start}} \) is the initial cost, and \( Fuel\_Cost_{\text{Change Rate}} \) is the yearly rate of change. This feature allows for enhanced flexibility and realism in financial analyses of mini-grid systems.

The integration of this feature may substantially influences the model's outcomes, particularly for operational costs, system design, and financial assessments, aligning it more closely with real-world scenarios in regions like rural Africa where fuel prices are highly volatile. This feature enhances the accuracy of operational expense estimation over the project's lifetime, crucial for effective budgeting and financial planning, and makes the model sensitive to fuel price changes, reflecting their true impact on mini-grid system costs. In terms of system design and optimization, variable fuel costs can influence the selection of technology, potentially making renewable sources more cost-effective as fuel prices rise. This may lead the model to prefer solutions with greater storage capacity or increased renewable energy integration to mitigate fuel price risks. For financial viability and investment decisions, the feature facilitates long-term financial planning by offering realistic fuel expense projections and enables comprehensive risk assessment considering fuel price volatility. Additionally, it allows for the analysis of the impact of fuel subsidies or taxes on project economics, providing valuable insights for policy-making. Overall, this feature significantly enhances MicroGridsPy's ability to simulate and evaluate energy systems under realistic economic conditions, especially in the context of rural electrification in developing countries where fuel price fluctuations are a major concern.

National Grid
----------------------

Mini-grid systems have been evolving through the years and newest generations (i.e., 3rd and 4th generation) present the possibility for connecting to the main electricity grid. The option to connect the system to the national grid is a feature embedded into the model where this can buy or sell electricity to the grid. For a realistic operation, the grid availability is also estimated based on grid power outages modelling.

- **Grid constraints**

Regarding the **energy constraint** on this component, the maximum possible energy exchange is directly related to the maximum active power that can be injected or withdrawn to or from the grid.

.. raw:: html

.. math::

    E_{\text{grid}}(s,yt,t) \leq P_{\text{max grid}} * 1000

.. raw:: html


- **Grid Availability**

The reliability of a national grid's electricity supply refers to the consistent and uninterrupted availability of electrical power to consumers. It is influenced by factors such as effective maintenance, weather resilience, robust infrastructure, adequate capacity planning, and preparedness for natural disasters. The grid availability estimation introduced in [8] is implemented in the model. This feature allows for a better characterization of the national grid "potential". 

* **In the model**: This estimation results in a **Grid Availability.csv** which has as many numbered columns (excluding the rows labels) as the total years of the project and as many rows (excluding the columns headers) as the periods in which one year is divided (e.g. 1-hour time resolution leads to 8760 rows). These are composed of binary numbers (i.e., '0' or '1') meaning:

- When the mini-grid isn't yet grid-connected:

.. raw:: html

.. math::

    G_{\text{yt,t}} = 0

.. raw:: html


- After grid-connection:


.. raw:: html

.. math::

    G_{\text{yt,t}} = 0 ; \text{if grid outage}

.. raw:: html

.. raw:: html

.. math::

    G_{\text{yt,t}} = 1 ; \text{if grid availability}

.. raw:: html


.. image:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/GRID%20availability.png?raw=true
     :width: 500
     :align: center


------------------------------------------------------------------------------------------------------------------------------------


Model formulation for Load Evolution
---------------------------------------

The approach introduced in [7] focuses on addressing the issue of load evolution in the long term. This model is designed to make informed decisions about expanding capacity throughout the specified time horizon. To simulate realistic load profiles, the model is integrated with a tool for generating stochastic load profiles. This formulation demonstrates advantages in making robust investment decisions under different load evolution scenarios.

- **Multi-Year formulation**

The system has the capability to take into account changes in energy demand over time, especially in rural areas. Each year in the planning period corresponds to a unique load curve, allowing for the analysis of various patterns. This includes factors like population growth, more connections to the network, which affect overall demand but not necessarily daily load profiles. Additionally, variations in consumption habits and the use of new appliances can cause shifts in the daily load curve. In essence, the model is flexible enough to adapt to different dynamics, considering both global demand changes and shifts in daily energy usage patterns.

* **In the model**: This introduction drops the old consideration about the yearly demand for project lifetime which was the same and equal to a typical year of consumption for the study area. For this new concept, all the model constraints are estimated at each time step (t) of every year (yt) along the mini-grid lifetime. Thus, all equations involving time-dependent variables must be thus verified at all time steps (yt,t) of the optimization horizon.

- **Capacity Expansion**

In the context of a capacity expansion formulation, the model considers the option of adding more capacity to a system in a step-by-step manner over a defined time horizon. This approach is driven by the idea of strategically expanding the installed capacity of various components, such as power generation units or storage, to manage costs effectively, especially during the initial years when lower energy demand is anticipated.

The multi-year formulation is a crucial prerequisite for implementing a capacity expansion concept. This approach enables the postponement of installing certain components' capacity, such as PV modules or battery banks, to later years based on the evolution of electricity demand. This flexibility helps avoid incurring large initial capital costs. Consequently, O&M costs become proportional to the actual capacity installed and utilized each year.

* **In the model**: In the capacity expansion formulation, the variables associated with component capacity are determined by decision steps (ut) within the time horizon. The user defines the number of decision steps, essentially dividing the time horizon. This user-defined parameter governs how finely the model considers the progression of time, allowing for a strategic and step-by-step approach to capacity expansion based on the evolving electricity demand.

Brownfield
----------------------

The feature for brownfield investment introduced in [8], enables the optimization of mini-grids by considering technologies that were previously installed by others in the field. The model can now factor in existing components from previous installations when determining the most efficient and effective way to optimize the microgrid.

* **In the model**: Regarding the constrainst related to **energy production** of each component at the first investment decision step (ut = 1) the energy yield has to be equal or higher than the energy produced by the capacity already installed on the field. 

.. raw:: html

.. math::

    C_{\text{x}}(ut = 1) \geq C_{\text{x}}(inst)

.. raw:: html

Some of the related system **cost** such as the investment for RES, battery bank and back-up generators and salvage value for RES and back-up generators, also suffer a slight modification so the already existing units aren't accounted in these calculation. Thus, at the cost of each technology at the first investment decision step is equal to the investment cost due to the total capacity installed in the first step minus the investment cost of the capacity already connected to the microgrid. In the equation shown previously the units section is changed into:

.. raw:: html

.. math::

    Units_{\text{x}}(ut = 1) - Units_{\text{x}}(inst)

.. raw:: html


Minute Resolution
----------------------
In order to capture the dynamism of energy systems, a minute resolution is applied to the model by using the periods parameter equal to 525 600 minutes/year. This allows to capture the changes in demand within each hour and corresponding RES potential. By modelling the energy system every minute, rapid changes and nuances can be captured more accurately contributing to a better optimization and  maintain system stability.

* **RES calculation** - **Solar potential**

Solar irradiance exhibits minute-to-minute variations influenced by cloud dynamics, atmospheric losses, and the transport of pollutants. These fluctuations, occurring concurrently with changes in electricity demand, impact the effectiveness of storage and self-consumption in solar power systems. Simulations integrating electricity demand, PV supply, and storage require minute-level irradiance data to capture these effects. While calibrated minute-level irradiance datasets are limited and often result from isolated research projects, hourly weather data is more readily available but fails to capture the intermittent nature of solar irradiance. The modelling approach introduced in [9], enables the estimation of minutely irradiance from hourly weather data, such as cloud amount, wind speed and surface pressure. This methodology is applied to the RES generation potential within the model allowing for a accurate minute resolution.


Battery Bank Degradation 
----------------------------

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
