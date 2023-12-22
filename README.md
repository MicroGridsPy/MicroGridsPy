
MicroGridsPy - Development_MILP version
======================== 

<img src="https://user-images.githubusercontent.com/73618037/225138390-a5593e6d-6b9f-408b-ab28-60ac3a9871c8.png">

### Description

The MicroGridsPy model main objective is to provide an open-source alternative to the problem of sizing and dispatch of energy in micro-grids in isolated places. It’s written in python(pyomo) and use excel and text files as input and output data handling and visualisation.

Main features:

- Optimal sizing of PV panels, wind turbines, other renewable technologies, back-up genset and electrochemical storage system for least cost electricity supply in rural remote areas.
- Optimal dispatch from the identified supply systems.
- Possibility to optimize on NPC or operation costs.
- LCOE evaluation for the identified system.
    
Possible features:

- Two-stage stochastic optimization.
- Unit commitment of generation sources with MILP formulation.
- Partal Load operation of diesel genset with MILP formulation.
- Optimization at 1 minute time-step (suited for coupling with RAMP load profiles).
- Multi-year evolving load demand and multi-step capacity expansion.\
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225139304-0c1d2ee3-5f2d-4b45-8c9f-21d967883f1b.png" width="50%" height="50%">
- Possibility of optimizing grid-connected microgrids.\
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225138883-b5085bb1-6378-4743-9ce5-b81bdab8dcba.png" width="50%" height="50%">
- Two-objective optimization (minimum Net Present Cost or CO2 emissions objective functions). 
  <img align="center" src="https://user-images.githubusercontent.com/73618037/225139420-01a71137-c7be-4dda-a5e3-ba766f3780b4.png">

- Brownfield optimization.
- Built-in load archetypes for rural users.
- Endogenous calculation of renewable energy sources production.
	

### Required libraries

In the current repository under the Environments branch MAC OS and Windows environment made available.
Works with Gurobi, CPLEX, cbc, glpk.

### Licence
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

### Getting started

Run from the main file "Micro-Grids.py". In the folder "Inputs" all the required inputs can be provided.

