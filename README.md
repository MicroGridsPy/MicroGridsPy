A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community.
========================

### Description

The porpuse of this page is to serve as a permanent repository of the paper:

"A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community." 

This repository is divided in two sections:
	Scenario Creation 
	Optimal sizing and Dispatch (Micro-Grids)


In the folder Scenario Creation you can find the following information:

	Demand_Creation.py: It is a script to create synthetic load demands scenarios.
	PV_Creation.py: It is a script to create two solar power output scenarios.
	Power_Data_2: It is the energy flows from the microgrid "El Espino", used in PV_Creation.py and Demand_Creation.py.
	Mix_Data_2: Contains PV module temperature and solar radiation used in PV_Creation.py and Demand_Creation.py. 


The MicroGrid folder contains the scripts and information needed to reproduce the results from the paper: A two-stage linear programming optimization framework for isolated hybrid microgrids in a rural context: the case study of the “El Espino” community. In the example folder, there are folders with the information of all the instances used in the paper.

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

Favio Riva
Politecnico di milano
E-mail: fabio.riva@polimi.it

Emanuela Colombo
Politecnico di milano
E-mail: emanuela.colombo@polimi.it

Walter Canedo
Universidad Mayor de San Simon
E-mail:w.canedo@umss.edu.bo 

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

First of all Micro-Grids needs Python 3.6 install in the computer. The easiest way to obtain it, is download anaconda in order to have all the tools needed to run python scripts.

Python libraries
----------------
 
The python libraries needed to run Micro-Grids are the following:

* pyomo: Optimization object library, interface to LP solver (e.g. CPLEX)
* pandas: for input and result data handling 
* matplotlib: for plotting

Solver
------

Any of the following solvents can be used during the optimization  process in the Micro-Grids library:

* cplex

### Inputs


The Micro-grids library needs the input files are stored in the folder 'Inputs', these are the needed files:

Data.dat                         Txt file 	In this file the value of the parameters are set
Demand.xls			 Excel file	The demand of energy of the system for each period is set in this file
PV_Energy.xls			 Excel file	The energy yield in each period from one PV is set in this file,it is used for the dispatch optimization			
Renewable_Energy.xls		 Excel file	The energy yield in each period from one renewable source is set in this file, it is used for the LP and MILP optimizations	


Run Micro-Grids library
-----------------------

Once all the above steps are performed, the easiest way to run the Micro-grids library is opening the Micro-Grids.py file in an development environment like spider and run the script inside it. Another way is to open a terminal in the folder where all the scripts are and use the following command:

python Micro-Grids.py

Additional parameters can be changed in the Microgrids.py, they are in explain in the the file. The formulation can be change by changing the variable "formulation" in the Micro-Grids file. if the value is set to LP then the problem will solve with the LP formulation for the sizing problem. If the value is set to MILP then the problem is solve as a MILP formulation for the sizing problem. Finally, if the value is set to  Dispatch then the problem is solved as the  MILP formulation for the dispatch problem.

To run the instance from the paper, copy the files in the Micro-Grids/MicroGrids/Example/...... folder that you want to reproduce  in the Micro-Grids/MicroGrids/Example and then run the Micro-Grids.py script.

### Outputs


After the optimization is finish a message will appear with the Levelized cost of energy and the net present value of the system. Addional files will be created in the 'Results' folder.

Licence
=======
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It 
can be redistributed and/or modified under the terms of this license.

