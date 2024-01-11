
=========================================
Energy Optimization Models
=========================================

Within the context of rural electrification, **hybrid microgrids** stand out as e one of the *most cost-effective solutions* to meet the need for access to **affordable, reliable and sustainable electricity** in areas where national grid connectivity is unfeasible, both financially and technically. They also serve to lessen *reliance on high-carbon* as well as imported energy through the exploitation of *locally available renewables (RES)* [1]. Nonetheless, the uncertainties associated with the **natural variability of RES** and the **unpredictable evolution of the electricity demand** among other factors [2] pose challenges to the technical and economic optimization and robust sizing of these systems [3].

In rural regions where access to the main power grid is limited and the cost of bringing electricity to each individual can be prohibitively high, it's crucial to use available resources wisely. This means that when planning for rural electrification, one must consider several factors that impact the effectiveness and efficiency of the project. Key considerations include determining the **appropriate size and configuration** of the system to meet local needs, **strategizing the dispatch** of electricity to maintain efficiency and reliability, selecting suitable energy generation and storage technologies based on local resources, costs, and technical capabilities, and designing a **robust and sustainable network** for electricity transmission and distribution. To address these challenges, accurate models for sizing and dispatching mini-grid systems are indispensable. There are three main types of energy optimization methods used for this purpose: intuitive, numerical, and analytical.

* The **intuitive method** is the simplest approach. It calculates the necessary system size using *daily electricity demand* values and data on available 
  resources. This method is straightforward but may not be as precise as other methods.

* The **numerical method** is more complex. It sizes the system based on *hourly demand profiles*, *energy generation profiles*, and specific system 
  parameters. This approach allows for a more nuanced understanding of how the system will operate throughout the day.

* The **analytical method** is the most sophisticated and relies on *mathematical optimization techniques* such as Linear Programming (LP) or Mixed Integer 
  Linear Programming (MILP). These mathematical models can incorporate a wide range of considerations, including cost, system reliability, and the 
  integration of sustainable technologies. They also can take into account various economic, social, and environmental constraints, ensuring that the 
  deployment of the mini-grid system is as effective and sustainable as possible.

Challenges in isolated Microgrids Modeling
============================================

Parametric uncertainty
-------------------------
The uncertainty associated with long-term demand and renewables projections is typically referred to as **parametric uncertainty**, as models are typically fed with these data in the form of *exogenous parameters*. Riva et al. [4] underscore the importance of system dynamics for *accurate forecasting*, as **underestimations** can lead to overdrawn systems where actual energy usage far exceeded initial calculations or the necessity to retrofit photovoltaic microgrids with additional generators due to higher-than-expected night-time use and expanding user bases. Fluctuations in renewable energy outputs also necessitate redesigns, as seen with wind systems affected by geographic features. These instances emphasize the critical need for precise demand and supply modeling to ensure the sustainability of off-grid power systems.

Structural uncertainty
------------------------
The mathematical modeling of microgrids faces **structural uncertainty** due to *simplifications made for computational efficiency*. Often, models use constant efficiencies or overlook technological constraints, leading to inaccurate predictions of system performance. To address non-linear behaviours within a practical timeframe, **heuristic optimization methods** like those used by Mandelli et al. [5] and the `HOMER® software <https://www.homerenergy.com/>`_   are common but may only provide local optima. **Meta-heuristic techniques** have also been successful [6], offering a balance between complexity and computation time. While **Linear programming (LP)** is popular for its ability to deterministically find global optima, it falls short in handling non-linearities. **Mixed-integer linear programming (MILP)** bridges this gap somewhat, though at a cost to computational speed and requiring high-quality data for precision.

Techniques for optimization under uncertainty
-----------------------------------------------

**Two-stage stochastic optimization** is a sophisticated technique that addresses uncertainty in microgrid design by optimizing decisions across two stages. The generic formulation of the problem aims to optimize an **objective function** subject to a **set of constraints**. This is done by determining the optimum value of the first-stage variables under the uncertainty generated by *stochastic parameters* on the second-stage scenarios. The second-stage variables are the resource actions done in each scenario to deal with the uncertainty. The two-stage stochastic framework is excellent to deal with the uncertainty in a microgrid, as shown by Zhou et al. [7] where a two-stage optimization problem is formulated to size a multi-energy distributed system. Despite its effectiveness, the literature on two-stage stochastic optimization for rural microgrids is limited, reflecting a *gap in handling uncertainties*, especially in remote areas where pre-electrification data monitoring is not feasible. 


Why MicroGridsPy is developed?
=========================================

**MicroGridsPy** is a *sophisticated and comprehensive analytical model* which provides a solution to the problem of sizing and dispatch of energy in microgrids in isolated places at a village scale with a time resolution of 1 hour and time-evolving load demand. The model is based on *two-stage stochastic optimization*, where the main optimization variables are divided into first-stage variables (rated capacities of each energy source) and second-stage variables (energy flows from the different components), to deal with the high level of uncertainty associated with renewable energy potential forecasts and the complex dynamics that govern the current and future evolution of electricity consumption in rural settings (parametric uncertainty), while LP or MILP formulation can be used to tackle the imperfect mathematical representation of component operation (structural uncertainty), mainly related to the modelling of non-linear behaviour. 

