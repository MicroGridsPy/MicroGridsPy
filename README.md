
MicroGridsPy 2.1
======================== 

![MicroGridsPy Logo](https://user-images.githubusercontent.com/73618037/225138390-a5593e6d-6b9f-408b-ab28-60ac3a9871c8.png)

### Description

The MicroGridsPy model main objective is to provide an open-source alternative to the problem of sizing and dispatch of energy in micro-grids in isolated places. It’s written in python(pyomo) and use excel and text files as input and output data handling and visualisation.

For more details, check out the online [Documentation](https://microgridspy-documentation.readthedocs.io/en/latest/) !

> :warning: **Warning**: For a MACOS compatible version, please refer to version 2.0. The project is under active development. 


## Main Features

- Optimal sizing of PV panels, wind turbines, other renewable technologies, back-up genset and electrochemical storage system for least cost electricity 
  supply in rural remote areas
- Optimal dispatch from the identified supply systems
- Possibility to optimize on NPC or operation costs
- LCOE evaluation for the identified system
- Two-stage stochastic optimization
- User Interface
  
![User Interface](https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Interface.png?raw=true)


## Advanced Features

MicroGridsPy 2.1 incorporates several advanced features, enhancing its versatility and effectiveness in various scenarios:

- **Variable Fuel Costs**: Adjust fuel costs dynamically based on market prices.
- **MILP Formulation for Unit Commitment**: Ensures optimal operation of generation sources.
- **Partial Load Operation of Diesel Genset**: Optimizes diesel genset operations, even under partial load, using MILP.
- **High-Resolution Optimization**: Conducts optimization at a 1-minute time-step, suitable for coupling with RAMP load profiles.
- **Evolving Load Demand & Multi-Step Capacity Expansion**: Adapts to changing load demands over multiple years.

![Load Demand and Capacity Expansion](https://user-images.githubusercontent.com/73618037/225139304-0c1d2ee3-5f2d-4b45-8c9f-21d967883f1b.png)

- **Optimization of Grid-Connected Microgrids**: Enhances the efficiency of grid-connected systems.

![Grid-Connected Microgrids](https://user-images.githubusercontent.com/73618037/225138883-b5085bb1-6378-4743-9ce5-b81bdab8dcba.png)

- **Two-Objective Optimization**: Focuses on minimizing either Net Present Cost or CO2 emissions.

![Two-Objective Optimization](https://user-images.githubusercontent.com/73618037/225139420-01a71137-c7be-4dda-a5e3-ba766f3780b4.png)

- **Brownfield Optimization**: Tailors solutions for existing infrastructure upgrades.
- **Built-In Load Archetypes**: Specifically designed for rural users in Sub-Sahara Africa.
- **NASA POWER Integration**: Utilizes NASA POWER for calculating renewable energy production.

	
### Environments and Solvers

In the current repository under the Environments branch MAC OS and Windows environments are available.
Currently, MicroGridsPy have been confirmed to work with Gurobi, and GPLK.

> :warning: While GLPK is a capable solver for many optimization problems, it may have longer operational times compared to commercial solvers like Gurobi, especially for large or complex problems. The difference can often be substantial, potentially ranging from several times to orders of magnitude faster, depending on the specifics of the problem even if it’s important to note that these are general observations, and actual performance will vary with each unique problem. It is advisable to consider this factor when choosing a solver for time-sensitive or large-scale applications.

### License
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

### Getting Started with MicroGridsPy

To install MicroGridsPy, the conda package manager is recommended. Here's the step-by-step guide:

1. **Install Anaconda**:
   - Download and install the Anaconda distribution for Python 3 from [Anaconda Archive](https://repo.anaconda.com/archive/). Anaconda simplifies package management in Python and R, especially for data science and machine learning applications.

2. **Download the MicroGridsPy Environment File**:
   - The environment file for MicroGridsPy can be found on the [MicroGridsPy/Environments SESAM GitHub repository](https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/tree/Environments). Download the file to set up your modeling environment.

3. **Create and Activate the MicroGridsPy Environment**:
   - Place the downloaded `mgpy_win.yml` file in an accessible directory (e.g., `C:\\Users\\youruser`).
   - Open Anaconda Prompt, navigate to the directory, and execute the following commands:
     ```
     conda env create -f mgpy_win.yml
     conda activate mgpy
     ```

4. **Development Environment Setup**:
   - Ensure your development environment contains necessary Python packages such as Pyomo (minimum version 6.4.3), Pandas, NumPy, and Matplotlib.

5. **Launch Spyder IDE for Development**:
   - Use Spyder for development and debugging, which is included in the Anaconda distribution. To start Spyder, run:
     ```
     conda activate mgpy
     spyder
     ```

6. **Run the GUI Application**:
   - MicroGridsPy provides a GUI for easy data input. Launch the GUI by running `app_main.py` located in the **Code/User Interface** folder using Spyder or your preferred IDE.

Follow these steps for a successful installation of MicroGridsPy.


