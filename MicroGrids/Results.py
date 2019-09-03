
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.ticker as mtick
import matplotlib.pylab as pylab



def Load_results1(instance):
    '''
    This function loads the results that depend of the periods in to a dataframe and creates a excel file with it.
    
    :param instance: The instance of the project resolution created by PYOMO.
    
    :return: A dataframe called Time_series with the values of the variables that depend of the periods.    
    '''
    
    # Load the variables that depend of the periods in python dyctionarys a
    
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Years = int(instance.Years.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    #Scenarios = [[] for i in range(Number_Scenarios)]
    
    columns = []
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))

#    columns=columns
    Scenarios = pd.DataFrame()
    
     
    Lost_Load = instance.Lost_Load.get_values()
    Renewable_Energy_1 = instance.Total_Energy_Renewable.get_values()
    
    Renewable_Energy = {}
   

    for s in range(1, Number_Scenarios + 1):
        for t in range(1, Number_Periods+1):
            
            foo = []
            for r in range(1,Number_Renewable_Source+1 ):
                foo.append((s,r,t))
        
            Renewable_Energy[s,t] = sum(Renewable_Energy_1[i] for i in foo)
            
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Generator_Energy = instance.Generator_Energy.get_values()
    
    
    Total_Generator_Energy = {}
    Total_Fuel = {}
    
    
    for s in range(1, Number_Scenarios + 1):
        for t in range(1, Number_Periods+1):
            foo = []
            for g in range(1,Number_Generator+1):
                foo.append((s,g,t))
            Total_Generator_Energy[s,t] = sum(Generator_Energy[i] for i in foo)
            Total_Fuel[s,t] = 0
            
            
    Scenarios_Periods = [[] for i in range(Number_Scenarios)]
    Scenarios_Ren =[[] for i in range(Number_Renewable_Source)]
    Renewable_Energy_2={}
    
    dum=[]
    for s in range(0, Number_Scenarios):
        for r in range(0,Number_Renewable_Source):
            for t in range(0, Number_Periods):
                dum.append((s+1,r+1,t+1))
    
    for s in range(0,Number_Scenarios):
        for t in range(0, Number_Periods):
            Scenarios_Periods[s].append((s+1,t+1))
    for r in range(0,Number_Renewable_Source ):
        for t in range(0, Number_Periods):
            Scenarios_Ren[r].append((r+1,t+1))
    for i in dum:
        Renewable_Energy_2.update({i:Renewable_Energy_1[i]}) 
    
    foo=0
        
    for i in columns:
        Information = [[] for i in range(0,9)]
        for j in  Scenarios_Periods[foo]:
            Information[0].append(Lost_Load[j])
            Information[1].append(Battery_Flow_Out[j]) 
            Information[2].append(Battery_Flow_in[j]) 
            Information[3].append(Curtailment[j]) 
            Information[4].append(Energy_Demand[j]) 
            Information[5].append(SOC[j])
            Information[6].append(Total_Generator_Energy[j])
            Information[7].append(Total_Fuel[j])
            Information[8].append(Renewable_Energy[j])
        
        Scenarios=Scenarios.append(Information)
        
        for k in range(0,Number_Renewable_Source):
            Information_2 = [[] for i in range(0,Number_Renewable_Source)]
            for t in range(0,Number_Periods):
                for r in range(0,Number_Renewable_Source):
                    Information_2[r].append(Renewable_Energy_2[(foo+1,r+1,t+1)]) 
        Scenarios=Scenarios.append(Information_2)
        
        foo+=1
    
    index=[]  
    for j in range(1, Number_Scenarios+1):   
       index.append('Lost_Load '+str(j))
       index.append('Battery_Flow_Out '+str(j)) 
       index.append('Battery_Flow_in '+str(j))
       index.append('Curtailment '+str(j))
       index.append('Energy_Demand '+str(j))
       index.append('SOC '+str(j))
       index.append('Gen energy '+str(j))
       index.append('Fuel '+str(j))
       index.append('Total Renewable Energy '+str(j))
       for r in range(1,Number_Renewable_Source+1):
           index.append('Renewable Energy: s='+str(j)+' r='+str(r))
    Scenarios.index= index
   
   
     # Creation of an index starting in the 'model.StartDate' value with a frequency step equal to 'model.Delta_Time'
    if instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1.0) : # if the step is in hours and minutes
        foo = str(instance.Delta_Time()) # trasform the number into a string
        hour = foo[0] # Extract the first character
        minutes = str(int(float(foo[1:3])*60)) # Extrac the last two character
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(hour + 'h'+ minutes + 'min')) # Creation of an index with a start date and a frequency
    elif instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1): # if the step is in hours
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(str(instance.Delta_Time()) + 'h')) # Creation of an index with a start date and a frequency
    else: # if the step is in minutes
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(str(int(instance.Delta_Time()*60)) + 'min'))# Creation of an index with a start date and a frequency
    
    Scenarios.columns = columns
    Scenarios = Scenarios.transpose()
    
    Scenarios.to_excel('Results/Fixed_Demand/Time_Series.xls') # Creating an excel file with the values of the variables that are in function of the periods
    
    columns = [] # arreglar varios columns
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario '+str(i))
        
    Scenario_information =[[] for i in range(Number_Scenarios)]
    Scenario_NPC = instance.Scenario_Net_Present_Cost.get_values()
    LoL_Cost = instance.Scenario_Lost_Load_Cost.get_values() 
    Scenario_Weight = instance.Scenario_Weight.extract_values()
    Fuel_Cost = instance.Fuel_Cost_Total.get_values()
    Battery_Reposition_Cost = instance.Battery_Reposition_Cost.get_values()
    Total_Fuel_Cost = {}

    for s in range(1,Number_Scenarios+1):
        foo = []
        for g in range(1, Number_Generator+1):
            foo.append((s,g))
        
        Total_Fuel_Cost[s] = sum(Fuel_Cost[j] for j in foo)
    
    
    for i in range(1, Number_Scenarios+1):
        Scenario_information[i-1].append(Scenario_NPC[i])
        Scenario_information[i-1].append(LoL_Cost[i])
        Scenario_information[i-1].append(Scenario_Weight[i])
        Scenario_information[i-1].append(Total_Fuel_Cost[i])
        Scenario_information[i-1].append(Battery_Reposition_Cost[i])
    
    Scenario_Information = pd.DataFrame(Scenario_information,index=columns)
    Scenario_Information.columns=['Scenario NPC', 'LoL Cost','Scenario Weight', 
                                  'Diesel Cost','Battery Reposition Cost']
    Scenario_Information = Scenario_Information.transpose()
    
    Scenario_Information.to_excel('Results/Fixed_Demand/Scenario_Information.xls')
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])    
    
    
    Renewable_Energy = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
        for r in range(1, Number_Renewable_Source + 1):
            column = 'Renewable ' + str(s) + ' ' + str(r)
            
            Energy = []
            for t in range(1, Number_Periods + 1):
                Energy.append(Renewable_Energy_1[(s,r,t)])
        
            Renewable_Energy[column] = Energy
        
        
    Renewable_Energy.index = Scenarios.index
    Renewable_Energy.to_excel('Results/Fixed_Demand/Renewable_Energy.xls')
    
    Generator_Energy
    
    Generator_Time_Series = pd.DataFrame()
    for s in range(1, Number_Scenarios + 1):
        for g in range(1, Number_Generator + 1):
            column_1 = 'Energy Generator ' + str(s) + ' ' + str(g)
            
            
            for t in range(1, Number_Periods + 1):
                Generator_Time_Series.loc[t,column_1] = Generator_Energy[s,g,t]
                    
    Generator_Time_Series.index = Scenarios.index           
    Generator_Time_Series.to_excel('Results/Fixed_Demand/Generator_time_series.xls')          
    
    

 
    # Load the variables that doesnot depend of the periods in python dyctionarys

    Renewable_Nominal_Capacity = instance.Renewable_Nominal_Capacity.extract_values()
    Inverter_Efficiency_Renewable = instance.Renewable_Inverter_Efficiency.extract_values()
    Renewable_Invesment_Cost = instance.Renewable_Invesment_Cost.extract_values()
    OyM_Renewable = instance.Maintenance_Operation_Cost_Renewable.extract_values()
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Renewable_Units = instance.Renewable_Units.get_values()
    Data_Renewable = pd.DataFrame()
    
    for r in range(1, Number_Renewable_Source + 1):
        
        Name = 'Source ' + str(r)
        Data_Renewable.loc['Units', Name] = Renewable_Units[r]
        Data_Renewable.loc['Nominal Capacity', Name] = Renewable_Nominal_Capacity[r]
        Data_Renewable.loc['Inverter Efficiency', Name] = Inverter_Efficiency_Renewable[r]
        Data_Renewable.loc['Investment Cost', Name] = Renewable_Invesment_Cost[r]
        Data_Renewable.loc['OyM', Name] = OyM_Renewable[r]
        Data_Renewable.loc['Invesment', Name] = Renewable_Units[r]*Renewable_Nominal_Capacity[r]*Renewable_Invesment_Cost[r]        
        Data_Renewable.loc['OyM Cost', Name] = Data_Renewable.loc['Invesment', Name]*OyM_Renewable[r]        
        Data_Renewable.loc['Total Nominal Capacity', Name] = Data_Renewable.loc['Nominal Capacity', Name]*Data_Renewable.loc['Units', Name]    

    Data_Renewable.to_excel('Results/Fixed_Demand/Source_Renewable_Data.xls')    
    
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
 
    Generator_Efficiency = instance.Generator_Efficiency.extract_values()
    Low_Heating_Value = instance.Low_Heating_Value.extract_values()
    Fuel_Cost = instance.Fuel_Cost.extract_values()
    Generator_Invesment_Cost = instance.Generator_Invesment_Cost.extract_values()
    Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.get_values()
    Maintenance_Operation_Cost_Generator = instance.Maintenance_Operation_Cost_Generator.extract_values()
    
    Generator_Data = pd.DataFrame()
    
    for g in range(1, Number_Generator + 1):
        Name = 'Generator ' + str(g)
        Generator_Data.loc['Generator Efficiency',Name] = Generator_Efficiency[g]
        Generator_Data.loc['Low Heating Value',Name] = Low_Heating_Value[g]
        Generator_Data.loc['Fuel Cost',Name] = Fuel_Cost[g]
        Generator_Data.loc['Generator Invesment Cost',Name] = Generator_Invesment_Cost[g]
        Generator_Data.loc['Generator Nominal Capacity',Name] = Generator_Nominal_Capacity[g]
        Generator_Data.loc['OyM Generator', Name] = Maintenance_Operation_Cost_Generator[g]
        Generator_Data.loc['Invesment Generator', Name] = Generator_Invesment_Cost[g]*Generator_Nominal_Capacity[g]
        Generator_Data.loc['OyM Cost', Name] = Generator_Data.loc['Invesment Generator', Name]*Generator_Data.loc['OyM Generator', Name]
        Generator_Data.loc['Marginal Cost', Name] = Generator_Data.loc['Fuel Cost',Name]/(Generator_Data.loc['Generator Efficiency',Name]*Generator_Data.loc['Low Heating Value',Name])
    Generator_Data.to_excel('Results/Fixed_Demand/Generator_Data.xls')      
    
    
    
    cc = instance.Battery_Nominal_Capacity.get_values()
    NPC = instance.ObjectiveFuntion.expr()
    DiscountRate = instance.Discount_Rate.value
    PriceBattery= instance.Battery_Invesment_Cost.value
    Years=instance.Years.value
    Initial_Inversion = instance.Initial_Inversion.get_values()[None]
    O_M_Cost = instance.Operation_Maintenance_Cost.get_values()[None]
    Battery_Reposition_Cost = instance.Unitary_Battery_Reposition_Cost.value
    VOLL = instance.Value_Of_Lost_Load.value
    OM_Bat = instance.Maintenance_Operation_Cost_Battery.value
    SOC_1 = instance.Battery_Initial_SOC.value
    Ch_bat_eff = instance.Charge_Battery_Efficiency.value
    Dis_bat_eff = instance.Discharge_Battery_Efficiency.value
    Year = instance.Years.value
    data3 = np.array([cc[None],NPC, DiscountRate, 
                      PriceBattery, Years, Initial_Inversion,
                      O_M_Cost, Battery_Reposition_Cost, VOLL,
                       OM_Bat, SOC_1, Ch_bat_eff, Dis_bat_eff, Year]) # Loading the values to a numpy array
    index_values = ['Battery Nominal Capacity','NPC','Discount Rate','Price Battery', 
                    'Years','Initial Inversion', 'O&M', 
                    'Battery Unitary Reposition Cost','VOLL', 'OyM Bat', 'Initial SOC',
                    'Battery charge efficiency', 'Battery discharge efficiency',
                    'Project Life Time']
    # Create a data frame for the variable that don't depend of the periods of analisys 
    Size_variables = pd.DataFrame(data3,index=index_values)
    Size_variables.to_excel('Results/Fixed_Demand/Size.xls') # Creating an excel file with the values of the variables that does not depend of the periods
    

    Battery_Data = pd.DataFrame()
    Battery_Data.loc['Invesment','Battery'] = Size_variables[0]['Battery Nominal Capacity']*Size_variables[0]['Price Battery']
    Battery_Data.loc['OyM','Battery'] = Battery_Data['Battery']['Invesment']*Size_variables[0]['OyM Bat']

    Generator_Energy = instance.Generator_Energy.get_values() 

    Generator_Time_Series = pd.DataFrame()
    for s in range(1, Number_Scenarios + 1):
        for g in range(1, Number_Generator + 1):
            column_1 = 'Energy Generator ' + str(s) + ' ' + str(g)
            column_2 = 'Fuel Cost ' + str(s) + ' ' + str(g)
            Name = Name = 'Generator ' + str(g)
            for t in range(1, Number_Periods + 1):
                Generator_Time_Series.loc[t,column_1] = Generator_Energy[s,g,t]
                Generator_Time_Series.loc[t,column_2] = Generator_Time_Series.loc[t,column_1]*Generator_Data.loc['Marginal Cost', Name] 
     
    Generator_Time_Series.index = Scenarios.index           
    Generator_Time_Series.to_excel('Results/Fixed_Demand/Generator_time_series.xls')                

    Cost_Time_Series = pd.DataFrame()
    for s in range(1, Number_Scenarios + 1):
        name_1 = 'Lost_Load ' + str(s)
        name_2 = 'Battery_Flow_Out ' + str(s)
        name_3 = 'Battery_Flow_in ' + str(s)
        name_4 = 'Generator Cost ' + str(s)
        for t in Scenarios.index:
            Cost_Time_Series.loc[t,name_1] = Scenarios[name_1][t]*Size_variables[0]['VOLL']
            Cost_Time_Series.loc[t,name_2] = Scenarios[name_2][t]*Size_variables[0]['Battery Unitary Reposition Cost']
            Cost_Time_Series.loc[t,name_3] = Scenarios[name_3][t]*Size_variables[0]['Battery Unitary Reposition Cost']
            Fuel_Cost = 0
            for g in range(1, Number_Generator + 1):
                name_5 = 'Fuel Cost ' + str(s) + ' ' + str(g)
                Fuel_Cost += Generator_Time_Series.loc[t,name_5]
            Cost_Time_Series.loc[t,name_4] = Fuel_Cost
 
                
    Scenario_Cost = pd.DataFrame()    
    for s in range(1, Number_Scenarios + 1):
        name_1 = 'Scenario ' + str(s)
        name_2 = 'Scenario ' + str(s)
        Scenario_Cost.loc['VOLL',name_1] = Cost_Time_Series['Lost_Load ' + str(s)].sum()
        Scenario_Cost.loc['Bat Out',name_1] = Cost_Time_Series['Battery_Flow_Out ' + str(s)].sum()
        Scenario_Cost.loc['Bat In',name_1] = Cost_Time_Series['Battery_Flow_in ' + str(s)].sum()
        Scenario_Cost.loc['Gen Cost',name_1] = Cost_Time_Series['Generator Cost ' + str(s)].sum() 
        
        gen_oym = 0
        for g in range(1, Number_Generator + 1):
            Name_2 = 'Generator ' + str(g)
            gen_oym += Generator_Data.loc['OyM Cost', Name_2]
        Scenario_Cost.loc['Gen OyM Cost',name_1] = gen_oym
        renewable_energy_oym = 0
        for r in range(1, Number_Renewable_Source + 1):
            Name = 'Source ' + str(r)
            renewable_energy_oym += Data_Renewable.loc['OyM Cost', Name]
        Scenario_Cost.loc['PV OyM Cost',name_1] = renewable_energy_oym
        Scenario_Cost.loc['Battery OyM Cost',name_1] = Battery_Data['Battery']['OyM']
        Scenario_Cost.loc['Operation Cost',name_1] = Scenario_Cost[name_1].sum()  
        a = Scenario_Cost[name_1]['Operation Cost']
        Discount_rate = Size_variables[0]['Discount Rate']
        Years =  int(Size_variables[0]['Project Life Time'])
        Scenario_Cost.loc['OyM',name_1] = Scenario_Cost.loc['Gen OyM Cost',name_1]+Scenario_Cost.loc['PV OyM Cost',name_1]+Scenario_Cost.loc['Battery OyM Cost',name_1]
        
        Scenario_Cost.loc['Present Gen Cost',name_1] = sum((Scenario_Cost.loc['Gen Cost',name_1]/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        Scenario_Cost.loc['Present VOLL Cost',name_1] = sum((Scenario_Cost.loc['VOLL',name_1]/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        
        Scenario_Cost.loc['Present Bat Out Cost',name_1] = sum((Scenario_Cost.loc['Bat Out',name_1]/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        Scenario_Cost.loc['Present Bat In Cost',name_1] = sum((Scenario_Cost.loc['Bat In',name_1]/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        Scenario_Cost.loc['Present Bat Reposition Cost',name_1] = Scenario_Cost.loc['Present Bat Out Cost',name_1] + Scenario_Cost.loc['Present Bat In Cost',name_1]
       
        Scenario_Cost.loc['Present OyM Cost',name_1] = sum((Scenario_Cost.loc['OyM',name_1]/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        Scenario_Cost.loc['Present Operation Cost',name_1] = sum((a/(1+Discount_rate)**i) 
                                        for i in range(1, Years+1)) 
        
        
        Scenario_Cost.loc['Present Operation Cost Weighted',name_1] = Scenario_Cost[name_1]['Present Operation Cost']*Scenario_Information[name_2]['Scenario Weight']
    

    
    NPC = pd.DataFrame()
    NPC.loc['Battery Invesment', 'Data'] = Battery_Data['Battery']['Invesment'] 
    
    gen_Invesment = 0
    for g in range(1, Number_Generator + 1):
        Name_2 = 'Generator ' + str(g)
        gen_Invesment += Generator_Data.loc['Invesment Generator', Name_2]
    NPC.loc['Gen Invesment Cost', 'Data'] = gen_Invesment
    
    renewable_energy_invesment = 0
    for r in range(1, Number_Renewable_Source + 1):
            Name = 'Source ' + str(r)
            renewable_energy_invesment += Data_Renewable.loc['Invesment', Name]
    NPC.loc['Renewable Investment Cost', 'Data'] = renewable_energy_invesment 
    
    operation_cost = 0
    for s in range(1, Number_Scenarios + 1):
        name_1 = 'Scenario ' + str(s)
        operation_cost += Scenario_Cost[name_1]['Present Operation Cost Weighted']

    NPC.loc['Present Operation Cost Weighted', 'Data'] = operation_cost

    
    NPC.loc['NPC', 'Data'] = NPC['Data'].sum()
    NPC.loc['NPC LP', 'Data'] = Size_variables[0]['NPC']
    NPC.loc['Invesment', 'Data'] = NPC.loc['Battery Invesment', 'Data']+NPC.loc['Gen Invesment Cost', 'Data']+NPC.loc['Renewable Investment Cost', 'Data']
    
    Demand = pd.DataFrame()
    NP_Demand = 0
    for s in range(1, Number_Scenarios + 1):
        a = 'Energy_Demand ' + str(s)
        b = 'Scenario ' + str(s)
        Demand.loc[a,'Total Demand'] = sum(Scenarios[a][i] for i in Scenarios.index)
        Demand.loc[a,'Present Demand'] = sum((Demand.loc[a,'Total Demand']/(1+Discount_rate)**i) 
                                                            for i in range(1, Years+1))  
        Demand.loc[a,'Rate'] = Scenario_Information[b]['Scenario Weight']                                                         
        Demand.loc[a,'Rated Demand'] = Demand.loc[a,'Rate']*Demand.loc[a,'Present Demand'] 
        NP_Demand += Demand.loc[a,'Rated Demand']
    LCOE_1 = (Size_variables[0]['NPC']/NP_Demand)*1000
    
    
#    NetPresentCost = instance.ObjectiveFuntion.expr()
#    CRF = (DiscountRate*(1 + DiscountRate)**Number_Years)/((1+DiscountRate)**Number_Years - 1)
#    LCOE_2 = NetPresentCost*CRF/Demand.loc[a,'Total Demand']*1000
    
    Data = []
    Data.append(NPC)
    Data.append(Scenario_Cost)
    Data.append(Size_variables)
    Data.append(Scenarios)
    Data.append(Generator_Data)
    Data.append(Scenario_Information)
    Data.append(LCOE_1)
    Data.append(Data_Renewable)
#    Data.append(LCOE_2)
    return Data
   
    
    

def Integer_Scenarios(instance):
    '''
    This function loads the results that depend of the periods in to a 
    dataframe and creates a excel file with it.
    
    :param instance: The instance of the project resolution created by PYOMO.
    
    :return: A dataframe called Time_series with the values of the variables 
    that depend of the periods.    
    '''

#      Creation of an index starting in the 'model.StartDate' value with a frequency step equal to 'model.Delta_Time'
   
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    
    columns = []
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))

#    columns=columns
    Scenarios = pd.DataFrame()
    
     
    Lost_Load = instance.Lost_Load.get_values()
    Renewable_Energy_Production = instance.Renewable_Energy_Production.extract_values()
    
    Renewable_Energy = {}
    Inverter_Efficiency_Renewable = instance.Inverter_Efficiency_Renewable.extract_values()
    Renewable_Units = instance.Renewable_Units.get_values()    


    for s in range(1, Number_Scenarios + 1):
        for t in range(1, Number_Periods+1):
            
            foo = []
            for r in range(1,Number_Renewable_Source+1 ):
                foo.append((s,r,t))
        
            Renewable_Energy[s,t] = sum(Renewable_Energy_Production[i]
                                        *Inverter_Efficiency_Renewable[i[1]]
                                        *Renewable_Units[i[1]]  
                                        for i in foo)
       
    
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Generator_Energy = instance.Generator_Total_Period_Energy.get_values() 
    
    
    Total_Generator_Energy = pd.DataFrame()
   
    
    for s in range(1, Number_Scenarios + 1):
        for t in range(1, Number_Periods+1):
            foo = []
            for g in range(1,Number_Generator+1):
                foo.append((s,g,t))
            Total_Generator_Energy.loc[t,s] = sum(Generator_Energy[i] for i in foo)
           
            
    Scenarios_Periods = [[] for i in range(Number_Scenarios)] 
       
    for i in range(0,Number_Scenarios):
        for j in range(1, Number_Periods+1):
            Scenarios_Periods[i].append((i+1,j))
    foo=0        
    for i in columns:
        Information = [[] for i in range(8)]
        for j in  Scenarios_Periods[foo]:
            Information[0].append(Lost_Load[j])
            Information[1].append(Renewable_Energy[j]) 
            Information[2].append(Battery_Flow_Out[j]) 
            Information[3].append(Battery_Flow_in[j]) 
            Information[4].append(Curtailment[j]) 
            Information[5].append(Energy_Demand[j]) 
            Information[6].append(SOC[j])
            Information[7].append(Total_Generator_Energy[j[0]][j[1]])
            
        
        Scenarios=Scenarios.append(Information)
        foo+=1
    
    index=[]  
    for j in range(1, Number_Scenarios+1):   
       index.append('Lost_Load '+str(j))
       index.append('Renewable Energy '+str(j))
       index.append('Battery_Flow_Out '+str(j)) 
       index.append('Battery_Flow_in '+str(j))
       index.append('Curtailment '+str(j))
       index.append('Energy_Demand '+str(j))
       index.append('SOC '+str(j))
       index.append('Gen energy '+str(j))
       
    Scenarios.index= index
     
    
   
   
     # Creation of an index starting in the 'model.StartDate' value with a frequency step equal to 'model.Delta_Time'
    if instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1.0) : # if the step is in hours and minutes
        foo = str(instance.Delta_Time()) # trasform the number into a string
        hour = foo[0] # Extract the first character
        minutes = str(int(float(foo[1:3])*60)) # Extrac the last two character
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(hour + 'h'+ minutes + 'min')) # Creation of an index with a start date and a frequency
    elif instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1): # if the step is in hours
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(str(instance.Delta_Time()) + 'h')) # Creation of an index with a start date and a frequency
    else: # if the step is in minutes
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods(), 
                                   freq=(str(int(instance.Delta_Time()*60)) + 'min'))# Creation of an index with a start date and a frequency
    
    Scenarios.columns = columns
    Scenarios = Scenarios.transpose()
    
    Scenarios.to_excel('Results/Time_Series.xls') # Creating an excel file with the values of the variables that are in function of the periods
    
    return Scenarios

def Integer_Scenario_Information(instance):
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    
    columns = [] # arreglar varios columns
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario '+str(i))
        
    Scenario_information =[[] for i in range(Number_Scenarios)]
    Scenario_Weight = instance.Scenario_Weight.extract_values()
    
    
    for i in range(1, Number_Scenarios+1):
        
        Scenario_information[i-1].append(Scenario_Weight[i])
        
    Scenario_Information = pd.DataFrame(Scenario_information,index=columns)
    Scenario_Information.columns=['Scenario Weight']
    Scenario_Information = Scenario_Information.transpose()
    
    Scenario_Information.to_excel('Results/Scenario_Information.xls')

    return Scenario_Information 

def Integer_Time_Series(instance,Scenarios, S): # S is the scenario that we want to plot
    
    if S == 0:
        S = instance.PlotScenario.value
    
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    
    Time_Series = pd.DataFrame(index=range(0,Number_Periods))
    Time_Series.index = Scenarios.index
    
    Time_Series['Lost Load'] = Scenarios['Lost_Load '+str(S)]
    Time_Series['Total Renewable Energy'] = Scenarios['Total Renewable Energy '+str(S)]
    for r in range(1,Number_Renewable_Source+1):
        Time_Series['Renewable Energy '+str(r)] = Scenarios['Renewable Energy: s='+str(S)+' r='+str(r)]
    Time_Series['Discharge energy from the Battery'] = Scenarios['Battery_Flow_Out '+str(S)] 
    Time_Series['Charge energy to the Battery'] = Scenarios['Battery_Flow_in '+str(S)]
    Time_Series['Curtailment'] = Scenarios['Curtailment '+str(S)]
    Time_Series['Energy_Demand'] = Scenarios['Energy_Demand '+str(S)]
    Time_Series['State_Of_Charge_Battery'] = Scenarios['SOC '+str(S)] 
    Time_Series['Energy Diesel'] = Scenarios['Gen energy '+str(S)]
    
    return Time_Series

def integer_Renewable_Energy(instance, Scenarios):
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])    
    Renewable_Energy_Production = instance.Renewable_Energy_Production.extract_values()
    Renewable_Units = instance.Renewable_Units.get_values()
    
    
    Renewable_Energy = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
        for r in range(1, Number_Renewable_Source + 1):
            column = 'Renewable ' + str(s) + ' ' + str(r)
            Energy = []
            for t in range(1, Number_Periods + 1):
                Energy.append(Renewable_Energy_Production[(s,r,t)]*Renewable_Units[r])
        
        Renewable_Energy[column] = Energy
        
        
    Renewable_Energy.index = Scenarios.index
    Renewable_Energy.to_excel('Results/Renewable_Energy.xls')
    
    return Renewable_Energy

def Integer_Data_Renewable(instance):    
    Renewable_Nominal_Capacity = instance.Renewable_Nominal_Capacity.extract_values()
    Inverter_Efficiency_Renewable = instance.Inverter_Efficiency_Renewable.extract_values()
    Renewable_Invesment_Cost = instance.Renewable_Invesment_Cost.extract_values()
    OyM_Renewable = instance.Maintenance_Operation_Cost_Renewable.extract_values()
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Renewable_Units = instance.Renewable_Units.get_values()
    Data_Renewable = pd.DataFrame()
    
    for r in range(1, Number_Renewable_Source + 1):
        
        Name = 'Source ' + str(r)
        Data_Renewable.loc['Units', Name] = Renewable_Units[r]
        Data_Renewable.loc['Nominal Capacity', Name] = Renewable_Nominal_Capacity[r]
        Data_Renewable.loc['Inverter Efficiency', Name] = Inverter_Efficiency_Renewable[r]
        Data_Renewable.loc['Investment Cost', Name] = Renewable_Invesment_Cost[r]
        Data_Renewable.loc['OyM', Name] = OyM_Renewable[r]
        
    Data_Renewable.to_excel('Results/Source_Renewable_Data.xls')
    
    return Data_Renewable


def Integer_Generator_time_series(instance, Scenarios):
        
    Generator_Integer = instance.Generator_Energy_Integer.get_values()
    Generator_Energy = instance.Generator_Total_Period_Energy.get_values() 
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None]) 
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    Generator_Time_Series = pd.DataFrame()
    for s in range(1, Number_Scenarios + 1):
        for g in range(1, Number_Generator + 1):
            column_1 = 'Energy Generator ' + str(s) + ' ' + str(g)
            column_2 = 'Integer Generator ' + str(s) + ' ' + str(g)
            
            for t in range(1, Number_Periods + 1):
                Generator_Time_Series.loc[t,column_1] = Generator_Energy[s,g,t]
                Generator_Time_Series.loc[t,column_2] = Generator_Integer[s,g,t]
     
    Generator_Time_Series.index = Scenarios.index           
    Generator_Time_Series.to_excel('Results/Generator_time_series.xls')            
    
    return Generator_Time_Series


