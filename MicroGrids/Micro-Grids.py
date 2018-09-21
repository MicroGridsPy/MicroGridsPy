# -*- coding: utf-8 -*-
#billy rioja
import pandas as pd
from pyomo.environ import  AbstractModel

from Results import Plot_Energy_Total, Load_results1,  Load_results1_binary, \
Load_results2_binary, Energy_Mix, \
Load_results1_Dispatch, Load_results2_Dispatch, Integer_Scenarios, Integer_Scenario_Information, \
Integer_Time_Series, integer_Renewable_Energy, Integer_Data_Renewable, Integer_Generator_time_series, \
Integer_Generator_Data, Integer_Results, Economic_Analysis
from Model_Creation import Model_Creation, Model_Creation_binary, Model_Creation_Integer, Model_Creation_Dispatch
from Model_Resolution import Model_Resolution, Model_Resolution_binary, Model_Resolution_Integer, Model_Resolution_Dispatch
from Economical_Analysis import Levelized_Cost_Of_Energy


# Type of problem formulation:
formulation = 'LP'

# Renewable energy penetrarion

Renewable_Penetration = 0 # a number from 0 to 1.
Battery_Independency = 0  # number of days of battery independency



model = AbstractModel() # define type of optimization problem

if formulation == 'LP':
    # Optimization model
        
    Model_Creation(model, Renewable_Penetration, Battery_Independency) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution(model,Renewable_Penetration, Battery_Independency) # Resolution of the instance


    ## Upload the resulst from the instance and saving it in excel files
    Data = Load_results1(instance) # Extract the results of energy from the instance and save it in a excel file 
    Scenarios =  Data[3]
    Scenario_Probability = Data[5].loc['Scenario Weight'] 
    print(str(Data[6]) + ' $/kW')

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
    print(NPC)
    print(LCOE)
    Scenario_Probability = Scenario_Information.loc['Scenario Weight']  
    
elif formulation =='Dispatch':
    Model_Creation_Dispatch(model)
    instance = Model_Resolution_Dispatch(model)
    Time_Series = Load_results1_Dispatch(instance) # Extract the results of energy from the instance and save it in a excel file 
    Results = Load_results2_Dispatch(instance)


# Energy Plot    
S = 5
Time_Series = Integer_Time_Series(instance,Scenarios, S)    
plot = 'Average' # 'No Average' or 'Average'
Plot_Energy_Total(instance, Time_Series, plot)


Energy_Mix(instance,Scenarios,Scenario_Probability)

#index = pd.DatetimeIndex(start='2017-01-01 00:00:00', periods=len(Time_Series), 
#                                   freq=('H'))
##Start_Date = '2017-01-01 00:00:00'
#end_Date = '2017-06-30 00:00:00'
#Time_Series.index = index
#cost = Time_Series['Total Cost Generator'][Start_Date:end_Date].sum()
#curtailment = Time_Series['Curtailment'][Start_Date:end_Date].sum()/1000000
#print(cost)
#print(curtailment)    

    
