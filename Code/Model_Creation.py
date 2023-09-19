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


from pyomo.environ import Param, RangeSet, NonNegativeReals, Var, Set, Reals 
from Initialize import * # Import library with initialitation funtions for the parameters


def Model_Creation(model, Renewable_Penetration,Battery_Independence):

#%% PARAMETERS  

    "Project parameters"
    model.Periods         = Param(within=NonNegativeReals)                          # Number of periods of analysis of the energy variables
    model.Years           = Param(within=NonNegativeReals)                          # Number of years of the project
    model.Step_Duration   = Param(within=NonNegativeReals)
    model.Min_Last_Step_Duration = Param(within=NonNegativeReals)
    model.Delta_Time      = Param(within=NonNegativeReals)                          # Time step in hours
    model.StartDate       = Param()                                                 # Start date of the analisis
    model.Scenarios       = Param(within=NonNegativeReals) 
    model.Discount_Rate   = Param(within=NonNegativeReals)                          # Discount rate of the project in %
    model.Investment_Cost_Limit = Param(within=NonNegativeReals)
    model.Steps_Number = Param(initialize = Initialize_Upgrades_Number)
    model.RES_Sources     = Param(within=NonNegativeReals)
    model.Generator_Types = Param(within=NonNegativeReals)
    model.Grid_Connection = Param(within=NonNegativeReals)
    model.Grid_Availability_Simulation = Param(within=NonNegativeReals)
    model.Year_Grid_Connection = Param(within=NonNegativeReals)                     
    model.RE_Supply_Calculation = Param(within=NonNegativeReals)
    model.Demand_Profile_Generation = Param(within=NonNegativeReals)
    
    "Sets"
    model.periods = RangeSet(1, model.Periods)                                      # Creation of a set from 1 to the number of periods in each year
    model.years = RangeSet(1, model.Years)                                          # Creation of a set from 1 to the number of years of the project
    model.scenarios = RangeSet(1, model.Scenarios)                                  # Creation of a set from 1 to the number of scenarios to analized
    model.renewable_sources = RangeSet(1, model.RES_Sources)                        # Creation of a set from 1 to the number of RES technologies to analized
    model.generator_types = RangeSet(1, model.Generator_Types)                      # Creation of a set from 1 to the number of generators types to analized
    model.steps = RangeSet(1, model.Steps_Number)                                   # Creation of a set from 1 to the number of investment decision steps
    model.years_steps = Set(dimen = 2, initialize=Initialize_YearUpgrade_Tuples)    # 2D set of tuples: it associates each year to the corresponding investment decision step
    model.years_grid_connection = RangeSet(model.Year_Grid_Connection,model.Years)  # Creation of a set from year of grid connection to last year
    model.Scenario_Weight = Param(model.scenarios, 
                                  within=NonNegativeReals) 
    
    "Parameters of RES" 
    model.RES_Names                    = Param(model.renewable_sources)               # RES names
    model.RES_Nominal_Capacity         = Param(model.renewable_sources,
                                               within=NonNegativeReals)               # Nominal capacity of the RES in W/unit
    model.RES_Inverter_Efficiency      = Param(model.renewable_sources)               # Efficiency of the inverter in %
    model.RES_Specific_Investment_Cost = Param(model.renewable_sources,
                                               within=NonNegativeReals)               # Cost of RES in USD/W
    model.RES_Specific_OM_Cost         = Param(model.renewable_sources,
                                               within=NonNegativeReals)               # Percentage of the total investment spend in operation and management of solar panels in each period in %                                             
    model.RES_Lifetime                 = Param(model.renewable_sources,
                                               within=NonNegativeReals)
    model.RES_units                    = Param(model.renewable_sources,
                                               within=NonNegativeReals)
    model.RES_years                    = Param(model.renewable_sources,
                                               within=NonNegativeReals)
    model.RES_unit_CO2_emission        = Param(model.renewable_sources,
                                               within=NonNegativeReals)                                    
    model.RES_Unit_Energy_Production   = Param(model.scenarios,
                                              model.renewable_sources,
                                              model.periods, 
                                              within=NonNegativeReals, 
                                              initialize=Initialize_RES_Energy)      # Energy production of a RES in Wh
    if Renewable_Penetration > 0:
        model.Renewable_Penetration = Renewable_Penetration
    
    "Parameters of the battery bank"
    model.Battery_Specific_Investment_Cost = Param(within=NonNegativeReals)                                     # Specific investment cost of the battery bank [USD/Wh]
    model.Battery_Specific_Electronic_Investment_Cost = Param(within=NonNegativeReals)   # Specific investment cost of non-replaceable parts (electronics) of the battery bank [USD/Wh]
    model.Battery_Specific_OM_Cost = Param(within=NonNegativeReals)                      # Percentage of the total investment spend in operation and management of batteries in each period in %
    model.Battery_Discharge_Battery_Efficiency = Param(within=NonNegativeReals)                                 # Efficiency of the discharge of the battery in %
    model.Battery_Charge_Battery_Efficiency    = Param(within=NonNegativeReals)                                 # Efficiency of the charge of the battery in  %
    model.Battery_Depth_of_Discharge       = Param()                                     # Depth of discharge of the battery (Depth_of_Discharge) in %
    model.Maximum_Battery_Discharge_Time   = Param(within=NonNegativeReals)              # Minimum time of charge of the battery in hours
    model.Maximum_Battery_Charge_Time      = Param(within=NonNegativeReals)              # Maximum time of discharge of the battery in hours                     
    model.Battery_Cycles                   = Param(within=NonNegativeReals)
    model.Unitary_Battery_Replacement_Cost = Param(within=NonNegativeReals, 
                                                   initialize=Initialize_Battery_Unit_Repl_Cost)
    model.Battery_Initial_SOC = Param(within=NonNegativeReals)
    model.Battery_capacity    = Param(within=NonNegativeReals)
    model.BESS_unit_CO2_emission = Param(within=NonNegativeReals)
    if  Battery_Independence > 0:
        model.Battery_Independence = Battery_Independence
        model.Battery_Min_Capacity = Param(model.steps, 
                                           initialize=Initialize_Battery_Minimum_Capacity)

    "Parameters of the genset"
    model.Generator_Names             = Param(model.generator_types)                # Generators names
    model.Generator_Efficiency        = Param(model.generator_types,
                                              within=NonNegativeReals)              # Generator efficiency to trasform heat into electricity %
    model.Generator_Specific_Investment_Cost = Param(model.generator_types,
                                                     within=NonNegativeReals)       # Cost of the diesel generator
    model.Generator_Specific_OM_Cost  = Param(model.generator_types,
                                              within=NonNegativeReals)              # Cost of the diesel generator
    model.Generator_Lifetime          = Param(model.generator_types,
                                              within=NonNegativeReals)    
    model.Fuel_Names                  = Param(model.generator_types)                # Fuel names
    model.Fuel_LHV                    = Param(model.generator_types,
                                              within=NonNegativeReals)              # Low heating value of the fuel in kg/l
    model.Generator_capacity          = Param(model.generator_types, 
                                              within=NonNegativeReals)
    model.GEN_years                   = Param(model.generator_types,
                                               within=NonNegativeReals)
    model.GEN_unit_CO2_emission       = Param(model.generator_types,
                                              within=NonNegativeReals)
    model.FUEL_unit_CO2_emission      = Param(model.generator_types,
                                              within=NonNegativeReals)
    model.Fuel_Specific_Cost          = Param(model.generator_types, 
                                              within=NonNegativeReals)
    model.Generator_Marginal_Cost     = Param(model.scenarios, 
                                              model.years, 
                                              model.generator_types,
                                              initialize=Initialize_Generator_Marginal_Cost)   
    "Parameters of the National Grid" ####
    model.Grid_Sold_El_Price           = Param(within=NonNegativeReals)
    model.Grid_Purchased_El_Price      = Param(within=NonNegativeReals)
    model.Grid_Lifetime                = Param(within=NonNegativeReals)
    model.Grid_Distance                = Param(within=NonNegativeReals)
    model.Grid_Connection_Cost         = Param(within=NonNegativeReals)
    model.Grid_Maintenance_Cost        = Param(within=NonNegativeReals)
    model.Maximum_Grid_Power           = Param(within=NonNegativeReals)
    model.Grid_Availability            = Param(model.scenarios,
                                               model.years,
                                               model.periods,
                                               initialize = Initialize_Grid_Availability)
    model.Grid_Average_Number_Outages  = Param(within=NonNegativeReals) 
    model.Grid_Average_Outage_Duration = Param(within=NonNegativeReals)                
    model.Grid_Connection_Type         = Param(within=NonNegativeReals)
    model.National_Grid_Specific_CO2_emissions = Param(within=NonNegativeReals)
    model.National_Grid_Investment_Cost = Param(within=NonNegativeReals, 
                                                initialize=Initialize_National_Grid_Inv_Cost)
    model.National_Grid_OM_Cost = Param(within=NonNegativeReals, 
                                                initialize=Initialize_National_Grid_OM_Cost)
    "Parameters of the electricity balance"                  
    model.Energy_Demand           = Param(model.scenarios, 
                                          model.years, 
                                          model.periods, 
                                          initialize=Initialize_Demand)             # Energy Energy_Demand in W 
    model.Lost_Load_Fraction      = Param(within=NonNegativeReals)                  # Lost load maxiumum admittable fraction in %
    model.Lost_Load_Specific_Cost = Param(within=NonNegativeReals)                  # Value of lost load in USD/Wh 

    "Parameters for the grid routing"
    model.CRS = Param(within=NonNegativeReals)  # Desired CRS for the projection of the geographical coordinates [-]
    model.Max_y = Param()   # Maximum latitude of the study area [-]                                                   
    model.Min_y = Param()    # Minimum latitude of the study area [-]                                                   
    model.Max_x = Param()    # Maximum longitude of the study area [-]
    model.Min_x = Param()    # Minimum latitude of the study area [-]
    model.Specific_Line_Cost = Param(within=NonNegativeReals)    # Specific cost of the distribution line considering LV line, panelboards and poles [USD/km]
    model.Meter_Cost = Param(within=NonNegativeReals)     # Specific cost of metering system [USD/unit]
   

    "Parameters of the plot"
    model.RES_Colors        = Param(model.renewable_sources)                        # HEX color codes for RES
    model.Battery_Color     = Param()                                               # HEX color codes for Battery bank
    model.Generator_Colors  = Param(model.generator_types)                          # HEX color codes for Generators
    model.Lost_Load_Color   = Param()                                               # HEX color codes for Lost load
    model.Curtailment_Color = Param()                                               # HEX color codes for Curtailment
    model.Energy_To_Grid_Color = Param()                                            # HEX color codes for Energy to grid
    model.Energy_From_Grid_Color = Param()                                          # HEX color codes for Energy from grid
    