def Integer_Generator_Data(instance):
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    Generator_Min_Out_Put = instance.Generator_Min_Out_Put.extract_values()
    Generator_Efficiency = instance.Generator_Efficiency.extract_values()
    Low_Heating_Value = instance.Low_Heating_Value.extract_values()
    Fuel_Cost = instance.Fuel_Cost.extract_values()
    Generator_Invesment_Cost = instance.Generator_Invesment_Cost.extract_values()
    Marginal_Cost_Generator_1 = instance.Marginal_Cost_Generator_1.extract_values()
    Cost_Increase = instance.Cost_Increase.extract_values()
    Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.extract_values()
    Start_Cost_Generator = instance.Start_Cost_Generator.extract_values()
    Marginal_Cost_Generator = instance.Marginal_Cost_Generator.extract_values()
    Integer_generator = instance.Integer_generator.get_values()
    Maintenance_Operation_Cost_Generator = instance.Maintenance_Operation_Cost_Generator.extract_values()
    
    Generator_Data = pd.DataFrame()
    
    for g in range(1, Number_Generator + 1):
        Name = 'Generator ' + str(g)
        Generator_Data.loc['Generator Min Out Put',Name] = Generator_Min_Out_Put[g]
        Generator_Data.loc['Generator Efficiency',Name] = Generator_Efficiency[g]
        Generator_Data.loc['Low Heating Value',Name] = Low_Heating_Value[g]
        Generator_Data.loc['Fuel Cost',Name] = Fuel_Cost[g]
        Generator_Data.loc['Generator Invesment Cost',Name] = Generator_Invesment_Cost[g]
        Generator_Data.loc['Marginal cost Full load',Name] = Marginal_Cost_Generator_1[g]
        Generator_Data.loc['Marginal cost Partial load',Name] = Marginal_Cost_Generator[g]
        Generator_Data.loc['Cost Increase',Name] = Cost_Increase[g]
        Generator_Data.loc['Generator Nominal Capacity',Name] = Generator_Nominal_Capacity[g]
        Generator_Data.loc['Start Cost Generator',Name] = Start_Cost_Generator[g]
        Generator_Data.loc['Number of Generator', Name] = Integer_generator[g]
        Generator_Data.loc['Maintenance Operation Cost Generator', Name] = Maintenance_Operation_Cost_Generator[g]
        
    Generator_Data.to_excel('Results/Generator_Data.xls')  
    
    return Generator_Data

