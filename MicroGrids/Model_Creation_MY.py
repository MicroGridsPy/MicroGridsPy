"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""

def Model_Creation(model, Renewable_Penetration,Battery_Independency):
    
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.
    
    :param model: Pyomo model as defined in the Micro-Grids library.
    
    '''
    from pyomo.environ import Param, RangeSet, NonNegativeReals, Var, Set 
    from Initialize_MY import Initialize_Demand, Initialize_Fuel_Cost, Unitary_Battery_Reposition_Cost, Initialize_Renewable_Energy, Generator_Marginal_Cost, Min_Bat_Capacity, Initialize_YearUpgrade_Tuples, Initialize_Upgrades_Number # Import library with initialitation funtions for the parameters

    # Time parameters
    model.Periods = Param(within=NonNegativeReals) # Number of periods of analysis of the energy variables
    model.Years = Param() # Number of years of the project
    model.StartDate = Param() # Start date of the analisis
    model.Scenarios = Param() 
    model.Renewable_Sources = Param()
    model.Generator_Types = Param()
    model.Step_Duration = Param()
    model.Min_Last_Step_Duration = Param()
    model.Upgrades_Number = Param(initialize = Initialize_Upgrades_Number)
    
    # SETS
    model.periods = RangeSet(1, model.Periods) # Creation of a set from 1 to the number of periods in each year
    model.years = RangeSet(1, model.Years) # Creation of a set from 1 to the number of years of the project
    model.scenarios = RangeSet(1, model.Scenarios) # Creation of a set from 1 to the number of scenarios to analized
    model.renewable_sources = RangeSet(1, model.Renewable_Sources) # Creation of a set from 1 to the number of RES technologies to analized
    model.generator_types = RangeSet(1, model.Generator_Types) # Creation of a set from 1 to the number of generators types to analized
    model.upgrades = RangeSet(1, model.Upgrades_Number) # Creation of a set from 1 to the number of investment decision steps
    model.yu_tup = Set(dimen = 2, initialize = Initialize_YearUpgrade_Tuples)  # 2D set of tuples: it associates each year to the corresponding investment decision step
    
    # PARAMETERS
    model.Scenario_Weight = Param(model.scenarios, within=NonNegativeReals) 
    
    # Parameters of RES   
    model.Renewable_Nominal_Capacity = Param(model.renewable_sources,
                                             within=NonNegativeReals) # Nominal capacity of the RES in W/unit
    model.Renewable_Inverter_Efficiency = Param(model.renewable_sources) # Efficiency of the inverter in %
    model.Renewable_Investment_Cost = Param(model.renewable_sources,
                                           within=NonNegativeReals) # Cost of RES in USD/W
    model.Renewable_Inv_Cost_Reduction = Param(model.renewable_sources,
                                           within=NonNegativeReals) # Cost of RES in USD/W
    model.Renewable_Lifetime = Param(model.renewable_sources,
                                             within=NonNegativeReals)
    model.Renewable_Energy_Production = Param(model.scenarios,model.renewable_sources,
                                              model.periods, within=NonNegativeReals, 
                                              initialize=Initialize_Renewable_Energy) # Energy production of a RES in W
    
    # Parameters of the battery bank
    model.Charge_Battery_Efficiency = Param() # Efficiency of the charge of the battery in  %
    model.Discharge_Battery_Efficiency = Param() # Efficiency of the discharge of the battery in %
    model.Depth_of_Discharge = Param() # Depth of discharge of the battery (Depth_of_Discharge) in %
    model.Maximum_Battery_Charge_Time = Param(within=NonNegativeReals) # Minimum time of charge of the battery in hours
    model.Maximum_Battery_Discharge_Time = Param(within=NonNegativeReals) # Maximum time of discharge of the battery in hours                     
    model.Battery_Investment_Cost = Param() # Cost of battery 
    model.Battery_Electronic_Investment_Cost = Param(within=NonNegativeReals)
    model.Battery_Cycles = Param(within=NonNegativeReals)
    model.Unitary_Battery_Reposition_Cost = Param(within=NonNegativeReals, 
                                          initialize=Unitary_Battery_Reposition_Cost)
    model.Battery_Initial_SOC = Param(within=NonNegativeReals)
    if  Battery_Independency > 0:
        model.Battery_Independency = Battery_Independency
        model.Battery_Min_Capacity = Param(model.upgrades, initialize=Min_Bat_Capacity)
  
    # Parameters of the diesel generator
    model.Generator_Efficiency = Param(model.generator_types) # Generator efficiency to trasform heat into electricity %
    model.Lower_Heating_Value = Param(model.generator_types) # Low heating value of the diesel in W/L

    model.Fuel_Cost = Param(model.scenarios, model.years, model.generator_types, initialize=Initialize_Fuel_Cost)
    model.Generator_Investment_Cost = Param(model.generator_types,
                                           within=NonNegativeReals) # Cost of the diesel generator
    model.Generator_Marginal_Cost = Param(model.scenarios, model.years, model.generator_types,
                                            initialize=Generator_Marginal_Cost)   
    model.Generator_Lifetime = Param(model.generator_types,
                                           within=NonNegativeReals)    
    # Parameters of the Energy balance                  
    model.Energy_Demand = Param(model.scenarios, model.years, model.periods, 
                                initialize=Initialize_Demand) # Energy Energy_Demand in W 
    model.Lost_Load_Probability = Param(within=NonNegativeReals) # Lost load probability in %
    model.Value_Of_Lost_Load = Param(within=NonNegativeReals) # Value of lost load in USD/W
    if Renewable_Penetration > 0:
        model.Renewable_Penetration =  Renewable_Penetration
   
    # Parameters of the project
    model.Delta_Time = Param(within=NonNegativeReals) # Time step in hours
    model.Renewable_Operation_Maintenance_Cost = Param(model.renewable_sources,
                                                       within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %                                             
    model.Battery_Operation_Maintenance_Cost = Param(within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Generator_Operation_Maintenance_Cost = Param(model.generator_types,
                                                       within=NonNegativeReals) # Percentage of the total investment spend in operation and management of solar panels in each period in %
    model.Discount_Rate = Param() # Discount rate of the project in %
    
    
    # VARIABLES

    # Variables associated to the RES
    model.Renewable_Units = Var(model.upgrades, model.renewable_sources,
                                within=NonNegativeReals) # Number of units of RES
    model.Renewable_Units_Years = Var(model.yu_tup, model.renewable_sources,
                                     within=NonNegativeReals)
    model.Total_Renewable_Energy = Var(model.scenarios, model.years, model.renewable_sources,
                                model.periods, within=NonNegativeReals) # Energy generated by the RES sistem in Wh

    # Variables associated to the battery bank
    model.Battery_Nominal_Capacity = Var(model.upgrades, within=NonNegativeReals) # Capacity of the battery bank in Wh
    model.Energy_Battery_Flow_Out = Var(model.scenarios, model.years, model.periods,
                                        within=NonNegativeReals) # Battery discharge energy in Wh
    model.Energy_Battery_Flow_In = Var(model.scenarios, model.years, model.periods, 
                                       within=NonNegativeReals) # Battery charge energy in Wh
    model.State_Of_Charge_Battery = Var(model.scenarios, model.years, model.periods, 
                                        within=NonNegativeReals) # State of Charge of the Battery in Wh
    model.Maximum_Charge_Power = Var(model.upgrades, within=NonNegativeReals)
    model.Maximum_Discharge_Power = Var(model.upgrades, within=NonNegativeReals)
    
    # Variables associated to the diesel generator
    model.Generator_Nominal_Capacity = Var(model.upgrades, model.generator_types,
                                           within=NonNegativeReals) # Capacity  of the diesel generator in Wh
    model.Total_Generator_Energy = Var(model.scenarios, model.years, model.generator_types,
                                 model.periods, within=NonNegativeReals) # Energy generated by the Diesel generator
    model.Total_Fuel_Cost = Var(model.scenarios, model.generator_types,
                                  within=NonNegativeReals) # actualized fuel cost
    
    
    # Variables associated to the energy balance
    model.Lost_Load = Var(model.scenarios, model.years, model.periods, within=NonNegativeReals) # Energy not supplied by the system kWh
    model.Energy_Curtailment = Var(model.scenarios, model.years, model.periods, within=NonNegativeReals) # Curtailment of RES in kWh
    model.Scenario_Lost_Load_Cost = Var(model.scenarios, within=NonNegativeReals)  #actualized lost load cost
    

    # Variables associated to the project
    model.Net_Present_Cost = Var(within=NonNegativeReals)
    model.Scenario_Net_Present_Cost = Var(model.scenarios, within=NonNegativeReals) 
    model.Investment_Cost = Var(within=NonNegativeReals)
    model.Battery_Replacement_Cost = Var(model.scenarios,within=NonNegativeReals)
    model.Salvage_Value = Var(within=NonNegativeReals)    
    model.Total_Variable_Cost = Var(within=NonNegativeReals)    
    model.Operation_Maintenance_Cost = Var(within=NonNegativeReals) 
    model.Battery_Reposition_Cost = Var(model.scenarios,within=NonNegativeReals)
    model.Total_Scenario_Variable_Cost = Var(model.scenarios,within=NonNegativeReals)
    