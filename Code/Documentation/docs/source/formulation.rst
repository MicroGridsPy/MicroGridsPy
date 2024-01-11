#######################################
Mathematical Formulation
#######################################


**Two-stage optimization mixed integer linear programming sizing model**

The considered system comprises an electrical load supplied by renewable sources, an inverter, a battery bank and backup generators (Fig. 1). The main optimization variables are divided into first-stage variables (rated capacities of each energy source) and second-stage variables (energy flows from the different components). The optimization is implemented in Python using Pyomo Library. 

.. image:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Minigrid%20components.jpg?raw=true
   :width: 500
   :align: center


----------------------------------------------------------------------------------------------------


Objective function
=======================
 
The choice of the objective function is guided by the **"Optimization_Goal"** parameter, which allows users to specify the primary focus of the optimization process as well as the **Multiobjective** parameter that introduces a multi-objective optimization option to the model adding CO2 emissions of generation technologies to the already existing NPC objective function.

* **Net Present Cost (NPC) Minimization** ("Optimization_Goal" = 1): When the "Optimization_Goal" parameter is set to 1, the optimization model prioritizes 
  the minimization of the Net Present Cost. The NPC is a comprehensive measure that represents the total cost of the microgrid over its entire lifespan, 
  discounted to the present value. This includes initial capital investments, operation and maintenance costs, fuel costs, and any other expenses, minus 
  the salvage value at the end of the microgrid's life. By minimizing the NPC, the model ensures that the microgrid is not only economically viable but 
  also cost-effective in the long term, making it an essential consideration for investors and policymakers focusing on financial sustainability.

* **Total Variable Cost (TVC) Minimization** ("Optimization_Goal" = 2): If the "Optimization_Goal" is set to 2, the model's objective shifts to minimizing 
  the Total Variable Cost. TVC encompasses all costs that vary directly with the level of energy production or consumption. This typically includes the 
  costs of operating and maintaining energy production facilities, the cost of fuel for generators, and any other costs that are not fixed. Minimizing TVC 
  is particularly important for the operational budgeting and planning of a microgrid, as it directly impacts the cost-effectiveness of its day-to-day 
  operations.

* **CO2 Emissions Minimization** (Multi-objective Optimization): In scenarios where environmental sustainability is as important as economic viability, the 
  MicroGridspy model can be set to perform multi-objective optimization. This approach includes minimizing CO2 emissions as one of the objectives, 
  reflecting the need to reduce the environmental impact of energy production. Minimizing CO2 emissions is aligned with global efforts to combat climate 
  change and is particularly relevant for projects that aim to meet certain environmental standards or qualifications for green funding.

The flexibility in choosing the objective function allows MicroGridspy to be adapted to a wide range of scenarios and policy goals, ensuring that the microgrid design is optimized not just for cost or environmental impact, but for the specific priorities of the project at hand.

Net Present Cost (NPC)
------------------------

The objective function for minimizing the Net Present Cost (NPC) is defined as the weighted sum of the scenario-specific NPC. This function aims to minimize the total cost of the microgrid over its lifecycle, accounting for the time value of money. It captures the comprehensive cost of the microgrid for a given scenario, including investment, operational costs, and salvage value.

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

    \text{NPC}(s) = \text{Investment Cost}(s) + \text{TVC}_{\text{Act}}(s) - \text{Salvage Value}


.. raw:: html

    </div>
    </div>

Total Variable Cost
----------------------

The Total Variable Cost (TVC) is a sum of the weighted scenario-specific variable costs. It reflects the operational expenses that fluctuate with the energy output.

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

    \text{TVC} = \sum_{s \in \text{Scenarios}} (\text{TVC}_{\text{NonAct}}(s) \times \text{Scenario Weight}(s))

.. raw:: html

    </div>
    </div>

Total CO2 emissions
--------------------

