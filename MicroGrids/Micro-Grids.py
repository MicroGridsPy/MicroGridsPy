# -*- coding: utf-8 -*-

from pyomo.environ import  AbstractModel

from Results import Plot_Energy_Total, Load_results1,  Load_results1_binary, \
Load_results2_binary, Energy_Mix, Print_Results,Print_Results_Dispatch, \
Load_results1_Dispatch, Load_results2_Dispatch, Energy_Mix_Dispatch, \
Dispatch_Economic_Analysis, Integer_Time_Series
from Model_Creation import Model_Creation, Model_Creation_binary,\
Model_Creation_Dispatch
from Model_Resolution import Model_Resolution, Model_Resolution_binary,\
 Model_Resolution_Dispatch
import time 
start = time.time()

# Type of problem formulation:
formulation = 'LP'
#datapath='Example/Dispatch/'
# Renewable energy penetrarion

Renewable_Penetration  =  0 # a number from 0 to 1
Battery_Independency   =  0    # number of days of battery independency
Lost_Load_Probability  =  0   # Allowed percentage of unmed demand in the system
Curtailment_Unitary_Cost =  0 # probando curtailment cost 0

S = 1 # Plot scenario
Plot_Date = '31/01/2016 00:00:00' # Day-Month-Year
PlotTime = 5# Days of the plot
plot = 'No Average' # 'No Average' or 'Average'

model = AbstractModel() # define type of optimization problem

if formulation == 'LP' or formulation == 'MILP':
    # Optimization model
    model.formulation = formulation
    model.Lost_Load_Probability =  Lost_Load_Probability  
    model.Curtailment_Unitary_Cost = Curtailment_Unitary_Cost
    Model_Creation(model, Renewable_Penetration, Battery_Independency)  
    instance = Model_Resolution(model, Renewable_Penetration, Battery_Independency) 
    ## Upload the resulst from the instance and saving it in excel files
    Data = Load_results1(instance) 
    Scenarios =  Data[3]
    Scenario_Probability = Data[5].loc['Scenario Weight'] 
    Generator_Data = Data[4]
    Data_Renewable = Data[6]
    Battery_Data = Data[7]
    Results = Data[0]

    # Energy Plot    

#    Time_Series = Integer_Time_Series(instance,Scenarios, S, Data) 
#    Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)
    # Data Analisys
    Print_Results(instance, Generator_Data, Data_Renewable, Battery_Data ,Results, 
             formulation)  
    Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)

elif formulation == 'Binary':
    Model_Creation_binary(model) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution_binary(model) # Resolution of the instance    
    Time_Series = Load_results1_binary(instance) # Extract the results of energy from the instance and save it in a excel file 
    Results = Load_results2_binary(instance) # Save results into a excel file
    
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

end = time.time()
print('The optimization take ' + str(round(end - start,0)) + ' segundos')