def Integer_Results(instance):
            
    Size_Bat = instance.Battery_Nominal_Capacity.get_values()[None]
    NPC = instance.ObjectiveFuntion.expr() 
    DiscountRate = instance.Discount_Rate.value
    PriceBatery= instance.Battery_Invesment_Cost.value
    OM_Bat = instance.Maintenance_Operation_Cost_Battery.value
    Years=instance.Years.value
    VOLL= instance.Value_Of_Lost_Load.value
    Bat_ef_out = instance.Discharge_Battery_Efficiency.value
    Bat_ef_in = instance.Charge_Battery_Efficiency.value
    Battery_Reposition_Cost  = instance.Battery_Reposition_Cost.value
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    data3 = [Size_Bat, NPC, DiscountRate, PriceBatery, OM_Bat, Years, VOLL, Bat_ef_out, Bat_ef_in,
            Battery_Reposition_Cost, Number_Scenarios, Number_Periods,
            Number_Renewable_Source, Number_Generator] # Loading the values to a numpy array  
    Results = pd.DataFrame(data3,index = ['Size of the Battery',
                                               'Net Present Cost', 'Discount Rate', 
                                               'Precio Bateria','OyM Battery',  
                                               'Project years','VOLL',
                                               'Battery efficiency discharge',
                                               'Battery efficiency charge','Battery Reposition Cost',
                                               'Number of scenarios', 'Number of periods', 'Number of renewable sources',
                                               'Number Of Generators'])
    Results.to_excel('Results/Size.xls') # Creating an excel file with the values of the variables that does not depend of the periods
    
    return Results


