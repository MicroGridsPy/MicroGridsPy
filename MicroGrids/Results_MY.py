"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from pandas import ExcelWriter

def Load_Results(instance):
    
    from win32com.client import Dispatch
    import os

    import warnings
    warnings.simplefilter(action='ignore', category=FutureWarning)
    
    cwd = os.getcwd()
    excel = Dispatch('Excel.Application')

    Number_Scenarios = int(instance.Scenarios.extract_values()[None])
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Years = int(instance.Years.extract_values()[None])
    Number_Upgrades = int(instance.Upgrades_Number.extract_values()[None])
    Number_Renewable_Sources = int(instance.Renewable_Sources.extract_values()[None])
    Number_Generators = int(instance.Generator_Types.extract_values()[None])

    upgrades = [i for i in range(1, Number_Upgrades+1)]
    
    upgrade_years_list = [1 for i in range(1, Number_Upgrades+1)]
    s_dur = instance.Step_Duration.value
    for i in range(1, Number_Upgrades): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur
    yu_tuples_list = [[] for i in range(1, Number_Years+1)]
    for y in range(1, Number_Years+1):  
        if len(upgrade_years_list) == 1:
            yu_tuples_list[y-1] = (y,1)
        else:
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, upgrades[i])       
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, len(upgrades)) 

    Lost_Load = instance.Lost_Load.get_values()
    Renewable_Energy_1 = instance.Total_Renewable_Energy.get_values()
    Battery_Flow_Out = instance.Energy_Battery_Flow_Out.get_values()
    Battery_Flow_in = instance.Energy_Battery_Flow_In.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    SOC = instance.State_Of_Charge_Battery.get_values()
    Generator_Energy = instance.Total_Generator_Energy.get_values()

    Energy_Demand = instance.Energy_Demand.extract_values()    
    Scenario_Weight = instance.Scenario_Weight.extract_values()
    Discount_Rate = instance.Discount_Rate.value
    LHV = (instance.Lower_Heating_Value.extract_values())
    Gen_Eff = (instance.Generator_Efficiency.extract_values())

    print('Number of scenarios = '+str(Number_Scenarios))
    print('Number of years = '+str(Number_Years)+'\n')


