
===============================
Model Resolution and Results
===============================

The ``Model_Resolution`` module is an integral part of the model, designed for optimizing energy systems in mini-grid settings. It incorporates multi-year capacity expansion and a variety of energy optimization strategies within a linear programming framework.

Overview
--------

This module orchestrates the entire optimization process, encompassing the initialization of parameters, definition of constraints, and the solving of the model. It is tailored to handle complex scenarios that involve variable load demands and infrastructure expansion over a series of years.

Key Functionalities:

- **Model Initialization**: Reads configuration from the ``Parameters.dat`` file to set up the optimization model with essential parameters such as renewable penetration, battery independence, investment scenarios, and optimization objectives.

- **Constraint Handling**: Implements a variety of constraints including economic factors like net present cost, operational parameters such as energy balance, and environmental metrics like CO2 emissions.

- **Objective Function Definition**: Depending on the goal—minimizing costs or emissions, or a multi-objective optimization—the appropriate objective function is formulated within the model.

- **Solver Integration**: Configures and connects with solvers like Gurobi or HiGHS to solve the optimization problem, providing flexibility for advanced solver options.

- **Pareto Front Generation**: For multi-objective optimization scenarios, it can compute a Pareto front to visualize the trade-offs between cost and CO2 emissions.

Implementation Highlights:

- **MILP Formulations**: The module supports Mixed Integer Linear Programming (MILP), vital for discrete decision-making processes in microgrid planning.

- **Investment Options**: It differentiates between greenfield and brownfield investment scenarios, accommodating various project stages from planning to retrofitting.

- **Partial Load Modeling**: Capable of simulating partial load operations for generators, which is essential for reflecting real-world operational constraints.

- **Component Flexibility**: The module can model different microgrid components like renewable energy sources, storage systems, and conventional generators.

Initialization and Parameter Parsing
-------------------------------------

The module begins by parsing key parameters from a 'Parameters.dat' file. These parameters include aspects like renewable energy penetration, battery independence, and types of investments, among others.

.. code-block:: python

    # Example of parsing Renewable Penetration and Battery Independence
    Renewable_Penetration = ...
    Battery_Independence = ...
    # ... other parameters

Constraint Definition
---------------------

A wide array of constraints is defined, ranging from economic constraints like net present cost and CO2 emissions, to technical constraints such as energy balance and generator capacities.

.. code-block:: python

    # Defining economic constraints
    model.NetPresentCost = Constraint(rule=C.Net_Present_Cost)
    # ... additional constraints

Capacity Expansion and Renewable Integration
--------------------------------------------

The module excels in modeling capacity expansion scenarios. It facilitates the incorporation of new energy sources, storage solutions, and technological advancements over the planning period.

.. code-block:: python

    # Constraints related to capacity expansion
    model.REScapacity = Constraint(...)
    # ... more capacity-related constraints

Solver Configuration and Execution
----------------------------------

The optimization model is solved using a configured solver. The choice of solver, such as Gurobi or HiGHS, depends on user preference and specific problem requirements.

.. code-block:: python

    # Solver configuration and execution
    opt = SolverFactory('gurobi')
    results = opt.solve(instance, ...)

   
Multi-Objective Resolution
-------------------------------

The integration of multi-objective optimization within the MicroGridsPy is a sophisticated approach that allows for the balancing of different and often conflicting objectives, such as minimizing costs while also reducing CO2 emissions.
This method is essential in projects with multiple stakeholders having varying priorities, such as rural electrification projects.

#. **Objective Function Definition**: Two objectives are defined within the model: `model.f1` for the Net Present Cost (NPC) and `model.f2` for CO2 emissions. The Objective expressions for these variables are declared, setting the sense to minimize, indicating that both objectives seek minimization.
#. **Solver Configuration and Initial Calculation**: The model employs the Gurobi solver with different settings for Mixed Integer Linear Programming (MILP) formulations and others. Initial calculations are made to determine the minimum NPC and maximum CO2 emissions, and vice versa, which are crucial for understanding the range of the Pareto frontier.
#. **Epsilon Constraint Method for Pareto Frontier**: The model then uses the epsilon constraint method, a popular approach in multi-objective optimization. This method involves systematically varying one objective within its feasible range (in this case, the CO2 emission) and optimizing the other objective (NPC or Operation Cost). For each step, the model deactivates one objective and activates the other, ensuring that only one objective is optimized at a time.
#. **Plotting the Pareto Frontier**: A Pareto curve is plotted, displaying the trade-off between the two objectives. This visualization is crucial as it provides decision-makers with a clear representation of the possible outcomes and the trade-offs involved.
#. **Selection of Optimal Solutions**: The model allows the selection of specific points on the Pareto frontier based on user preference, represented by the variable `p` in the code. This flexibility is key in multi-objective optimization, as it accommodates different preferences and priorities.

.. code-block:: python

    if Optimization_Goal == 1:
        # Define the objective functions
        model.f1 = Var()
        model.C_f1 = Constraint(expr=model.f1 == model.Net_Present_Cost)
        model.ObjectiveFunction = Objective(expr=model.f1, sense=minimize)
        model.f2 = Var()
        model.C_f2 = Constraint(expr=model.f2 == model.CO2_emission)
        model.ObjectiveFunction1 = Objective(expr=model.f2, sense=minimize)

        # Example of solver options and NPC, CO2 emission calculations
        opt = SolverFactory('gurobi')
        # Solver options vary based on the problem formulation (MILP or others)
        opt.set_options('Method=3 BarHomogeneous=1 Crossover=1 MIPfocus=1 BarConvTol=1e-3 OptimalityTol=1e-3 FeasibilityTol=1e-4 TimeLimit=10000')
        instance = model.create_instance(datapath)
        opt.solve(instance, tee=True)
        NPC_min = value(instance.ObjectiveFunction)
        CO2emission_max = value(instance.ObjectiveFunction1)

        # Plotting the Pareto Curve
        # The Pareto curve is plotted to visualize the trade-off between NPC and CO2 emissions.
        # Plotting code includes customization options for labels, legend, and resolution.

