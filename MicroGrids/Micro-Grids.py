#####
#MicroGridsPy-Student, v.0.1. 2018/2019
#Based on the original model by Sergio Balderrama and Sylvain Quoilin
#Student version managed by Francesco Lombardi
######
import pandas as pd
from pyomo.environ import  AbstractModel

from Results import Plot_Energy_Total,  Load_results1, Energy_Mix, Print_Results, Integer_Scenarios, Integer_Scenario_Information, \
Integer_Time_Series, integer_Renewable_Energy, Integer_Data_Renewable, Integer_Generator_time_series, \
Integer_Generator_Data, Integer_Results,Economic_Analysis, Integer_Time_Series
from Model_Creation import Model_Creation
from Model_Resolution import Model_Resolution
from Economical_Analysis import Levelized_Cost_Of_Energy


# Type of problem formulation:
formulation = 'LP'

# Renewable energy penetrarion

Renewable_Penetration = 0.6 # a number from 0 to 1.
Battery_Independency = 1  # number of days of battery independency

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
    

else:
    print('Model formulation type not allowed')


# Energy Plot    
S = 1 # Plot scenario
Plot_Date = '07/10/2017 00:00:00' # Day-Month-Year
PlotTime = 7# Days of the plot
Time_Series = Integer_Time_Series(instance,Scenarios, S) 

plot = 'Average' # 'No Average' or 'Average'
Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)


# Data Analisys
Print_Results(instance, Generator_Data, Data_Renewable, Results, LCOE)  
Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)


#index = pd.DatetimeIndex(start='2017-01-01 00:00:00', periods=len(Time_Series), 
#                                   freq=('H'))
##Start_Date = '2017-01-01 00:00:00'
#end_Date = '2017-06-30 00:00:00'
#Time_Series.index = index
#cost = Time_Series['Total Cost Generator'][Start_Date:end_Date].sum()
#curtailment = Time_Series['Curtailment'][Start_Date:end_Date].sum()/1000000
#print(cost)
#print(curtailment)    
