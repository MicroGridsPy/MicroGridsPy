"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

Authors: 
    Giulia Guidicini   - Department of Energy, Politecnico di Milano 
    Lorenzo Rinaldi    - Department of Energy, Politecnico di Milano
    Nicolò Stevanato   - Department of Energy, Politecnico di Milano / Fondazione Eni Enrico Mattei
    Francesco Lombardi - Department of Energy, Politecnico di Milano
    Emanuela Colombo   - Department of Energy, Politecnico di Milano
Based on the original model by:
    Sergio Balderrama  - Department of Mechanical and Aerospace Engineering, University of Liège / San Simon University, Centro Universitario de Investigacion en Energia
    Sylvain Quoilin    - Department of Mechanical Engineering Technology, KU Leuven
"""


from pyomo.opt import SolverFactory
from pyomo.environ import Objective, minimize, Constraint
from Constraints import *


def Model_Resolution(model, Optimization_Goal, Renewable_Penetration, Battery_Independence,datapath="Inputs/data.dat"):      
    
#%% Economic constraints
    if Optimization_Goal == 'NPC':
        model.ObjectiveFuntion = Objective(rule=Net_Present_Cost_Obj, 
                                           sense=minimize)  
    elif Optimization_Goal == 'Operation cost':
        model.ObjectiveFunction = Objective(rule=Total_Variable_Cost_Obj, 
                                            sense=minimize)
        model.NetPresentCost = Constraint(rule=Net_Present_Cost)

    model.ScenarioNetPresentCost = Constraint(model.scenarios, 
                                              rule=Scenario_Net_Present_Cost)    
    
    "Investment cost"
    model.InvestmentCost = Constraint(rule=Investment_Cost)
    if Optimization_Goal == 'Operation cost':
        model.InvestmentCostLimit = Constraint(rule=Investment_Cost_Limit)

    "Fixed costs"    
    model.OperationMaintenanceCostAct = Constraint(rule=Operation_Maintenance_Cost_Act)
    model.OperationMaintenanceCostNonAct = Constraint(rule=Operation_Maintenance_Cost_NonAct)

    "Variable costs"
    model.TotalVariableCostAct         = Constraint(rule=Total_Variable_Cost_Act)
    model.FuelCostTotalAct             = Constraint(model.scenarios, 
                                            model.generator_types,
                                            rule=Total_Fuel_Cost_Act)
    model.BatteryReplacementCostAct    = Constraint(model.scenarios,
                                                 rule=Battery_Replacement_Cost_Act) 
    model.ScenarioLostLoadCostAct      = Constraint(model.scenarios, 
                                                 rule=Scenario_Lost_Load_Cost_Act)
    model.ScenarioVariableCostAct      = Constraint(model.scenarios,
                                                 rule=Scenario_Variable_Cost_Act)    

    model.FuelCostTotalNonAct          = Constraint(model.scenarios, 
                                                    model.generator_types, 
                                                    rule=Total_Fuel_Cost_NonAct)
    model.BatteryReplacementCostNonAct = Constraint(model.scenarios,
                                                    rule=Battery_Replacement_Cost_NonAct) 
    model.ScenarioLostLoadCostNonAct   = Constraint(model.scenarios, 
                                                    rule=Scenario_Lost_Load_Cost_NonAct)
    model.ScenarioVariableCostNonAct   = Constraint(model.scenarios,
                                                    rule=Scenario_Variable_Cost_NonAct)     

    "Salvage value"
    model.SalvageValue = Constraint(rule=Salvage_Value)


#%% Electricity generation system constraints 
    model.EnergyBalance = Constraint(model.scenarios, 
                                     model.years_steps, 
                                     model.periods, 
                                     rule=Energy_balance)

    "Renewable Energy Sources constraints"
    model.RenewableEnergy = Constraint(model.scenarios, model.years_steps, 
                                       model.renewable_sources,
                                       model.periods, 
                                       rule=Renewable_Energy)  # Energy output of the solar panels
    model.ResMinStepUnits = Constraint(model.years_steps,
                                       model.renewable_sources, 
                                       rule=Renewables_Min_Step_Units)
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(model.steps, 
                                                      rule=Renewable_Energy_Penetration)

    "Battery Energy Storage constraints"
    model.StateOfCharge            = Constraint(model.scenarios, 
                                                model.years_steps,
                                                model.periods, 
                                                rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge            = Constraint(model.scenarios,
                                                model.years_steps, 
                                                model.periods, 
                                                rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge            = Constraint(model.scenarios, 
                                                model.years_steps,
                                                model.periods,
                                                rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge    = Constraint(model.steps, 
                                                rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(model.steps,
                                                rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint
    model.MaxBatIn                 = Constraint(model.scenarios,
                                                model.years_steps,
                                                model.periods, 
                                                rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout                = Constraint(model.scenarios, 
                                                model.years_steps, 
                                                model.periods,
                                                rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    model.BatteryMinStepCapacity   = Constraint(model.years_steps, 
                                                rule=Battery_Min_Step_Capacity)
    if Battery_Independence > 0:
        model.BatteryMinCapacity   = Constraint(model.steps, 
                                                rule=Battery_Min_Capacity)

    "Diesel generator constraints"
    model.MaximunFuelEnergy        = Constraint(model.scenarios, 
                                                model.years_steps, 
                                                model.generator_types,
                                                model.periods, 
                                                rule=Maximun_Generator_Energy) # Maximun energy output of the diesel generator
    model.GeneratorMinStepCapacity = Constraint(model.years_steps, 
                                                model.generator_types, 
                                                rule = Generator_Min_Step_Capacity)
    
    "Lost load constraints"
    model.MaximunLostLoad = Constraint(model.scenarios, model.years, 
                                       rule=Maximun_Lost_Load) # Maximum permissible lost load
    
       
    
    instance = model.create_instance(datapath) # load parameters

    print('\nInstance created')
    
    opt = SolverFactory('gurobi') # Solver use during the optimization

    opt.set_options('Method=2 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000') # !! only works with GUROBI solver   
    # opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000') # !! only works with GUROBI solver   

    print('Calling solver...')
    results = opt.solve(instance, tee=True) # Solving a model instance 
    print('Instance solved')

    instance.solutions.load_from(results)  # Loading solution into instance
    return instance
