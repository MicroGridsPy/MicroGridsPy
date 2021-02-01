# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from pandas import ExcelWriter
from numpy import interp
import math

def Load_results1(instance):
    '''
    This function loads the results that depend of the periods in to a dataframe and creates a excel file with it.
    
    :param instance: The instance of the project resolution created by PYOMO.
    
    :return: A dataframe called Time_series with the values of the variables that depend of the periods.    
    '''
    
    path = 'Results/Results.xls'
    writer = ExcelWriter(path, engine='xlsxwriter')
    
    # Load the variables that does not depend of the periods in python dyctionarys
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
    Number_Generator = int(instance.Generator_Type.extract_values()[None])
    
    Renewable_Nominal_Capacity = instance.Renewable_Nominal_Capacity.extract_values()
    Inverter_Efficiency_Renewable = instance.Renewable_Inverter_Efficiency.extract_values()
    Renewable_Invesment_Cost = instance.Renewable_Invesment_Cost.extract_values()
    OyM_Renewable = instance.Maintenance_Operation_Cost_Renewable.extract_values()
    Renewable_Units = instance.Renewable_Units.get_values()
    Data_Renewable = pd.DataFrame()
    
    for r in range(1, Number_Renewable_Source + 1):
        
        Name = 'Source ' + str(r)
        Data_Renewable.loc['Units', Name] = Renewable_Units[r]
        Data_Renewable.loc['Nominal Capacity (kW)', Name] = Renewable_Nominal_Capacity[r]
        Data_Renewable.loc['Inverter Efficiency', Name] = Inverter_Efficiency_Renewable[r]
        Data_Renewable.loc['Investment Cost (USD/kW)', Name] = Renewable_Invesment_Cost[r]
        Data_Renewable.loc['OyM', Name] = OyM_Renewable[r]
        Data_Renewable.loc['Invesment (USD)', Name] = Renewable_Units[r]*Renewable_Nominal_Capacity[r]*Renewable_Invesment_Cost[r]        
        Data_Renewable.loc['OyM Cost (USD)', Name] = Data_Renewable.loc['Invesment (USD)', Name]*OyM_Renewable[r]        
        Data_Renewable.loc['Total Nominal Capacity (kW)', Name] = Data_Renewable.loc['Nominal Capacity (kW)', Name]*Data_Renewable.loc['Units', Name]    

    Data_Renewable.to_excel(writer, sheet_name='Data Renewable')    
    
    columns = []
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))


    # Energy Time Series
    Scenarios = pd.DataFrame()
    
    Number = 7
    
    if instance.Lost_Load_Probability > 0: 
        Lost_Load = instance.Lost_Load.get_values()
        Number += 1
    
    Renewable_Energy_1 = instance.Renewable_Energy_Production.extract_values()
    Renewable_Units = instance.Renewable_Units.get_values()
    Renewable_Energy = {}
   
    for s in range(1, Number_Scenarios + 1):
        for t in range(1, Number_Periods+1):
            
            foo = []
            for r in range(1,Number_Renewable_Source+1 ):
                foo.append((s,r,t))
            
            Renewable_Energy[s,t] = sum(Renewable_Energy_1[s,r,t]*Data_Renewable.loc['Inverter Efficiency', 'Source ' + str(r)]
                            *Data_Renewable.loc['Units', 'Source ' + str(r)] for s,r,t in foo)
            
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Generator_Energy = instance.Generator_Energy.get_values()
    Total_Generator_Energy = {}
    
                
    for s in range(1, Number_Scenarios + 1):
          for t in range(1, Number_Periods+1):
                foo = []
                for g in range(1,Number_Generator+1):
                    foo.append((s,g,t))
                Total_Generator_Energy[s,t] = sum(Generator_Energy[i] for i in foo)
                
    Scenarios_Periods = [[] for i in range(Number_Scenarios)]
    
    for i in range(0,Number_Scenarios):
        for j in range(1, Number_Periods+1):
            Scenarios_Periods[i].append((i+1,j))
    foo=0        
    for i in columns:
        Information = [[] for i in range(Number)]
        for j in  Scenarios_Periods[foo]:
            
            Information[0].append(Renewable_Energy[j]) 
            Information[1].append(Battery_Flow_Out[j]) 
            Information[2].append(Battery_Flow_in[j]) 
            Information[3].append(Curtailment[j]) 
            Information[4].append(Energy_Demand[j]) 
            Information[5].append(SOC[j])
            Information[6].append(Total_Generator_Energy[j])
            if instance.Lost_Load_Probability > 0: 
                Information[7].append(Lost_Load[j])
        
        Scenarios=Scenarios.append(Information)
        foo+=1
    
    index=[]  
    for j in range(1, Number_Scenarios+1):   
       index.append('Renewable Energy '+str(j) + ' (kWh)')
       index.append('Battery Flow Out '+str(j) + ' (kWh)') 
       index.append('Battery Flow in '+str(j) + ' (kWh)')
       index.append('Curtailment '+str(j) + ' (kWh)')
       index.append('Energy Demand '+str(j) + ' (kWh)')
       index.append('SOC '+str(j) + ' (kWh)')
       index.append('Gen energy '+str(j) + ' (kWh)')
       if instance.Lost_Load_Probability > 0: 
           index.append('Lost Load '+str(j) + ' (kWh)')
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
    
    Scenarios.to_excel(writer, sheet_name='Time Series') # Creating an excel file with the values of the variables that are in function of the periods
    
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
    
    Scenario_Information.to_excel(writer, sheet_name='Scenario Information')
           
    Renewable_Energy = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
        for r in range(1, Number_Renewable_Source + 1):
            column = 'Renewable ' + str(s) + ' ' + str(r) + ' (kWh)'
            
            Energy = []
            for t in range(1, Number_Periods + 1):
                Source = 'Source ' + str(r)
                Energy.append(Renewable_Energy_1[s,r,t]*Data_Renewable.loc['Inverter Efficiency', Source]
                            *Data_Renewable.loc['Units', Source])
        
            Renewable_Energy[column] = Energy
        
        
    Renewable_Energy.index = Scenarios.index
    Renewable_Energy.to_excel(writer, sheet_name='Renewable Energy Time Series')
    
    

    Generator_Data = pd.DataFrame()
    
    if instance.formulation == 'LP':
 
        Generator_Efficiency = instance.Generator_Efficiency.extract_values()
        Low_Heating_Value = instance.Low_Heating_Value.extract_values()
        Fuel_Cost = instance.Fuel_Cost.extract_values()
        Generator_Invesment_Cost = instance.Generator_Invesment_Cost.extract_values()
        Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.get_values()
        Maintenance_Operation_Cost_Generator = instance.Maintenance_Operation_Cost_Generator.extract_values()
        
        for g in range(1, Number_Generator + 1):
            Name = 'Generator ' + str(g)
            Generator_Data.loc['Generator Efficiency',Name] = Generator_Efficiency[g]
            Generator_Data.loc['Low Heating Value (kWh/l)',Name] = Low_Heating_Value[g]
            Generator_Data.loc['Fuel Cost (USD/l)',Name] = Fuel_Cost[g]
            Generator_Data.loc['Generator Invesment Cost (USD/kW)',Name] = Generator_Invesment_Cost[g]
            Generator_Data.loc['Generator Nominal Capacity (kW)',Name] = Generator_Nominal_Capacity[g]
            Generator_Data.loc['OyM Generator', Name] = Maintenance_Operation_Cost_Generator[g]
            Generator_Data.loc['Invesment Generator (USD)', Name] = Generator_Invesment_Cost[g]*Generator_Nominal_Capacity[g]
            Generator_Data.loc['OyM Cost (USD)', Name] = Generator_Data.loc['Invesment Generator (USD)', Name]*Generator_Data.loc['OyM Generator', Name]
            Generator_Data.loc['Marginal Cost (USD/kWh)', Name] = (Generator_Data.loc['Fuel Cost (USD/l)',Name]/
                                      (Generator_Data.loc['Generator Efficiency',Name]*Generator_Data.loc['Low Heating Value (kWh/l)',Name]))
            Generator_Data.loc['Marginal Cost (USD/kWh)', Name] = round(Generator_Data.loc['Marginal Cost (USD/kWh)', Name],3)
    
    if instance.formulation == 'MILP':
        Generator_Min_Out_Put = instance.Generator_Min_Out_Put.extract_values()
        Generator_Efficiency = instance.Generator_Efficiency.extract_values()
        Low_Heating_Value = instance.Low_Heating_Value.extract_values()
        Fuel_Cost = instance.Fuel_Cost.extract_values()
        Generator_Invesment_Cost = instance.Generator_Invesment_Cost.extract_values()
        Cost_Increase = instance.Cost_Increase.extract_values()       
        Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.extract_values()
        Integer_generator = instance.Integer_generator.get_values()
        Maintenance_Operation_Cost_Generator = instance.Maintenance_Operation_Cost_Generator.extract_values()
    
        for g in range(1, Number_Generator + 1):
                Name = 'Generator ' + str(g)
                Generator_Data.loc['Generator Nominal Capacity (kW)',Name] = Generator_Nominal_Capacity[g]
                Generator_Data.loc['Generator Min Out Put',Name] = Generator_Min_Out_Put[g]
                Generator_Data.loc['Generator Efficiency',Name] = Generator_Efficiency[g]
                Generator_Data.loc['Low Heating Value (kWh/l)',Name] = Low_Heating_Value[g]
                Generator_Data.loc['Fuel Cost (USD/l)',Name] = Fuel_Cost[g]
                Generator_Data.loc['Generator Invesment Cost (USD/kW)',Name] = Generator_Invesment_Cost[g]
                Generator_Data.loc['Cost Increase',Name] = Cost_Increase[g]
                M_1 = Fuel_Cost[g]/(Generator_Efficiency[g]*Low_Heating_Value[g])
                Generator_Data.loc['Marginal cost Full load (USD/kWh)',Name] = round(M_1,3)
                Generator_Data.loc['Start Cost Generator (USD)',Name] = Generator_Data.loc['Marginal cost Full load (USD/kWh)',Name]*Generator_Nominal_Capacity[g]*Cost_Increase[g]
                Generator_Data.loc['Start Cost Generator (USD)',Name] = round(Generator_Data.loc['Start Cost Generator (USD)',Name],3)
                Generator_Data.loc['Marginal cost Partial load (USD/kWh)',Name] = (Generator_Data.loc['Marginal cost Full load (USD/kWh)',Name]\
                                                                                  *Generator_Data.loc['Generator Nominal Capacity (kW)',Name]\
                                                                      - Generator_Data.loc['Start Cost Generator (USD)',Name])/Generator_Data.loc['Generator Nominal Capacity (kW)',Name]
                
                
                
                
                
                
                Generator_Data.loc['Marginal cost Partial load (USD/kWh)',Name] = round(Generator_Data.loc['Marginal cost Partial load (USD/kWh)',Name],3)
                Generator_Data.loc['Number of Generators', Name] = Integer_generator[g]
                Generator_Data.loc['Maintenance Operation Cost Generator', Name] = Maintenance_Operation_Cost_Generator[g]
                Generator_Data.loc['Invesment Generator (USD)', Name] = (Generator_Nominal_Capacity[g]
                                                                        *Integer_generator[g]*Generator_Invesment_Cost[g])
                Generator_Data.loc['OyM Cost (USD)', Name] = (Generator_Nominal_Capacity[g]*Integer_generator[g]
                                                                         *Generator_Invesment_Cost[g]
                                                                         *Maintenance_Operation_Cost_Generator[g])
    
    Generator_Data.to_excel(writer, sheet_name='Generator Data')      

    Project_Data = pd.Series()
    Project_Data['Net Present Cost (USD)'] = instance.ObjectiveFuntion.expr()
    Project_Data['Discount Rate'] = instance.Discount_Rate.value
    Project_Data['Proyect Life Time (years)'] = instance.Years.value
    Project_Data['Number of Scenarios'] = Number_Scenarios
    Project_Data['Periods of the year'] = Number_Periods
    Project_Data['Value of lost load (USD/kWh)'] = instance.Value_Of_Lost_Load.value
    Project_Data['Types of generators'] = Number_Generator
    Project_Data['Types of renewable sources'] = Number_Renewable_Source
    a =  Project_Data['Discount Rate']*((1+Project_Data['Discount Rate'])**Project_Data['Proyect Life Time (years)'])
    b =  ((1 + Project_Data['Discount Rate'])**Project_Data['Proyect Life Time (years)']) - 1
    Project_Data['Capital Recovery Factor'] = a/b
    if instance.Curtailment_Unitary_Cost > 0:
        Project_Data['Curtailment Unitary Cost (USD/kWh)'] = instance.Curtailment_Unitary_Cost
    if instance.Lost_Load_Probability > 0:
        Project_Data['Lost Load Probability (%)'] = instance.Lost_Load_Probability*100
    else:
        Project_Data['Lost Load Probability (%)'] = instance.Lost_Load_Probability
        
    Project_Data.to_excel(writer, sheet_name='Project Data') 
    
    
    Battery_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()[None]
    PriceBattery = instance.Battery_Invesment_Cost.value
    Battery_Electronic_Invesmente_Cost = instance.Battery_Electronic_Invesmente_Cost.value
    OM_Bat = instance.Maintenance_Operation_Cost_Battery.value
    SOC_1 = instance.Battery_Initial_SOC.value
    Ch_bat_eff = instance.Charge_Battery_Efficiency.value
    Dis_bat_eff = instance.Discharge_Battery_Efficiency.value
    Deep_of_Discharge = instance.Deep_of_Discharge.value
    Battery_Cycles = instance.Battery_Cycles.value
    
    Unitary_Battery_Cost = PriceBattery - Battery_Electronic_Invesmente_Cost
    Battery_Repostion_Cost =  Unitary_Battery_Cost/(Battery_Cycles*2*(1-Deep_of_Discharge))
    Battery_Repostion_Cost = round(Battery_Repostion_Cost, 3)
    Battery_Data = pd.DataFrame()
    
    Battery_Data.loc['Nominal Capacity (kWh)','Battery'] = Battery_Nominal_Capacity
    Battery_Data.loc['Unitary Invesment Cost (USD/kWh)','Battery'] = PriceBattery
    Battery_Data.loc['Unitary invesment cost electronic equipment (USD/kWh)','Battery'] = Battery_Electronic_Invesmente_Cost
    Battery_Data.loc['OyM','Battery'] = OM_Bat
    Battery_Data.loc['Initial State of Charge','Battery'] = SOC_1
    Battery_Data.loc['Charge efficiency','Battery'] = Ch_bat_eff
    Battery_Data.loc['Discharge efficiency','Battery'] = Dis_bat_eff
    Battery_Data.loc['Deep of Discharge','Battery'] = Deep_of_Discharge
    Battery_Data.loc['Battery Cycles','Battery'] = Battery_Cycles
    Battery_Data.loc['Unitary Battery Reposition Cost (USD/kWh)','Battery'] =  Battery_Repostion_Cost
    Battery_Data.loc['Invesment Cost (USD)','Battery'] = Battery_Nominal_Capacity*PriceBattery
    Battery_Data.loc['OyM Cost (USD)', 'Battery'] = Battery_Nominal_Capacity*PriceBattery*OM_Bat
     
    Battery_Data.to_excel(writer, sheet_name='Battery Data')
    
    Generator_Time_Series = pd.DataFrame()
    
    if instance.formulation == 'LP': 
        for s in range(1, Number_Scenarios + 1):   
            for g in range(1, Number_Generator + 1):
                column_1 = 'Energy Generator ' + str(s) + ' ' + str(g) + ' (kWh)'  
                column_2 = 'Fuel Cost ' + str(s) + ' ' + str(g) + ' (USD)'  
                Name =  'Generator ' + str(g)
                for t in range(1, Number_Periods + 1):
                    Generator_Time_Series.loc[t,column_1] = Generator_Energy[s,g,t]
                    Generator_Time_Series.loc[t,column_2] = (Generator_Time_Series.loc[t,column_1]
                                                            *Generator_Data.loc['Marginal Cost (USD/kWh)', Name]) 
    if instance.formulation == 'MILP':
            Generator_Integer = instance.Generator_Energy_Integer.get_values()
            for s in range(1, Number_Scenarios + 1):
                for g in range(1, Number_Generator + 1):
                    column_1 = 'Energy Generator ' + str(s) + ' ' + str(g)  + ' (kWh)' 
                    column_2 = 'Integer Generator ' + str(s) + ' ' + str(g)
                    column_3 = 'Fuel Cost ' + str(s) + ' ' + str(g) + ' (USD)' 
                    Name =  'Generator ' + str(g)
                    for t in range(1, Number_Periods + 1):
                        Generator_Time_Series.loc[t,column_1] = Generator_Energy[s,g,t]
                        Generator_Time_Series.loc[t,column_2] = Generator_Integer[s,g,t]
                        Generator_Time_Series.loc[t,column_3] = (Generator_Integer[s,g,t]*Generator_Data.loc['Start Cost Generator (USD)',Name] 
                                        + Generator_Energy[s,g,t]*Generator_Data.loc['Marginal cost Partial load (USD/kWh)',Name] )
            
         
    Generator_Time_Series.index = Scenarios.index           
    Generator_Time_Series.to_excel(writer, sheet_name='Generator Time Series')                

    Cost_Time_Series = pd.DataFrame()
    for s in range(1, Number_Scenarios + 1):
        if instance.Lost_Load_Probability > 0:
            name_1 = 'Lost Load ' + str(s) + ' (kWh)'
            name_1_1 = 'Lost Load ' + str(s) + ' (USD)'
        name_2 = 'Battery Flow Out ' + str(s) + ' (kWh)' 
        name_2_1 = 'Battery Flow Out ' + str(s) + ' (USD)' 
        name_3 = 'Battery Flow in ' + str(s) + ' (kWh)'  
        name_3_1 = 'Battery Flow In ' + str(s) + ' (USD)' 
        name_4_1 = 'Generator Cost ' + str(s) + ' (USD)' 

        for t in Scenarios.index:
            if instance.Lost_Load_Probability > 0:
                Cost_Time_Series.loc[t,name_1_1] = Scenarios[name_1][t]*Project_Data['Value of lost load (USD/kWh)']
            Cost_Time_Series.loc[t,name_2_1] = (Scenarios[name_2][t]
                                              *Battery_Data.loc['Unitary Battery Reposition Cost (USD/kWh)','Battery'])
            Cost_Time_Series.loc[t,name_3_1] = (Scenarios[name_3][t]
                                              *Battery_Data.loc['Unitary Battery Reposition Cost (USD/kWh)','Battery'])
            Fuel_Cost = 0
            for g in range(1, Number_Generator + 1):
                name_5 = 'Fuel Cost ' + str(s) + ' ' + str(g) + ' (USD)'  
                Fuel_Cost += Generator_Time_Series.loc[t,name_5]
            Cost_Time_Series.loc[t,name_4_1] = Fuel_Cost
            
            if instance.Curtailment_Unitary_Cost > 0:
                name_6 = 'Curtailment ' + str(s) + ' (kWh)'
                name_6_1 = 'Curtailment Cost ' + str(s) + ' (USD)' 
                Cost_Time_Series.loc[t,name_6_1] = (Scenarios[name_6][t]*Project_Data['Curtailment Unitary Cost (USD/kWh)'])
            
    Cost_Time_Series.to_excel(writer, sheet_name='Cost Time Series')
            
    Scenario_Cost = pd.DataFrame()    
    for s in range(1, Number_Scenarios + 1):
        if instance.Lost_Load_Probability > 0:
            name_1_1 = 'Lost Load ' + str(s) + ' (USD)'
            name_1 ='Lost Load (USD)'
        name_2_1 = 'Battery Flow Out ' + str(s) + ' (USD)'
        name_2 = 'Battery Flow Out (USD)'
        name_3_1 = 'Battery Flow In ' + str(s) + ' (USD)' 
        name_3 = 'Battery Flow In (USD)'
        name_4_1 = 'Generator Cost ' + str(s) + ' (USD)'
        name_4 = 'Generator Cost (USD)'
        if instance.Curtailment_Unitary_Cost > 0:
                name_6 = 'Curtailment ' + str(s) + ' (kWh)'
                name_6_1 = 'Curtailment Cost ' + str(s) + ' (USD)' 
        
        
        name_5 = 'Scenario ' + str(s)
        if instance.Lost_Load_Probability > 0:
            Scenario_Cost.loc[name_1,name_5] = Cost_Time_Series[name_1_1].sum()
        Scenario_Cost.loc[name_2,name_5] = Cost_Time_Series[name_2_1].sum()
        Scenario_Cost.loc[name_3,name_5] = Cost_Time_Series[name_3_1].sum()
        Scenario_Cost.loc[name_4,name_5] = Cost_Time_Series[name_4_1].sum() 
        if instance.Curtailment_Unitary_Cost > 0:    
            Scenario_Cost.loc[name_6,name_5] = Cost_Time_Series[name_6_1].sum() 
        
        gen_oym = 0
        for g in range(1, Number_Generator + 1):
            Name_2 = 'Generator ' + str(g)
            gen_oym += Generator_Data.loc['OyM Cost (USD)', Name_2]
        Scenario_Cost.loc['Gen OyM Cost (USD)',name_5] = gen_oym
        
        renewable_energy_oym = 0
        for r in range(1, Number_Renewable_Source + 1):
            Name = 'Source ' + str(r)
            renewable_energy_oym += Data_Renewable.loc['OyM Cost (USD)', Name]
        Scenario_Cost.loc['PV OyM Cost (USD)',name_5] = renewable_energy_oym

        Scenario_Cost.loc['Battery OyM Cost (USD)',name_5] = Battery_Data['Battery']['OyM Cost (USD)']
        
        Scenario_Cost.loc['Operation Cost (USD)',name_5] = Scenario_Cost[name_5].sum()  
        
        Discount_rate = Project_Data['Discount Rate']
        Years =  int(Project_Data['Proyect Life Time (years)'])
        
        
        Scenario_Cost.loc['OyM (USD)',name_5] = (Scenario_Cost.loc['Gen OyM Cost (USD)',name_5] 
                                        +Scenario_Cost.loc['PV OyM Cost (USD)',name_5]
                                        +Scenario_Cost.loc['Battery OyM Cost (USD)',name_5])