The total CO2 emissions are calculated as the sum of the weighted scenario-specific emissions. This equation is relevant for environmental impact assessments.

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

    \text{CO2 emissions} = \sum_{s \in \text{Scenarios}} (\text{CO2 emission}(s) \times \text{Scenario Weight}(s))

.. math::

    \text{CO2 emissions}(s) = 
    \begin{cases}
    \text{RES emission} + \text{GEN emission} + \text{BESS emission} + \text{FUEL emission}(s) + \text{GRID emission}(s), & \text{if Model_Components} = 0 \\
    \text{RES emission} + \text{BESS emission} + \text{GRID emission}(s), & \text{if Model_Components} = 1 \\
    \text{RES emission} + \text{GEN emission} + \text{FUEL emission}(s) + \text{GRID emission}(s), & \text{if Model_Components} = 2 \\
    \end{cases}

.. raw:: html

    </div>
    </div>


----------------------------------------------------------------------------------------------------------------

Cost
======

The cost constraints are associated with the financial aspects of planning, implementing, and operating a mini-grid. These involve various factors that can impact the overall cost-effectiveness of the mini-grid, potentially affecting its feasibility, sustainability, and affordability. 

Investment
--------------------

- **National Grid**

.. raw:: html

.. math::

   \text{Investment Cost}_{\text{GRID}} = \frac {\text{Specific Investment Cost}_{\text{GRID}} \times \text{Distance}_{\text{GRID}}}
    {(1+d)^{\text{yt}_{\text{GRID connection}}-1}}

.. raw:: html



Fixed Costs
--------------------

- **National Grid**
O&M fixed - Fixed costs for power line and transformer maintenance

.. raw:: html

.. math::

   \text{O&M fixed}_{\text{GRID}} = \sum_{yt = {\text{yt}_{\text{GRID connection}}}} \frac {\text{Specific Investment Cost}_{\text{GRID}} \times 
   \text{Distance}_{\text{GRID}} \times x_{\text{O&M}}}{(1+d)^{\text{yt}}}

.. raw:: html


Variable Costs 
--------------------

- **National Grid**
O&M variable - related to the energy purchased from the grid

.. raw:: html

.. math::

   \text{O&M variable}_{\text{GRID}} = \sum_{yt}\sum_{t} \frac {E_{\text{from GRID}}(s,yt,t) \times Price_{\text{purchased}}}{(1+d)^{\text{yt}}}

.. raw:: html

Revenue - related to the energy sold to the grid

.. raw:: html

.. math::

   \text{Revenue}_{\text{GRID}} = \sum_{yt}\sum_{t} \frac {E_{\text{to GRID}}(s,yt,t) \times Price_{\text{sold}}}{(1+d)^{\text{yt}}}

.. raw:: html



- **Battery replacement**
When it comes to replacing the Battery Energy Storage System (BESS), the calculation is based on data provided by the battery manufacturer regarding the number of charge-discharge cycles the battery can handle before reaching the end of its useful life. This cycle life data, in combination with the investment cost, is used to determine when the battery should be replaced. The battery's capacity is assumed to remain constant, as the model doesn't consider capacity degradation. Therefore, the replacement is solely based on the number of completed cycles. With each cycle, a portion of the initial investment cost is added to the overall project cost, ensuring that the cost of replacing the battery is covered by the time it reaches its End of Life (EOL). The investment cost mentioned above doens't account for the cost of the electronics.

.. raw:: html

  <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

    \text{Replacement}_{\text{BESS}}(s) = \sum_{yt} \sum_{t} [(E_{\text{BESS charge}}(s,yt,t) \times \text{U}_{\text{Replacement}}) +
    (E_{\text{BESS discharge}}(s,yt,t) \times \text{U}_{\text{Replacement}})]

.. math::

     \text{U}_{\text{Replacement}} = \frac{\text{Specific Investment Cost}_{\text{BESS}} - \text{Specific Investment Cost}_{\text{BESS electronics}}}
        {2*Cycles*DOD} 