#################################### TIME SERIES ####################################

    columns = []
    for i in range(1, Number_Scenarios+1):
        columns.append('Scenario_'+str(i))
     
    Renewable_Energy = {}
    for s in range(1, Number_Scenarios + 1):
        for y in range(1, Number_Years + 1):
            for t in range(1, Number_Periods+1):                
                foo = []
                for r in range(1,Number_Renewable_Sources+1):
                    foo.append((s,y,r,t))           
                Renewable_Energy[s,y,t] = sum(Renewable_Energy_1[i] for i in foo)
                    
    Total_Generator_Energy = {}
    Total_Fuel = {}
    
    for s in range(1, Number_Scenarios + 1):
        for y in range(1, Number_Years + 1):
            for t in range(1, Number_Periods + 1):
                foo = []
                for g in range(1,Number_Generators+1):
                    foo.append((s,y,g,t))
                Total_Generator_Energy[s,y,t] = sum(Generator_Energy[i] for i in foo)
                Total_Fuel[s,y,t] = sum((Generator_Energy[i]/(LHV[i[2]]*Gen_Eff[i[2]])) for i in foo) 
                
    Scenarios_Periods = [[] for i in range(Number_Scenarios)]
    Scenarios_Ren =[[] for i in range(Number_Renewable_Sources)]
        
    for s in range(0,Number_Scenarios):
        for y in range(0, Number_Years):
            for t in range(0, Number_Periods):
                Scenarios_Periods[s].append((s+1,y+1,t+1))
    
    for r in range(0,Number_Renewable_Sources ):
        for t in range(0, Number_Periods):
            Scenarios_Ren[r].append((r+1,t+1))
       
    Scenarios = pd.DataFrame()
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
            
        for k in range(0,Number_Renewable_Sources):
            Information_2 = [[] for i in range(0,Number_Renewable_Sources)]
            for y in range(0, Number_Years):
                for t in range(0,Number_Periods):
                    for r in range(0,Number_Renewable_Sources):
                        Information_2[r].append(Renewable_Energy_1[(foo+1,y+1,r+1,t+1)]) 
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
       index.append('Fuel '+str(j)+' [Lt]')
       index.append('Total Renewable Energy '+str(j))
       for r in range(1,Number_Renewable_Sources+1):
           index.append('Renewable Energy: s='+str(j)+' r='+str(r))
    Scenarios.index = index
    Scenarios_2 = Scenarios.transpose() 
    
    # Creation of an index starting in the 'model.StartDate' value with a frequency step equal to 'model.Delta_Time'
    if instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1.0) : # if the step is in hours and minutes
        foo = str(instance.Delta_Time()) # trasform the number into a string
        hour = foo[0] # Extract the first character
        minutes = str(int(float(foo[1:3])*60)) # Extrac the last two character
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods()*instance.Years, 
                                   freq=(hour + 'h'+ minutes + 'min')) # Creation of an index with a start date and a frequency
    elif instance.Delta_Time() >= 1 and type(instance.Delta_Time()) == type(1): # if the step is in hours
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods()*instance.Years, 
                                   freq=(str(instance.Delta_Time()) + 'h')) # Creation of an index with a start date and a frequency
    else: # if the step is in minutes
        columns = pd.DatetimeIndex(start=instance.StartDate(), 
                                   periods=instance.Periods()*instance.Years, 
                                   freq=(str(int(instance.Delta_Time()*60)) + 'min'))# Creation of an index with a start date and a frequency
    
    Scenarios.columns = columns
    Scenarios = Scenarios.transpose()
    
    Scenarios_yearly = pd.DataFrame()
    t_0 = 0
    Time_Series = ExcelWriter('Results/Multi_Year/Time_Series.xlsx')
    
    for y in range(1,Number_Years+1):
        Scenarios_yearly = Scenarios.iloc[[t for t in range(t_0, y*Number_Periods)]]
        Scenarios_yearly.to_excel(Time_Series, sheet_name = 'Year ' + str(y))
        t_0 = y * Number_Periods
    
    Time_Series.save()
    print('Results: Time_Series.xlsx exported')
    
    wb = excel.Workbooks.Open(cwd+"\\Results\\Multi_Year\\Time_Series.xlsx")
    for y in range(1,Number_Years+1):
        excel.Worksheets(y).Activate()
        excel.ActiveSheet.Columns.AutoFit()
    wb.Save()
    wb.Close()

        
#################################### RENEWABLE SOURCE DATA ####################################
    
    Renewable_Nominal_Capacity = instance.Renewable_Nominal_Capacity.extract_values()
    Inverter_Efficiency_Renewable = instance.Renewable_Inverter_Efficiency.extract_values()
    Renewable_Investment_Cost = instance.Renewable_Investment_Cost.extract_values()
    OyM_Renewable = instance.Renewable_Operation_Maintenance_Cost.extract_values()
    Renewable_Units = instance.Renewable_Units.get_values()
    Renewable_Investment_Cost_Reduction = instance.Renewable_Inv_Cost_Reduction.extract_values()
    
    Data_Renewable = pd.DataFrame()
    for r in range(1, Number_Renewable_Sources + 1):
        Name = 'Source ' + str(r)
        Data_Renewable.loc['Unitary Nominal Capacity [W]', Name] = Renewable_Nominal_Capacity[r]
        Data_Renewable.loc['Inverter Efficiency', Name] = Inverter_Efficiency_Renewable[r]
        Data_Renewable.loc['Investment Cost [USD/W]', Name] = Renewable_Investment_Cost[r]
        Data_Renewable.loc['O&M Cost [%]', Name] = OyM_Renewable[r]

        for u in range(1, Number_Upgrades +1):
            Data_Renewable.loc['Units at upgrade ' +str(u), Name] = Renewable_Units[u,r]
        
        for u in range(1, Number_Upgrades +1):
            Data_Renewable.loc['Total Nominal Capacity at upgrade ' +str(u), Name] = Data_Renewable.loc['Unitary Nominal Capacity [W]', Name]*Data_Renewable.loc['Units at upgrade ' +str(u), Name]            
        
        for u in range(1, Number_Upgrades +1):
            if u == 1:
                Data_Renewable.loc['Investment at upgrade '+ str(u), Name] = Renewable_Units[u,r]*Renewable_Nominal_Capacity[r]*Renewable_Investment_Cost[r]        
            else:
                Data_Renewable.loc['Investment at upgrade '+ str(u), Name] = (Renewable_Units[u,r] - Renewable_Units[u-1,r])*Renewable_Nominal_Capacity[r]*Renewable_Investment_Cost[r]*Renewable_Investment_Cost_Reduction[r]

        for u in range(1, Number_Upgrades +1):
            Data_Renewable.loc['Yearly O&M Cost at upgrade ' +str(u), Name] = Renewable_Units[u,r]*Renewable_Nominal_Capacity[r]*Renewable_Investment_Cost[r]*OyM_Renewable[r]

    Data_Renewable.to_excel('Results/Multi_Year/Renewable_Sources_Data.xlsx')    
    print('Results: Renewable_Sources_Data.xlsx exported')

    wb = excel.Workbooks.Open(cwd+"\\Results\\Multi_Year\\Renewable_Sources_Data.xlsx")
    excel.Worksheets(1).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    wb.Save()
    wb.Close()