# Present values with capital recovery factor        
        Scenario_Cost.loc['Present Gen Cost (USD)',name_5] = Scenario_Cost.loc[name_4,name_5]/Project_Data['Capital Recovery Factor']
        if instance.Lost_Load_Probability > 0:
            Scenario_Cost.loc['Present Lost Load Cost (USD)',name_5] = Scenario_Cost.loc[name_1,name_5]/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present Bat Out Cost (USD)',name_5] = Scenario_Cost.loc[name_2,name_5]/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present Bat In Cost (USD)',name_5] = Scenario_Cost.loc[name_3,name_5]/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present Bat Reposition Cost (USD)',name_5] = (Scenario_Cost.loc[name_2,name_5] + Scenario_Cost.loc[name_3,name_5])/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present OyM Cost (USD)',name_5] = Scenario_Cost.loc['OyM (USD)',name_5]/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present Operation Cost (USD)',name_5] = Scenario_Cost[name_5]['Operation Cost (USD)']/Project_Data['Capital Recovery Factor']
        Scenario_Cost.loc['Present Operation Cost Weighted (USD)',name_5] = (Scenario_Cost[name_5]['Present Operation Cost (USD)']
                                                                    *Scenario_Information[name_5]['Scenario Weight'])
        
# Present values with sum of the different years
        
        # Scenario_Cost.loc['Present Gen Cost (USD)',name_5] = sum((Scenario_Cost.loc[name_4,name_5]/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # if instance.Lost_Load_Probability > 0:
        #     Scenario_Cost.loc['Present Lost Load Cost (USD)',name_5] = sum((Scenario_Cost.loc[name_1,name_5]/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present Bat Out Cost (USD)',name_5] = sum((Scenario_Cost.loc[name_2,name_5]/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present Bat In Cost (USD)',name_5] = sum((Scenario_Cost.loc[name_2,name_5]/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present Bat Reposition Cost (USD)',name_5] = sum(((Scenario_Cost.loc[name_2,name_5] + Scenario_Cost.loc[name_3,name_5])/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present OyM Cost (USD)',name_5] = sum((Scenario_Cost.loc['OyM (USD)',name_5]/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present Operation Cost (USD)',name_5] = sum((Scenario_Cost[name_5]['Operation Cost (USD)']/((1+Discount_rate)**period) for period in range(1,Years+1)))
        # Scenario_Cost.loc['Present Operation Cost Weighted (USD)',name_5] = (Scenario_Cost[name_5]['Present Operation Cost (USD)']
        #                                                             *Scenario_Information[name_5]['Scenario Weight'])
    
    Scenario_Cost.to_excel(writer, sheet_name='Scenario Costs')
    
    NPC = pd.DataFrame()
    NPC.loc['Battery Invesment (USD)', 'Data'] = Battery_Data['Battery']['Invesment Cost (USD)'] 
    
    gen_Invesment = 0
    for g in range(1, Number_Generator + 1):
        Name_2 = 'Generator ' + str(g)
        gen_Invesment += Generator_Data.loc['Invesment Generator (USD)', Name_2]
    NPC.loc['Generator Invesment Cost (USD)', 'Data'] = gen_Invesment
    
    renewable_energy_invesment = 0
    for r in range(1, Number_Renewable_Source + 1):
            Name = 'Source ' + str(r)
            renewable_energy_invesment += Data_Renewable.loc['Invesment (USD)', Name]
    NPC.loc['Renewable Investment Cost (USD)', 'Data'] = renewable_energy_invesment 
    
    operation_cost = 0
    for s in range(1, Number_Scenarios + 1):
        name_1 = 'Scenario ' + str(s)
        operation_cost += Scenario_Cost[name_1]['Present Operation Cost Weighted (USD)']

    NPC.loc['Present Operation Cost Weighted (USD)', 'Data'] = operation_cost

    
    NPC.loc['NPC (USD)', 'Data'] = NPC['Data'].sum()
    
    print(round(NPC.loc['NPC (USD)', 'Data'],5) == round(instance.ObjectiveFuntion.expr(), 5))
    
    NPC.loc['NPC LP (USD)', 'Data'] = Project_Data['Net Present Cost (USD)']
    NPC.loc['Invesment (USD)', 'Data'] = (NPC.loc['Battery Invesment (USD)', 'Data'] 
                                     + NPC.loc['Generator Invesment Cost (USD)', 'Data'] 
                                     + NPC.loc['Renewable Investment Cost (USD)', 'Data'])
    
    
    
    Demand = pd.DataFrame()
    NP_Demand = 0
    for s in range(1, Number_Scenarios + 1):
        a = 'Energy Demand ' + str(s) + ' (kWh)'
        b = 'Scenario ' + str(s)
        Demand.loc[a,'Total Demand (kWh)'] = sum(Scenarios[a][i] for i in Scenarios.index)
        Demand.loc[a,'Present Demand (kWh)'] = sum((Demand.loc[a,'Total Demand (kWh)']/(1+Discount_rate)**i) 
                                                            for i in range(1, Years+1))  
        Demand.loc[a,'Rate'] = Scenario_Information[b]['Scenario Weight']                                                         
        Demand.loc[a,'Rated Demand (kWh)'] = Demand.loc[a,'Rate']*Demand.loc[a,'Present Demand (kWh)'] 
        NP_Demand += Demand.loc[a,'Rated Demand (kWh)']
    NPC.loc['LCOE (USD/kWh)', 'Data'] = (Project_Data['Net Present Cost (USD)']/NP_Demand)
    
    
    NPC.to_excel(writer, sheet_name='Results')
    
    Data = []
    Data.append(NPC)
    Data.append(Scenario_Cost)
    Data.append(Project_Data)
    Data.append(Scenarios)
    Data.append(Generator_Data)
    Data.append(Scenario_Information)
    Data.append(Data_Renewable)
    Data.append(Battery_Data)
    
    writer.save()

    return Data

