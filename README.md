
MicroGridsPy - Development_Interface version
======================== 

<img src="https://user-images.githubusercontent.com/73618037/225138390-a5593e6d-6b9f-408b-ab28-60ac3a9871c8.png">

### Description

The MicroGridsPy model main objective is to provide an open-source alternative to the problem of sizing and dispatch of energy in micro-grids in isolated places. It’s written in python(pyomo) and use excel and text files as input and output data handling and visualisation.

Check out the **Documentation** for more details: https://mgpy-docs.readthedocs.io/en/latest/

Main features:
----------------

- Optimal sizing of PV panels, wind turbines, other renewable technologies, back-up genset and electrochemical storage system for least cost electricity 
  supply in rural remote areas
- Optimal dispatch from the identified supply systems
- Possibility to optimize on NPC or operation costs
- LCOE evaluation for the identified system
- Two-stage stochastic optimization
- User Interface
  
  <img align="center" src="https://github.com/AleOnori98/MicroGridsPy_Doc/blob/main/docs/source/Images/Interface.png?raw=true">

Advanced features:
----------------------

- Variable Fuel Costs
- Unit commitment of generation sources with MILP formulation
- Partal Load operation of diesel genset with MILP formulation
- Optimization at 1 minute time-step (suited for coupling with RAMP load profiles)
- Multi-year evolving load demand and multi-step capacity expansion
  
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225139304-0c1d2ee3-5f2d-4b45-8c9f-21d967883f1b.png" width="50%" height="50%">
- Possibility of optimizing grid-connected microgrids
  
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225138883-b5085bb1-6378-4743-9ce5-b81bdab8dcba.png" width="50%" height="50%">
- Two-objective optimization (minimum Net Present Cost or CO2 emissions objective functions)
  
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225139420-01a71137-c7be-4dda-a5e3-ba766f3780b4.png">
- Brownfield optimization
- Built-in load archetypes for rural users in Sub-Sahara Africa.
- Endogenous calculation of renewable energy sources production from NASA POWER

	

### Required libraries

In the current repository under the Environments branch MAC OS and Windows environment made available.
Works with Gurobi, CPLEX, cbc, glpk.

### License
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

### Getting started

The easiest way to get a working MicroGridsPy installation is to use the free conda package manager, which can install all of the four things described above in a single step. To get conda, download and install the `Anaconda <https://repo.anaconda.com/archive/>`_ distribution for your operating system (using the version for Python 3). Anaconda is a free and open-source distribution of the Python and R programming languages for data science and machine learning-related applications that aims to simplify package management and deployment. With Anaconda installed, it is possible to create a new environment (e.g. "mgp"). To create a modelling environment that already contains everything needed to run MicrogridsPy, it's suggested to download the environment from `here <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/tree/Environments>`_. After placing the mgp_win.yml file in "C:\Users\youruser", you can create and activate the new mgp environment by running the following command in the Anaconda Prompt terminal:

*conda env create -f mgp_win.yml*

*conda activate mgp*

To ensure a smooth and efficient operation of MicroGridsPy, it is crucial to properly set up the development environment. This involves creating an isolated space that contains all the necessary Python packages and their specific versions as defined in the MicroGridsPy base.yml file. Key packages include Pyomo (minimum version 6.4.3 for the HiGHS solver), Pandas, NumPy, and Matplotlib.
For code development and debugging, consider using an Integrated Development Environment (IDE) like Spyder, which is included in the created environment.


*conda activate mgp*

*spyder*

The graphical user interface (GUI) application provides a user-friendly way to define and input data for MicroGridsPy. 
Run the ``app_main.py`` file located into the **Code/User Interface** folder using the prefered IDE (e.g. Spyder) to open the interface and interact with it.