.. raw:: html

    </div>
    </div>


Salvage Value
--------------------

The Salvage Value calculation in MicroGridsPy plays a crucial role in the financial analysis of mini-grid projects. It accounts for the remaining value of key components like renewable energy sources, generators, and grid connections at the project's end.

**Calculation Steps**

1. **Identifying Upgrades and Lifespan**

   The model tracks the timing of upgrades throughout the project's lifespan using `upgrade_years_list` and calculates the time intervals between these upgrades based on `s_dur` (Step Duration).

2. **Component-wise Salvage Value Calculation**

   Salvage value for each component is computed considering their initial cost, operational life, and remaining value at the project's end.

   - **Renewable Sources (SV_Ren)**

     .. raw:: html

        <div class="equation-container">
        <div class="scrollable-equation">

     .. math::
        SV_{\text{Ren}} = \sum (\text{RES Units} \times \text{RES Nominal Capacity} \times \text{RES Specific Investment Cost} \times \frac{\text{RES Lifetime} - \text{Years}}{\text{RES Lifetime}}) \times \frac{1}{(1 + \text{Discount Rate})^{\text{Years}}}

     .. raw:: html

        </div>
        </div>

   - **Generators (SV_Gen)**

     .. raw:: html

        <div class="equation-container">
        <div class="scrollable-equation">

     .. math::
        SV_{\text{Gen}} = \sum (\text{Generator Nominal Capacity} \times \text{Generator Specific Investment Cost} \times \frac{\text{Generator Lifetime} - \text{Years}}{\text{Generator Lifetime}}) \times \frac{1}{(1 + \text{Discount Rate})^{\text{Years}}}

     .. raw:: html

        </div>
        </div>

   - **Grid Connection (SV_Grid)**

     .. math::
        SV_{\text{Grid}} = \frac{\text{Grid Distance} \times \text{Grid Connection Cost} \times \text{Grid Connection}}{(1 + \text{Discount Rate})^{\text{Years - Year Grid Connection}}}


3. **Total Salvage Value**

   The total salvage value is the sum of the salvage values of all components, which is used to refine the overall project cost.

.. warning::
   The calculation of battery salvage value is currently a work in progress within the model. Accurately modeling battery salvage value requires a detailed understanding of battery


-----------------------------------------------------------------------------------------------------------------

Energy
========

Limitations or challenges associated with the availability, generation, storage, and distribution of energy within the mini-grid power system can impact the reliability, efficiency, and overall performance of the system. Thus, energy constraints are introduced to represent a more realistic system operation accounting for these factors in the energy model. 


Energy Balance
--------------------

The energy balance of the system is ensured by the following equation. This considers that the energy demand must be meet by energy provided by the RES, generators and BESS while accouting for Lost Load and curtailment, which is the excess energy that can't be stored or consumed.

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

    E_{\text{demand}}(s,yt,t) = 
    \sum_{r} E_{\text{RES}}(s,r,yt,t) + 
    \sum_{g} E_{\text{GEN}}(s,g,yt,t) + E_{\text{from GRID}}(s,yt,t) -
    E_{\text{to GRID}}(s,yt,t) + E_{\text{BESS charge}}(s,yt,t) - 
    E_{\text{BESS discharge}}(s,yt,t) +
    \text{Lost Load}(s,yt,t) - E_{\text{curtailment}}(s,yt,t)

.. raw:: html

    </div>
    </div>


Renewable Sources
--------------------

The total energy delivered by the RES generation system is estimated based on the inverter efficiency, the unitary energy production and the total installed units for each RES technology.

.. raw:: html

.. math::

    E_{\text{RES}}(s,yt,r,t) = E_{\text{unit_RES}}(s,r,t) \times \eta_{\text{inverter}}(r) \times Units_{\text{RES}}(ut,r)

.. raw:: html