def Integer_Time_Series(instance,Scenarios, S, Data):
    
    if S == 0:
        S = instance.PlotScenario.value
    
    Time_Series = pd.DataFrame(index=range(0,8760))
    Time_Series.index = Scenarios.index
    if instance.Lost_Load_Probability > 0:
        Time_Series['Lost Load (kWh)'] = Scenarios['Lost Load ' + str(S) + ' (kWh)']
    Time_Series['Renewable Energy (kWh)'] = Scenarios['Renewable Energy '+str(S) + ' (kWh)']
    Time_Series['Discharge energy from the Battery (kWh)'] = Scenarios['Battery Flow Out ' + str(S) + ' (kWh)'] 
    Time_Series['Charge energy to the Battery (kWh)'] = Scenarios['Battery Flow in '+str(S) + ' (kWh)']
    Time_Series['Curtailment (kWh)'] = Scenarios['Curtailment '+str(S) + ' (kWh)']
    Time_Series['Energy Demand (kWh)'] = Scenarios['Energy Demand '+str(S) + ' (kWh)']
    Time_Series['State Of Charge Battery (kWh)'] = Scenarios['SOC '+str(S) + ' (kWh)'] 
    Time_Series['Generator Energy (kWh)'] = Scenarios['Gen energy '+str(S) + ' (kWh)']
    
    Renewable_Source = instance.Renewable_Source.value
    if Renewable_Source > 1:
        Renewable_Energy =  pd.read_excel('Results/Results.xls',index_col=0,Header=None,
                                          sheet_name='Renewable Energy Time Series')
        for r in range(1,Renewable_Source+1):
            name = 'Renewable ' + str(S) + ' ' + str(r) + ' (kWh)'
            name_1 = 'Renewable '  + str(r) + ' (kWh)'
            Time_Series[name_1] = Renewable_Energy[name]
    
    return Time_Series   
    
    

def Load_results1_binary(instance):
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
    
    #Scenarios = [[] for i in range(Number_Scenarios)]
    
    columns = []
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))

