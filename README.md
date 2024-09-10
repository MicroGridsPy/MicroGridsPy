# Welcome to MicroGridsPy!

![MicroGridsPy](microgridspy\gui\assets\images\model_overview.png)

**MicroGridsPy** is a modern, open-source optimization model for **energy scaling and dispatch optimization** in microgrids, specifically designed for remote locations. The model now runs using the [Linopy](https://linopy.readthedocs.io/) optimization framework, which provides fast, efficient, and scalable solutions for linear and mixed-integer programming. MicroGridsPy supports both open-source solvers like **HiGHS** and common commercial solvers, giving users a range of options for solving optimization problems.

The model features a **streamlined web interface** built using [Streamlit](https://streamlit.io/), offering a dynamic and user-friendly environment for inputting data, visualizing results, and running optimizations. **Pydantic** is used for robust data validation, ensuring data accuracy and consistency.

With **Streamlit**, users can:
- Interact with **real-time data visualizations** of the optimization process.
- Input parameters through a **responsive web interface**.
- Generate, monitor, and adjust simulation scenarios with ease.
- View **live results and graphical outputs** directly in the browser.
- Use Pydantic's validation to ensure data integrity and minimize input errors.

The goal of MicroGridsPy is to provide an open-source approach to **energy system optimization**, allowing users to design the optimal configuration for their microgrids using advanced modeling techniques.

---

## Features

MicroGridsPy is under continuous development and the latest version includes:

- **Modern Web Interface**: Built with Streamlit for interactive, real-time optimization and scenario exploration.
- **Pydantic-Based Data Validation**: Ensures accurate data entry and provides dynamic feedback to users.
- **Dynamic Data Visualization**: Real-time graphs and metrics during simulation, powered by Streamlit's rich visualization tools.
- **Linopy Optimization**: Leveraging Linopy for scalable and efficient linear/mixed-integer programming.
- **Open-Source Solver Support**: Native support for **HiGHS** as well as integration with commercial solvers.
- **Multi-Year Formulation**: Simulates long-term changes in energy demand.
- **Capacity Expansion**: Plans for future infrastructure investments.
- **Multi-Objective Optimization**: Balances between cost and environmental goals.
- **Mixed-Integer Linear Programming (MILP)**: Ensures optimal generation scheduling while accounting for complex system behavior.
- **Partial Load Generator Modeling**: Considers generator efficiency under varied loads.
- **Endogenous Load Curve Estimation**: Creates load curves based on local rural village data.
- **Endogenous RES Production Time Series**: Utilizes NASA POWER for solar and wind predictions.
- **Brownfield Feature**: Takes into account existing technologies in the field.
- **Main Grid Connectivity Simulation**: Models interactions with an existing main grid, including outages.

---

## Quick Start

Here below is a general introduction to the different steps in building and running a model:

### Time Series Data Input
Begin by providing specific data, over the lifetime of the project, about the available renewable resources and demand profiles. For sub-Saharan Africa, it is also possible to estimate these time series data **endogenously** based on editable parameters and built-in load demand archetypes.

### Configuration and Optimization Setup
Set the model’s general parameters, such as:
- The number of periods (e.g., 8760 for hourly analysis).
- The total duration of the project.
- Specific features and modes like **MILP formulation**, **Multi-Objective optimization**, **Grid connection**, etc.

Also, define the model's optimization goals and constraints, such as:
- Aiming for a minimum renewable penetration.
- Achieving a certain level of battery independence.

### Component Selection
Choose the technologies to include, such as PV panels, wind turbines, or batteries. Define their capacities and operational characteristics.

### Execution
Run the model to perform the optimization. MicroGridsPy processes the inputs through its algorithms to find the most cost-effective and efficient system setup.

### Output Analysis
Review the outputs, which include:
- The sizing of system components.
- Financial analyses like **Net Present Cost (NPC)** and **Levelized Cost of Energy (LCOE)**.
- **Dispatch plots** showing system operation over time.

---

## Contributors

MicroGridsPy has been developed within the SESAM group in the Department of Energy Engineering at Politecnico di Milano. The research activity of SESAM focuses on the use of mathematical models for the study of systems, components, and processes in the energy field and industrial ecology.

The current version of **MicroGridsPy** in linopy has been developed by **Alessandro Onori**, based on the original model created in Pyomo with contributions from other developers and the previous version listed here below:

- **Nicolò Stevanato**, Politecnico di Milano
- **Riccardo Mereu**, Politecnico di Milano
- **Emanuela Colombo**, Politecnico di Milano

### Past contributors:
- **Gianluca Pellecchia**, Politecnico di Milano
- **Ivan Sangiorgio**, Politecnico di Milano
- **Francesco Lombardi**, TU Delft
- **Giulia Guidicini**, Politecnico di Milano
- **Lorenzo Rinaldi**, Politecnico di Milano

### Based on the original model by:
- **Sergio Balderrama**, Universidad Mayor de San Simón <s.balderrama@umss.edu>
- **Sylvain Quoilin**, Université de Liège <squoilin@uliege.be>

MicroGridsPy is developed in the open on GitHub ([MicroGridsPy-SESAM](https://github.com/SESAM-Polimi/MicroGridsPy-SESAM)) and contributions are very welcome!

> **Note:** This version of MicroGridsPy is under **active development** and has not been officially released yet. It is recommended to check regularly for updates and changes in the repository.

