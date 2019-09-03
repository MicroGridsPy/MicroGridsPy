"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""

from pyomo.opt import SolverFactory
from pyomo.environ import Objective, minimize, Constraint


def Model_Resolution(model, Renewable_Penetration, Battery_Independency,datapath="Inputs/data_MY.dat"):   
    '''
    This function creates the model and call Pyomo to solve the instance of the proyect 
    
    :param model: Pyomo model as defined in the Model_creation library
    :param datapath: path to the input data file
    
    :return: The solution inside an object call instance.
    '''
    from Constraints_MY import  Renewable_Energy,State_of_Charge,\
    Maximun_Charge, Minimun_Charge, Max_Power_Battery_Charge, Max_Power_Battery_Discharge, Max_Bat_in, Max_Bat_out, \
    Energy_balance, Maximun_Lost_Load,Scenario_Net_Present_Cost, Scenario_Lost_Load_Cost, Renewable_Energy_Penetration,\
    Investment_Cost, Operation_Maintenance_Cost, Battery_Reposition_Cost, Maximun_Generator_Energy, Total_Fuel_Cost,\
    Battery_Min_Capacity, Battery_Min_Step_Capacity, Renewables_Min_Step_Units, Generator_Min_Step_Capacity, Salvage_Value, Net_Present_Cost_Obj, \
    Total_Variable_Cost, Scenario_Variable_Cost
#    , Battery_Replacement    

    
    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost_Obj, sense=minimize)  
    
    # CONSTRAINTS
    
    #Energy constraints
    model.EnergyBalance = Constraint(model.scenarios, model.yu_tup, model.periods, rule=Energy_balance)

    model.MaximunLostLoad = Constraint(model.scenarios, model.years, rule=Maximun_Lost_Load) # Maximum permissible lost load
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(model.upgrades, rule=Renewable_Energy_Penetration)
    
    # RES constraints
    model.RenewableEnergy = Constraint(model.scenarios, model.yu_tup, model.renewable_sources,
                                       model.periods, rule=Renewable_Energy)  # Energy output of the solar panels
    model.RenewablesMinStepUnits = Constraint(model.yu_tup, model.renewable_sources, rule=Renewables_Min_Step_Units)
    
    # Battery constraints
    model.StateOfCharge = Constraint(model.scenarios, model.yu_tup, model.periods, rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.scenarios, model.yu_tup, model.periods, rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.scenarios, model.yu_tup, model.periods, rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge = Constraint(model.upgrades, rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(model.upgrades, rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint
    model.MaxBatIn = Constraint(model.scenarios, model.yu_tup, model.periods, rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.scenarios, model.yu_tup, model.periods, rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    
    model.BatteryMinStepCapacity = Constraint(model.yu_tup, rule=Battery_Min_Step_Capacity)
    
    if Battery_Independency > 0:
        model.BatteryMinCapacity = Constraint(model.upgrades, rule=Battery_Min_Capacity)
       
    # Diesel Generator constraints
    model.MaximunFuelEnergy = Constraint(model.scenarios, model.yu_tup, model.generator_types,
                                               model.periods, rule=Maximun_Generator_Energy) # Maximun energy output of the diesel generator
    model.GeneratorMinStepCapacity = Constraint(model.yu_tup, model.generator_types, rule = Generator_Min_Step_Capacity)
    
    # Financial Constraints
    model.ScenarioNetPresentCost = Constraint(model.scenarios, rule=Scenario_Net_Present_Cost)    
    model.InitialInvestment = Constraint(rule=Investment_Cost)
    model.SalvageValue = Constraint(rule=Salvage_Value)
    model.OperationMaintenanceCost = Constraint(rule=Operation_Maintenance_Cost)
    model.ScenarioLostLoadCost = Constraint(model.scenarios, rule=Scenario_Lost_Load_Cost)
    model.FuelCostTotal = Constraint(model.scenarios, model.generator_types, rule=Total_Fuel_Cost)
    model.BatteryRepositionCost = Constraint(model.scenarios,rule=Battery_Reposition_Cost) 
#    model.BatteryReplacement = Constraint(model.scenarios,rule=Battery_Replacement)     
    model.ScenarioVariableCost = Constraint(model.scenarios,rule=Scenario_Variable_Cost)    
    model.TotalVariableCost = Constraint(rule=Total_Variable_Cost)
    
    print('Model_Resolution: Constraints imported')
    
    instance = model.create_instance(datapath) # load parameters

    print('Model_Resolution: Instance created')
    
    opt = SolverFactory('cplex') # Solver use during the optimization    
    
    print('Model_Resolution: cplex called')
    
    results = opt.solve(instance, tee=True) # Solving a model instance 
    
    print('Model_Resolution: instance solved')

    instance.solutions.load_from(results)  # Loading solution into instance
    return instance