Renewable penetration ({I\_{RES}}) refers to the extent to which renewable energy sources contribute to the overall energy mix. The related constrainted allows to impose a minimum percentage of energy to be produced by non-dispatchable energy sources. 

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

   \sum_{s}(\sum_{r}\sum_{yt}\sum_{t}  E_{\text{RES}}(s,yt,r,t) \times Scenario_Weight(s)) \times (1-I_{\text{RES}}) \geq 
   \sum_{s}(\sum_{g}\sum_{yt}\sum_{t}  E_{\text{generator}}(s,yt,g,t) \times Scenario_Weight(s)) \times I_{\text{RES}}
.. raw:: html

    </div>
    </div>

Battery Bank
-----------------------

The operation of the BESS is modelled with simple and straightforward model with low complexity. This model relies on both analytical and empirical approaches to estimate the State of Charge (SOC) of the battery based on how energy flows in and out. Importantly, this battery model doesn't account for the battery's degradation over time.

.. raw:: html

.. math::

    SOC(s,yt,t) = 
    SOC(s,yt,t-1) + 
    E_{\text{BESS charge}}(s,yt,t) \times \eta_{\text{BESS charge}} -
    \frac{E_{\text{BESS discharge}}(s,yt,t)}{\eta_{\text{BESS discharge}}}

.. raw:: html

The operational SOC range is constrainted in the model for a better and more realistic BESS operation. The SOC can vary between a maximum value when the battery is fully charged and a minimum value when the battery discharges its share of usable capacity (DOD). Therefore, the SOC can vary between 100% and (1-DOD)%.


.. raw:: html

.. math::

    Units_{\text{BESS}}(ut) \times C_{\text{BESS}} \times (1 - DOD) \leq SOC(s,yt,t) \leq Units_{\text{BESS}}(ut) \times C_{\text{BESS}}

.. raw:: html


The maximum BESS power when charging or discharging is also constrainted into the model assuming a maximum time for charging or discharging the BESS constinuously. While the maximum energy exchange is directly related to the maximum power value.


.. raw:: html

.. math::

    P_{\text{BESS}}(ut) = \frac{Units_{\text{BESS}}(ut) \times C_{\text{BESS}}}{time_{\text{max}}}

.. math::

    E_{\text{BESS}}(s,yt,t) \leq P_{\text{BESS}}(ut) \times \Delta t

.. raw:: html


battery min capacity (add)


.. raw:: html

.. math::

    Units_{\text{BESS}}(ut) \times C_{\text{BESS}} \geq min_cap

.. raw:: html


Diesel Generator
--------------------

In MicroGridsPy, the diesel generator is modeled with a straightforward approach, allowing for operational flexibility within its capacity limits. The generator can function across a range of outputs, from 0 to 100% of its capacity, adapting to the varying energy demands of the mini-grid system. This flexibility is crucial for ensuring the reliability of power supply, especially in scenarios where renewable energy sources are intermittent or insufficient.

**Operational Constraints**

The operational constraints of the diesel generator are formulated to ensure that its energy production at any given time does not exceed its nominal capacity and to meet the energy demands efficiently.

1. **Maximum Generator Energy Constraint:**

   The energy production of the generator at any given time is limited by its nominal capacity. This constraint is crucial for preventing the generator from operating beyond its designed capacity, thereby ensuring safety and longevity.

   .. math::
      E_{\text{GEN}}(s,yt,g,t) \leq C_{\text{GEN}}(g) \times \text{Units}_{\text{GEN}}(ut,g) \times \Delta t

2. **Demand Fulfillment Constraint:**

   The generator’s output is also constrained to be less than or equal to the energy demand at each time step, ensuring that it only produces the necessary amount of energy required by the system.

   .. math::
      E_{\text{GEN}}(s,yt,g,t) \leq \text{Energy Demand}_{s,yt,t} \times \Delta t