def Economic_Analysis(Scenarios, Scenario_Information, Renewable_Energy, Data_Renewable,
                      Generator_Time_Series, Generator_Data, Results):
    
    Number_Scenarios = int(Results[0]['Number of scenarios'])
    
    Renewable_Economic = pd.DataFrame(columns=Data_Renewable.columns)
    
    for i in  Data_Renewable.columns:
        Renewable_Economic.loc['Invesment',i] = (Data_Renewable[i]['Units']
                                          *Data_Renewable[i]['Nominal Capacity']
                                          *Data_Renewable[i]['Investment Cost'])
        Renewable_Economic.loc['Total Nominal Capacity',i] = (Data_Renewable[i]['Units']
                                          *Data_Renewable[i]['Nominal Capacity'])
        Renewable_Economic.loc['OyM',i] = (Data_Renewable[i]['Units']
                                          *Data_Renewable[i]['Nominal Capacity']
                                          *Data_Renewable[i]['Investment Cost']
                                          *Data_Renewable[i]['OyM'])
    
    Generator_Economic = pd.DataFrame(columns = Generator_Data.columns)
    
    for i in  Generator_Data.columns:
        Generator_Economic.loc['Invesment',i] = (Generator_Data[i]['Number of Generator']
                                        *Generator_Data[i]['Generator Nominal Capacity']
                                        *Generator_Data[i]['Generator Invesment Cost'])
        Generator_Economic.loc['Nominal Capacity',i] = (Generator_Data[i]['Number of Generator']
                                        *Generator_Data[i]['Generator Nominal Capacity'])
        Generator_Economic.loc['OyM',i] = (Generator_Data[i]['Number of Generator']
                                        *Generator_Data[i]['Generator Nominal Capacity']
                                        *Generator_Data[i]['Generator Invesment Cost']
                                        *Generator_Data[i]['Maintenance Operation Cost Generator'])        
    
    Economic_Time_Series = pd.DataFrame(index = Generator_Time_Series.index)    
                 
    columns_gen = []
    for s in range(1, Number_Scenarios + 1):
        for g in range(1, int(Results[0]['Number Of Generators']) + 1):
            a = 'Energy Generator ' + str(s) + ' ' + str(g)
            b = 'Integer Generator ' + str(s) + ' ' + str(g)
            c = 'Cost Generator ' + str(s) + ' ' + str(g)
            d = 'Generator ' + str(g) 
            columns_gen.append((a,b,c,d))
            
    for e,i,c,g in columns_gen:
        for t in Generator_Time_Series.index:
            Economic_Time_Series.loc[t,c] = (Generator_Time_Series[i][t]*Generator_Data[g]['Start Cost Generator'] 
               + Generator_Time_Series[e][t]*Generator_Data[g]['Marginal cost Partial load'])
    
    columns_2 = []
    for j in range(1, Number_Scenarios + 1):   
       a = 'Lost_Load '+str(j)
       b = 'Battery_Flow_Out '+str(j)
       c = 'Battery_Flow_in '+str(j)        
       columns_2.append((a,b,c))
    
    for l,o,i in columns_2:
        for t in Generator_Time_Series.index:
            Economic_Time_Series.loc[t,l] = Scenarios[l][t]*Results[0]['VOLL']
            Economic_Time_Series.loc[t,o] = Scenarios[o][t]*Results[0]['Battery Reposition Cost']
            Economic_Time_Series.loc[t,i] = Scenarios[i][t]*Results[0]['Battery Reposition Cost']
    
    Total_Variable_Cost = Economic_Time_Series.sum()    

    Scenario_Variable_Cost = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
        foo = []
        for g in range(1, int(Results[0]['Number Of Generators']) + 1):
            foo.append('Cost Generator ' + str(s) + ' ' + str(g))
        index = 'Generator ' + str(s)
        Scenario_Variable_Cost.loc[index,'Period Cost'] = sum(Total_Variable_Cost[i] 
                                                            for i in foo)
    
    for l,o,i in columns_2:      
        Scenario_Variable_Cost.loc[l,'Period Cost'] = Total_Variable_Cost[l]
        Scenario_Variable_Cost.loc[o,'Period Cost'] = Total_Variable_Cost[o]
        Scenario_Variable_Cost.loc[i,'Period Cost'] = Total_Variable_Cost[i]
    
    Discount_rate = float(Results[0]['Discount Rate'])
    Years = int(Results[0]['Project years'])
    
    OyM_Cost = pd.Series()
    OyM_Cost['Renewable'] = sum(Renewable_Economic[i]['OyM'] 
                                for i in Renewable_Economic.columns ) 

    OyM_Cost['Generator'] = sum(Generator_Economic[i]['OyM'] 
                                for i in Generator_Economic.columns ) 
    
    OyM_Cost['Battery'] = (Results[0]['OyM Battery']*Results[0]['Size of the Battery']
                            *Results[0]['Precio Bateria'])
    
    for i in Scenario_Variable_Cost.index:
        a = Scenario_Variable_Cost.loc[i,'Period Cost']
        Scenario_Variable_Cost.loc[i,'Present Value'] = sum((a/(1+Discount_rate)**i) 
                                                            for i in range(1, Years+1)) 
    
    Scenario_Variable_Cost.loc['OyM','Period Cost'] = OyM_Cost.sum()
    Scenario_Variable_Cost.loc['OyM','Present Value'] = sum((OyM_Cost.sum()/(1+Discount_rate)**i) 
                                                            for i in range(1, Years+1)) 

    
    Cost_Scenario = pd.Series()
        
    for s in range(1, Number_Scenarios + 1):
       foo = [] 
       foo.append('Lost_Load '+str(s))
       foo.append('Battery_Flow_Out '+str(s))
       foo.append('Battery_Flow_in '+str(s))
       foo.append('Generator ' + str(s))
       foo.append('OyM')
       
       Cost_Scenario.loc['Scenario ' + str(s)] = sum(
                                  Scenario_Variable_Cost['Present Value'][i] 
                                    for i in foo)
    Invesment = pd.Series()
    Invesment.loc['Renewable'] = sum(Renewable_Economic[i]['Invesment'] 
                                    for i in Renewable_Economic.columns)                                                               
    Invesment.loc['Generator'] = sum(Generator_Economic[i]['Invesment'] 
                                    for i in Generator_Economic.columns)   
    Invesment.loc['Battery'] = Results[0]['Size of the Battery']*Results[0]['Precio Bateria']
    Invesment['Total'] = (Invesment['Renewable'] + Invesment['Generator']
                            + Invesment['Battery']) 

    NPC_Scenarios = pd.DataFrame()
     
    for i in Cost_Scenario.index:
        NPC_Scenarios.loc[i,'NPC Scenario'] = Cost_Scenario[i] + Invesment['Total']
        NPC_Scenarios.loc[i,'Rate'] = Scenario_Information[i]['Scenario Weight']
        NPC_Scenarios.loc[i,'NPC Ponderado'] = (NPC_Scenarios.loc[i,'NPC Scenario']
                                                *NPC_Scenarios.loc[i,'Rate']) 
    NPC = NPC_Scenarios['NPC Ponderado'].sum()
    
    Demand = pd.DataFrame()
    NP_Demand = 0
    for s in range(1, Number_Scenarios + 1):
        a = 'Energy_Demand ' + str(s)
        b = 'Scenario ' + str(s)
        Demand.loc[a,'Total Demand'] = sum(Scenarios[a][i] for i in Scenarios.index)
        Demand.loc[a,'Present Demand'] = sum((Demand.loc[a,'Total Demand']/(1+Discount_rate)**i) 
                                                            for i in range(1, Years+1))  
        Demand.loc[a,'Rate'] = Scenario_Information[b]['Scenario Weight']                                                         
        Demand.loc[a,'Rated Demand'] = Demand.loc[a,'Rate']*Demand.loc[a,'Present Demand'] 
        NP_Demand += Demand.loc[a,'Rated Demand']
    LCOE = (NPC/NP_Demand)*1000
    
    Energy_Balance = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
         a = 'Scenario ' + str(s)
         b = 'Energy_Demand ' + str(s)
         c = 'Lost_Load '+str(s)
         d = 'Battery_Flow_Out '+str(s)
         e = 'Battery_Flow_in '+str(s)
         f = 'Gen energy ' + str(s)
         g = 'Balance ' + str(s)
         h = 'Renewable Energy ' +str(s)
         j = 'Curtailment ' + str(s)
         for t in Scenarios.index:
             Energy_Balance.loc[t,g] = (Scenarios[c][t] - Scenarios[b][t] +Scenarios[d][t]
              - Scenarios[e][t] + Scenarios[f][t] +  Scenarios[h][t] + Scenarios[j][t]) 
    
    return (NPC,LCOE)

   