#    columns=columns
    Scenarios = pd.DataFrame()
    
     
    Lost_Load = instance.Lost_Load.get_values()
    PV_Energy = instance.Total_Energy_PV.get_values()
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Gen_Energy_Integer = instance.Generator_Energy_Integer.get_values()
    Gen_Energy_I = {}
    
    for i in range(1,Number_Scenarios+1):
        for j in range(1, Number_Periods+1):
            Gen_Energy_I[i,j]=(Gen_Energy_Integer[i,j]*instance.Generator_Nominal_Capacity.extract_values()[None])        
    
    Last_Generator_Energy = instance.Last_Energy_Generator.get_values()        
    Total_Generator_Energy = instance.Generator_Total_Period_Energy.get_values() 
    Gen_cost = instance.Period_Total_Cost_Generator.get_values()       
    
    Scenarios_Periods = [[] for i in range(Number_Scenarios)]
    
    for i in range(0,Number_Scenarios):
        for j in range(1, Number_Periods+1):
            Scenarios_Periods[i].append((i+1,j))
    foo=0        
    for i in columns:
        Information = [[] for i in range(11)]
        for j in  Scenarios_Periods[foo]:
            Information[0].append(Lost_Load[j])
            Information[1].append(PV_Energy[j]) 
            Information[2].append(Battery_Flow_Out[j]) 
            Information[3].append(Battery_Flow_in[j]) 
            Information[4].append(Curtailment[j]) 
            Information[5].append(Energy_Demand[j]) 
            Information[6].append(SOC[j])
            Information[7].append(Gen_Energy_I[j])
            Information[8].append(Last_Generator_Energy[j])
            Information[9].append(Total_Generator_Energy[j])
            Information[10].append(Gen_cost[j])
        
        Scenarios=Scenarios.append(Information)
        foo+=1
    
    index=[]  
    for j in range(1, Number_Scenarios+1):   
       index.append('Lost_Load '+str(j))
       index.append('PV_Energy '+str(j))
       index.append('Battery_Flow_Out '+str(j)) 
       index.append('Battery_Flow_in '+str(j))
       index.append('Curtailment '+str(j))
       index.append('Energy_Demand '+str(j))
       index.append('SOC '+str(j))
       index.append('Gen energy Integer '+str(j))
       index.append('Last Generator Energy '+str(j))
       index.append('Total Generator Energy '+str(j))
       index.append('Total Cost Generator'+str(j))
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
    
    columns = [] # arreglar varios columns
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))
        
    Scenario_information =[[] for i in range(Number_Scenarios)]
    Scenario_NPC = instance.Scenario_Net_Present_Cost.get_values()
    LoL_Cost = instance.Scenario_Lost_Load_Cost.get_values() 
    Scenario_Weight = instance.Scenario_Weight.extract_values()
    Diesel_Cost = instance.Sceneario_Generator_Total_Cost.get_values()
    
    for i in range(1, Number_Scenarios+1):
        Scenario_information[i-1].append(Scenario_NPC[i])
        Scenario_information[i-1].append(LoL_Cost[i])
        Scenario_information[i-1].append(Scenario_Weight[i])
        Scenario_information[i-1].append(Diesel_Cost[i])
    
    
    Scenario_Information = pd.DataFrame(Scenario_information,index=columns)
    Scenario_Information.columns=['Scenario NPC', 'LoL Cost','Scenario Weight', 'Diesel Cost']
    Scenario_Information = Scenario_Information.transpose()
    
    Scenario_Information.to_excel('Results/Scenario_Information.xls')
    
    S = instance.PlotScenario.value
    Time_Series = pd.DataFrame(index=range(0,8760))
    Time_Series.index = Scenarios.index
    
    Time_Series['Lost Load'] = Scenarios['Lost_Load '+str(S)]
    Time_Series['Energy PV'] = Scenarios['PV_Energy '+str(S)]
    Time_Series['Discharge energy from the Battery'] = Scenarios['Battery_Flow_Out '+str(S)] 
    Time_Series['Charge energy to the Battery'] = Scenarios['Battery_Flow_in '+str(S)]
    Time_Series['Curtailment'] = Scenarios['Curtailment '+str(S)]
    Time_Series['Energy_Demand'] = Scenarios['Energy_Demand '+str(S)]
    Time_Series['State_Of_Charge_Battery'] = Scenarios['SOC '+str(S)]
    Time_Series['Gen energy Integer'] = Scenarios['Gen energy Integer '+str(S)]
    Time_Series['Last Generator Energy'] = Scenarios['Last Generator Energy ' +str(j)]    
    Time_Series['Energy Diesel'] = Scenarios['Total Generator Energy '+str(j)]
    
    
    return Time_Series
    
    
    
    
def Load_results2_binary(instance):
    '''
    This function extracts the unidimensional variables into a  data frame 
    and creates a excel file with this data
    
    :param instance: The instance of the project resolution created by PYOMO. 
    
    :return: Data frame called Size_variables with the variables values. 
    '''
    # Load the variables that doesnot depend of the periods in python dyctionarys
    Amortizacion = instance.Cost_Financial.get_values()[None]
    cb = instance.PV_Units.get_values()
    cb = cb.values()
    Size_PV=[list(cb)[0]*instance.PV_Nominal_Capacity.value]
    Size_Bat = instance.Battery_Nominal_Capacity.get_values()[None]
    Gen_cap = instance.Generator_Nominal_Capacity.value
    Gen_Power = Gen_cap*instance.Integer_generator.get_values()[None]
    NPC = instance.ObjectiveFuntion.expr()
    Mge_1 = instance.Marginal_Cost_Generator_1.value
    Start_Cost = instance.Start_Cost_Generator.value
    Funded= instance.Porcentage_Funded.value
    DiscountRate = instance.Discount_Rate.value
    InterestRate = instance.Interest_Rate_Loan.value
    PricePV = instance.PV_invesment_Cost.value
    PriceBatery= instance.Battery_Invesment_Cost.value
    PriceGenSet= instance.Generator_Invesment_Cost.value
    OM = instance.Maintenance_Operation_Cost_PV.value
    Years=instance.Years.value
    VOLL= instance.Value_Of_Lost_Load.value
    Mge_2 = instance.Marginal_Cost_Generator.value
    data3 = [Amortizacion, Size_PV[0], Size_Bat, Gen_cap, Gen_Power,NPC,Mge_1, Mge_2 , 
            Start_Cost, Funded,DiscountRate,InterestRate,PricePV,PriceBatery,
            PriceGenSet,OM,Years,VOLL] # Loading the values to a numpy array  
    Size_variables = pd.DataFrame(data3,index=['Amortization', 'Size of the solar panels', 
                                               'Size of the Battery','Nominal Capacity Generator',
                                               'Generator Install power','Net Present Cost',
                                               'Marginal cost Full load',
                                               'Marginal cost Partial load', 'Start Cost',
                                               'Funded Porcentage', 'Discount Rate', 
                                               'Interest Rate','Precio PV', 'Precio Bateria',
                                               'Precio GenSet','OyM', 'Project years','VOLL'])
    Size_variables.to_excel('Results/Size.xls') # Creating an excel file with the values of the variables that does not depend of the periods
    
    I_Inv = instance.Initial_Inversion.get_values()[None] 
    O_M = instance.Operation_Maintenance_Cost.get_values()[None] 
    Financial_Cost = instance.Total_Finalcial_Cost.get_values()[None] 
    Batt_Reposition = instance.Battery_Reposition_Cost.get_values()[None] 
    
    Data = [I_Inv, O_M, Financial_Cost,Batt_Reposition]
    Value_costs = pd.DataFrame(Data, index=['Initial Inversion', 'O & M',
                                            'Financial Cost', 'Battery reposition'])

    Value_costs.to_excel('Results/Partial Costs.xls')    


    VOLL = instance.Scenario_Lost_Load_Cost.get_values() 
    Scenario_Generator_Cost = instance.Sceneario_Generator_Total_Cost.get_values() 
    NPC_Scenario = instance.Scenario_Net_Present_Cost.get_values() 
    
    columns = ['VOLL', 'Scenario Generator Cost', 'NPC Scenario']
    scenarios= range(1,instance.Scenarios.extract_values()[None]+1)
    Scenario_Costs = pd.DataFrame(columns=columns, index=scenarios)
    
    
    for j in scenarios:
        Scenario_Costs['VOLL'][j]= VOLL[j] 
        Scenario_Costs['Scenario Generator Cost'][j]= Scenario_Generator_Cost[j]
        Scenario_Costs['NPC Scenario'][j]= NPC_Scenario[j]
    Scenario_Costs.to_excel('Results/Scenario Cost.xls')    
    
    return Size_variables