#################################### GENERATOR DATA ####################################

    Generator_Efficiency = instance.Generator_Efficiency.extract_values()
    Lower_Heating_Value = instance.Lower_Heating_Value.extract_values()
#    Fuel_Cost = instance.Fuel_Cost.extract_values()
    Generator_Investment_Cost = instance.Generator_Investment_Cost.extract_values()
    Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.get_values()
    Generator_Operation_Maintenance_Cost = instance.Generator_Operation_Maintenance_Cost.extract_values()
    Marginal_Cost_Gen = instance.Generator_Marginal_Cost.extract_values()
    FCT = instance.Total_Fuel_Cost.extract_values()
    
    Gen_data = ExcelWriter('Results/Multi_Year/Generator_Data.xlsx')
    
    Generator_Data = pd.DataFrame()
    for g in range(1, Number_Generators + 1):
        Name = 'Generator ' + str(g)
        Generator_Data.loc['Efficiency',Name] = Generator_Efficiency[g]
        Generator_Data.loc['Lower Heating Value [Wh/Lt]',Name] = Lower_Heating_Value[g]
#        Generator_Data.loc['Fuel Cost [USD/Lt]',Name] = Fuel_Cost[g]
        Generator_Data.loc['Investment Cost [USD/W]',Name] = Generator_Investment_Cost[g]
        Generator_Data.loc['O&M Cost [%]', Name] = Generator_Operation_Maintenance_Cost[g]