def Results_Analysis_3(instance):
    
    data_4 = instance.Generator_Nominal_Capacity.values()
    foo=instance.Binary_generator.get_values()
    for i in range(1,(len(instance.Generator_Nominal_Capacity.values()))+1):
        data_4.append(foo[i])
    data_5 = np.array(data_4)
    
    Generator_info = pd.DataFrame(data_5, index=['Cap 1', 'Cap 2', 'Cap 3', 'Bin 1', 'Bin 2', 'Bin 3'])
    Generator_info.to_excel('Results/Generator.xls')
    
    
def Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime):  
    '''
    This function creates a plot of the dispatch of energy of a defined number of days.
    
    :param instance: The instance of the project resolution created by PYOMO. 
    :param Time_series: The results of the optimization model that depend of the periods.
    
    
    '''
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])

    if plot == 'No Average':
        Periods_Day = 24/instance.Delta_Time() # periods in a day
        foo = pd.DatetimeIndex(start=Plot_Date,periods=1,freq='1h')# Assign the start date of the graphic to a dumb variable
        
        for x in range(0, instance.Periods()): # Find the position from which the plot will start in the Time_Series dataframe
            if foo == Time_Series.index[x]: 
               Start_Plot = x # assign the value of x to the position where the plot will start 
        
        End_Plot = Start_Plot + PlotTime*Periods_Day # Create the end of the plot position inside the time_series
        Time_Series.index=range(1,(len(Time_Series)+1))
        Plot_Data = Time_Series[Start_Plot:int(End_Plot)] # Extract the data between the start and end position from the Time_Series
        columns = pd.DatetimeIndex(start=Plot_Date, 
                                   periods=PlotTime*Periods_Day, 
                                    freq=('1h'))    
        Plot_Data.index=columns
    
        Plot_Data = Plot_Data.astype('float64')
        Plot_Data = Plot_Data/1000  #from W to kW
        Plot_Data['Charge energy to the Battery'] = -Plot_Data['Charge energy to the Battery']
                           
        Fill = pd.DataFrame()
        dummy = pd.DataFrame()
        
        r_tot = 'Total Renewable Energy'
        g = 'Energy Diesel'
        c = 'Curtailment'
        c2 ='Curtailment min'
        b = 'Discharge energy from the Battery'
        
        for t in Plot_Data.index:
            if (Plot_Data[r_tot][t] > 0 and  Plot_Data[g][t] > 0):
                for r in range(1,Number_Renewable_Source+1):
                    dummy.loc[t,r] = Plot_Data['Renewable Energy '+str(r)][t]
                    Fill.loc[t,'Ren ' +str(r)] = pd.Series.to_frame(dummy.sum(1))[0][t]
                Fill.loc[t,g] = Fill['Ren ' +str(r)][t] + Plot_Data[g][t]
                Fill.loc[t,c] = Fill.loc[t,g]
                Fill.loc[t,c2] = Fill.loc[t,g]
            elif Plot_Data[r_tot][t] > 0:
                Fill.loc[t,'Ren 1'] = Plot_Data['Renewable Energy 1'][t]-Plot_Data[c][t]*Plot_Data['Renewable Energy 1'][t]/Plot_Data[r_tot][t]
                for r in range(2,Number_Renewable_Source+1):
                    dummy.loc[t,r] = Plot_Data['Renewable Energy '+str(r)][t]
                    Fill.loc[t,'Ren ' +str(r)] = Fill.loc[t,'Ren '+str(r-1)]+dummy.loc[t,r]-Plot_Data[c][t]*Plot_Data['Renewable Energy '+str(r)][t]/Plot_Data[r_tot][t]
                Fill.loc[t,g] = Fill['Ren ' +str(r)][t]
                Fill.loc[t,c] = Fill.loc[t,g] + Plot_Data[c][t]
                Fill.loc[t,c2] = Fill.loc[t,g]
            elif Plot_Data[g][t] > 0:
                for r in range(1,Number_Renewable_Source+1):
                    Fill.loc[t,'Ren ' +str(r)] = 0                
                Fill.loc[t,g] = Plot_Data[g][t]
                Fill.loc[t,c] = Fill.loc[t,g]
                Fill.loc[t,c2] = Fill.loc[t,g]
            else:
                for r in range(1,Number_Renewable_Source+1):
                    Fill.loc[t,'Ren ' +str(r)] = 0
                Fill.loc[t,g]= 0
                if  Plot_Data[g][t] == 0:
                    Fill.loc[t,c] = Plot_Data[g][t]
                    Fill.loc[t,c2] = Plot_Data[g][t]
                else:
                    if Plot_Data[g][t] > 0:
                        Fill.loc[t,c] = Plot_Data[g][t]
                        Fill.loc[t,c2] = Plot_Data['Energy_Demand'][t]
                    else:
                        Fill.loc[t,c] = Plot_Data[b][t]
                        Fill.loc[t,c2] = Plot_Data['Energy_Demand'][t]