def Load_results1_Dispatch(instance):
    '''
    This function loads the results that depend of the periods in to a 
    dataframe and creates a excel file with it.
    
    :param instance: The instance of the project resolution created by PYOMO.
    
    :return: A dataframe called Time_series with the values of the variables 
    that depend of the periods.    
    '''
    Names = ['Lost_Load', 'PV_Energy', 'Battery_Flow_Out','Battery_Flow_in',
             'Curtailment', 'Energy_Demand', 'SOC', 'Gen Int', 'Gen energy',
             'Total Cost Generator']
    Number_Periods = int(instance.Periods.extract_values()[None])
    Time_Series = pd.DataFrame(columns= Names, index=range(1,Number_Periods+1))            
             
    Lost_Load = instance.Lost_Load.get_values()
    PV_Energy = instance.Total_Energy_PV.extract_values()
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Gen_Energy_Integer = instance.Generator_Energy_Integer.get_values()
    Total_Generator_Energy = instance.Generator_Total_Period_Energy.get_values() 
    Gen_cost = instance.Period_Total_Cost_Generator.get_values()             
    
    
    for i in range(1,Number_Periods+1):
        Time_Series['Lost_Load'][i] = Lost_Load[i]
        Time_Series['PV_Energy'][i] = PV_Energy[i]
        Time_Series['Battery_Flow_Out'][i] = Battery_Flow_Out[i]
        Time_Series['Battery_Flow_in'][i] = Battery_Flow_in[i]
        Time_Series['Curtailment'][i] = Curtailment[i]
        Time_Series['Energy_Demand'][i] = Energy_Demand[i]
        Time_Series['SOC'][i] = SOC[i]
        Time_Series['Gen Int'][i] = Gen_Energy_Integer[i]
        Time_Series['Gen energy'][i] = Total_Generator_Energy[i]
        Time_Series['Total Cost Generator'][i] = Gen_cost[i] 

  
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
    
    Time_Series.index = columns
       
    Time_Series.to_excel('Results/Time_Series.xls') # Creating an excel file with the values of the variables that are in function of the periods
              

    Time_Series_2 = pd.DataFrame()        
    Time_Series_2['Lost Load'] =  Time_Series['Lost_Load']
    Time_Series_2['Renewable Energy'] = Time_Series['PV_Energy']
    Time_Series_2['Discharge energy from the Battery'] = Time_Series['Battery_Flow_Out']
    Time_Series_2['Charge energy to the Battery'] = Time_Series['Battery_Flow_in']
    Time_Series_2['Curtailment'] = Time_Series['Curtailment']
    Time_Series_2['Energy_Demand'] = Time_Series['Energy_Demand']
    Time_Series_2['State_Of_Charge_Battery'] = Time_Series['SOC']
    Time_Series_2['Energy Diesel'] = Time_Series['Gen energy']
    Time_Series_2['Total Cost Generator'] = Time_Series['Total Cost Generator']    

    Time_Series_2.index = columns
    
    
    
    return Time_Series_2

def Load_results2_Dispatch(instance):
    '''
    This function extracts the unidimensional variables into a  data frame 
    and creates a excel file with this data
    
    :param instance: The instance of the project resolution created by PYOMO. 
    
    :return: Data frame called Size_variables with the variables values. 
    '''
    Data = []
    # Load the variables that doesnot depend of the periods in python dyctionarys
    
    Generator_Efficiency = instance.Generator_Efficiency.extract_values()
    Generator_Min_Out_Put = instance.Generator_Min_Out_Put.extract_values()
    Low_Heating_Value = instance.Low_Heating_Value.extract_values()
    Fuel_Cost = instance.Diesel_Cost.extract_values()
    Marginal_Cost_Generator_1 = instance.Marginal_Cost_Generator_1.extract_values()
    Cost_Increase = instance.Cost_Increase.extract_values()
    Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.extract_values()
    Start_Cost_Generator = instance.Start_Cost_Generator.extract_values()
    Marginal_Cost_Generator = instance.Marginal_Cost_Generator.extract_values()
    
    Generator_Data = pd.DataFrame()
    g = None
    Name = 'Generator ' + str(1)
    Generator_Data.loc['Generator Min Out Put',Name] = Generator_Min_Out_Put[g]
    Generator_Data.loc['Generator Efficiency',Name] = Generator_Efficiency[g]
    Generator_Data.loc['Low Heating Value',Name] = Low_Heating_Value[g]
    Generator_Data.loc['Fuel Cost',Name] = Fuel_Cost[g]
    Generator_Data.loc['Marginal cost Full load',Name] = Marginal_Cost_Generator_1[g]
    Generator_Data.loc['Marginal cost Partial load',Name] = Marginal_Cost_Generator[g]
    Generator_Data.loc['Cost Increase',Name] = Cost_Increase[g]
    Generator_Data.loc['Generator Nominal Capacity',Name] = Generator_Nominal_Capacity[g]
    Generator_Data.loc['Start Cost Generator',Name] = Start_Cost_Generator[g]
    Data.append(Generator_Data) 
    Generator_Data.to_excel('Results/Generator_Data.xls')  
    
    Size_Bat = instance.Battery_Nominal_Capacity.extract_values()[None]
    O_Cost = instance.ObjectiveFuntion.expr() 
    VOLL= instance.Value_Of_Lost_Load.value
    Bat_ef_out = instance.Discharge_Battery_Efficiency.value
    Bat_ef_in = instance.Charge_Battery_Efficiency.value
    DoD = instance.Deep_of_Discharge.value
    Inv_Cost_Bat = instance.Battery_Invesment_Cost.value
    Inv_Cost_elec = instance.Battery_Electronic_Invesmente_Cost.value
    Bat_Cycles = instance.Battery_Cycles.value
    Bat_U_C = Inv_Cost_Bat - Inv_Cost_elec
    Battery_Reposition_Cost= Bat_U_C/(Bat_Cycles*2*(1-DoD))
    Number_Periods = int(instance.Periods.extract_values()[None])
    
    data3 = [Size_Bat, O_Cost, VOLL, Bat_ef_out, Bat_ef_in, DoD, 
             Inv_Cost_Bat, Inv_Cost_elec, Bat_Cycles,
            Battery_Reposition_Cost, Number_Periods] # Loading the values to a numpy array  
    Results = pd.DataFrame(data3,index = ['Size of the Battery',
                                          'Operation Cost', 'VOLL',
                                          'Battery efficiency discharge',
                                          'Battery efficiency charge',
                                          'Deep of discharge',
                                          'Battery unitary invesment cost',
                                          'Battery electronic unitary cost',
                                          'Battery max cycles',
                                          'Battery Reposition Cost',
                                          'Number of periods'])
    Results.to_excel('Results/Size.xls') # Creating an excel file with the values of the variables that does not depend of the periods
    Data.append(Results) 
    return Data

def Dispatch_Economic_Analysis(Results,Time_Series):
    Data = []
    Generator_Data = Results[0]
    Result = Results[1]
    Time_Series_Economic = pd.DataFrame()
    for t in Time_Series.index:
        name_1 = "Fuel"
        name_2 = "Discharge energy from the Battery"
        name_3 = "Charge energy to the Battery"
        name_4 = 'Battery Reposition Cost'
        name_5 = 'Battery operation Cost'
        name_6 = 'VOLL'
        Power_Bat = Time_Series[name_2][t] + Time_Series[name_3][t]
        Time_Series_Economic.loc[t,name_5] = Power_Bat*Result[0][name_4]
        LL = Time_Series['Lost Load'][t]
        Time_Series_Economic.loc[t,name_6] = LL*Result[0][name_6]
        
        if Time_Series['Energy Diesel'][t] > 0.1:
            a = Generator_Data['Generator 1']['Start Cost Generator']        
            b = Generator_Data['Generator 1']['Marginal cost Partial load']
            Time_Series_Economic.loc[t,name_1]=a + b*Time_Series['Energy Diesel'][t]
            
        else:
            Time_Series_Economic.loc[t,name_1]= 0 
            
        Operation_Cost = Time_Series_Economic.sum()
        Operation_Cost['Total Cost'] = Operation_Cost.sum() 
    Data.append(Time_Series_Economic)
    Data.append(Operation_Cost)
    
    return Data
     
    
    
def Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime):  
    '''
    This function creates a plot of the dispatch of energy of a defined number of days.
    
    :param instance: The instance of the project resolution created by PYOMO. 
    :param Time_series: The results of the optimization model that depend of the periods.
    
    
    '''
   
    if plot == 'No Average':
        Periods_Day = 24/instance.Delta_Time() # periods in a day
        foo = pd.DatetimeIndex(start=Plot_Date,periods=1,freq='1h')# Asign the start date of the graphic to a dumb variable
        for x in range(0, instance.Periods()): # Find the position form wich the plot will start in the Time_Series dataframe
            if foo == Time_Series.index[x]: 
               Start_Plot = x # asign the value of x to the position where the plot will start 
        End_Plot = Start_Plot + PlotTime*Periods_Day # Create the end of the plot position inside the time_series
        Time_Series.index=range(1,(len(Time_Series)+1))
        Plot_Data = Time_Series[Start_Plot:int(End_Plot)] # Extract the data between the start and end position from the Time_Series
        columns = pd.DatetimeIndex(start=Plot_Date, 
                                   periods=PlotTime*Periods_Day, 
                                    freq=('1H'))    
        Plot_Data.index=columns
    
        Plot_Data = Plot_Data.astype('float64')
        Plot_Data = Plot_Data
        Plot_Data['Charge energy to the Battery (kWh)'] = -Plot_Data['Charge energy to the Battery (kWh)']
        Plot_Data = round(Plot_Data,4)                   
        Fill = pd.DataFrame()
        
        r = 'Renewable Energy (kWh)'
        
        g = 'Generator Energy (kWh)'
        c = 'Curtailment (kWh)'
        c2 ='Curtailment min (kWh)'
        b = 'Discharge energy from the Battery (kWh)'
        d = 'Energy Demand (kWh)'
        ch =  'Charge energy to the Battery (kWh)'
        SOC = 'State Of Charge Battery (kWh)'
        Renewable_Source = instance. Renewable_Source.value
        

            
        for t in Plot_Data.index:
            if (Plot_Data[r][t] > 0 and  Plot_Data[g][t]>0):
                curtailment = Plot_Data[c][t]
                Fill.loc[t,r] = Plot_Data[r][t] 

                Fill.loc[t,g] = Fill[r][t] + Plot_Data[g][t]-curtailment
                Fill.loc[t,c] = Fill[r][t] + Plot_Data[g][t]
                Fill.loc[t,c2] = Fill.loc[t,g]
            elif Plot_Data[r][t] > 0:
                Fill.loc[t,r] = Plot_Data[r][t]-Plot_Data[c][t]
                Fill.loc[t,g] = Fill[r][t] + Plot_Data[g][t]
                Fill.loc[t,c] = Fill[r][t] + Plot_Data[g][t]+Plot_Data[c][t]
                Fill.loc[t,c2] = Plot_Data[r][t]-Plot_Data[c][t]
            elif Plot_Data[g][t] > 0:
                Fill.loc[t,r] = 0
                Fill.loc[t,g]= (Fill[r][t] + Plot_Data[g][t] - Plot_Data[c][t] )
                Fill.loc[t,c] = Fill[r][t] + Plot_Data[g][t]
                Fill.loc[t,c2] = (Fill[r][t] + Plot_Data[g][t] - Plot_Data[c][t] )
            else:
                Fill.loc[t,r] = 0
                Fill.loc[t,g]= 0
                if  Plot_Data[g][t] == 0:
                    Fill.loc[t,c] = Plot_Data[g][t]
                    Fill.loc[t,c2] = Plot_Data[g][t]
                else:
                    if Plot_Data[g][t] > 0:
                        Fill.loc[t,c] = Plot_Data[g][t]
                        Fill.loc[t,c2] = Plot_Data[d][t]
                    else:
                        Fill.loc[t,c] = Plot_Data[b][t]
                        Fill.loc[t,c2] = Plot_Data[d][t]
        
        if Renewable_Source > 1:
            for R in range(1,Renewable_Source+1):
                name = 'Renewable ' + str(R) + ' (kWh)'
                if R == 1:   
                    Fill[name] = Plot_Data[name]
                else:
                    name_1 = 'Renewable ' + str(R-1) + ' (kWh)'
                    Fill[name] = Fill[name_1] + Plot_Data[name]


        
        Fill[b] = (Fill[g] + Plot_Data[b])
        Fill[d] =  Plot_Data[d]
        Fill[ch] =  Plot_Data[ch]
        Fill[SOC] =  Plot_Data[SOC]
        
        Fill.index = columns
        New =  pd.DataFrame()

        
        for t in Fill.index[:-1]:
            if Fill[b][t] > Fill[g][t]:
                if  Fill[r][t+1]>Fill[d][t+1]:
                    print(t)
                    b_d = (Fill[d][t+1] - Fill[d][t])/60
                    b_g = (Fill[g][t+1] - Fill[g][t])/60
                    
                    a_d = Fill[d][t]
                    a_g = Fill[g][t]
                    
                    x = (a_g - a_d)/(b_d - b_g)
                    x = round(x,4)
                    second, minute = math.modf(x)
                    minute = int(minute)
                    second = second*60
                    second = int(second)
                    
                    if x < 60:
                        t_1 = t
                        t_1 = t_1.replace(minute=minute, second=second, microsecond=0)
                        
                        xp = [0, 60]
                        
                        New.loc[t_1,r]   = interp(x,xp,[Fill[r][t],  Fill[r][t+1]])
                        New.loc[t_1,g]   = interp(x,xp,[Fill[g][t],  Fill[g][t+1]])
                        New.loc[t_1,c]   = interp(x,xp,[Fill[c][t],  Fill[c][t+1]])
                        New.loc[t_1,c2]  = interp(x,xp,[Fill[c2][t], Fill[c2][t+1]])
                        New.loc[t_1,b]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,d]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,SOC] = interp(x,xp,[Fill[SOC][t], Fill[SOC][t+1]])
                        New.loc[t_1,ch]  = interp(x,xp,[Fill[ch][t], Fill[ch][t+1]])
                        if Renewable_Source > 1:
                            for R in range(1,Renewable_Source+1):
                                name = 'Renewable ' + str(R) + ' (kWh)'
                                New.loc[t_1,name]  = interp(x,xp,[Fill[name][t], Fill[name][t+1]])



                                     
                    
        for t in Fill.index[:-1]:
            if (Fill[b][t] == Fill[d][t]) and (Fill[g][t+1] > Plot_Data[d][t+1]):
                if  Fill[b][t] > Fill[g][t]:
                    print(t)
                    b_d = (Fill[d][t+1] - Fill[d][t])/60
                    b_g = (Fill[g][t+1] - Fill[g][t])/60
                    
                    a_d = Fill[d][t]
                    a_g = Fill[g][t]
                    
                    x = (a_g - a_d)/(b_d - b_g)
                    x = round(x,4)
                    second, minute = math.modf(x)
                    minute = int(minute)
                    second = second*60
                    second = int(second)
                    
                    if x < 60:
                        t_1 = t
                        t_1 = t_1.replace(minute=minute, second=second, microsecond=0)
                        
                        xp = [0, 60]
                        
                        New.loc[t_1,r]   = interp(x,xp,[Fill[r][t],  Fill[r][t+1]])
                        New.loc[t_1,g]   = interp(x,xp,[Fill[g][t],  Fill[g][t+1]])
                        New.loc[t_1,c]   = interp(x,xp,[Fill[c][t],  Fill[c][t+1]])
                        New.loc[t_1,c2]  = interp(x,xp,[Fill[c2][t], Fill[c2][t+1]])
                        New.loc[t_1,b]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,d]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,SOC] = interp(x,xp,[Fill[SOC][t], Fill[SOC][t+1]])
                        New.loc[t_1,ch]  = interp(x,xp,[Fill[ch][t], Fill[ch][t+1]])
                        if Renewable_Source > 1:
                            for R in range(1,Renewable_Source+1):
                                name = 'Renewable ' + str(R) + ' (kWh)'
                                New.loc[t_1,name]  = interp(x,xp,[Fill[name][t], Fill[name][t+1]])

        
        # fix the battery if in one step before the energy production is more than demand
        # and in time t the battery is used            
        for t in Fill.index[1:-1]:
            if Fill[g][t] > Plot_Data[d][t] and Fill[b][t+1] == Plot_Data[d][t+1] and Plot_Data[b][t+1] > 0:
                    print(t)
                    b_d = (Fill[d][t+1] - Fill[d][t])/60
                    b_g = (Fill[g][t+1] - Fill[g][t])/60
                    
                    a_d = Fill[d][t]
                    a_g = Fill[g][t]
                    
                    x = (a_g - a_d)/(b_d - b_g)
                    x = round(x,4)
                    second, minute = math.modf(x)
                    minute = int(minute)
                    second = second*60
                    second = int(second)
                    
                    if x < 60:
                        t_1 = t
                        t_1 = t_1.replace(minute=minute, second=second, microsecond=0)
                        
                        xp = [0, 60]
                        
                        New.loc[t_1,r]   = interp(x,xp,[Fill[r][t],  Fill[r][t+1]])
                        New.loc[t_1,g]   = interp(x,xp,[Fill[g][t],  Fill[g][t+1]])
                        New.loc[t_1,c]   = interp(x,xp,[Fill[c][t],  Fill[c][t+1]])
                        New.loc[t_1,c2]  = interp(x,xp,[Fill[c2][t], Fill[c2][t+1]])
                        New.loc[t_1,b]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,d]   = interp(x,xp,[Fill[d][t], Fill[d][t+1]])
                        New.loc[t_1,SOC] = interp(x,xp,[Fill[SOC][t], Fill[SOC][t+1]])
                        New.loc[t_1,ch]  = interp(x,xp,[Fill[ch][t], Fill[ch][t+1]])
                        if Renewable_Source > 1:
                            for R in range(1,Renewable_Source+1):
                                name = 'Renewable ' + str(R) + ' (kWh)'
                                New.loc[t_1,name]  = interp(x,xp,[Fill[name][t], Fill[name][t+1]])

        Fill = Fill.append(New)
        Fill.sort_index(inplace=True)

        size = [20,10]  
        plt.figure(figsize=size)