#        Generator_Data.loc['Marginal Cost [USD/Wh]', Name] = Marginal_Cost_Gen[g]
        
        for u in range(1, Number_Upgrades +1):
            Generator_Data.loc['Nominal Capacity at upgrade '+str(u),Name] = Generator_Nominal_Capacity[u,g]
                
        for u in range(1, Number_Upgrades +1):
            if u==1:
                Generator_Data.loc['Investment at upgrade ' + str(u), Name] = Generator_Investment_Cost[g]*Generator_Nominal_Capacity[u,g]
            else:
                Generator_Data.loc['Investment at upgrade ' + str(u), Name] = Generator_Investment_Cost[g]*(Generator_Nominal_Capacity[u,g] - Generator_Nominal_Capacity[u-1,g])
        
        for u in range(1, Number_Upgrades +1):        
            Generator_Data.loc['Yearly O&M Cost at upgrade ' + str(u), Name] = Generator_Investment_Cost[g]*Generator_Nominal_Capacity[u,g]*Generator_Data.loc['O&M Cost [%]', Name]
               
        Generator_Data.loc['Total actualized Fuel Cost', Name] = sum(FCT[(s,g)]*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
                
    Generator_Data.to_excel(Gen_data, sheet_name = 'Generator Data')      

    Generator_Data_2 = pd.DataFrame()
        
    for s in range(1, Number_Scenarios+1):
        for y in range(1, Number_Years+1):
            Yearly_Fuel_Cost = 0
            for g in range(1, Number_Generators+1):
                Yearly_Fuel_Cost += sum(Generator_Energy[s,y,g,t]*Marginal_Cost_Gen[s,y,g] for t in range(1, Number_Periods+1))
            
            Generator_Data_2.loc['Total Fuel Cost at y = '+str(y),'Scenario '+str(s)] = Yearly_Fuel_Cost
    
    Generator_Data_2.to_excel(Gen_data, sheet_name = 'Yearly Fuel Costs')    
    Gen_data.save()
    print('Results: Generator_Data.xlsx exported')

    wb = excel.Workbooks.Open(cwd+"\\Results\\Multi_Year\\Generator_Data.xlsx")
    excel.Worksheets(1).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    excel.Worksheets(2).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    wb.Save()
    wb.Close()
    
    
#################################### BATTERY DATA ####################################

    Battery_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()
    PriceBattery= instance.Battery_Investment_Cost.value
    Unitary_Battery_Reposition_Cost = instance.Unitary_Battery_Reposition_Cost.value
    OM_Bat = instance.Battery_Operation_Maintenance_Cost.value
    BRC = instance.Battery_Reposition_Cost.get_values()

    Bat_data = ExcelWriter('Results/Multi_Year/Battery_Data.xlsx')
    
    Battery_Data = pd.DataFrame()
    Battery_Data.loc['Unitary Investment Cost [USD/Wh]',0] = PriceBattery
    Battery_Data.loc['O&M Cost [%]',0] = OM_Bat
    Battery_Data.loc['Unitary Battery Reposition Cost [USD/Wh]',0] = Unitary_Battery_Reposition_Cost
    
    for u in range(1, Number_Upgrades +1):
        Battery_Data.loc['Nominal Capacity at upgrade '+str(u),0] = Battery_Nominal_Capacity[u]   
    
    for u in range(1, Number_Upgrades +1):
        if u == 1:
            Battery_Data.loc['Investment at upgrade '+str(u),0] = Battery_Nominal_Capacity[u]*PriceBattery
        else:
            Battery_Data.loc['Investment at upgrade '+str(u),0] = (Battery_Nominal_Capacity[u] - Battery_Nominal_Capacity[u-1])*PriceBattery

    for u in range(1, Number_Upgrades +1):
        Battery_Data.loc['Yearly O&M Cost at upgrade '+str(u),0] = Battery_Nominal_Capacity[u]*PriceBattery*OM_Bat
        
    Battery_Data.loc['Total actualized Battery Reposition Cost', 0] = sum(BRC[(s)]*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
    
    Battery_Data.to_excel(Bat_data, sheet_name = 'Battery_Data') # Creating an excel file with the values of the variables that does not depend of the periods
    
    Battery_Data_2 = pd.DataFrame()
            
    for s in range(1, Number_Scenarios+1):
        for y in range(1, Number_Years+1):
            Yearly_BRC = 0
               
            Battery_cost_in = sum(Battery_Flow_in[s,y,t]*Unitary_Battery_Reposition_Cost for t in range(1, Number_Periods+1))
            Battery_cost_out = sum(Battery_Flow_Out[s,y,t]*Unitary_Battery_Reposition_Cost for t in range(1, Number_Periods+1))           
            Yearly_BRC += Battery_cost_in + Battery_cost_out
            Battery_Data_2.loc['Battery Reposition Cost at y = '+str(y),'Scenario '+str(s)] = Yearly_BRC

    Battery_Data_2.to_excel(Bat_data, sheet_name = 'Yearly BRC')    
    Bat_data.save()
        
    print('Results: Battery_Data.xlsx exported')    
    
    wb = excel.Workbooks.Open(cwd+"\\Results\\Multi_Year\\Battery_Data.xlsx")
    excel.Worksheets(1).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    excel.Worksheets(2).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    wb.Save()
    wb.Close()
    

#################################### PROJECT INFORMATION ####################################

    NPC = instance.ObjectiveFuntion.expr()
    
    TotVarCost = instance.Total_Variable_Cost.value
    TotInvCost = instance.Investment_Cost.value
    VOLL = instance.Value_Of_Lost_Load.value
    Renewable_Units = instance.Renewable_Units.get_values()
    
    PRJ_Info = ExcelWriter('Results/Multi_Year/Project_Information.xlsx')

    Project_Info_1 = pd.DataFrame()

    Project_Info_1.loc['NPC', 0] = NPC
    
    Project_Info_1.loc['Total actualized Operation cost', 0] = TotVarCost
        

    Demand = pd.DataFrame()
    NP_Demand = 0
    for s in range(1, Number_Scenarios + 1):
        a = 'Energy_Demand ' + str(s)
        k = 0
        for y in range(1, Number_Years + 1):
            Demand.loc[a,'Total Demand y=' + str(y)] = sum(Scenarios_2[a][i] for i in range(k, k + Number_Periods))
            Demand.loc[a,'Present Demand y=' + str(y)] = Demand.loc[a,'Total Demand y=' + str(y)]/((1+Discount_Rate)**y) 
            k = k + Number_Periods  
        Present_Demand = sum(Demand.loc[a, 'Present Demand y=' + str(y)] for y in range(1,Number_Years+1))   
        Weighted_Present_Demand = Scenario_Weight[s]*Present_Demand   
        NP_Demand += Weighted_Present_Demand
   
    LCOE = NPC/NP_Demand*1000
    Project_Info_1.loc['LCOE', 0] = LCOE

    Project_Info_1.to_excel(PRJ_Info, sheet_name = 'Project Info')


    Project_Info_2 = pd.DataFrame()
    
    for u in range(1, Number_Upgrades+1):
        
        Project_Info_2.loc['Battery Nominal Capacity [kWh]', 'Upgrade '+str(u)] = Battery_Nominal_Capacity[u]/1000
        Project_Info_2.loc['Generator Nominal Capacity [kW]', 'Upgrade '+str(u)] = sum(Generator_Nominal_Capacity[u,g] for g in range(1, Number_Generators +1))/1000
        for r in range(1, Number_Renewable_Sources+1):
            Project_Info_2.loc['Renewable '+str(r)+' Nominal Capacity [kW]', 'Upgrade '+str(u)] = Renewable_Nominal_Capacity[r]*Renewable_Units[u,r]/1000
    
        Project_Info_2.loc['Battery Investment [USD]', 'Upgrade '+str(1)] = Battery_Nominal_Capacity[1]*PriceBattery
        if u != 1:
            Project_Info_2.loc['Battery Investment [USD]', 'Upgrade '+str(u)] = (Battery_Nominal_Capacity[u]-Battery_Nominal_Capacity[u-1])*PriceBattery   
        
        Project_Info_2.loc['Generator Investment [USD]', 'Upgrade '+str(1)] = sum(Generator_Nominal_Capacity[1,g]*Generator_Investment_Cost[g] for g in range(1, Number_Generators+1))
        if u != 1:
            Project_Info_2.loc['Generator Investment [USD]', 'Upgrade '+str(u)] = sum((Generator_Nominal_Capacity[u,g]-Generator_Nominal_Capacity[u-1,g])*Generator_Investment_Cost[g] for g in range(1, Number_Generators+1))
        
        for r in range(1, Number_Renewable_Sources+1):
            Project_Info_2.loc['Renewable '+str(r)+' Investment [USD]', 'Upgrade '+str(1)] = Renewable_Nominal_Capacity[r]*Renewable_Units[1,r]*Renewable_Investment_Cost[r]
            if u != 1:
                Project_Info_2.loc['Renewable '+str(r)+' Investment [USD]', 'Upgrade '+str(u)] = (Renewable_Units[u,r]-Renewable_Units[u-1,r])*Renewable_Nominal_Capacity[r]*Renewable_Investment_Cost[r] *Renewable_Investment_Cost_Reduction[r]
        
        Project_Info_2.loc['Total Investment [USD]', 'Upgrade '+str(u)] = Project_Info_2['Upgrade '+str(u)]['Battery Investment [USD]':].sum()
        
    Project_Info_2.to_excel(PRJ_Info, sheet_name = 'Upgrades Info')


    Project_Info_3 = pd.DataFrame()
    for (y,u) in yu_tuples_list:
        Project_Info_3.loc['Year '+str(y), 'Battery O&M Cost'] = Battery_Nominal_Capacity[u]*PriceBattery*OM_Bat
        Project_Info_3.loc['Year '+str(y), 'Generator O&M Cost'] = sum(Generator_Nominal_Capacity[u,g]*Generator_Investment_Cost[g]*Generator_Operation_Maintenance_Cost[g] for g in range(1, Number_Generators+1))
        Project_Info_3.loc['Year '+str(y), 'Renewable O&M Cost'] = sum(Renewable_Units[u,r]*Renewable_Nominal_Capacity[r]*Renewable_Investment_Cost[r]*OyM_Renewable[r] for r in range(1, Number_Renewable_Sources+1))
        Project_Info_3.loc['Year '+str(y), 'Total O&M Cost'] =  Project_Info_3.loc['Year '+str(y), 'Battery O&M Cost'] + Project_Info_3.loc['Year '+str(y), 'Generator O&M Cost'] + Project_Info_3.loc['Year '+str(y), 'Renewable O&M Cost']
        
        Project_Info_3.loc['Year '+str(y), 'Fuel Cost'] = sum(sum(sum(Generator_Energy[s,y,g,t]*Marginal_Cost_Gen[s,y,g]*Scenario_Weight[s] for t in range(1, Number_Periods+1)) for g in range(1, Number_Generators+1))for s in range(1, Number_Scenarios+1))
        Project_Info_3.loc['Year '+str(y), 'Battery Reposition Cost'] = sum(sum((Battery_Flow_in[s,y,t]+Battery_Flow_Out[s,y,t])*Unitary_Battery_Reposition_Cost*Scenario_Weight[s] for t in range(1, Number_Periods+1)) for s in range(1, Number_Scenarios+1))
        Project_Info_3.loc['Year '+str(y), 'Lost Load Cost'] = sum(sum(Lost_Load[s,y,t]*VOLL*Scenario_Weight[s] for t in range(1, Number_Periods+1)) for s in range(1, Number_Scenarios+1))
    
    Project_Info_3.to_excel(PRJ_Info, sheet_name = 'Yearly Costs Info')


    Project_Info_4 = pd.DataFrame()
    k = 0
    
    for y in range(1, Number_Years+1):
        
        Tot_Ren_En = sum(Scenarios_2['Total Renewable Energy '+str(s)][k:k+Number_Periods].sum()*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
        Tot_Gen_En = sum(Scenarios_2['Gen energy '+str(s)][k:k+Number_Periods].sum()*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
        Renewable_Real_Penetration = Tot_Ren_En / (Tot_Ren_En + Tot_Gen_En)

        Curtailment = sum(Scenarios_2['Curtailment '+str(s)][k:k+Number_Periods].sum()*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
        
        Batt_Flow_Out = sum(Scenarios_2['Battery_Flow_Out '+str(s)][k:k+Number_Periods].sum()*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
        Demand = sum(Scenarios_2['Energy_Demand '+str(s)][k:k+Number_Periods].sum()*Scenario_Weight[s] for s in range(1, Number_Scenarios+1))
        
        Project_Info_4.loc['Year '+str(y), 'Renewable Real Penetration'] = Renewable_Real_Penetration
        Project_Info_4.loc['Year '+str(y), 'Curtailment %'] = Curtailment / (Tot_Ren_En + Tot_Gen_En)
        Project_Info_4.loc['Year '+str(y), 'Battery Usage'] = Batt_Flow_Out / Demand
        
        k += Number_Periods

    Project_Info_4.to_excel(PRJ_Info, sheet_name = 'Yearly Energy Averages')

    PRJ_Info.save()
    print('Results: Project_Information.xlsx exported')    
    
    wb = excel.Workbooks.Open(cwd+"\\Results\\Multi_Year\\Project_Information.xlsx")
    excel.Worksheets(1).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    excel.Worksheets(2).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    excel.Worksheets(3).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    excel.Worksheets(4).Activate()
    excel.ActiveSheet.Columns.AutoFit()
    wb.Save()
    wb.Close()
    
    
    Data = []
    Data.append(NPC)
    Data.append(Battery_Data)
    Data.append(Scenarios)
    Data.append(Generator_Data)
    Data.append(Scenario_Weight)
    Data.append(LCOE)
    Data.append(Data_Renewable)
    Data.append(TotVarCost)
    Data.append(TotInvCost)
    
    print('Results: Loadresults1 executed properly')
    return Data



def Integer_Time_Series(instance,Scenarios, S):  #S is the scenario that we want to plot
    
    if S == 0:
        S = instance.PlotScenario.value
    
    Number_Periods = int(instance.Periods.extract_values()[None])
    Number_Renewable_Sources = int(instance.Renewable_Sources.extract_values()[None])
    Number_Years = int(instance.Years.extract_values()[None])

    Time_Series = pd.DataFrame(index=range(0,Number_Periods*Number_Years))
    Time_Series.index = Scenarios.index
    
    Time_Series['Lost Load'] = Scenarios['Lost_Load '+str(S)]
    Time_Series['Total Renewable Energy'] = Scenarios['Total Renewable Energy '+str(S)]
    for r in range(1,Number_Renewable_Sources+1):
        Time_Series['Renewable Energy '+str(r)] = Scenarios['Renewable Energy: s='+str(S)+' r='+str(r)]
    Time_Series['Discharge energy from the Battery'] = Scenarios['Battery_Flow_Out '+str(S)] 
    Time_Series['Charge energy to the Battery'] = Scenarios['Battery_Flow_in '+str(S)]
    Time_Series['Curtailment'] = Scenarios['Curtailment '+str(S)]
    Time_Series['Energy_Demand'] = Scenarios['Energy_Demand '+str(S)]
    Time_Series['State_Of_Charge_Battery'] = Scenarios['SOC '+str(S)] 
    Time_Series['Energy Diesel'] = Scenarios['Gen energy '+str(S)]

    return Time_Series


def Plot_Energy_Total(instance, Time_Series, plot, Plot_Date, PlotTime):  
    '''
    This function creates a plot of the dispatch of energy of a defined number of days.
    
    :param instance: The instance of the project resolution created by PYOMO. 
    :param Time_series: The results of the optimization model that depend of the periods.
    
    
    '''
    Number_Renewable_Sources = int(instance.Renewable_Sources.extract_values()[None])
    
    if plot == 'No Average':
        Periods_Day = 24/instance.Delta_Time() # periods in a day
        foo = pd.DatetimeIndex(start=Plot_Date,periods=1,freq='1h')# Assign the start date of the graphic to a dumb variable
        
        for x in range(0, instance.Periods()*instance.Years()): # Find the position from which the plot will start in the Time_Series dataframe
            if foo == Time_Series.index[x]: 
               Start_Plot = x # assign the value of x to the position where the plot will start 
               break
        
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
                for r in range(1,Number_Renewable_Sources+1):
                    dummy.loc[t,r] = Plot_Data['Renewable Energy '+str(r)][t]
                    Fill.loc[t,'Ren ' +str(r)] = pd.Series.to_frame(dummy.sum(1))[0][t]
                Fill.loc[t,g] = Fill['Ren ' +str(r)][t] + Plot_Data[g][t]
                Fill.loc[t,c] = Fill.loc[t,g]
                Fill.loc[t,c2] = Fill.loc[t,g]
            elif Plot_Data[r_tot][t] > 0:
                Fill.loc[t,'Ren 1'] = Plot_Data['Renewable Energy 1'][t]-Plot_Data[c][t]*Plot_Data['Renewable Energy 1'][t]/Plot_Data[r_tot][t]
                for r in range(2,Number_Renewable_Sources+1):
                    dummy.loc[t,r] = Plot_Data['Renewable Energy '+str(r)][t]
                    Fill.loc[t,'Ren ' +str(r)] = Fill.loc[t,'Ren '+str(r-1)]+dummy.loc[t,r]-Plot_Data[c][t]*Plot_Data['Renewable Energy '+str(r)][t]/Plot_Data[r_tot][t]
                Fill.loc[t,g] = Fill['Ren ' +str(r)][t]
                Fill.loc[t,c] = Fill.loc[t,g] + Plot_Data[c][t]
                Fill.loc[t,c2] = Fill.loc[t,g]
            elif Plot_Data[g][t] > 0:
                for r in range(1,Number_Renewable_Sources+1):
                    Fill.loc[t,'Ren ' +str(r)] = 0                
                Fill.loc[t,g] = Plot_Data[g][t]
                Fill.loc[t,c] = Fill.loc[t,g]
                Fill.loc[t,c2] = Fill.loc[t,g]
            else:
                for r in range(1,Number_Renewable_Sources+1):
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

        Fill[b] = Fill[g] + Plot_Data[b] #+ Plot_Data[b_ch]
        
        # Renewable energy plot (first renewable outside for loop, if >1 renewables the others are plotted in the loop)
        color_list = ['yellow',(255/255,141/255,14/255),'c','0.6','y']
        Alpha_r = 0.4
        ax0 = Fill['Ren 1'].plot(style='y-', linewidth=0)
        ax0.fill_between(Plot_Data.index, 0, Fill['Ren 1'].values,   
                             alpha=Alpha_r, color = color_list[0])
        
        if Number_Renewable_Sources > 1:
            for r in range(2,Number_Renewable_Sources+1):
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
        for r in range(1,Number_Renewable_Sources+1):
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
        leg = Legend(ax0, From_Renewables[:], ['From Renewable '+str(i+1) for i in range(Number_Renewable_Sources)],
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
        
        if Number_Renewable_Sources > 1:
            dummy = Vec  
            for r in range(2,Number_Renewable_Sources+1):
                dummy.loc[:,'Ren '+str(r)] = Plot_Data['Renewable Energy '+str(r)]
                Vec.loc[:,'Ren '+str(r)] = pd.Series.to_frame(dummy.sum(1))[0]                 
        
        Vec.loc[:,'Tot'] = Plot_Data['Total Renewable Energy'] + Plot_Data['Energy Diesel']
        
        # Renewable energy plot (first renewable outside for loop, if >1 renewables the others are plotted in the loop)
        color_list = ['yellow',(255/255,141/255,14/255),'c','0.6','y']
        Alpha_r = 0.4
        ax0 = Vec['Ren 1'].plot(style='y-', linewidth=0)
        ax0.fill_between(Plot_Data.index, Plot_Data['Energy Diesel'].values, Vec['Ren 1'].values,   
                             alpha=Alpha_r, color = color_list[0])
        
        if Number_Renewable_Sources > 1:
            for r in range(2,Number_Renewable_Sources+1):
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
        for r in range(1,Number_Renewable_Sources+1):
            c_ren = color_list[r-1]
            From_Renewables.append(mpatches.Patch(color=c_ren,alpha=Alpha_r, label='From Renewable '+str(r)))

        from matplotlib.legend import Legend
        leg = Legend(ax0, From_Renewables[:], ['From Renewable '+str(i+1) for i in range(Number_Renewable_Sources)],
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
    
    Scenario_Weight = [i for i in instance.Scenario_Weight.extract_values()]
    
    for j in range(1, Number_Scenarios+1):   
       
        index_1 = 'Total Renewable Energy ' + str(j)    
        index_2 = 'Gen energy ' + str(j)
        index_3 = 'Scenario ' + str(j)
        index_4 = 'Curtailment ' + str(j)
        index_5 = 'Battery_Flow_Out ' + str(j)
        index_6 = 'Energy_Demand ' + str(j)
        
        Ren = Energy_Totals[index_1]
        Ge = Energy_Totals[index_2]
        Cu = Energy_Totals[index_4]
        B_O = Energy_Totals[index_5]        
        De = Energy_Totals[index_6] 
        
        Renewable_Energy += Ren*Scenario_Weight[j-1]
        Generator_Energy += Ge*Scenario_Weight[j-1]  
        Curtailment += Cu*Scenario_Weight[j-1]
        Battery_Out += B_O*Scenario_Weight[j-1]
        Demand += De*Scenario_Weight[j-1]
        
        
        Energy_Mix.loc['Renewable Penetration',index_3] = Ren/(Ren+Ge)
        Energy_Mix.loc['Curtailment Percentage',index_3] = Cu/(Ren+Ge)
        Energy_Mix.loc['Battery Usage',index_3] = B_O/De
        
    Renewable_Real_Penetration = Renewable_Energy/(Renewable_Energy+Generator_Energy)
    Renewable_Real_Penetration = round(Renewable_Real_Penetration,4)
    Curtailment_Percentage = Curtailment/(Renewable_Energy+Generator_Energy)
    Curtailment_Percentage = round(Curtailment_Percentage,4)
    Battery_Usage = Battery_Out/Demand
    Battery_Usage = round(Battery_Usage,4)
    print('\nRenewable Penetration = '+str(round(Renewable_Real_Penetration*100,2))+' %')
    print('Energy curtailed = '+str(round(Curtailment_Percentage*100,2))+' %')
    print('Battery usage = '+str(round(Battery_Usage*100,2)) + ' %')
    
    return Energy_Mix    
    
    
def Print_Results(LCOE, NPC, TotVarCost, TotInvCost):
    
    print('\nProject NPC = '+str(round(NPC,2))+' USD')
    print('Project Total actualized Operation Cost = '+str(round(TotVarCost,2))+' USD')
    print('Project Total Investment Cost = '+str(round(TotInvCost,2))+' USD')
    print('Project LCOE = '+str(round(LCOE,4))+' USD/kWh')
    