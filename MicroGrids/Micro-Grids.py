"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""


############### MULTI-YEAR CAPACITY-EXPANSION MODEL ###########################

Multi_Year = 'Yes'   #Options: Yes / No

from pyomo.environ import  AbstractModel

################################################################################################
################################## VARIABLE DEMAND MODEL #######################################
################################################################################################


if Multi_Year == 'Yes':
    
    from Results_MY import Plot_Energy_Total, Load_Results, Integer_Time_Series, Print_Results, Energy_Mix
    from Model_Creation_MY import Model_Creation
    from Model_Resolution_MY import Model_Resolution
   
        
#    Optimization_Goal = 'NPC'  # Options: NPC / Operation cost 
    
    Renewable_Penetration = 0  # a number from 0 to 1.
    Battery_Independency = 0   # number of days of battery independence
    
    model = AbstractModel() # define type of optimization problem
    
    # Optimization model    
    Model_Creation(model, Renewable_Penetration, Battery_Independency) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution(model, Renewable_Penetration,
                                Battery_Independency) # Resolution of the instance
    
    # Upload the results from the instance and saving it in excel files
    Data = Load_Results(instance) # Extract the results of energy from the instance and save it in a excel file 
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
    Print_Results(LCOE, NPC, TotVarCost, TotInvCost, SalvageValue)  

    
################################################################################################    
################################### FIXED DEMAND MODEL #########################################
################################################################################################

    
elif Multi_Year == 'No':   
    
    from Results import Plot_Energy_Total,  Load_results1, Energy_Mix, Print_Results, Integer_Time_Series
    from Model_Creation import Model_Creation
    from Model_Resolution import Model_Resolution
    
           
    Renewable_Penetration = 0 # a number from 0 to 1.
    Battery_Independency = 0  # number of days of battery independency

    model = AbstractModel() # define type of optimization problem
    
            
    Model_Creation(model, Renewable_Penetration, Battery_Independency) # Creation of the Sets, parameters and variables.
    instance = Model_Resolution(model, Renewable_Penetration, Battery_Independency) # Resolution of the instance


    ## Upload the resulst from the instance and saving it in excel files
    Data = Load_results1(instance) # Extract the results of energy from the instance and save it in a excel file 
    Scenarios =  Data[3]
    Scenario_Probability = Data[5].loc['Scenario Weight'] 
    Generator_Data = Data[4]
    Data_Renewable = Data[7]
    Results = Data[2]
    LCOE_1 = Data[6]

    
    # Energy Plot    
    S = 1 # Plot scenario
    Plot_Date = '07/10/2015 00:00:00' # Day-Month-Year
    PlotTime = 2# Days of the plot
    Time_Series = Integer_Time_Series(instance,Scenarios, S) 
    
    plot = 'No Average' # 'No Average' or 'Average'
    Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime)
    
    # Data Analisys
    Print_Results(instance, Generator_Data, Data_Renewable, Results, LCOE_1)  
    Energy_Mix_S = Energy_Mix(instance,Scenarios,Scenario_Probability)
    