3. **Minimum Step Capacity Constraint:**

   For successive investment steps, the model ensures that the nominal capacity of the generator does not decrease. This constraint maintains or increases the generator's capacity over time, supporting the system's scalability.

   .. math::
      \text{if } ut > 1: C_{\text{GEN}}(ut,g) \geq C_{\text{GEN}}(ut-1,g)
   
   .. math::
      \text{if } ut = 1: C_{\text{GEN}}(ut,g) = C_{\text{GEN}}(ut,g)

.. note::
    The model provides the option to activate an advanced feature for simulating the efficiency of the generator at partial loads. This feature, which is explained in detail in the :ref:`advanced` section of the documentation, allows for a more accurate representation of the generator's performance under varying load conditions.


Lost Load
--------------------

The fraction of lost load should be equal or less than the input value parameter in the model.

.. raw:: html

.. math::

    \text{Lost_Load_Fraction} \geq \frac{\sum_{t} Lost Load (s,yt,t)}{\sum_{t} E_{\text{demand}}(s,yt,t)}

.. raw:: html

Emissions
===================

Calculation of CO2 emissions related to each component of the system.

RES
--------------------

Related to the installed capacity for RES generation system.

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

   \text{RES emission} = \sum_{r}(\text{CO2 emission}_{\text{RES}}(r) \times \text{Units}_{\text{RES}}(1,r) \times \text{C}_{\text{RES}}(r)) +
    \sum_{r}\sum_{ut}(\text{CO2 emission}_{\text{RES}}(r) \times (\text{Units}_{\text{RES}}(ut,r) - \text{Units}_{\text{RES}}(ut-1,r)) 
    \times \text{C}_{\text{RES}}(r)) 

.. raw:: html

    </div>
    </div>

Battery Bank
--------------------

.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

   \text{BESS emission} = (\text{CO2 emission}_{\text{BESS}} \times \text{Units}_{\text{BESS}}(1) \times \text{C}_{\text{BESS}}) +
    \sum_{ut}(\text{CO2 emission}_{\text{BESS}} \times (\text{Units}_{\text{BESS}}(ut) - \text{Units}_{\text{BESS}}(ut-1)) 
    \times \text{C}_{\text{BESS}}) 

.. raw:: html

    </div>
    </div>


Diesel Generator
--------------------


.. raw:: html

    <style>
    .equation-container {
        overflow-x: auto;
        width: 100%;
        display: block;
    }
    .scrollable-equation {
        white-space: nowrap;
        overflow-x: scroll;
        display: block;
    }
    </style>
    <div class="equation-container">
    <div class="scrollable-equation">

.. math::

   \text{GEN emission} = \sum_{g}(\text{CO2 emission}_{\text{GEN}}(g) \times \text{Units}_{\text{GEN}}(1,g) \times \text{C}_{\text{GEN}}(g)) +
    \sum_{g}\sum_{ut}(\text{CO2 emission}_{\text{GEN}}(g) \times (\text{Units}_{\text{GEN}}(ut,g) - \text{Units}_{\text{GEN}}(ut-1,g)) 
    \times \text{C}_{\text{GEN}}(g)) 

.. raw:: html

    </div>
    </div>


- **Fuel**

Emissions associated to consumption of fuel for the back-up generator at each model time step.


.. raw:: html

.. math::

   \text{FUEL emission}(s,yt,g,t) = \frac{\text{E}_{\text{GEN}}(s,yt,g,t)}{\text{LHV}_{\text{FUEL}}(g) \times \eta_{\text{GEN}(g)}}
    \times \text{CO2 emission}_{\text{FUEL}}(g)

.. raw:: html

National Grid
--------------------

Emissions associated to consumption of electricity from the national grid at each model time step.

.. raw:: html

.. math::

   \text{GRID emission}(s,yt,t) = \text{E}_{\text{from GRID}}(s,yt,t) \times \text{CO2 emission}_{\text{GRID}}

.. raw:: html

