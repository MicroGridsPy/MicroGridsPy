Overview
========

The main objective of the MicroGridsPy model is to determine the combination of installed capacities of PV (or other RES), Lion-Ion Batteries and diesel (or other-fuel) generators that makes the lowest Net Present Cost (NPC) for the lifetime of the project and accomplishes the constraints of the system. For this objective the problem is expressed as a linear programming (LP) problem.


.. image:: /images/System.png

**Fig. 1. The considered micro-grid typology: adapted from[1].**
            

The main optimisation variables are the sizes of the PV array (or other RES capacity), battery bank and diesel (or other-fuel) generator(s) that minimise the objective function and satisfy the physical, technical and economical constraints of the different elements in the micro-grid. The optimal dispatch of energy is also a result of the optimisation process. The time step of the demand load and the irradiation is, by default, 1 hour and the optimisation horizon is 1 year.

After the optimisation process finishes and the results are found, a post-processing tool is used in order to present the results and the most important parameters in an excel sheet; finally a Figure with the energy flows from the chosen days is created.

.. image:: /images/Dispatch.png

**Fig. 2. Example of a figure created by the micro-grids library.**

Reference
---------

[1] Agarwal N., Kumar A., Varun., Optimization of grid independent hybrid PV-diesel-battery system for power generation in remote villages of uttar Pradesh, india. Energy for Sustainable Development 2013; 17:210-219
