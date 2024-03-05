
########################################
User Interface Walkthrough
########################################

The graphical user interface (GUI) for MicroGridsPy offers a user-friendly platform for defining and inputting data, organized into specialized pages catering to different model aspects. 
It facilitates comprehensive data input and validation, ensuring accuracy through tooltips and validation mechanisms across various input fields such as basic parameters, RES time series, and technology configurations. 
With dynamic parameter management, the interface adapts to user selections, enabling or disabling options in real-time, streamlining the input process, and enhancing decision-making through effective visualization. 
Additionally, it provides efficient run functionalities, allowing users to track progress and visualize results seamlessly, thereby optimizing the modeling process for enhanced efficiency.


Model configuration
=====================

This first section of the GUI is designed to configure the key aspects of your project's timeline and financial settings. Users can specify the total duration of the project in years and set the discount rate as a decimal to impact the actuarial considerations of the costs, 
which will influence the selection and sizing of the mini-grid technologies. 
In the *Optimization Setup*,' users can tailor essential parameters to fit project's analytical model. This includes setting the time resolution in periods per year and choosing your optimization goal between net present cost and operation cost, with the former focusing on both investment and operation costs 
and the latter on operational expenses with an option to limit capital expenditure. The *Time Resolution* field can be adjusted to impact the accuracy of the results. It requires careful consideration, especially when integrating external time series data, to ensure matching resolution. 


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/model_configuration.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Users can set constraints on the types of technologies used for backup and storage within the model. This option enables the selection among batteries and generators, batteries only, or generators only. 
This choice determines the flexibility and resilience of the power supply in the face of variable renewable energy outputs and consumption patterns.
The interface allows users to set important optimization constraints that affect the performance of the mini-grid:

- **Renewable Penetration**: This parameter sets the minimum percentage of total electricity that must come from renewable sources, ensuring that the project meets sustainability goals.
  
- **Battery Independence**: Indicates the number of days the battery storage system can power the grid without external support, which is crucial for reliability in off-grid or unstable grid scenarios.
  
- **Lost Load Fraction and Cost**: Defines the threshold for unmet demand, along with associated costs that apply only if there is a non-zero lost load. This helps to quantify the impact of shortages and prioritize reliability in the system design.


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/model_configuration_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Two solvers are (currently) available and integrated in MicroGridsPy:

- **GLPK**: The GNU Linear Programming Kit (GLPK) is an open-source solver that is suitable for solving small to medium-sized optimization problems. It is a cost-effective solution that can handle various linear optimization tasks.

- **Gurobi**: For larger and more complex problems, Gurobi is the recommended solver. It is a commercial solver known for its high performance and speed, making it ideal for academic and professional use where large-scale optimization tasks are involved. Although it requires license activation, Gurobi is free for academic use, and installation instructions can be obtained from the official Gurobi website.

**Important Note**: While GLPK is an adequate choice for many scenarios, its performance may be slower compared to commercial solvers like Gurobi, especially when dealing with large-scale or complex optimization problems. Therefore, it is recommended to consider the size and complexity of your microgrid project when choosing the solver to ensure efficient computation times and optimization results.


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/model_configuration_3.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Advanced features
====================

By clicking the *Advanced Features* button, the section offers a suite of enhanced modeling options and configurations that extend beyond basic settings.

Advanced Modeling Options:

- **Capacity Expansion**: This feature allows planning for additional capacity requirements as the project grows over time.

If capacity Expansion is activated, users can also specify:

- **Step Duration [Years]**: Users can determine the time increments for the model to evaluate capacity expansion.
- **Minimum Last Step Duration [Years]**: This sets the mandatory duration for the last expansion step, ensuring stability in the project's growth phase.
- **LP vs MILP Formulation**: Linear Programming (LP) approaches provide a simplified, continuous representation of operations, ideal for scenarios where decisions do not need to be binary. Mixed-Integer Linear Programming (MILP), however, incorporates integer variables, allowing for a unit commitment approach that can handle on/off decisions and more complex relationships, crucial for discrete decision-making processes like those found in many energy systems.

Delving into the MILP formulation of the model, additional and more advanced modeling equations could be integrated. Currently, if MILP is activated:

- **Generator Partial Load**: Allows for the inclusion of generator partial load characteristics in the model, optimizing the operation of generators according to their load profiles.

Considering the investment strategy:

- **Greenfield vs. Brownfield**: Users can select between a new site development (Greenfield) or an upgrade to existing infrastructure (Brownfield), affecting investment strategies and costs.

Grid Connection:

- **On-grid vs. Off-grid**: This determines whether the microgrid will be connected to a larger grid or operate independently.
- **Grid Availability**: Users can activate this setting if grid availability is variable and should be considered in the model.
- **Grid Connection Type**: Offers a choice between purchase-only or the ability to both purchase and sell electricity, reflecting the microgrid’s interaction with the main grid.

For financial modeling:
- **WACC Calculation**: Activating this computes the Weighted Average Cost of Capital, integrating the cost implications of both debt and equity financing into the project's financial planning.

Expanding on cost calculations:
- **Fuel Specific Cost Calculation**: This feature enables users to estimate the variable costs of fuel over time, considering both the initial cost and the rate of change.

When configuring the optimization process:
- **Multi-Objective Optimization**: This advanced feature goes beyond single-objective cost minimization by also considering emissions. It provides a mechanism for building a Pareto Curve, which represents various trade-offs between cost and emissions. Users can select the number of Pareto points to analyze, allowing them to explore the spectrum of solutions from minimizing emissions to minimizing costs. The interface also enables users to choose and display a specific solution on this curve, facilitating informed decision-making based on environmental impact and economic factors.
- **Multi-Scenario Optimization**: This allows for the evaluation of different operational scenarios within a single run, providing valuable insights into potential performance under varying conditions.

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/advanced_features.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------


Resource Assessment
====================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/res.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/res_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Load Demand Assessment
=========================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/load.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/load_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Renewables Characterization
==============================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/res_param.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/res_param_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Storage System Characterization
==================================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/battery.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Backup System Characterization
==================================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/gen.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/gen_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/gen_3.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Running the Model
==================================


.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/run.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/run_2.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

Obtaining the Results
==================================

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/run_3.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/run_4.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------------------

.. image:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Interface/run_5.png?raw=true
   :width: 700
   :align: center

---------------------------------------------------------------------