A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community.
========================

### Description

The porpuse of this page is to serve as a permanent repository of the paper:

"A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community." 

This repository is diveded in two sections:
	Scenario Creation 
	Optimal sizing and mispatch (Micro-Grids)


In the folder Scenario Creation you can find the following information:

	Demand_Creation.py: It is a script to create synthetic load demands scenarios.
	PV_Creation.py: It is a script to create two solar power output scenarios.
	Power_Data_2: It is the energy flows from the microgrid "El Espino", used in PV_Creation.py and Demand_Creation.py.
	Mix_Data_2: Contains PV module temperature and solar radiation used in PV_Creation.py and Demand_Creation.py. 


The MicroGrid folder contains the scripts and information needed to reproduce the results for the paper: A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community. In the example folder, there are folders with the information of all the instances used in the paper.

Main features:

    Optimal sizing of Lion-Ion batteries, diesel generators and PV panels in order to supply a demand with the lowest cost possible.
    Optimal dispatch from different energy sources.
    Calculation of the net present cost of the system for the project lifetime.
    Determination of the LCOE for the optimal system.


### Authors

Sergio Balderrana
University of Liege, Belgium - Universidad Mayor de San Simon, Bolivia
E-mail: slbalderrama@doct.ulg.ac.be

Francesco Lombardi
Politecnico di milano
E-mail: francesco.lombardi@polimi.it

Sylvain Quoilin
University of Liege, Belgium.
E-mail: squoilin@ulg.ac.be 
 

Tutorial
========

This section is a walkthrough of how to use the Micro-Grids library in order to obtain the optimal nominal capacity for an isolated micro-grid with a given demand and PV production.

Requirements
------------

The MicroGrid library can be use in Linux or windows and needs different programs and phyton libraries in order to work. 

Python
------------

First of all Micro-Grids needs Python 3 install in the computer. The easiest way to obtain it, is download `anaconda`_ in order to have all the tools needed to run python scripts.

Python libraries
----------------
 
The python libraries needed to run Micro-Grids are the following:

* pyomo: Optimization object library, interface to LP solver (e.g. CPLEX)
* pandas: for input and result data handling 
* matplotlib: for plotting

Solver
------

Any of the fallowing solvers can be used during the optimization process in the Micro-Grids library:

* cplex

### Inputs


The Micro-grids library needs the input files are stored in the folder 'Inputs', these are the needed files:

Data.dat                         Txt file 	In this file the value of the parameters are set
Demand.xls			 Excel file	The demand of energy of the system for each period is set in this file
PV_Energy.xls			 Excel file	The energy yield in each period from one PV is set in this file				

### Data.dat file

This file has to contain all the parameters for the Micro-Grids library to be able to perform an optimization of the nominal capacity of the PV, battery bank and diesel generator. This file has to be write in AMPL data format. A table of all the parameters with an example of value and how they have to be written in the txt can be seen in the next table.

### Demand.xls file


The Demand.xls file has to have the energy demand of the system in each period of analysis. The excel file must have a column with the periods and another with the demand in W as shown in the following figure.

### PV_Energy.xls/Renewable_Energy.xls


TheV_Energy.xls/Renewable_Energy.xls file has to have the energy yield for one PV in each period of analysis. The excel file must have a column with the periods and the number of columns equal to the number of scenarios energy yield in W as shown in the following figure.

Run Micro-Grids library
-----------------------

Once all the above steps are performed, the easiest way to run the Micro-grids library is opening the Micro-Grids.py file in an development environment like spider and run the script inside it. Another way is to open a terminal in the folder where all the scripts are and use the following command:

python Micro-Grids.py

Aditional parameters can be change in the Micro-Grids.py, they are in explain in the the file. The formulation can be change by changing the variable "formulation" in the Micro-Grids file. if the value is set to LP then the problem will solve with the LP formulation for the sizing problem. If the value is set to MILP then the problem is solve as a MILP formulation for the sizing problem. Finally, if the value is set to  Dispatch then the problem is solver as the  MILP formulation for the dispatch problem.



### Outputs


After the optimization is finish a message will appear with the Levelized cost of energy and the net present value of the system. Addional files will be created in the 'Results' folder.

### Licence
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

