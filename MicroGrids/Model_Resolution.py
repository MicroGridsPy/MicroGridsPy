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
    
    from Constraints import  Net_Present_Cost, State_of_Charge,\
    Maximun_Charge, Minimun_Charge, Max_Power_Battery_Charge,\
    Max_Power_Battery_Discharge, Max_Bat_in, Max_Bat_out, \
    Energy_balance, Maximun_Lost_Load, Renewable_Energy_Penetration,\
    Maximun_Generator_Energy,Generator_Bounds_Min_Integer,\
    Battery_Min_Capacity,Generator_Bounds_Max_Integer,Energy_Genarator_Energy_Max_Integer, \
    Generator_Thermal_Energy, Fuel_Flow_Demand_CHP, Thermal_Energy_Combustor_Max,  \
    Thermal_balance, Maximum_Fuel_Available, Fuel_Flow_Demand_Comb 
   # ,  ,, Maximum_Fuel_Available Combustor_Thermal_Energy, \
           
    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.scenario,model.periods, rule=Energy_balance)
    if model.Lost_Load_Probability > 0:
        model.MaximunLostLoad = Constraint(rule=Maximun_Lost_Load) 
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(rule=Renewable_Energy_Penetration)
    
    # Renewable constraints

    # Battery constraints
    model.StateOfCharge = Constraint(model.scenario, model.periods, rule=State_of_Charge) 
    model.MaximunCharge = Constraint(model.scenario, model.periods, rule=Maximun_Charge) 
    model.MinimunCharge = Constraint(model.scenario, model.periods, rule=Minimun_Charge) 
    model.MaxPowerBatteryCharge = Constraint(rule=Max_Power_Battery_Charge)  
    model.MaxPowerBatteryDischarge = Constraint(rule=Max_Power_Battery_Discharge)
    model.MaxBatIn = Constraint(model.scenario, model.periods, rule=Max_Bat_in) 
    model.Maxbatout = Constraint(model.scenario, model.periods, rule=Max_Bat_out) 
    
#    #Thermal Energy constraints JVS
    model.ThermalBalance = Constraint(model.scenario, model.periods, rule=Thermal_balance)  # Thermal Energy balance
#    
#    #CHP constraints
    model.GeneratorThermalEnergy = Constraint(model.scenario, model.generator_type, model.periods, rule =Generator_Thermal_Energy)
    model.FuelFlowCHP =  Constraint(model.scenario, model.generator_type, model.periods, rule =Fuel_Flow_Demand_CHP)
    model.MaxFuel =  Constraint(model.scenario, model.generator_type, model.combustor_type, 
                                           model.periods, rule =Maximum_Fuel_Available)
    model.FuelFlowCom = Constraint(model.scenario, model.combustor_type, model.generator_type, model.periods, rule =Fuel_Flow_Demand_Comb)

     #Combustor constraints
    model.CombustorThermalEnergy = Constraint(model.scenario, model.combustor_type, 
                                              model.periods, rule =Thermal_Energy_Combustor_Max)
    
#    model.ThermalCombustorMax = Constraint(model.scenario, model.combustor_type, 
#                                           model.periods, rule =Thermal_Energy_Combustor_Max)    
    
    if Battery_Independency > 0:
        model.BatteryMinCapacity = Constraint(rule=Battery_Min_Capacity) 

    # Diesel Generator constraints
    
    
    if model.formulation == 'LP':
        model.MaximunFuelEnergy = Constraint(model.scenario, model.generator_type,
                                         model.periods, rule=Maximun_Generator_Energy) 
        instance = model.create_instance(datapath) # load parameters       
        opt = SolverFactory('cplex') # Solver use during the optimization    
        results = opt.solve(instance, tee=True) # Solving a model instance 
        instance.solutions.load_from(results)  # Loading solution into instance
        
    elif model.formulation == 'MILP':
        model.GeneratorBoundsMin = Constraint(model.scenario,model.generator_type,
                                          model.periods, rule=Generator_Bounds_Min_Integer) 
        model.GeneratorBoundsMax = Constraint(model.scenario,model.generator_type,
                                          model.periods, rule=Generator_Bounds_Max_Integer)
   
        model.EnergyGenaratorEnergyMax = Constraint(model.scenario, model.generator_type,
                                                model.periods, rule=Energy_Genarator_Energy_Max_Integer)
        instance = model.create_instance("Example/data_Integer.dat") # load parameters       
        opt = SolverFactory('cplex') # Solver use during the optimization    