#        for t in Plot_Data.index:
#            if Plot_Data[r][t] > Plot_Data['Energy_Demand'][t]:
#                Fill.loc[t,c2] =  Fill.loc[t,r]
#            else:
#                Fill.loc[t,c2] = Plot_Data['Energy_Demand'][t]
        
        
        Fill[b] = Fill[g] + Plot_Data[b] #+ Plot_Data[b_ch]

        # Renewable energy plot (first renewable outside for loop, if >1 renewables the others are plotted in the loop)
        color_list = ['yellow',(255/255,141/255,14/255),'c','0.6','y']
        Alpha_r = 0.4
        ax0 = Fill['Ren 1'].plot(style='y-', linewidth=0)
        ax0.fill_between(Plot_Data.index, 0, Fill['Ren 1'].values,   
                             alpha=Alpha_r, color = color_list[0])
        
        if Number_Renewable_Source > 1:
            for r in range(2,Number_Renewable_Source+1):
                c_ren = color_list[r-1]   
                ax1 = Fill['Ren ' +str(r)].plot(style='y-', linewidth=0)
                ax1.fill_between(Plot_Data.index, Fill['Ren ' +str(r-1)], Fill['Ren ' +str(r)].values,   
                                 alpha=Alpha_r, color = c_ren)

        # Genset Plot
        c_d = 'm'
        Alpha_g = 0.3 
        hatch_g = '\\'
        ax2 = Fill[g].plot(style='c', linewidth=0)
        ax2.fill_between(Plot_Data.index, Fill['Ren ' +str(r)].values, Fill[g].values,
                         alpha=Alpha_g, color=c_d, edgecolor=c_d, hatch =hatch_g)

        # Battery discharge
        alpha_bat = 0.3
        hatch_b ='x'
        c_bat = 'g'
        ax3 = Fill[b].plot(style='b', linewidth=0)
        ax3.fill_between(Plot_Data.index, Fill[g].values, Fill[b].values,   
                         alpha=alpha_bat, color=c_bat, edgecolor=c_bat, hatch =hatch_b)

        # Demand
        Plot_Data['Energy_Demand'].plot(style='k', linewidth=2)

        # Battery Charge        
        ax5= Plot_Data['Charge energy to the Battery'].plot(style='m', linewidth=0.5) # Plot the line of the energy flowing into the battery
        ax5.fill_between(Plot_Data.index, 0, 
                         Plot_Data['Charge energy to the Battery'].values
                         , alpha=alpha_bat, color=c_bat,edgecolor= c_bat, hatch ='x') 

        # State of charge of battery
        ax6= Plot_Data['State_Of_Charge_Battery'].plot(style='k--', 
                secondary_y=True, linewidth=2, alpha=0.7 ) 

        # Curtailment
        alpha_cu = 0.3
        hatch_cu = '+'
        C_Cur = 'b'
        ax7 = Fill[c].plot(style='b-', linewidth=0)
        ax7.fill_between(Plot_Data.index, Fill[c2].values , Fill[c].values, 
                         alpha=alpha_cu, color=C_Cur,edgecolor= C_Cur, 
                         hatch =hatch_cu,
                         where=Fill[c].values>Plot_Data['Energy_Demand']) 
        
        # Define name  and units of the axis
        ax0.set_ylabel('Power (kW)')
        ax0.set_xlabel('Time')
        ax6.set_ylabel('Battery State of charge (kWh)')
                
        # Define the legends of the plot
        From_Renewables = []
        for r in range(1,Number_Renewable_Source+1):
            c_ren = color_list[r-1]
            From_Renewables.append(mpatches.Patch(color=c_ren,alpha=Alpha_r, label='From Renewable '+str(r)))
        
        From_Generator = mpatches.Patch(color=c_d,alpha=Alpha_g,
                                        label='From Generator',hatch =hatch_g)
        Battery = mpatches.Patch(color=c_bat ,alpha=alpha_bat, 
                                 label='Battery Energy Flow',hatch =hatch_b)
        Curtailment = mpatches.Patch(color=C_Cur ,alpha=alpha_cu, 
                                 label='Curtailment',hatch =hatch_cu)

        Energy_Demand = mlines.Line2D([], [], color='black',label='Energy Demand')
        State_Of_Charge_Battery = mlines.Line2D([], [], color='black',
                                                label='State Of Charge Battery',
                                                linestyle='--',alpha=0.7)
        
        plt.legend(handles=[From_Generator, Battery, Curtailment,
                            Energy_Demand, State_Of_Charge_Battery],
                            bbox_to_anchor=(1.75, 1))
        
        from matplotlib.legend import Legend
        leg = Legend(ax0, From_Renewables[:], ['From Renewable '+str(i+1) for i in range(Number_Renewable_Source)],
             bbox_to_anchor=(1.67, 0.6), frameon=True)
        ax0.add_artist(leg);
        
        plt.savefig('Results/Energy_Dispatch.png', bbox_inches='tight')    
        plt.show()    
        
    else:   
        start = Time_Series.index[0]
        end = Time_Series.index[instance.Periods()-1]
        Time_Series = Time_Series.astype('float64')
        Plot_Data_2 = Time_Series[start:end].groupby([Time_Series[start:end].index.hour]).mean() # Creates a "typical" day by averaging over the time steps
        Plot_Data_2 = Plot_Data_2/1000
        Plot_Data_2['Charge energy to the Battery'] = -Plot_Data_2['Charge energy to the Battery']
        Plot_Data = Plot_Data_2
        
        Vec = pd.DataFrame()
        Vec.loc[:,'Ren 1'] = Plot_Data['Renewable Energy 1'] + Plot_Data['Energy Diesel']

        if Number_Renewable_Source > 1:
            dummy = Vec  
            for r in range(2,Number_Renewable_Source+1):
                dummy.loc[:,'Ren '+str(r)] = Plot_Data['Renewable Energy '+str(r)]
                Vec.loc[:,'Ren '+str(r)] = pd.Series.to_frame(dummy.sum(1))[0]                 
        
        Vec.loc[:,'Tot'] = Plot_Data['Total Renewable Energy'] + Plot_Data['Energy Diesel']
        
        # Renewable energy plot (first renewable outside for loop, if >1 renewables the others are plotted in the loop)
        color_list = ['yellow',(255/255,141/255,14/255),'c','0.6','y']
        Alpha_r = 0.4
        ax0 = Vec['Ren 1'].plot(style='y-', linewidth=0)
        ax0.fill_between(Plot_Data.index, Plot_Data['Energy Diesel'].values, Vec['Ren 1'].values,   
                             alpha=Alpha_r, color = color_list[0])

        if Number_Renewable_Source > 1:
            for r in range(2,Number_Renewable_Source+1):
                c_ren = color_list[r-1]   
                ax1 = Vec['Ren ' +str(r)].plot(style='y-', linewidth=0)
                ax1.fill_between(Plot_Data.index, Vec['Ren ' +str(r-1)], Vec['Ren ' +str(r)].values,   
                                 alpha=Alpha_r, color = c_ren)
        
        ax2= Plot_Data['Energy Diesel'].plot(style='m', linewidth=0.5)
        ax2.fill_between(Plot_Data.index, 0, Plot_Data['Energy Diesel'].values, 
                         alpha=0.2, color='m') # Fill the area of the energy produced by the diesel generator
        
        ax3 = Plot_Data['Energy_Demand'].plot(style='k', linewidth=2)
        ax3.fill_between(Plot_Data.index, Vec['Tot'].values , 
                         Plot_Data['Energy_Demand'].values,
                         alpha=0.3, color='g', 
                         where= Plot_Data['Energy_Demand']>= Vec['Tot'],interpolate=True)
        
        ax5= Plot_Data['Charge energy to the Battery'].plot(style='g', linewidth=0.5) # Plot the line of the energy flowing into the battery
        ax5.fill_between(Plot_Data.index, 0, 
                         Plot_Data['Charge energy to the Battery'].values
                         , alpha=0.3, color='g') # Fill the area of the energy flowing into the battery

        ax6= Plot_Data['State_Of_Charge_Battery'].plot(style='k--', secondary_y=True, linewidth=2, alpha=0.7 ) # Plot the line of the State of charge of the battery
        
        # Define name  and units of the axis
        ax0.set_ylabel('Power (kW)')
        ax0.set_xlabel('hours')
        ax6.set_ylabel('Battery State of charge (kWh)')
                
        # Define the legends of the plot
        From_Generator = mpatches.Patch(color='m',alpha=0.3, label='From Generator')

        Battery_Flow = mpatches.Patch(color='g',alpha=0.5, label='Battery Energy Flow')
        
        Lost_Load = mpatches.Patch(color='grey', alpha= 0.3, label= 'Lost Load')
        
        Energy_Demand = mlines.Line2D([], [], color='black',label='Energy_Demand')
        
        State_Of_Charge_Battery = mlines.Line2D([], [], color='black',
                                                label='State_Of_Charge_Battery',
                                                linestyle='--',alpha=0.7)

        plt.legend(handles=[From_Generator, Battery_Flow, Lost_Load, Energy_Demand, 
                            State_Of_Charge_Battery], bbox_to_anchor=(1.83, 1))

        From_Renewables = []
        for r in range(1,Number_Renewable_Source+1):
            c_ren = color_list[r-1]
            From_Renewables.append(mpatches.Patch(color=c_ren,alpha=Alpha_r, label='From Renewable '+str(r)))

        from matplotlib.legend import Legend
        leg = Legend(ax0, From_Renewables[:], ['From Renewable '+str(i+1) for i in range(Number_Renewable_Source)],
             bbox_to_anchor=(1.73, 0.6), frameon=True)
        ax0.add_artist(leg);

        plt.savefig('Results/Energy_Dispatch.png', bbox_inches='tight')    
        plt.show()    
    
