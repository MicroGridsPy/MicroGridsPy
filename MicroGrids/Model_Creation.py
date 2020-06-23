#!/usr/bin/env python3
# -*- coding: utf-8 -*-



def Model_Creation(model, Renewable_Penetration,Battery_Independency):
    
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.
    
    :param model: Pyomo model as defined in the Micro-Grids library.
    
    '''
    from pyomo.environ import  Param, RangeSet, NonNegativeReals, Var
    from Initialize import Initialize_years, Initialize_Demand, Battery_Reposition_Cost, Initialize_Renewable_Energy, Marginal_Cost_Generator_1,Min_Bat_Capacity # Import library with initialitation funtions for the parameters

    # Time parameters
    model.Periods = Param(within=NonNegativeReals) # Number of periods of analysis of the energy variables
    model.Years = Param() # Number of years of the project
    model.StartDate = Param() # Start date of the analisis
    model.Scenarios = Param() 
    model.Renewable_Source = Param()
    model.Generator_Type = Param()
    
    #SETS
    model.periods = RangeSet(1, model.Periods) # Creation of a set from 1 to the number of periods in each year
    model.years = RangeSet(1, model.Years) # Creation of a set from 1 to the number of years of the project
    model.scenario = RangeSet(1, model.Scenarios) # Creation of a set from 1 to the numbero scenarios to analized
    model.renewable_source = RangeSet(1, model.Renewable_Source)
    model.generator_type = RangeSet(1, model.Generator_Type)    


    # PARAMETERS
    model.Scenario_Weight = Param(model.scenario, within=NonNegativeReals) #########
    # Parameters of the PV 
   

    model.Renewable_Nominal_Capacity = Param(model.renewable_source,
                                             within=NonNegativeReals) # Nominal capacity of the PV in W/unit
    model.Renewable_Inverter_Efficiency = Param(model.renewable_source) # Efficiency of the inverter in %
    model.Renewable_Invesment_Cost = Param(model.renewable_source,
                                           within=NonNegativeReals) # Cost of solar panel in USD/W
    model.Renewable_Energy_Production = Param(model.scenario,model.renewable_source,
                                              model.periods, within=NonNegativeReals, 
                                              initialize=Initialize_Renewable_Energy) # Energy produccion of a solar panel in W
    
    # Parameters of the battery bank
    model.Charge_Battery_Efficiency = Param() # Efficiency of the charge of the battery in  %
    model.Discharge_Battery_Efficiency = Param() # Efficiency of the discharge of the battery in %
    model.Deep_of_Discharge = Param() # Deep of discharge of the battery (Deep_of_Discharge) in %
    model.Maximun_Battery_Charge_Time = Param(within=NonNegativeReals) # Minimun time of charge of the battery in hours
    model.Maximun_Battery_Discharge_Time = Param(within=NonNegativeReals) # Maximun time of discharge of the battery  in hours                     
    model.Battery_Invesment_Cost = Param() # Cost of battery 
    model.Battery_Electronic_Invesmente_Cost = Param(within=NonNegativeReals)
    model.Battery_Cycles = Param(within=NonNegativeReals)
    model.Unitary_Battery_Reposition_Cost = Param(within=NonNegativeReals, 
                                          initialize=Battery_Reposition_Cost)
    model.Battery_Initial_SOC = Param(within=NonNegativeReals)
    if  Battery_Independency > 0:
        model.Battery_Independency = Battery_Independency
        model.Battery_Min_Capacity = Param(initialize=Min_Bat_Capacity)
  
    # Parametes of the diesel generator
    model.Generator_Efficiency = Param(model.generator_type) # Generator efficiency to trasform heat into electricity %
    model.Low_Heating_Value = Param(model.generator_type) # Low heating value of the diesel in W/L
    model.Fuel_Cost = Param(model.generator_type,
                                      within=NonNegativeReals) # Cost of diesel in USD/L
    model.Generator_Invesment_Cost = Param(model.generator_type,
                                           within=NonNegativeReals) # Cost of the diesel generator
    model.Marginal_Cost_Generator_1 = Param(model.generator_type,
                                            initialize=Marginal_Cost_Generator_1)
        
    # Parameters of the Energy balance                  
    model.Energy_Demand = Param(model.scenario, model.periods, 
                                initialize=Initialize_Demand) # Energy Energy_Demand in W 
    model.Lost_Load_Probability = Param(within=NonNegativeReals) # Lost load probability in %
    model.Value_Of_Lost_Load = Param(within=NonNegativeReals) # Value of lost load in USD/W
    if Renewable_Penetration > 0:
        model.Renewable_Penetration =  Renewable_Penetration
    # Parameters of the proyect
    model.Delta_Time = Param(within=NonNegativeReals) # Time step in hours
    model.Project_Years = Param(model.years, initialize= Initialize_years) # Years of the project
    model.Maintenance_Operation_Cost_Renewable = Param(model.renewable_source,
                                                       within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %                                             
    model.Maintenance_Operation_Cost_Battery = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Maintenance_Operation_Cost_Generator = Param(model.generator_type,
                                                       within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Discount_Rate = Param() # Discount rate of the project in %
    
    
       

    # VARIABLES
   
    # Variables associated to the solar panels
        
    model.Renewable_Units = Var(model.renewable_source,
                                within=NonNegativeReals) # Number of units of solar panels
    model.Total_Energy_Renewable = Var(model.scenario,model.renewable_source,
                                model.periods, within=NonNegativeReals) # Energy generated for the Pv sistem in Wh


    # Variables associated to the battery bank
    model.Battery_Nominal_Capacity = Var(within=NonNegativeReals) # Capacity of the battery bank in Wh
    model.Energy_Battery_Flow_Out = Var(model.scenario, model.periods,
                                        within=NonNegativeReals) # Battery discharge energy in wh
    model.Energy_Battery_Flow_In = Var(model.scenario, model.periods, 
                                       within=NonNegativeReals) # Battery charge energy in wh
    model.State_Of_Charge_Battery = Var(model.scenario, model.periods, 
                                        within=NonNegativeReals) # State of Charge of the Battery in wh
    model.Maximun_Charge_Power = Var(within=NonNegativeReals)
    model.Maximun_Discharge_Power = Var(within=NonNegativeReals)
    # Variables associated to the diesel generator
    model.Generator_Nominal_Capacity = Var(model.generator_type,
                                           within=NonNegativeReals) # Capacity  of the diesel generator in Wh

    model.Generator_Energy = Var(model.scenario,model.generator_type,
                                 model.periods, within=NonNegativeReals) # Energy generated for the Diesel generator
    model.Fuel_Cost_Total = Var(model.scenario, model.generator_type,
                                  within=NonNegativeReals)
    
    
    
    # Varialbles associated to the energy balance
    model.Lost_Load = Var(model.scenario, model.periods, within=NonNegativeReals) # Energy not suply by the system kWh
    model.Energy_Curtailment = Var(model.scenario, model.periods, within=NonNegativeReals) # Curtailment of solar energy in kWh
    model.Scenario_Lost_Load_Cost = Var(model.scenario, within=NonNegativeReals) ####    

    # Variables associated to the project
    model.Scenario_Net_Present_Cost = Var(model.scenario, within=NonNegativeReals) ####
    model.Initial_Inversion = Var(within=NonNegativeReals)
    model.Operation_Maintenance_Cost = Var(within=NonNegativeReals)
    model.Battery_Reposition_Cost = Var(model.scenario,within=NonNegativeReals)




def Model_Creation_binary(model):
    
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.
    The problem is solved by discretizing the efficiency curve of the generators and uses binary variables
    
    :param model: Pyomo model as defined in the Micro-Grids library.
    
    '''
    from pyomo.environ import  Param, RangeSet, NonNegativeReals, Var, Binary, NonNegativeIntegers
    from Initialize import Initialize_years, Initialize_Demand, Initialize_PV_Energy, Marginal_Cost_Generator, Start_Cost,Marginal_Cost_Generator_1 # Import library with initialitation funtions for the parameters
   
    # Time parameters
    model.Periods = Param(within=NonNegativeReals) # Number of periods of analysis of the energy variables
    model.Years = Param() # Number of years of the project
    model.StartDate = Param() # Start date of the analisis
    model.PlotTime = Param() # Quantity of days that are going to be plot
    model.PlotDay = Param() # Start day for the plot
    model.Scenarios = Param()  
    model.PlotScenario = Param()
    
    #SETS
    model.periods = RangeSet(1, model.Periods) # Creation of a set from 1 to the number of periods in each year
    model.years = RangeSet(1, model.Years) # Creation of a set from 1 to the number of years of the project
    model.Slops = RangeSet(1,2)
    model.scenario = RangeSet(1, model.Scenarios) # Creation of a set from 1 to the numbero scenarios to analized
    
    # PARAMETERS
    
    # Parameters of the PV 
    model.PV_Nominal_Capacity = Param(within=NonNegativeReals) # Nominal capacity of the PV in W/unit
    model.Inverter_Efficiency = Param() # Efficiency of the inverter in %
    model.PV_invesment_Cost = Param(within=NonNegativeReals) # Cost of solar panel in USD/W
    model.PV_Energy_Production = Param(model.scenario, model.periods, within=NonNegativeReals, initialize=Initialize_PV_Energy) # Energy produccion of a solar panel in W
    
    # Parameters of the battery bank
    model.Charge_Battery_Efficiency = Param() # Efficiency of the charge of the battery in  %
    model.Discharge_Battery_Efficiency = Param() # Efficiency of the discharge of the battery in %
    model.Deep_of_Discharge = Param() # Deep of discharge of the battery (Deep_of_Discharge) in %
    model.Maximun_Battery_Charge_Time = Param(within=NonNegativeReals) # Minimun time of charge of the battery in hours
    model.Maximun_Battery_Discharge_Time = Param(within=NonNegativeReals) # Maximun time of discharge of the battery  in hours                     
    model.Battery_Reposition_Time = Param(within=NonNegativeReals) # Period of repocition of the battery in years
    model.Battery_Invesment_Cost = Param(within=NonNegativeReals) # Cost of battery 
    
    # Parametes of the diesel generator
    model.Generator_Effiency = Param(within=NonNegativeReals)
    model.Generator_Min_Out_Put = Param(within=NonNegativeReals)
    model.Generator_Efficiency = Param() # Generator efficiency to trasform heat into electricity %
    model.Low_Heating_Value = Param() # Low heating value of the diesel in W/L
    model.Diesel_Cost = Param(within=NonNegativeReals) # Cost of diesel in USD/L
    model.Generator_Invesment_Cost = Param(within=NonNegativeReals) # Cost of the diesel generator  
    model.Marginal_Cost_Generator_1 = Param(initialize=Marginal_Cost_Generator_1)
    model.Cost_Increase = Param(within=NonNegativeReals)
    model.Generator_Nominal_Capacity = Param(within=NonNegativeReals)
    model.Start_Cost_Generator = Param(within=NonNegativeReals, initialize=Start_Cost)  
    model.Marginal_Cost_Generator = Param(initialize=Marginal_Cost_Generator)
    # Parameters of the Energy balance                  
    model.Energy_Demand = Param(model.scenario,model.periods, initialize=Initialize_Demand) # Energy Energy_Demand in W 
    model.Lost_Load_Probability = Param() # Lost load probability in %
    model.Value_Of_Lost_Load = Param(within=NonNegativeReals) # Value of lost load in USD/W

    # Parameters of the proyect
    model.Delta_Time = Param(within=NonNegativeReals) # Time step in hours
    model.Porcentage_Funded = Param(within=NonNegativeReals) # Porcentaje of the total investment that is Porcentage_Porcentage_Funded by a bank or another entity in %
    model.Project_Years = Param(model.years, initialize= Initialize_years) # Years of the project
    model.Maintenance_Operation_Cost_PV = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %                                             
    model.Maintenance_Operation_Cost_Battery = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Maintenance_Operation_Cost_Generator = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Discount_Rate = Param() # Discount rate of the project in %
    model.Interest_Rate_Loan = Param() # Interest rate of the loan in %
    model.Scenario_Weight = Param(model.scenario, within=NonNegativeReals)
    
    # VARIABLES
    
    # Variables associated to the solar panels
    model.PV_Units = Var(within=NonNegativeReals) # Number of units of solar panels
    model.Total_Energy_PV = Var(model.scenario,model.periods, within=NonNegativeReals) # Energy generated for the Pv sistem in Wh
    
    # Variables associated to the battery bank
    model.Battery_Nominal_Capacity = Var(within=NonNegativeReals) # Capacity of the battery bank in Wh
    model.Energy_Battery_Flow_Out = Var(model.scenario,model.periods, within=NonNegativeReals) # Battery discharge energy in wh
    model.Energy_Battery_Flow_In = Var(model.scenario,model.periods, within=NonNegativeReals) # Battery charge energy in wh
    model.State_Of_Charge_Battery = Var(model.scenario,model.periods, within=NonNegativeReals) # State of Charge of the Battery in wh
    model.Maximun_Charge_Power= Var() # Maximun charge power in w
    model.Maximun_Discharge_Power = Var() #Maximun discharge power in w
    
     # Variables associated to the diesel generator
    
    model.Period_Total_Cost_Generator = Var(model.scenario,model.periods, within=NonNegativeReals)    
    model.Energy_Generator_Total = Var(model.scenario, model.periods, within=NonNegativeReals)
    model.Binary_generator_1 = Var(model.scenario,model.periods, within=Binary)
    model.Integer_generator = Var(within=NonNegativeIntegers)
    model.Total_Cost_Generator = Var(model.scenario,within=NonNegativeReals)  
    model.Generator_Total_Period_Energy = Var(model.scenario,model.periods, within=NonNegativeReals)   
    model.Generator_Energy_Integer = Var(model.scenario, model.periods, within=NonNegativeIntegers)
    model.Last_Energy_Generator = Var(model.scenario, model.periods, within=NonNegativeReals)
    
    # Varialbles associated to the energy balance
    model.Lost_Load = Var(model.scenario,model.periods, within=NonNegativeReals) # Energy not suply by the system kWh
    model.Energy_Curtailment = Var(model.scenario,model.periods, within=NonNegativeReals) # Curtailment of solar energy in kWh
    
    # Variables associated to the project
    model.Cost_Financial = Var(within=NonNegativeReals) # Financial cost of each period in USD
    model.Initial_Inversion = Var(within=NonNegativeReals)
    model.Operation_Maintenance_Cost = Var(within=NonNegativeReals)
    model.Total_Finalcial_Cost = Var(within=NonNegativeReals)
    model.Battery_Reposition_Cost = Var(within=NonNegativeReals)
    model.Scenario_Lost_Load_Cost = Var(model.scenario, within=NonNegativeReals) ####  
    model.Sceneario_Generator_Total_Cost = Var(model.scenario, within=NonNegativeReals)
    model.Scenario_Net_Present_Cost = Var(model.scenario, within=NonNegativeReals)