MicroGridsPy has been developed in a collaborative effort aiming at providing a **free and easy-to-access tool** for practitioners in the field of microgrids. Therefore it is released as `open-source <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM>`_ and it can also be adapted to user needs, projects characteristics and/or technical and/or economic context of each project. This **open-science approach** is also selected to increase the transparency and reproducibility of the proposed methods [8].

MicroGridsPy in academic literature
=========================================

* Sergio Balderrama, Francesco Lombardi, Fabio Riva, Walter Canedo, Emanuela Colombo, Sylvain Quoilin, *"A two-stage linear programming optimization 
  framework for isolated hybrid microgrids in a rural context: The case study of the “El Espino” community"*, Energy **2019**, 188, 116073

* Nicolò Stevanato, Francesco Lombardi, Emanuela Colombo, Sergio Balderrama, Sylvain Quoilin, *"Two-Stage Stochastic Sizing of a Rural Micro-Grid Based on 
  Stochastic Load Generation"*, **2019** IEEE Milan PowerTech, pp. 1-6

* Nicolò Stevanato, Francesco Lombardi, Giulia Guidicini, Lorenzo Rinaldi, Sergio L. Balderrama, Matija Pavičević, Sylvain Quoilin, Emanuela Colombo, 
  *"Long- term sizing of rural microgrids: Accounting for load evolution through multi-step investment plan and stochastic optimization"*, Energy for 
  Sustainable Development **2020**, 58, pp. 16-29

* Nicolò Stevanato, Gianluca Pellecchia, Ivan Sangiorgio, Diana Shendrikova, Castro Antonio Soares, Riccardo Mereu, Emanuela Colombo, *"Planning third 
  generation minigrids: Multi-objective optimization and brownfield investment approaches in modelling village-scale on-grid and off-grid energy systems"*, 
  Renewable and Sustainable Energy Transition **2023**, 3, 100053

* Giacomo Crevani, Castro Soares, Emanuela Colombo, *"Modelling Financing Schemes for Energy System Planning: A Mini-Grid Case Study"*, ECOS **2023**, pp. 
  1958-1969 

* N. Stevanato, I. Sangiorgio, R. Mereu and E. Colombo, "*Archetypes of Rural Users in Sub-Saharan Africa for Load Demand Estimation*", 
  2023 IEEE PES/IAS PowerAfrica, Marrakech, Morocco, **2023**, pp. 1-5, doi: 10.1109/PowerAfrica57932.2023.10363287.




License
========

.. image:: https://img.shields.io/badge/License-Apache_2.0-blue.svg
    :target: https://www.apache.org/licenses/


This work is licensed under `Apache 2.0 <https://www.apache.org/licenses/>`_


References
=========================================
.. [1] S. Mandelli, J. Barbieri, R. Mereu, and E. Colombo, “Off-grid systems for rural electrification in developing countries: Definitions,  
       classification and a comprehensive literature review,” Renew. Sustain. Energy Rev., vol. 58, pp. 1621–1646, 2016 
.. [2] G. C. Lazaroiu, V. Dumbrava, G. Balaban, M. Longo, and D. Zaninelli, “Stochastic optimization of microgrids with renewable and storage energy 
       systems,” EEEIC 2016 - Int. Conf. Environ. Electr. Eng., pp. 1–5, 2016
.. [3] D. E. Majewski, M. Lampe, P. Voll, and A. Bardow, “TRusT: A Two-stage Robustness Trade-off approach for the design of decentralized energy supply 
       systems,” Energy, vol. 118, pp. 590–599, 2017
.. [4] F. Riva, A. Tognollo, F. Gardumi, E. Colombo, "Long-term energy planning and demand forecast in remote areas of developing countries: classification 
       of case studies and insights from a modelling perspective", Energy strategy rev., 20 (2018), pp. 71-89
.. [5] S. Mandelli, C. Brivio, E. Colombo, M. Merlo, "A sizing methodology based on levelized cost of supplied and lost energy for off-grid rural 
       electrification systems", Renew Energy, 89 (2016), pp. 475-488
.. [6] Q. Altes Buch, M. Orosz, S. Quoilin, V. Lemort, "Rule-based control and optimization of a hybrid solar microgrid for rural electrification and heat 
       supply in sub-saharan Africa", Proceedings of the 30th international conference on efficiency, cost, optimization, simulation and environmental 
       impact of energy systems, vol. 1 (2017), pp. 1263-1273
.. [7] Z. Zhou, J. Zhang, P. Liu, Z. Li, M.C. Georgiadis, E.N. Pistikopoulos, "A two-stage stochastic programming model for the optimal design of 
       distributed energy systems", Appl Energy, 103 (2013), pp. 135-144
.. [8] S. Pfenninger, J. DeCarolis, L. Hirth, S. Quoilin, I. Staffell, "The importance of open data and software: is energy research lagging behind?", 
       Energy Policy, 101 (2017), pp. 211-215