#        Fill[b] = ( Fill[g] + Plot_Data[b])
        # Renewable energy
        
        # For 1 energy Source            
        if Renewable_Source == 1:
                c_PV = 'yellow'   
                Alpha_r = 0.4 
                ax1 =Fill[r].plot(style='y-', linewidth=1)
                ax1.fill_between(Fill.index, 0,Fill[r].values,   
                                 alpha=Alpha_r, color = c_PV)        
        else:
            c_r = ['aqua', 'chocolate', 'lightcoral', 'lightgreen']
            for R in range (1,  Renewable_Source+1):
                name = 'Renewable '  + str(R) + ' (kWh)'
                print(name)
                if R == 1:
                    c_PV_1 = 'yellow'   
                    Alpha_r = 0.4 
                    ax1 = Fill[name].plot(style='y-', linewidth=0)
                    ax1.fill_between(Fill.index, 0, Fill[name].values,   
                                 alpha=Alpha_r, color = c_PV_1)
                elif R == Renewable_Source:
                        name_1 = 'Renewable '  + str(R-1) + ' (kWh)'
                        c_r_1 = c_r[R-1]    
                        Alpha_r = 0.4                            
                        ax1 = Fill[r].plot(style='c-', linewidth=0)
                        ax1.fill_between(Fill.index, Fill[name_1].values, Fill[r].values, 
                                     alpha=Alpha_r, color =c_r_1)
                else:
                        name_1 = 'Renewable '  + str(R-1) + ' (kWh)'
                        c_r_1 = c_r[R-1]    
                        Alpha_r = 0.4                            
                        ax1 = Fill[r].plot(style='c-', linewidth=0)
                        ax1.fill_between(Fill.index, Fill[name_1].values, Fill[name].values, 
                                     alpha=Alpha_r, color =c_r_1)
        
        
        # Genset Plot
        c_d = 'm'
        Alpha_g = 0.3 
        hatch_g = '\\'
        ax2 = Fill[g].plot(style='c', linewidth=0)
        ax2.fill_between(Fill.index, Fill[r].values, Fill[g].values,
                         alpha=Alpha_g, color=c_d, edgecolor=c_d , hatch =hatch_g)
        # Battery discharge
        alpha_bat = 0.3
        hatch_b ='x'
        C_Bat = 'green'
        ax3 = Fill[b].plot(style='b', linewidth=0)
        ax3.fill_between(Fill.index, Fill[g].values, Fill[b].values,   
                         alpha=alpha_bat, color =C_Bat,edgecolor=C_Bat, hatch =hatch_b)
        # Demand
        ax4 = Plot_Data[d].plot(style='k', linewidth=2, marker= 'o')
        # Battery Charge        
        ax5= Fill[ch].plot(style='m', linewidth=0.5) # Plot the line of the energy flowing into the battery
        ax5.fill_between(Fill.index, 0, 
                         Fill[ch].values
                         , alpha=alpha_bat, color=C_Bat,edgecolor= C_Bat, hatch ='x') 
        # State of charge of battery
        ax6= Fill[SOC].plot(style='k--', 
                secondary_y=True, linewidth=2, alpha=0.7 ) 
        # Curtailment
        alpha_cu = 0.3
        hatch_cu = '+'
        C_Cur = 'blue'
        ax7 = Fill[c].plot(style='b-', linewidth=0)
        ax7.fill_between(Fill.index, Fill[c2].values , Fill[c].values, 
                         alpha=alpha_cu, color=C_Cur,edgecolor= C_Cur, 
                         hatch =hatch_cu,
                         where=Fill[c].values>Fill[d]) 
        # Lost load
        
        if instance.Lost_Load_Probability > 0:
        
            alpha_LL = 0.3
            hatch_LL = '-'
            C_LL = 'crimson'
            ax4.fill_between(Fill.index, Fill[b].values, Fill[d].values, 
                             alpha=alpha_LL, color=C_LL,edgecolor=  C_LL, 
                             hatch =hatch_LL) 
        
        
        # Define name  and units of the axis
        ax1.set_ylabel('Power (kkW)',size=30)
        ax1.set_xlabel('Time',size=30)
        ax6.set_ylabel('Battery State of charge (kWh)',size=30)
        ax1.set_xlim(Fill.index[0], Fill.index[len(Fill)-1])
        tick_size = 15    
        #mpl.rcParams['xtick.labelsize'] = tick_size    
        ax1.tick_params(axis='x', which='major', labelsize = tick_size,pad=8 ) 
        ax1.tick_params(axis='y', which='major', labelsize = tick_size )
 #       ax1.tick_params(axis='x', which='major', labelsize = tick_size) 
        ax6.tick_params(axis='y', which='major', labelsize = tick_size )       
        # Define the legends of the plot
        From_Renewable =[]
        for R in range(1, Renewable_Source + 1):
            if R == 1:
                From_Renewable.append(mpatches.Patch(color='yellow',alpha=Alpha_r, label='Renewable 1'))  
            else:
                name = 'From Renewable ' +str(R) 
                c_r_1 = c_r[R-1] 
                foo = mpatches.Patch(color=c_r_1,alpha=Alpha_r, label=name)
                From_Renewable.append(foo)
            
        From_Generator = mpatches.Patch(color=c_d,alpha=Alpha_g,
                                        label='From Generator',hatch =hatch_g)
        Battery = mpatches.Patch(color=C_Bat ,alpha=alpha_bat, 
                                 label='Battery Energy Flow',hatch =hatch_b)
        Curtailment = mpatches.Patch(color=C_Cur ,alpha=alpha_cu, 
                                 label='Curtailment',hatch =hatch_cu)

        Energy_Demand = mlines.Line2D([], [], color='black',label='Energy Demand')
        State_Of_Charge_Battery = mlines.Line2D([], [], color='black',
                                                label='State Of Charge Battery',
                                                linestyle='--',alpha=0.7)
        
        
        Legends = []
        
        Legends.append(From_Generator)
        for R in range(Renewable_Source):
            Legends.append(From_Renewable[R])
        Legends.append(Battery)
        Legends.append(Curtailment)
        Legends.append(Energy_Demand)
        Legends.append(State_Of_Charge_Battery)
        
        if instance.Lost_Load_Probability > 0:
            Lost_Load = mpatches.Patch(color=C_LL,alpha=alpha_LL,
                                        label='Lost Laod',hatch =hatch_LL)
            Legends.append(Lost_Load)
        
        plt.legend(handles=Legends,
                            bbox_to_anchor=(1.025, -0.15),fontsize = 20,
                            frameon=False,  ncol=4)
        plt.savefig('Results/Energy_Dispatch.png', bbox_inches='tight')    
        plt.show()    
        
    else:   
        start = Time_Series.index[0]
        end = Time_Series.index[instance.Periods()-1]
        Time_Series = Time_Series.astype('float64')
        Plot_Data_2 = Time_Series[start:end].groupby([Time_Series[start:end].index.hour]).mean()
        Plot_Data_2 = Plot_Data_2/1000
        Plot_Data_2['Charge energy to the Battery'] = -Plot_Data_2['Charge energy to the Battery']
        Plot_Data = Plot_Data_2
        Vec = Plot_Data['Renewable Energy'] + Plot_Data['Energy Diesel']
        Vec2 = (Plot_Data['Renewable Energy'] + Plot_Data['Energy Diesel'] + 
                Plot_Data['Discharge energy from the Battery'])
        
        
        ax1= Vec.plot(style='b-', linewidth=0.5) # Plot the line of the diesel energy plus the PV energy
        ax1.fill_between(Plot_Data.index, Plot_Data['Energy Diesel'].values, Vec.values,   
                         alpha=0.3, color = 'b')
        ax2= Plot_Data['Energy Diesel'].plot(style='r', linewidth=0.5)
        ax2.fill_between(Plot_Data.index, 0, Plot_Data['Energy Diesel'].values, 
                         alpha=0.2, color='r') # Fill the area of the energy produce by the diesel generator
        ax3 = Plot_Data['Energy_Demand'].plot(style='k', linewidth=2)
        ax3.fill_between(Plot_Data.index, Vec.values , 
                         Plot_Data['Energy_Demand'].values,
                         alpha=0.3, color='g', 
                         where= Plot_Data['Energy_Demand']>= Vec,interpolate=True)
        ax5= Plot_Data['Charge energy to the Battery'].plot(style='m', linewidth=0.5) # Plot the line of the energy flowing into the battery
        ax5.fill_between(Plot_Data.index, 0, 
                         Plot_Data['Charge energy to the Battery'].values
                         , alpha=0.3, color='m') # Fill the area of the energy flowing into the battery
        ax6= Plot_Data['State_Of_Charge_Battery'].plot(style='k--', secondary_y=True, linewidth=2, alpha=0.7 ) # Plot the line of the State of charge of the battery
        
        # Define name  and units of the axis
    




        # Define name  and units of the axis
        ax1.set_ylabel('Power (kkW)')
        ax1.set_xlabel('hours')
        ax6.set_ylabel('Battery State of charge (kWh)')
                
        # Define the legends of the plot
        From_PV = mpatches.Patch(color='blue',alpha=0.3, label='From PV')
        From_Generator = mpatches.Patch(color='red',alpha=0.3, label='From Generator')
        From_Battery = mpatches.Patch(color='green',alpha=0.5, label='From Battery')
        To_Battery = mpatches.Patch(color='magenta',alpha=0.5, label='To Battery')
        Lost_Load = mpatches.Patch(color='yellow', alpha= 0.3, label= 'Lost Load')
        Energy_Demand = mlines.Line2D([], [], color='black',label='Energy Demand')
        State_Of_Charge_Battery = mlines.Line2D([], [], color='black',
                                                label='State Of Charge Battery',
                                                linestyle='--',alpha=0.7)
        plt.legend(handles=[From_Generator, From_PV, From_Battery, 
                            To_Battery, Lost_Load, Energy_Demand, 
                            State_Of_Charge_Battery], bbox_to_anchor=(1.83, 1))
        plt.savefig('Results/Energy_Dispatch.png', bbox_inches='tight')    
        plt.show()    
    
def Energy_Mix(instance,Scenarios,Scenario_Probability):
    
    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Energy_Totals = Scenarios.sum()
    
    PV_Energy = 0 
    Generator_Energy = 0
    Curtailment = 0
    Battery_Out = 0
    Demand = 0
    Lost_Load = 0
    Energy_Mix = pd.DataFrame()
    
    for s in range(1, Number_Scenarios+1):   
       
        index_1 = 'Renewable Energy ' + str(s) + ' (kWh)' 
        index_2 = 'Gen energy ' + str(s) + ' (kWh)'
        index_3 = 'Scenario ' + str(s)
        index_4 = 'Curtailment ' + str(s) + ' (kWh)'
        index_5 = 'Battery Flow Out ' + str(s) + ' (kWh)'
        index_6 = 'Energy Demand ' + str(s) + ' (kWh)'
        index_7 = 'Lost Load '+str(s) + ' (kWh)'
        
        PV = Energy_Totals[index_1]
        Ge = Energy_Totals[index_2]
        We = Scenario_Probability[index_3]
        Cu = Energy_Totals[index_4]
        B_O = Energy_Totals[index_5]        
        De = Energy_Totals[index_6] 
        
        PV_Energy += PV*We
        Generator_Energy += Ge*We  
        Curtailment += Cu*We
        Battery_Out += B_O*We
        Demand += De*We
        
        
        Energy_Mix.loc['PV Penetration',index_3] = PV/(PV+Ge)
        Energy_Mix.loc['Curtailment Percentage',index_3] = Cu/(PV+Ge)
        Energy_Mix.loc['Battery Usage',index_3] = B_O/De
        
        if instance.Lost_Load_Probability > 0:
            LL = Energy_Totals[index_7]*We 
            Lost_Load += LL*We
            Energy_Mix.loc['Lost Load', index_3] = LL/De
        
    Renewable_Real_Penetration = PV_Energy/(PV_Energy+Generator_Energy)     
    Curtailment_Percentage = Curtailment/(PV_Energy+Generator_Energy)
    Battery_Usage = Battery_Out/Demand
        
    print(str(round(Renewable_Real_Penetration*100, 1)) + ' % Renewable Penetration')
    print(str(round(Curtailment_Percentage*100,1)) + ' % of energy curtail')
    print(str(round(Battery_Usage*100,1)) + ' % Battery usage')
    
    if instance.Lost_Load_Probability > 0:
        foo = []
        for s in range(1, Number_Scenarios+1):
            name = 'Scenario ' + str(s)
            foo.append(name)
        
        Lost_Load_Real = sum(Energy_Mix.loc['Lost Load', name] for name in foo)
        print(str(round(Lost_Load_Real*100,1)) + ' % Lost load in the system')
    
    return Energy_Mix    
    
    