def Energy_Mix(instance,Scenarios,Scenario_Probability):
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Energy_Totals = Scenarios.sum()
    
    Renewable_Energy = 0 
    Generator_Energy = 0
    Curtailment = 0
    Battery_Out = 0
    Demand = 0
    Energy_Mix = pd.DataFrame()
    
    for j in range(1, Number_Scenarios+1):   
       
        index_1 = 'Total Renewable Energy ' + str(j)    
        index_2 = 'Gen energy ' + str(j)
        index_3 = 'Scenario ' + str(j)
        index_4 = 'Curtailment ' + str(j)
        index_5 = 'Battery_Flow_Out ' + str(j)
        index_6 = 'Energy_Demand ' + str(j)
        
        Ren = Energy_Totals[index_1]
        Ge = Energy_Totals[index_2]
        We = Scenario_Probability[index_3]
        Cu = Energy_Totals[index_4]
        B_O = Energy_Totals[index_5]        
        De = Energy_Totals[index_6] 
        
        Renewable_Energy += Ren*We
        Generator_Energy += Ge*We  
        Curtailment += Cu*We
        Battery_Out += B_O*We
        Demand += De*We
        
        
        Energy_Mix.loc['Renewable Penetration',index_3] = Ren/(Ren+Ge)
        Energy_Mix.loc['Curtailment Percentage',index_3] = Cu/(Ren+Ge)
        Energy_Mix.loc['Battery Usage',index_3] = B_O/De
        
    Renewable_Real_Penetration = Renewable_Energy/(Renewable_Energy+Generator_Energy)
    Renewable_Real_Penetration = round(Renewable_Real_Penetration,4)
    Curtailment_Percentage = Curtailment/(Renewable_Energy+Generator_Energy)
    Curtailment_Percentage = round(Curtailment_Percentage,4)
    Battery_Usage = Battery_Out/Demand
    Battery_Usage = round(Battery_Usage,4)
    print(str(Renewable_Real_Penetration*100) + ' % Renewable Penetration')
    print(str(Curtailment_Percentage*100) + ' % of energy curtail')
    print(str(Battery_Usage*100) + ' % Battery usage')
    
    return Energy_Mix    
 
    
