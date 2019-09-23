#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pyomo.opt import SolverFactory
from pyomo.environ import Objective, minimize, Constraint


def Model_Resolution(model,Renewable_Penetration, Battery_Independency,datapath="Example/data.dat"):   
    '''
    This function creates the model and call Pyomo to solve the instance of the proyect 
    
    :param model: Pyomo model as defined in the Model_creation library
    :param datapath: path to the input data file
    
    :return: The solution inside an object call instance.
    '''
    
    from Constraints import  Net_Present_Cost, Renewable_Energy,State_of_Charge,\
    Maximun_Charge, Minimun_Charge, Max_Power_Battery_Charge, Max_Power_Battery_Discharge, Max_Bat_in, Max_Bat_out, \
    Energy_balance, Maximun_Lost_Load,Scenario_Net_Present_Cost, Scenario_Lost_Load_Cost, Renewable_Energy_Penetration,\
    Initial_Inversion, Operation_Maintenance_Cost, Battery_Reposition_Cost, Maximun_Generator_Energy,  Fuel_Cost_Total,Battery_Min_Capacity
    
    
    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.scenario,model.periods, rule=Energy_balance)
    model.MaximunLostLoad = Constraint(model.scenario, rule=Maximun_Lost_Load) # Maximum permissible lost load
    model.ScenarioLostLoadCost = Constraint(model.scenario, rule=Scenario_Lost_Load_Cost)
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(rule=Renewable_Energy_Penetration)
    # PV constraints
    model.RenewableEnergy = Constraint(model.scenario, model.renewable_source,
                                       model.periods, rule=Renewable_Energy)  # Energy output of the solar panels
    # Battery constraints
    model.StateOfCharge = Constraint(model.scenario, model.periods, rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.scenario, model.periods, rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.scenario, model.periods, rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge = Constraint(rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint
    model.MaxBatIn = Constraint(model.scenario, model.periods, rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.scenario, model.periods, rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    if Battery_Independency > 0:
        model.BatteryMinCapacity = Constraint(rule=Battery_Min_Capacity)

    # Diesel Generator constraints
    model.MaximunFuelEnergy = Constraint(model.scenario, model.generator_type,
                                         model.periods, rule=Maximun_Generator_Energy) # Maximun energy output of the diesel generator

    model.FuelCostTotal = Constraint(model.scenario, model.generator_type,
                                     rule=Fuel_Cost_Total)
    
    # Financial Constraints
    model.ScenarioNetPresentCost = Constraint(model.scenario, rule=Scenario_Net_Present_Cost)    
    model.InitialInversion = Constraint(rule=Initial_Inversion)
    model.OperationMaintenanceCost = Constraint(rule=Operation_Maintenance_Cost)
    model.BatteryRepositionCost = Constraint(model.scenario,rule=Battery_Reposition_Cost) 

    
    instance = model.create_instance(datapath) # load parameters       
    opt = SolverFactory('gurobi') # Solver use during the optimization    
    results = opt.solve(instance, tee=True) # Solving a model instance 
    instance.solutions.load_from(results)  # Loading solution into instance
    return instance
    
    
    #\
def Model_Resolution_binary(model,datapath="Example/data_binary.dat"):   
    '''
    This function creates the model and call Pyomo to solve the instance of the proyect 
    
    :param model: Pyomo model as defined in the Model_creation library
    
    :return: The solution inside an object call instance.
    '''
    from Constraints_binary import  Net_Present_Cost, Solar_Energy, State_of_Charge, Maximun_Charge, \
    Minimun_Charge, Max_Power_Battery_Charge, Max_Power_Battery_Discharge, Max_Bat_in, Max_Bat_out, \
    Financial_Cost, Energy_balance, Maximun_Lost_Load, Generator_Cost_1_binary, Generator_Total_Period_Energy_binary, \
    Total_Cost_Generator_binary, Initial_Inversion, Operation_Maintenance_Cost,Total_Finalcial_Cost,\
    Battery_Reposition_Cost, Scenario_Lost_Load_Cost, Sceneario_Generator_Total_Cost, \
    Scenario_Net_Present_Cost, Generator_Bounds_Min_binary, Generator_Bounds_Max_binary,Energy_Genarator_Energy_Max_binary

    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.scenario,model.periods, rule=Energy_balance)  # Energy balance
    model.MaximunLostLoad = Constraint(model.scenario,rule=Maximun_Lost_Load) # Maximum permissible lost load
    # PV constraints
    model.SolarEnergy = Constraint(model.scenario,model.periods, rule=Solar_Energy)  # Energy output of the solar panels
    # Battery constraints
    model.StateOfCharge = Constraint(model.scenario,model.periods, rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.scenario,model.periods, rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.scenario,model.periods, rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge = Constraint(rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint
    model.MaxBatIn = Constraint(model.scenario,model.periods, rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.scenario,model.periods, rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    #Diesel Generator constraints
    model.GeneratorBoundsMin = Constraint(model.scenario,model.periods, rule=Generator_Bounds_Min_binary) 
    model.GeneratorBoundsMax = Constraint(model.scenario,model.periods, rule=Generator_Bounds_Max_binary)
    model.GeneratorCost1 = Constraint(model.scenario, model.periods,  rule=Generator_Cost_1_binary)
    model.EnergyGenaratorEnergyMax = Constraint(model.scenario,model.periods, rule=Energy_Genarator_Energy_Max_binary)
    model.TotalCostGenerator = Constraint(model.scenario, rule=Total_Cost_Generator_binary)
    model.GeneratorTotalPeriodEnergybinary = Constraint(model.scenario,model.periods, rule=Generator_Total_Period_Energy_binary) 
    
    # Financial Constraints
    model.FinancialCost = Constraint(rule=Financial_Cost) # Financial cost
    model.InitialInversion = Constraint(rule=Initial_Inversion)
    model.OperationMaintenanceCost = Constraint(rule=Operation_Maintenance_Cost)
    model.TotalFinalcialCost = Constraint(rule=Total_Finalcial_Cost)
    model.BatteryRepositionCost = Constraint(rule=Battery_Reposition_Cost) 
    model.ScenarioLostLoadCost = Constraint(model.scenario, rule=Scenario_Lost_Load_Cost)
    model.ScenearioGeneratorTotalCost = Constraint(model.scenario, rule=Sceneario_Generator_Total_Cost)
    model.ScenarioNetPresentCost = Constraint(model.scenario, rule=Scenario_Net_Present_Cost) 
    
    
    instance = model.create_instance("Example/data_binary.dat") # load parameters       
    opt = SolverFactory('cplex') # Solver use during the optimization    
#    opt.options['emphasis_memory'] = 'y'
#    opt.options['node_select'] = 3
    results = opt.solve(instance, tee=True,options_string="mipgap=0.05") # Solving a model instance 

    #    instance.write(io_options={'emphasis_memory':True})
    #options_string="mipgap=0.03", timelimit=1200
    instance.solutions.load_from(results) # Loading solution into instance
    return instance
    
def Model_Resolution_Integer(model,Renewable_Penetration, Battery_Independency,
                             datapath="Example/data_Integer.dat"):   
    '''
    This function creates the model and call Pyomo to solve the instance of the proyect 
    
    :param model: Pyomo model as defined in the Model_creation library
    
    :return: The solution inside an object call instance.
    '''
    from Constraints_Integer import  Net_Present_Cost, State_of_Charge, Maximun_Charge, Battery_Min_Capacity,\
    Minimun_Charge, Max_Bat_in, Max_Bat_out, Energy_balance, Maximun_Lost_Load, Renewable_Energy_Penetration, \
    Generator_Bounds_Min_Integer, Generator_Bounds_Max_Integer,Energy_Genarator_Energy_Max_Integer
    
    
    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.scenario,
                                     model.periods, rule=Energy_balance)  # Energy balance
    model.MaximunLostLoad = Constraint(model.scenario,rule=Maximun_Lost_Load) # Maximum permissible lost load
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(rule=Renewable_Energy_Penetration)

    # PV constraints
      
    # Battery constraints
    model.StateOfCharge = Constraint(model.scenario,model.periods, 
                                     rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.scenario,model.periods, 
                                     rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.scenario,model.periods, 
                                     rule=Minimun_Charge) # Minimun state of charge
    model.MaxBatIn = Constraint(model.scenario,model.periods,
                                rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.scenario,model.periods, 
                                 rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    if Battery_Independency > 0:
        model.BatteryMinCapacity = Constraint(rule=Battery_Min_Capacity)

    #Diesel Generator constraints
    model.GeneratorBoundsMin = Constraint(model.scenario,model.generator_type,
                                          model.periods, rule=Generator_Bounds_Min_Integer) 
    model.GeneratorBoundsMax = Constraint(model.scenario,model.generator_type,
                                          model.periods, rule=Generator_Bounds_Max_Integer)
   
    model.EnergyGenaratorEnergyMax = Constraint(model.scenario, model.generator_type,
                                                model.periods, rule=Energy_Genarator_Energy_Max_Integer)
    
    
    
    instance = model.create_instance("Example/data_Integer.dat") # load parameters       
    opt = SolverFactory('gurobi') # Solver use during the optimization    
#    opt.options['emphasis_memory'] = 'y'
    opt.options['timelimit'] = 200000
#    opt.options['node_select'] = 3
#    opt.options['emphasis_mip'] = 2
    results = opt.solve(instance, tee=True,options_string="mipgap=0.05",
                        warmstart=True,keepfiles=False) # Solving a model instance 

    #    instance.write(io_options={'emphasis_memory':True})
    #options_string="mipgap=0.03", timelimit=1200
    instance.solutions.load_from(results) # Loading solution into instance
    return instance

    
def Model_Resolution_Dispatch(model,datapath="Example/data_Dispatch.dat"):   
    '''
    This function creates the model and call Pyomo to solve the instance of the proyect 
    
    :param model: Pyomo model as defined in the Model_creation library
    
    :return: The solution inside an object call instance.
    '''
    from Constraints_Dispatch import  Net_Present_Cost,  State_of_Charge,\
    Maximun_Charge, Minimun_Charge, Max_Bat_in, Max_Bat_out, Battery_Reposition_Cost,\
    Energy_balance, Maximun_Lost_Load, Generator_Cost_1_Integer,  \
    Total_Cost_Generator_Integer, Scenario_Lost_Load_Cost, Max_Power_Battery_Charge, \
    Max_Power_Battery_Discharge, Generator_Bounds_Min_Integer,\
    Generator_Bounds_Max_Integer,Energy_Genarator_Energy_Max_Integer

    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.periods, rule=Energy_balance)  # Energy balance
    model.MaximunLostLoad = Constraint(rule=Maximun_Lost_Load) # Maximum permissible lost load
    
    # Battery constraints
    model.StateOfCharge = Constraint(model.periods, rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.periods, rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.periods, rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge = Constraint(rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint

    model.MaxBatIn = Constraint(model.periods, rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.periods, rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    model.BatteryRepositionCost = Constraint(rule=Battery_Reposition_Cost)
    #Diesel Generator constraints
    model.GeneratorBoundsMin = Constraint(model.periods, rule=Generator_Bounds_Min_Integer) 
    model.GeneratorBoundsMax = Constraint(model.periods, rule=Generator_Bounds_Max_Integer)
    model.GeneratorCost1 = Constraint(model.periods,  rule=Generator_Cost_1_Integer)
    model.EnergyGenaratorEnergyMax = Constraint(model.periods, rule=Energy_Genarator_Energy_Max_Integer)
    model.TotalCostGenerator = Constraint(rule=Total_Cost_Generator_Integer)
    
    # Financial Constraints
    model.ScenarioLostLoadCost = Constraint(rule=Scenario_Lost_Load_Cost)
    
    instance = model.create_instance("Example/data_dispatch.dat") # load parameters       
    opt = SolverFactory('cplex') # Solver use during the optimization    
#    opt.options['emphasis_memory'] = 'y'
#    opt.options['node_select'] = 3
    results = opt.solve(instance, tee=True,options_string="mipgap=0.05") # Solving a model instance 

    #    instance.write(io_options={'emphasis_memory':True})
    #options_string="mipgap=0.03", timelimit=1200
    instance.solutions.load_from(results) # Loading solution into instance
    return instance