#%% VARIABLES

    "Variables associated to the RES"
    model.RES_Units             = Var(model.steps, 
                                      model.renewable_sources,
                                      within=NonNegativeReals)                      # Number of units of RES
    model.RES_Energy_Production = Var(model.scenarios, 
                                      model.years,
                                      model.renewable_sources,
                                      model.periods,
                                      within=NonNegativeReals)                      # Energy generated by the RES sistem in Wh
    model.RES_emission          = Var(within=NonNegativeReals)

    "Variables associated to the battery bank"
    model.Battery_Nominal_Capacity        = Var(model.steps, 
                                                within=NonNegativeReals)            # Capacity of the battery bank in Wh
    model.Battery_Outflow                 = Var(model.scenarios, 
                                                model.years, 
                                                model.periods,
                                                within=NonNegativeReals)            # Battery discharge energy in Wh
    model.Battery_Inflow                  = Var(model.scenarios,
                                                model.years, 
                                                model.periods, 
                                                within=NonNegativeReals)            # Battery charge energy in Wh
    
    model.Battery_SOC                     = Var(model.scenarios, 
                                                model.years, 
                                                model.periods, 
                                                within=NonNegativeReals)            # State of Charge of the Battery in Wh
    model.Battery_Maximum_Charge_Power    = Var(model.steps, 
                                                within=NonNegativeReals)
    model.Battery_Maximum_Discharge_Power = Var(model.steps,
                                                within=NonNegativeReals)
    model.Battery_Replacement_Cost_Act    = Var(model.scenarios,
                                                within=NonNegativeReals)
    model.Battery_Replacement_Cost_NonAct = Var(model.scenarios,
                                                within=NonNegativeReals)
    model.BESS_emission                   = Var(within=NonNegativeReals)

    "Variables associated to the diesel generator"
    model.Generator_Nominal_Capacity  = Var(model.steps, 
                                            model.generator_types,
                                            within=NonNegativeReals)                # Capacity  of the diesel generator in Wh
    model.Generator_Energy_Production = Var(model.scenarios, 
                                            model.years,
                                            model.generator_types,
                                            model.periods, 
                                            within=NonNegativeReals)                # Energy generated by the Diesel generator
    model.Total_Fuel_Cost_Act         = Var(model.scenarios,
                                            model.generator_types,
                                            within=NonNegativeReals)
    model.Total_Fuel_Cost_NonAct      = Var(model.scenarios, 
                                            model.generator_types,
                                            within=NonNegativeReals)
    model.GEN_emission                = Var(within=NonNegativeReals)
    model.FUEL_emission               = Var(model.scenarios, 
                                            model.years,
                                            model.generator_types,
                                            model.periods, 
                                            within=NonNegativeReals)
    model.Scenario_FUEL_emission      = Var(model.scenarios,
                                            within=NonNegativeReals)
    
    "Variable associated to the National Grid"  
    model.Total_Revenues_Act             = Var(model.scenarios,
                                               within=NonNegativeReals)
    model.Total_Revenues_NonAct          = Var(model.scenarios,
                                               within=NonNegativeReals)
    model.Total_Electricity_Cost_Act        = Var(model.scenarios,
                                              within=NonNegativeReals)
    model.Total_Electricity_Cost_NonAct     = Var(model.scenarios,
                                              within=NonNegativeReals)
    model.Energy_To_Grid                 = Var(model.scenarios, 
                                               model.years,
                                               model.periods, 
                                               within=NonNegativeReals)
    model.Energy_From_Grid               = Var(model.scenarios, 
                                               model.years,
                                               model.periods, 
                                               within=NonNegativeReals)
    model.GRID_emission                  = Var(model.scenarios, 
                                                model.years,
                                                model.periods, 
                                                within=NonNegativeReals)    
    model.Scenario_GRID_emission      = Var(model.scenarios,
                                            within=NonNegativeReals)
    "Variables associated to the energy balance"
    model.Lost_Load             = Var(model.scenarios, 
                                      model.years, 
                                      model.periods, 
                                      within=NonNegativeReals)                      # Energy not supplied by the system kWh
    model.Energy_Curtailment    = Var(model.scenarios,
                                      model.years,
                                      model.periods, 
                                      within=NonNegativeReals)                      # Curtailment of RES in kWh
    model.Scenario_Lost_Load_Cost_Act    = Var(model.scenarios, 
                                               within=NonNegativeReals) 
    model.Scenario_Lost_Load_Cost_NonAct = Var(model.scenarios,
                                               within=NonNegativeReals)    
    

    "Variables associated to the project"
    model.Net_Present_Cost                    = Var(within=Reals)
    model.Scenario_Net_Present_Cost           = Var(model.scenarios, 
                                                    within=Reals) 
    model.Total_Variable_Cost                 = Var(within=NonNegativeReals)
    model.CO2_emission                        = Var(within=NonNegativeReals)
    model.Scenario_CO2_emission               = Var(model.scenarios, 
                                                    within=NonNegativeReals)
    model.Investment_Cost                     = Var(within=NonNegativeReals)
    model.Salvage_Value                       = Var(within=NonNegativeReals)   
    model.Total_Variable_Cost_Act             = Var(within=NonNegativeReals) 
    model.Operation_Maintenance_Cost_Act      = Var(within=NonNegativeReals)
    model.Operation_Maintenance_Cost_NonAct   = Var(within=NonNegativeReals)
    model.Total_Scenario_Variable_Cost_Act    = Var(model.scenarios, 
                                                    within=Reals) 
    model.Total_Scenario_Variable_Cost_NonAct = Var(model.scenarios, 
                                                    within=NonNegativeReals) 
    #model.NPC                                 = Var()
    #model.CO2                                 = Var()
        

