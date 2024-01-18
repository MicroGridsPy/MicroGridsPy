
=======================================
Introduction
=======================================

**MicroGridsPy** is a *bottom-up, open-source optimization model*, running on `Pyomo <https://pyomo.readthedocs.io/en/stable/>`_, a Python library used to model optimisation problems, whose primary goal is 
to offer an open-source approach to the issue of **energy scaling and dispatch in micro grids** in remote locations. 
It was firstly developed in 2016 by University of Liege and the code is freely available on `GitHub <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/>`_ [40]. 
The model enables the optimization of micro-grid size and its dispatch strategy, typically at *1-hour temporal resolution*, returning also as output the fixed and variable costs associated with each technology and the **Levelized Cost of Energy (LCOE)** of the system. 
It is based on Linear Programming, and it enables the choice of the installed capacities of batteries, generators, and renewable energy sources that results in the lowest Net Present Cost (NPC) or lowest Operation and Maintenance expenses (O&M) during the project's lifespan while achieving the system limitations. 

.. figure:: https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Mgpy_Scheme_2.png?raw=true
   :width: 700
   :align: center

   Visualization of the model conceptual structure

The model requires **time series of load demand** and **RES production** (both at 1-hour resolution for a year or more), and **techno-economic parameters** of technologies and project parameters. It addresses long-term load evolution, integrating tools for generating stochastic load profiles, aiding in robust investment decisions under various scenarios.

In the latest version of MicroGridsPy, these advanced features have been implemented:

* **Multi-Year Formulation**: Adapts to changes in energy demand over time, analyzing various patterns like population growth, network connections, and shifts in daily energy usage.
* **Capacity Expansion**: Strategically plans infrastructure enhancements to meet rising demand, including new generation facilities and renewable energy sources.
* **Multi-objective Optimization**: Balances costs and emissions to model scenarios with different priorities, such as environmental impact.
* **Mixed-Integer Linear Programming (MILP)**: Integrates a unit commitment approach for optimal power generation scheduling, balancing operational costs and non-linear behavior.
* **Generator Partial Load Effect Modeling**: Addresses the efficiency and operational aspects of generators under partial load conditions.
* **Endogenous Load Curve Estimation**: Uses archetypes specific to rural villages in Sub-Saharan Africa to estimate load curves.
* **Endogenous RES Production Time Series Calculation**: Leverages the `NASA POWER platform <https://power.larc.nasa.gov/api/temporal/>`_ for accurate solar and wind energy predictions.
* **Brownfield Feature**: Optimizes microgrids considering pre-existing technologies in the field.
* **Main Grid Connectivity Simulation**: Details electricity flows to and from an existing main grid, including grid availability during blackouts.

.. note::

   This project is under active development!

Table of Contents
-------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   index
   intro
   installation
   building
   running
   advanced
   example
   contributors

.. toctree::
   :maxdepth: 2
   :caption: Developers Guide

   folder
   model_structure
   formulation
   model_results

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api