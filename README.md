MicroGridsPy - Version 2.0
========================

### Description

The MicroGridsPy model main objective is to provide an open-source alternative to the problem of sizing and dispatch of energy in micro-grids in isolated places. It’s written in python(pyomo) and use excel and text files as input and output data handling and visualisation.

Main features:

    Optimal sizing of PV panels, wind turbines, other renewable technologies, back-up genset and electrochemical storage system for least cost electricity supply in rural isolated areas.
    Optimal dispatch from the identified supply systems.
    Possibility to optimize on NPC or operation costs.
    LCOE evaluation for the identified system.
    
Possible features:

    Two-stage stochastic optimization.
    Multi-year evolving load demand and multi-step capacity expansion.
    Possibility of connecting to the national grid.
    Two-objective optimization (economic and environmental objective functions).
    Brownfield optimization.
    Built-in load archetypes for rural users.
    Endogenous calculation of renewable energy sources production.
	
 
### Required libraries

In the current repository under the Environments branch MAC OS and Windows environment made available.
Works with Gurobi, CPLEX, cbc, glpk.

### Licence
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

### Getting started

Run from the main file "Micro-Grids.py". In the folder "Inputs" all the required inputs can be provided.