def Print_Results(instance, Generator_Data, Data_Renewable, Battery_Data ,Results, 
                  formulation):
        Number_Renewable_Source = int(instance.Renewable_Source.extract_values()[None])
        Number_Generator = int(instance.Generator_Type.extract_values()[None])
        
        for i in range(1, Number_Renewable_Source + 1):
            index_1 = 'Source ' + str(i)
            index_2 = 'Total Nominal Capacity (kW)'
        
            Renewable_Rate = float(Data_Renewable[index_1][index_2])
            Renewable_Rate = round(Renewable_Rate, 1)
            print('Renewable ' + str(i) + ' nominal capacity is ' 
                  + str(Renewable_Rate) +' kW')    
        if formulation == 'LP':    
            for i in range(1, Number_Generator + 1):
                index_1 = 'Generator ' + str(i)
                index_2 = 'Generator Nominal Capacity (kW)'
                
                Generator_Rate = float(Generator_Data[index_1][index_2])
                Generator_Rate = round(Generator_Rate, 1)
                
                print('Generator ' + str(i) + ' nominal capacity is ' 
                      + str(Generator_Rate) +' kW')  
        if formulation == 'MILP': 
             Number_Generator = int(instance.Generator_Type.extract_values()[None])
             for i in range(1, Number_Generator + 1):
                index_1 = 'Generator ' + str(i)
                index_2 = 'Generator Nominal Capacity (kW)'
                index_3 = 'Number of Generators'
                Generator_Rate = float(Generator_Data[index_1][index_2])
                Generator_Rate = round(Generator_Rate, 1)
                Generator_Rate = Generator_Rate*Generator_Data[index_1][index_3]
                print('Generator ' + str(i) + ' nominal capacity is ' 
                  + str(Generator_Rate) +' kW')                
        
        index_2 = 'Nominal Capacity (kWh)'    
        Battery_Rate = Battery_Data['Battery'][index_2]
        Battery_Rate = round(Battery_Rate, 1)
        
        print('Battery nominal capacity is ' 
                  + str(Battery_Rate) +' kWh') 
        
        index_2 = 'NPC (USD)'    
        NPC = Results['Data'][index_2]/1000
        NPC = round(NPC, 0)
        
        print('NPC is ' + str(NPC) +' Thousand USD') 
    
    
        index_2 = 'LCOE (USD/kWh)'    
        LCOE = Results['Data'][index_2]
        LCOE = round(LCOE, 3)
            
        print('The LCOE is ' + str(LCOE) + ' USD/kWh')  


    
def Print_Results_Dispatch(instance, Economic_Results):
    Operation_Costs = Economic_Results[1]
    Fuel_Cost = round(Operation_Costs['Fuel'],2) 
    
    print('Diesel cost is ' + str(Fuel_Cost) + ' USD')
    
    LL_Cost = round(Operation_Costs['VOLL'],2) 
    
    print('Lost load cost is ' + str(LL_Cost) + ' USD')
    
    Battery_Cost = round(Operation_Costs['Battery operation Cost'],2) 
    
    print('Battery operation cost is ' + str(Battery_Cost) + ' USD')
    
    Total_Cost = round(Operation_Costs['Total Cost'],2) 
    
    print('Total operation cost is ' + str(Total_Cost) + ' USD')
    
    
def Energy_Mix_Dispatch(instance,Time_Series):
    
    Energy_Totals = Time_Series.sum()
    
    PV_Energy = Energy_Totals['Renewable Energy']
    Generator_Energy = Energy_Totals['Energy Diesel']
    Curtailment = Energy_Totals['Curtailment']
    Demand = Energy_Totals['Energy_Demand']
    Battery_Out = Energy_Totals['Discharge energy from the Battery']

    Renewable_Real_Penetration = PV_Energy/(PV_Energy+Generator_Energy)
    Renewable_Real_Penetration = round(Renewable_Real_Penetration,4)
    Curtailment_Percentage = Curtailment/(PV_Energy+Generator_Energy)
    Curtailment_Percentage = round(Curtailment_Percentage,4)
    Battery_Usage = Battery_Out/Demand
    Battery_Usage = round(Battery_Usage,4)
    
    print(str(Renewable_Real_Penetration*100) + ' % Renewable Penetration')
    print(str(Curtailment_Percentage*100) + ' % of energy curtail')
    print(str(Battery_Usage*100) + ' % Battery usage')


def energy_check(instance):
    
    Energy_Demand = pd.read_excel('Results/Results.xls',sheet_name= 'Time Series'
                                  ,index_col=0,Header=None)

    Data_Scenarios = pd.read_excel('Results/Results.xls',sheet_name= 'Project Data'
                                  ,index_col=0,Header=None)
    Number_Scenarios = int(Data_Scenarios[0]['Number of Scenarios'])
    Number_Periods = int(Data_Scenarios[0]['Periods of the year'])
    
    Data_Bat = pd.read_excel('Results/Results.xls',sheet_name= 'Battery Data'
                                  ,index_col=0,Header=None)
    
    Bat = Data_Bat['Battery']['Nominal Capacity (kWh)']
    Bat_Initial = Data_Bat['Battery']['Initial State of Charge']
    eff_out = Data_Bat['Battery']['Discharge efficiency']
    eff_in = Data_Bat['Battery']['Charge efficiency']

    
    Lost_Load_Probability = Data_Scenarios[0]['Lost Load Probability (%)'] 
    
    Generator_Number = int(Data_Scenarios[0]['Types of generators'])
    Renewablwe_Source_Number = int(Data_Scenarios[0]['Types of renewable sources'])
    
    
    for j in range(1, Number_Scenarios+1):   
        re = 'Renewable Energy '+str(j) + ' (kWh)'
        bat_out ='Battery Flow Out '+str(j) + ' (kWh)' 
        bat_in = 'Battery Flow in '+str(j) + ' (kWh)'
        cu ='Curtailment '+str(j) + ' (kWh)'
        e = 'Energy Demand '+str(j) + ' (kWh)'
        soc = 'SOC '+str(j) + ' (kWh)'
        ge ='Gen energy '+str(j) + ' (kWh)'
        if Lost_Load_Probability  > 0: 
            ll= 'Lost Load '+str(j) + ' (kWh)'
        
        generation = Energy_Demand[re] + Energy_Demand[bat_out] + Energy_Demand[ge] - Energy_Demand[bat_in] - Energy_Demand[cu]         
    
        if Lost_Load_Probability  > 0: 
            ll= 'Lost Load '+str(j) + ' (kWh)'
            generation += Energy_Demand[ll]
            
        comparation = round(Energy_Demand[e],3) == round(generation,3)
        comparation = pd.Series(comparation).all()
        
        comparation_2 = round(Energy_Demand[e].sum(),3) == round(generation.sum(),3)
    
        print(comparation)
        print(comparation_2)
        
        SoC = pd.DataFrame(index=range(Number_Periods),columns=[0])
        for i in range(Number_Periods):
            
            if i == 0:
                SoC.loc[i,0] = Bat*Bat_Initial  - Energy_Demand[bat_out][i]/eff_out + Energy_Demand[bat_in][i]*eff_in
            else:
               SoC.loc[i,0] = SoC.loc[i-1,0]  - Energy_Demand[bat_out][i]/eff_out + Energy_Demand[bat_in][i]*eff_in
        
        copy = Energy_Demand[soc]
        copy.index = SoC.index
        copy = round(copy,3)
        SoC = SoC.astype(float).round(3)
        
        comparation_3 = copy == SoC[0]
        comparation_3 = pd.Series(comparation_3).all()
        
        comparation_4 = copy.sum() == SoC[0].sum()
        
        print(comparation_3)
        print(comparation_4)
    
        # geset test
        print('Gen test')
        gen_ene = pd.read_excel('Results/Results.xls',sheet_name= 'Generator Time Series'
                                  ,index_col=0,Header=None)
       
        Generator_Total_Energy = pd.DataFrame(index=Energy_Demand.index)
        Generator_Total_Energy[0] = 0
        for g in range(1, Generator_Number+1):
        
            name = 'Energy Generator ' + str(j) + ' ' + str(g) + ' (kWh)'
            Generator_Total_Energy[0] +=   gen_ene[name]
                
        comparation_5 = Energy_Demand[ge] == Generator_Total_Energy[0]
        comparation_5 = pd.Series(comparation_5).all()
        comparation_6 = round(Energy_Demand[ge].sum(),3) == round(Generator_Total_Energy[0].sum(),3)
        print(comparation_5)
        print(comparation_6)
    
    
        re_ene = pd.read_excel('Results/Results.xls',sheet_name= 'Renewable Energy Time Series'
                                  ,index_col=0,Header=None)
        Data_Renewable = pd.read_excel('Results/Results.xls',sheet_name= 'Data Renewable'
                                  ,index_col=0,Header=None)
        
        
        Renewable_Total_Energy = pd.DataFrame(index=Energy_Demand.index)
        Renewable_Total_Energy[0] = 0
        
        for r in range(1, Renewablwe_Source_Number+1):

            name = 'Renewable ' + str(j) + ' ' + str(r) + ' (kWh)'
            Renewable_Total_Energy[0] +=   re_ene[name]
                
        comparation_7 = round(Energy_Demand[re],3) == round(Renewable_Total_Energy[0],3)
        comparation_7 = pd.Series(comparation_7).all()
        comparation_8 = round(Energy_Demand[re].sum(),3) == round(Renewable_Total_Energy[0].sum(),3)
        print(comparation_7)
        print(comparation_8)    
    
    
        Renewable_Energy_1 = instance.Renewable_Energy_Production.extract_values()
    
    Renewable_Energy = pd.DataFrame()
    
    for s in range(1, Number_Scenarios + 1):
        for r in range(1, Renewablwe_Source_Number + 1):
            column = 'Renewable ' + str(s) + ' ' + str(r) + ' (kWh)'
            
            Energy = []
            for t in range(1, Number_Periods + 1):
                Source = 'Source ' + str(r)
                Energy.append(Renewable_Energy_1[s,r,t]*Data_Renewable.loc['Inverter Efficiency', Source]
                            *Data_Renewable.loc['Units', Source])
        
            Renewable_Energy[column] = Energy
            Renewable_Energy.index = re_ene.index
            comparation_9 = round(re_ene[column]*1000,1) == round(Renewable_Energy[column]*1000,1)
            comparation_9 = pd.Series(comparation_9).all()
            comparation_10 = round(re_ene[column].sum(),4) ==  round(Renewable_Energy[column].sum(),4)
            print(comparation_9)
            print(comparation_10)    
            