#       opt.options['emphasis_memory'] = 'y'
        opt.options['timelimit'] = 36000
#        opt.options['StartNodeLimit'] = 10 # 500 Default
#       opt.options['emphasis_mip'] = 2
#        opt.options['Presolve'] = 2
        results = opt.solve(instance, tee=True, options_string="mipgap=0.05",
                            warmstart=False,keepfiles=False,
                            load_solutions=False, logfile="Solver_Output.log") # Solving a model instance 

        #    instance.write(io_options={'emphasis_memory':True})
        #options_string="mipgap=0.03", timelimit=1200
        instance.solutions.load_from(results) # Loading solution into instance
    
    return instance
    

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
#    model.ScenarioNetPresentCost = Constraint(model.scenario, rule=Scenario_Net_Present_Cost) 
    
    
    instance = model.create_instance("Example/data_binary.dat") # load parameters       
    opt = SolverFactory('cplex') # Solver use during the optimization    
#    opt.options['emphasis_memory'] = 'y'
#    opt.options['node_select'] = 3
    results = opt.solve(instance, tee=True,options_string="mipgap=0.8") # Solving a model instance 

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
    Maximun_Charge, Minimun_Charge, Max_Bat_in, Max_Bat_out, \
    Energy_balance, Maximun_Lost_Load, Fuel_Flow_Demand_CHP, Maximum_Fuel_Available, \
    Thermal_balance, Combustor_Thermal_Energy, \
    Max_Power_Battery_Charge, Generator_Thermal_Energy, Thermal_Energy_Combustor_Max, \
    Max_Power_Battery_Discharge, Generator_Bounds_Min_Integer,\
    Generator_Bounds_Max_Integer,Energy_Genarator_Energy_Max_Integer
#Thermal_use_factor_system,  
    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=Net_Present_Cost, sense=minimize)  
    
    # CONSTRAINTS
    #Energy constraints
    model.EnergyBalance = Constraint(model.periods, rule=Energy_balance)  # Energy balance
    model.MaximunLostLoad = Constraint(rule=Maximun_Lost_Load) # Maximum permissible lost load
    
    #Thermal Energy constraints
    model.ThermalBalance = Constraint(model.periods, rule=Thermal_balance)  # Thermal Energy balance
     
    # Battery constraints
    model.StateOfCharge = Constraint(model.periods, rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge = Constraint(model.periods, rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge = Constraint(model.periods, rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge = Constraint(rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint

    model.MaxBatIn = Constraint(model.periods, rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout = Constraint(model.periods, rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    #Diesel Generator constraints
    model.GeneratorBoundsMin = Constraint(model.generator_type, model.periods, rule=Generator_Bounds_Min_Integer) 
    model.GeneratorBoundsMax = Constraint(model.generator_type, model.periods, rule=Generator_Bounds_Max_Integer)
    
    #CHP constraints
    model.GeneratorThermalEnergy = Constraint(model.generator_type, model.periods, rule =Generator_Thermal_Energy)
    model.FuelFlowCHP =  Constraint(model.generator_type, model.periods, rule =Fuel_Flow_Demand_CHP)
    model.MaxFuel =  Constraint(model.combustor_type, model.generator_type, model.periods, rule =Maximum_Fuel_Available)
#    model.ThermalUseFactor = Constraint(model.generator_type, model.combustor_type, model.periods, rule =Thermal_use_factor_system)
    
    #Combustor constraints
    model.CombustorThermalEnergy = Constraint(model.generator_type, model.combustor_type, model.periods, rule =Combustor_Thermal_Energy)
    model.ThermalCombustorMax = Constraint(model.combustor_type, model.periods, rule =Thermal_Energy_Combustor_Max)
    
    
    instance = model.create_instance("Example/data_dispatch.dat") # load parameters       
    opt = SolverFactory('cplex') # Solver use during the optimization    
#    opt.options['emphasis_memory'] = 'y'
#    opt.options['node_select'] = 3
    results = opt.solve(instance, tee=True,options_string="mipgap=0.005") # Solving a model instance 

    #    instance.write(io_options={'emphasis_memory':True})
    #options_string="mipgap=0.03", timelimit=1200
    instance.solutions.load_from(results) # Loading solution into instance
    return instance