def Model_Creation_Integer(model,Renewable_Penetration, Battery_Independency):
    
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.
    The problem is solved by discretizing the efficiency curve of the generators and uses binary variables
    
    :param model: Pyomo model as defined in the Micro-Grids library.
    
    '''
    from pyomo.environ import  Param, RangeSet, NonNegativeReals, Var, NonNegativeIntegers
    from Initialize import Initialize_years, Initialize_Demand, Marginal_Cost_Generator, Start_Cost, Marginal_Cost_Generator_1, Capital_Recovery_Factor,Battery_Reposition_Cost, Initialize_Renewable_Energy,Min_Bat_Capacity  # Import library with initialitation funtions for the parameters
    # Time parameters
    model.Periods = Param(within=NonNegativeReals) # Number of periods of analysis of the energy variables
    model.Years = Param() # Number of years of the project
    model.StartDate = Param() # Start date of the analisis

    model.Scenarios = Param()  

    model.Renewable_Source = Param()
    model.Generator_Type = Param()
    
    #SETS
    model.periods = RangeSet(1, model.Periods) # Creation of a set from 1 to the number of periods in each year
    model.years = RangeSet(1, model.Years) # Creation of a set from 1 to the number of years of the project
    model.scenario = RangeSet(1, model.Scenarios) # Creation of a set from 1 to the numbero scenarios to analized
    model.renewable_source = RangeSet(1, model.Renewable_Source)
    model.generator_type = RangeSet(1, model.Generator_Type)
    
    # PARAMETERS
    model.Scenario_Weight = Param(model.scenario, within=NonNegativeReals)
    # Parameters of the PV 
    model.Renewable_Nominal_Capacity = Param(model.renewable_source, 
                                             within=NonNegativeReals)
    model.Inverter_Efficiency_Renewable = Param(model.renewable_source, 
                                                within=NonNegativeReals)
    model.Renewable_Invesment_Cost = Param(model.renewable_source, 
                                           within=NonNegativeReals)
    model.Renewable_Energy_Production = Param(model.scenario, 
                                              model.renewable_source, 
                                              model.periods,
                                              initialize=Initialize_Renewable_Energy)
    
    
 #instance.Renewable_Invesment_Cost.extract_values()   
    # Parameters of the battery bank
    model.Charge_Battery_Efficiency = Param() # Efficiency of the charge of the battery in  %
    model.Discharge_Battery_Efficiency = Param() # Efficiency of the discharge of the battery in %
    model.Deep_of_Discharge = Param() # Deep of discharge of the battery (Deep_of_Discharge) in %
    model.Maximun_Battery_Charge_Time = Param(within=NonNegativeReals) # Minimun time of charge of the battery in hours
    model.Maximun_Battery_Discharge_Time = Param(within=NonNegativeReals) # Maximun time of discharge of the battery  in hours                     
    model.Battery_Electronic_Invesmente_Cost = Param(within=NonNegativeReals)
    model.Battery_Invesment_Cost = Param(within=NonNegativeReals) # Cost of battery 
    model.Battery_Cycles = Param(within=NonNegativeReals)
    model.Battery_Reposition_Cost = Param(within=NonNegativeReals, 
                                          initialize=Battery_Reposition_Cost)
   
    if  Battery_Independency > 0:
        model.Battery_Independency = Battery_Independency
        model.Battery_Min_Capacity = Param(initialize=Min_Bat_Capacity)
    
    # Parametes of the diesel generator
    model.Generator_Min_Out_Put = Param(model.generator_type,
                                        within=NonNegativeReals)
    model.Generator_Efficiency = Param(model.generator_type) # Generator efficiency to trasform heat into electricity %
    model.Low_Heating_Value = Param(model.generator_type) # Low heating value of the diesel in W/L
    model.Fuel_Cost = Param(model.generator_type,
                              within=NonNegativeReals) # Cost of diesel in USD/L
    model.Generator_Invesment_Cost = Param(model.generator_type,within=NonNegativeReals) # Cost of the diesel generator  
    model.Marginal_Cost_Generator_1 = Param(model.generator_type,
                                            initialize=Marginal_Cost_Generator_1)
    model.Cost_Increase = Param(model.generator_type,
                                within=NonNegativeReals)
    model.Generator_Nominal_Capacity = Param(model.generator_type,
                                             within=NonNegativeReals)
    model.Start_Cost_Generator = Param(model.generator_type,
                                       within=NonNegativeReals, initialize=Start_Cost)  
    model.Marginal_Cost_Generator = Param(model.generator_type,
                                          initialize=Marginal_Cost_Generator)
    
    # Parameters of the Energy balance                  
    model.Energy_Demand = Param(model.scenario,model.periods, initialize=Initialize_Demand) # Energy Energy_Demand in W 
    model.Lost_Load_Probability = Param() # Lost load probability in %
    model.Value_Of_Lost_Load = Param(within=NonNegativeReals) # Value of lost load in USD/W
    if Renewable_Penetration > 0:
        model.Renewable_Penetration =  Renewable_Penetration
    # Parameters of the proyect
    model.Delta_Time = Param(within=NonNegativeReals) # Time step in hours
    model.Project_Years = Param(model.years, initialize= Initialize_years) # Years of the project
    model.Maintenance_Operation_Cost_Renewable = Param(model.renewable_source, within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %                                             
    model.Maintenance_Operation_Cost_Battery = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Maintenance_Operation_Cost_Generator = Param(model.generator_type,
                                                       within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Discount_Rate = Param() # Discount rate of the project in %

    model.Capital_Recovery_Factor = Param(within=NonNegativeReals, initialize= Capital_Recovery_Factor) 
    # VARIABLES
    
    # Variables associated to the solar panels
      
    model.Renewable_Units = Var(model.renewable_source, within=NonNegativeReals,bounds= (0,1000))
    
    # Variables associated to the battery bank
    model.Battery_Nominal_Capacity = Var(within=NonNegativeReals,bounds= (0,700000)) # Capacity of the battery bank in Wh
    model.Energy_Battery_Flow_Out = Var(model.scenario,model.periods, within=NonNegativeReals) # Battery discharge energy in wh
    model.Energy_Battery_Flow_In = Var(model.scenario,model.periods, within=NonNegativeReals) # Battery charge energy in wh
    model.State_Of_Charge_Battery = Var(model.scenario,model.periods, within=NonNegativeReals) # State of Charge of the Battery in wh
    


    def gen(model,g):
        if g == 1:
            return 2
        else:
            return 0
    
    def bounds_N(model,g):
        if g == 1:
            return (0,3)
        else:
            return (0,2)
    def bounds_E(model,s,g,t):
        if g == 1:
            return (0,3)
        else:
            return (0,2)    
     # Variables associated to the diesel generator
    
    model.Energy_Generator_Total = Var(model.scenario,model.generator_type,
                                       model.periods, within=NonNegativeReals)
    model.Integer_generator = Var(model.generator_type,
                                  within=NonNegativeIntegers, 
                                  initialize=gen, 
                                  bounds=bounds_N)
    
    model.Generator_Total_Period_Energy = Var(model.scenario,
                                              model.generator_type,
                                              model.periods, 
                                              within=NonNegativeReals)   
    model.Generator_Energy_Integer = Var(model.scenario, model.generator_type,
                                         model.periods, within=NonNegativeIntegers,
                                         bounds=bounds_E)
    model.Last_Energy_Generator = Var(model.scenario, model.generator_type,
                                      model.periods, within=NonNegativeReals)
    
    # Varialbles associated to the energy balance
    model.Lost_Load = Var(model.scenario,model.periods, within=NonNegativeReals) # Energy not suply by the system kWh
    model.Energy_Curtailment = Var(model.scenario,model.periods, 
                                   within=NonNegativeReals,bounds=(0,100000)) # Curtailment of solar energy in kWh
    
    
    
def Model_Creation_Dispatch(model):
    
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.
    The problem is solved by discretizing the efficiency curve of the generators and uses binary variables
    
    :param model: Pyomo model as defined in the Micro-Grids library.
    
    '''
    from pyomo.environ import  Param, RangeSet, NonNegativeReals, Var, NonNegativeIntegers
    from Initialize import Initialize_Demand, Initialize_PV_Energy, Initialize_Demand_Dispatch, Initialize_PV_Energy_Dispatch, Marginal_Cost_Generator_Dispatch, Start_Cost_Dispatch,Marginal_Cost_Generator_1_Dispatch, Battery_Reposition_Cost  # Import library with initialitation funtions for the parameters
    
    
    # Time parameters
    model.Periods = Param(within=NonNegativeReals) # Number of periods of analysis of the energy variables 
    model.StartDate = Param() # Start date of the analisis
    model.PlotTime = Param() # Quantity of days that are going to be plot
    model.PlotDay = Param() # Start day for the plot
    
    #SETS
    model.periods = RangeSet(1, model.Periods) # Creation of a set from 1 to the number of periods in each year   
    # PARAMETERS
    
    # Parameters of the PV 

    model.Total_Energy_PV = Param(model.periods, within=NonNegativeReals, 
                                  initialize=Initialize_PV_Energy_Dispatch) # Energy produccion of a solar panel in W
    
    # Parameters of the battery bank
    model.Charge_Battery_Efficiency = Param() # Efficiency of the charge of the battery in  %
    model.Discharge_Battery_Efficiency = Param() # Efficiency of the discharge of the battery in %
    model.Deep_of_Discharge = Param() # Deep of discharge of the battery (Deep_of_Discharge) in %
    model.Maximun_Battery_Charge_Time = Param(within=NonNegativeReals) # Minimun time of charge of the battery in hours
    model.Maximun_Battery_Discharge_Time = Param(within=NonNegativeReals) # Maximun time of discharge of the battery  in hours                     
    model.Battery_Nominal_Capacity = Param(within=NonNegativeReals) # Capacity of the battery bank in Wh   
    model.Battery_Initial_SOC = Param(within=NonNegativeReals) 
    
    model.Battery_Electronic_Invesmente_Cost = Param(within=NonNegativeReals)
    model.Battery_Invesment_Cost = Param(within=NonNegativeReals) # Cost of battery 
    model.Battery_Cycles = Param(within=NonNegativeReals)
    model.Unitary_Battery_Reposition_Cost = Param(within=NonNegativeReals, 
                                          initialize=Battery_Reposition_Cost)
    # Parametes of the diesel generator
    model.Generator_Efficiency = Param(within=NonNegativeReals)
    model.Generator_Min_Out_Put = Param(within=NonNegativeReals)
    model.Low_Heating_Value = Param() # Low heating value of the diesel in W/L
    model.Diesel_Cost = Param(within=NonNegativeReals) # Cost of diesel in USD/L
    model.Marginal_Cost_Generator_1 = Param(initialize=Marginal_Cost_Generator_1_Dispatch)
    model.Cost_Increase = Param(within=NonNegativeReals)
    model.Generator_Nominal_Capacity = Param(within=NonNegativeReals)
    model.Start_Cost_Generator = Param(within=NonNegativeReals, initialize=Start_Cost_Dispatch)  
    model.Marginal_Cost_Generator = Param(initialize=Marginal_Cost_Generator_Dispatch)
    
    # Parameters of the Energy balance                  
    model.Energy_Demand = Param(model.periods, initialize=Initialize_Demand_Dispatch) # Energy Energy_Demand in W 
    model.Lost_Load_Probability = Param() # Lost load probability in %
    model.Value_Of_Lost_Load = Param(within=NonNegativeReals) # Value of lost load in USD/W
    
    # Parameters of the proyect
    model.Delta_Time = Param(within=NonNegativeReals) # Time step in hours
   
    # VARIABLES
            
    # Variables associated to the battery bank
    
    model.Energy_Battery_Flow_Out = Var(model.periods, within=NonNegativeReals) # Battery discharge energy in wh
    model.Energy_Battery_Flow_In = Var(model.periods, within=NonNegativeReals) # Battery charge energy in wh
    model.State_Of_Charge_Battery = Var(model.periods, within=NonNegativeReals) # State of Charge of the Battery in wh
    model.Maximun_Charge_Power= Var(within=NonNegativeReals) # Maximun charge power in w
    model.Maximun_Discharge_Power = Var(within=NonNegativeReals) #Maximun discharge power in w
    model.Battery_Yearly_cost = Var(within=NonNegativeReals)
    
     # Variables associated to the diesel generator
    
    model.Period_Total_Cost_Generator = Var(model.periods, within=NonNegativeReals)    
    model.Energy_Generator_Total = Var(model.periods, within=NonNegativeReals)
    model.Integer_generator = Var(within=NonNegativeIntegers)
    model.Total_Cost_Generator = Var(within=NonNegativeReals)  
    model.Generator_Total_Period_Energy = Var(model.periods, within=NonNegativeReals)   
    model.Generator_Energy_Integer = Var(model.periods, within=NonNegativeIntegers)
    model.Last_Energy_Generator = Var(model.periods, within=NonNegativeReals)
    
    # Varialbles associated to the energy balance
    model.Lost_Load = Var(model.periods, within=NonNegativeReals) # Energy not suply by the system kWh
    model.Energy_Curtailment = Var(model.periods, within=NonNegativeReals) # Curtailment of solar energy in kWh
    
    # Variables associated to the project
    
    
    model.Scenario_Lost_Load_Cost = Var(within=NonNegativeReals) ####  
   