def Print_Results(instance, Generator_Data, Data_Renewable, Results, LCOE_1): #, LCOE_2):
    
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    for i in range(1, Number_Renewable_Source + 1):
        index_1 = 'Source ' + str(i)
        index_2 = 'Total Nominal Capacity'
    
        Renewable_Rate = float(Data_Renewable[index_1][index_2]/1000)
        Renewable_Rate = round(Renewable_Rate, 1)
        print('Renewable ' + str(i) + ' nominal capacity is ' 
              + str(Renewable_Rate) +' kW')    
        
    for i in range(1, Number_Generator + 1):
        index_1 = 'Generator ' + str(i)
        index_2 = 'Generator Nominal Capacity'
    
        Generator_Rate = float(Generator_Data[index_1][index_2]/1000)
        Generator_Rate = round(Generator_Rate, 1)
        print('Generator ' + str(i) + ' nominal capacity is ' 
              + str(Generator_Rate) +' kW')    
        
    
    index_2 = 'Battery Nominal Capacity'    
    Battery_Rate = Results[0][index_2]/1000
    Battery_Rate = round(Battery_Rate, 1)
    
    print('Battery nominal capacity is ' 
              + str(Battery_Rate) +' kWh') 
    
    index_2 = 'NPC'    
    NPC = Results[0][index_2]/1000
    NPC = round(NPC, 0)
    
    print('NPC is ' + str(NPC) +'Thousand USD') 



    LCOE_1 = round(LCOE_1, 3)    
    print('LCOE_1 is ' + str(LCOE_1) + ' $/kWh')  
    
#    LCOE_2 = round(LCOE_2, 3)    
#    print('LCOE_2 is ' + str(LCOE_2) + ' $/kWh')  

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
