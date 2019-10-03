"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""


############### MULTI-YEAR CAPACITY-EXPANSION MODEL ###########################

from pyomo.environ import  AbstractModel

################################################################################################
################################## VARIABLE DEMAND MODEL #######################################
################################################################################################

    
from Results_MY import Plot_Energy_Total, Load_Results, Integer_Time_Series, Print_Results, Energy_Mix
from Model_Creation_MY import Model_Creation
from Model_Resolution_MY import Model_Resolution
   
    
Optimization_Goal = 'NPC'  # Options: NPC / Operation cost 

Renewable_Penetration = 0  # a number from 0 to 1.
Battery_Independency = 0   # number of days of battery independence

model = AbstractModel() # define type of optimization problem

# Optimization model    
Model_Creation(model, Renewable_Penetration, Battery_Independency) # Creation of the Sets, parameters and variables.
instance = Model_Resolution(model, Optimization_Goal, Renewable_Penetration, Battery_Independency) # Resolution of the instance

# Upload the results from the instance and saving it in excel files
Data = Load_Results(instance, Optimization_Goal) # Extract the results of energy from the instance and save it in a excel file 
NPC = Data[0]
Scenarios =  Data[2]
Scenario_Probability = Data[4]
Generator_Data = Data[3]
Data_Renewable = Data[6]
Battery_Data = Data[1]
LCOE = Data[5]
TotVarCost = Data[7]
TotInvCost = Data[8]
SalvageValue = Data[9]
     
# Energy Plot    
S = 1 # Plot scenario
Plot_Date = '01/01/2015 00:00:00' # Day-Month-Year ####ACTUALLY IT WILL INTERPRET A DATE PREFERABLY AS MONTH-DAY; IF DEVOID OF MEANING, IT WILL TRY DAY-MONTH
PlotTime = 3# Days of the plot
Time_Series = Integer_Time_Series(instance,Scenarios, S) 
   
plot = 'No Average' # 'No Average' or 'Average'
Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)

# Data Analisys    
Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)
Print_Results(LCOE, NPC, TotVarCost, TotInvCost, SalvageValue, Optimization_Goal)  