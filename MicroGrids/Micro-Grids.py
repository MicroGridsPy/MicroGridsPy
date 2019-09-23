# -*- coding: utf-8 -*-


from pyomo.environ import  AbstractModel

from Results import Plot_Energy_Total, Load_results1,  Load_results1_binary, \
Load_results2_binary, Energy_Mix, Print_Results,Print_Results_Dispatch, \
Load_results1_Dispatch, Load_results2_Dispatch, Integer_Scenarios,\
Integer_Scenario_Information, Integer_Time_Series, integer_Renewable_Energy,\
Integer_Data_Renewable, Integer_Generator_time_series, Energy_Mix_Dispatch, \
Integer_Generator_Data, Integer_Results, Economic_Analysis, Dispatch_Economic_Analysis
from Model_Creation import Model_Creation, Model_Creation_binary,\
Model_Creation_Integer, Model_Creation_Dispatch
from Model_Resolution import Model_Resolution, Model_Resolution_binary,\
Model_Resolution_Integer, Model_Resolution_Dispatch
#21212
# Type of problem formulation:
formulation = 'Integer' # there are 4 formulations LP, Integer, Binary and Dispatch

# Renewable energy penetrarion

Renewable_Penetration = 0 # a number from 0 to 1.a
Battery_Independency = 0  # number of days of battery independency

S = 3 # Plot scenario
Plot_Date = '25/12/2016 00:00:00' # Day-Month-Year
PlotTime = 5# Days of the plot
plot = 'No Average' # 'No Average' or 'Average'

model = AbstractModel() # define type of optimization problem

if formulation == 'LP':
    # Optimization model
        
    Model_Creation(model, Renewable_Penetration, Battery_Independency) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution(model,Renewable_Penetration,
                                Battery_Independency) # Resolution of the instance
    ## Upload the resulst from the instance and saving it in excel files
    Data = Load_results1(instance) # Extract the results of energy from the instance and save it in a excel file 
    Scenarios =  Data[3]
    Scenario_Probability = Data[5].loc['Scenario Weight'] 
    Generator_Data = Data[4]
    Data_Renewable = Data[7]
    Results = Data[2]
    LCOE = Data[6]
    # Energy Plot    

    Time_Series = Integer_Time_Series(instance,Scenarios, S) 
    Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)
    # Data Analisys
    Print_Results(instance, Generator_Data, Data_Renewable, Results, 
              LCOE,formulation)  
    Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)

elif formulation == 'Binary':
    Model_Creation_binary(model) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution_binary(model) # Resolution of the instance    
    Time_Series = Load_results1_binary(instance) # Extract the results of energy from the instance and save it in a excel file 
    Results = Load_results2_binary(instance) # Save results into a excel file
elif formulation =='Integer':
    Model_Creation_Integer(model, Renewable_Penetration, Battery_Independency)
    instance = Model_Resolution_Integer(model,Renewable_Penetration, Battery_Independency)
    Scenarios = Integer_Scenarios(instance) # Extract the results of energy from the instance and save it in a excel file 
    Scenario_Information = Integer_Scenario_Information(instance)
    
    Renewable_Energy = integer_Renewable_Energy(instance, Scenarios)
    Data_Renewable = Integer_Data_Renewable(instance)
    Generator_Time_Series = Integer_Generator_time_series(instance, Scenarios)
    Generator_Data = Integer_Generator_Data(instance)
    Results = Integer_Results(instance)
    
    NPC,LCOE = Economic_Analysis(Scenarios, Scenario_Information, Renewable_Energy, Data_Renewable,
                      Generator_Time_Series, Generator_Data, Results)

    Scenario_Probability = Scenario_Information.loc['Scenario Weight']  
    # Energy Plot    

    Time_Series = Integer_Time_Series(instance,Scenarios, S) 
    Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)
    # Data Analisys
    Print_Results(instance, Generator_Data, Data_Renewable, Results, 
              LCOE,formulation)  
    Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)
    
elif formulation =='Dispatch':
    Model_Creation_Dispatch(model)
    instance = Model_Resolution_Dispatch(model)
    # Extract the results of energy from the instance and save it in a excel file 
    Time_Series = Load_results1_Dispatch(instance) 
    Results = Load_results2_Dispatch(instance)     
    # Energy Plot
    Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)
    # Economic analysis
    Time_Series = Load_results1_Dispatch(instance) 
    Economic_Results = Dispatch_Economic_Analysis(Results,Time_Series)
    # Data Analisys
    Print_Results_Dispatch(instance, Economic_Results)
    Energy_Mix_Dispatch(instance,Time_Series)