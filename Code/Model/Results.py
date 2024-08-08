import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from pandas import ExcelWriter
import re
import os
import warnings; warnings.simplefilter(action='ignore', category=FutureWarning)

#%% Results summary
def ResultsSummary(instance, Optimization_Goal, TimeSeries):

    from Results import EnergySystemCost, EnergySystemSize, YearlyCosts, YearlyEnergyParams, YearlyEnergyParamsSC, EnergySystemLandUse
    
    print('Results: exporting economic results...')
    EnergySystemCost                              = EnergySystemCost(instance, Optimization_Goal)
    YearlyCost                                    = YearlyCosts(instance) 
    print('         exporting technical results...')
    EnergySystemSize                              = EnergySystemSize(instance)
    YearlyEnergyParams, RenewablePenetration      = YearlyEnergyParams(instance, TimeSeries)
    YearlyEnergyParamsSC, RenewablePenetrationSC  = YearlyEnergyParamsSC(instance, TimeSeries)
    if instance.Land_Use.value == 1: EnergySystemLandUse = EnergySystemLandUse(instance)
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    results_directory = os.path.join(current_directory, '..', 'Results/Results_Summary.xlsx')
    
    Excel = ExcelWriter(results_directory)

    EnergySystemSize.to_excel(Excel, sheet_name='Size')
    if instance.Land_Use.value == 1: EnergySystemLandUse.to_excel(Excel, sheet_name='Land Use')
    EnergySystemCost.to_excel(Excel, sheet_name='Cost')
    YearlyCost.to_excel(Excel, sheet_name='Yearly cash flows')
    YearlyEnergyParams.to_excel(Excel, sheet_name='Yearly energy parameters')
    YearlyEnergyParamsSC.to_excel(Excel, sheet_name='Yearly energy parameters SC')

    Excel.close()

    Results = {
        'Costs': EnergySystemCost,
        'Size': EnergySystemSize,
        'Land Use': EnergySystemLandUse if instance.Land_Use.value == 1 else None,
        'Yearly cash flows': YearlyCost,
        'Yearly energy parameters': YearlyEnergyParams,
        'Renewables Penetration': RenewablePenetration,
        'Yearly energy parameters SC': YearlyEnergyParamsSC,
        'Renewables Penetration SC': RenewablePenetrationSC,
    }
    
    return Results

#%% TimeSeries generation
def TimeSeries(instance):

    print('\nResults: exporting time-series...')
    "Importing parameters"
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    Scenario_Weight = instance.Scenario_Weight.extract_values()
    Discount_Rate   = instance.Discount_Rate.value
    RES_Names       = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names      = instance.Fuel_Names.extract_values()

    StartDate       = pd.to_datetime(instance.StartDate())    
    start_year      = StartDate.year
    start_month     = StartDate.month
    start_day       = StartDate.day
    start_hour      = StartDate.hour
    start_minute    = StartDate.minute
    start_second    = StartDate.second

    "Generating years-steps tuples list"
    steps = [i for i in range(1, ST+1)]
    
    years_steps_list = [1 for i in range(1, ST+1)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        years_steps_list[i] = years_steps_list[i-1] + s_dur
    ys_tuples_list = [[] for i in range(1, Y+1)]
    for y in range(1, Y+1):  
        if len(years_steps_list) == 1:
            ys_tuples_list[y-1] = (y,1)
        else:
            for i in range(len(years_steps_list)-1):
                if y >= years_steps_list[i] and y < years_steps_list[i+1]:
                    ys_tuples_list[y-1] = (y, steps[i])       
                elif y >= years_steps_list[-1]:
                    ys_tuples_list[y-1] = (y, len(steps)) 
                    
    "Importing energy flows timeseries"  
    RES_Energy_Production       = instance.RES_Energy_Production.get_values()
    BESS_Outflow                = instance.Battery_Outflow.get_values()
    BESS_Inflow                 = instance.Battery_Inflow.get_values()
    if instance.MILP_Formulation.value == 1 and instance.Generator_Partial_Load.value == 1:
       Generator_Energy_Total      = instance.Generator_Energy_Total.get_values()
       Generator_Energy_Partial    = instance.Generator_Energy_Partial.get_values()
       Generator_Partial           = instance.Generator_Partial.get_values()
       Generator_Full              = instance.Generator_Full.get_values()
    elif instance.MILP_Formulation.value == 1 and instance.Generator_Partial_Load.value == 0:
       Generator_Energy_Total = instance.Generator_Energy_Total.get_values()
    else :
       Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
    Curtailment                 = instance.Energy_Curtailment.get_values()
    Lost_Load                   = instance.Lost_Load.get_values()
    Electric_Demand             = instance.Energy_Demand.extract_values() 
    Electricity_From_Grid       = instance.Energy_From_Grid.get_values() 
    Electricity_To_Grid         = instance.Energy_To_Grid.get_values()   
    
    BESS_SOC                    = instance.Battery_SOC.get_values()
    LHV                         = instance.Fuel_LHV.extract_values()
    Generator_Efficiency        = instance.Generator_Efficiency.extract_values()
    FUEL_emission               = instance.FUEL_emission.get_values()
    
    "Creating TimeSeries dictionary and exporting excel"
    TimeSeries = {}
        
    for s in range(1,S+1):
        TimeSeries[s] = {}
        current_directory = os.path.dirname(os.path.abspath(__file__))
        results_directory = os.path.join(current_directory, '..', 'Results')
        results_2_path = os.path.join(results_directory, 'Time_Series_SC_%d.xlsx' % (s))
        with pd.ExcelWriter(results_2_path) as writer:
         for y in range(1,Y+1):
            
            scenario_header  = []
            flow_header      = []
            component_header = []
            unit_header      = []
            
            TimeSeries[s][y] = pd.DataFrame()
            DEM = pd.DataFrame([Electric_Demand[(s,y,t)] for t in range(1,P+1)])
            TimeSeries[s][y] = pd.concat([TimeSeries[s][y], DEM], axis=1)
            scenario_header  += ['Scenario ' + str(s)]
            flow_header      += ['Electric Demand']
            component_header += ['']
            unit_header      += ['Wh']
            
            for r in range(1,R+1):
                RES = pd.DataFrame([RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)])
                TimeSeries[s][y] = pd.concat([TimeSeries[s][y], RES], axis=1)
                scenario_header  += ['Scenario ' + str(s)]
                flow_header      += ['RES Production']
                component_header += [RES_Names[r]]
                unit_header      += ['Wh']
            
            # Total Energy Production of the generator
            if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
                for g in range(1,G+1):
                    if instance.MILP_Formulation.value:
                       GEN = pd.DataFrame([Generator_Energy_Total[(s,y,g,t)] for t in range(1,P+1)])
                    else:
                       GEN = pd.DataFrame([Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1)])
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], GEN], axis=1)
                    scenario_header  += ['Scenario ' + str(s)]
                    flow_header      += ['Generator Production']
                    component_header += [Generator_Names[g]]
                    unit_header      += ['Wh']
                    
                " Partial Load Effect"
                # Generator Partial Load Production
                if instance.MILP_Formulation.value == 1 and instance.Generator_Partial_Load.value == 1:
                   for g in range(1,G+1):
                       GEN_p = pd.DataFrame([Generator_Energy_Partial[(s,y,g,t)] for t in range(1,P+1)])
                       TimeSeries[s][y] = pd.concat([TimeSeries[s][y], GEN_p], axis=1)
                       scenario_header  += ['Scenario ' + str(s)]
                       flow_header      += ['Generator Partial Load Production']
                       component_header += [Generator_Names[g]]
                       unit_header      += ['Wh']
                
                # Units of Generators in Partial Load (1 o 0)       
                if instance.MILP_Formulation.value == 1 and instance.Generator_Partial_Load.value == 1:
                   for g in range(1,G+1):
                       GEN_pu = pd.DataFrame([Generator_Partial[(s,y,g,t)] for t in range(1,P+1)])
                       TimeSeries[s][y] = pd.concat([TimeSeries[s][y], GEN_pu], axis=1)
                       scenario_header  += ['Scenario ' + str(s)]
                       flow_header      += ['Units of Generators in Partial Load']
                       component_header += [Generator_Names[g]]
                       unit_header      += ['Wh']
                
                # Units of Generators in Full Load
                if instance.MILP_Formulation.value == 1 and instance.Generator_Partial_Load.value == 1:
                   for g in range(1,G+1):
                       GEN_fu = pd.DataFrame([Generator_Full[(s,y,g,t)] for t in range(1,P+1)])
                       TimeSeries[s][y] = pd.concat([TimeSeries[s][y], GEN_fu], axis=1)
                       scenario_header  += ['Scenario ' + str(s)]
                       flow_header      += ['Units of Generators in Full Load']
                       component_header += [Generator_Names[g]]
                       unit_header      += ['Wh']
                
            BESS_OUT         = pd.DataFrame([BESS_Outflow[(s,y,t)] for t in range(1,P+1)])
            BESS_IN          = pd.DataFrame([BESS_Inflow[(s,y,t)] for t in range(1,P+1)])
            LL               = pd.DataFrame([Lost_Load[(s,y,t)] for t in range(1,P+1)])
            CURTAIL          = pd.DataFrame([Curtailment[(s,y,t)] for t in range(1,P+1)])
            EL_FROM_GRID     = pd.DataFrame([Electricity_From_Grid[(s,y,t)] for t in range(1,P+1)]) 
            EL_TO_GRID       = pd.DataFrame([Electricity_To_Grid[(s,y,t)] for t in range(1,P+1)])    
            if instance.Model_Components.value == 0 or instance.Model_Components.value == 1: 
                if instance.Grid_Connection.value == 1:
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], BESS_OUT, BESS_IN, LL, CURTAIL, EL_FROM_GRID,EL_TO_GRID], axis=1) 
                    scenario_header  += ['Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s)]
                    flow_header      += ['Battery Discharge','Battery Charge','Lost Load','Curtailment','Electricity from grid','Electricity to grid'] 
                    component_header += ['','','','','','']
                    unit_header      += ['Wh','Wh','Wh','Wh','Wh','Wh']
                if instance.Grid_Connection.value == 0:
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], BESS_OUT, BESS_IN, LL, CURTAIL], axis=1) 
                    scenario_header  += ['Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s)]
                    flow_header      += ['Battery Discharge','Battery Charge','Lost Load','Curtailment'] 
                    component_header += ['','','','']
                    unit_header      += ['Wh','Wh','Wh','Wh']
                
                
                SOC              = pd.DataFrame([BESS_SOC[(s,y,t)] for t in range(1,P+1)])
                TimeSeries[s][y] = pd.concat([TimeSeries[s][y], SOC], axis=1)
                scenario_header  += ['Scenario ' + str(s)]
                flow_header      += ['Battery SOC']
                component_header += ['']
                unit_header      += ['Wh']

            if instance.Model_Components.value == 2: 
                if instance.Grid_Connection.value == 1:
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], LL, CURTAIL, EL_FROM_GRID, EL_TO_GRID], axis=1) 
                    scenario_header  += ['Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s),'Scenario ' + str(s)]
                    flow_header      += ['Lost Load','Curtailment','Electricity from grid','Electricity to grid'] 
                    component_header += ['','','','']
                    unit_header      += ['Wh','Wh','Wh','Wh']
                if instance.Grid_Connection.value == 0:
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], LL, CURTAIL], axis=1) 
                    scenario_header  += ['Scenario ' + str(s),'Scenario ' + str(s)]
                    flow_header      += ['Lost Load','Curtailment'] 
                    component_header += ['','']
                    unit_header      += ['Wh','Wh']
                
            if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
                for g in range(1,G+1):
                    if instance.MILP_Formulation.value:
                       FUEL = pd.DataFrame([Generator_Energy_Total[(s,y,g,t)]/LHV[g]/Generator_Efficiency[g] for t in range(1,P+1)])
                    else:
                       FUEL = pd.DataFrame([Generator_Energy_Production[(s,y,g,t)]/LHV[g]/Generator_Efficiency[g] for t in range(1,P+1)]) 
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], FUEL], axis=1)
                    scenario_header  += ['Scenario ' + str(s)]
                    flow_header      += ['Fuel Consumption']
                    component_header += [Fuel_Names[g]]
                    unit_header      += ['Lt']
                    
                for g in range(1,G+1):
                    CO2              = pd.DataFrame([FUEL_emission[(s,y,g,t)] for t in range(1,P+1)])
                    TimeSeries[s][y] = pd.concat([TimeSeries[s][y], CO2], axis=1)
                    scenario_header  += ['Scenario ' + str(s)]
                    flow_header      += ['CO2 emission']
                    component_header += [Fuel_Names[g]]
                    unit_header      += ['kg']            
                
            TimeSeries[s][y].columns = pd.MultiIndex.from_arrays([scenario_header, flow_header, component_header, unit_header], names=['','Flow','Component','Unit'])
            date                     = str(start_year+y-1)+'/'+str(start_month)+'/'+str(start_day)+' '+str(start_hour)+':'+str(start_minute)
            TimeSeries[s][y].index   = pd.date_range(start=date, periods=P, freq='H')
            
            round(TimeSeries[s][y],1).to_excel(writer, sheet_name='Year ' + str(y))
            
    return TimeSeries

    
#%% Economic output        
def EnergySystemCost(instance, Optimization_Goal):
    
    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names = instance.Fuel_Names.extract_values()
    Discount_Rate = instance.Discount_Rate.value

    upgrade_years_list = [1 for i in range(ST)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur    
    yu_tuples_list = [0 for i in range(1,Y+1)]    
    if ST == 1:    
        for y in range(1,Y+1):            
            yu_tuples_list[y-1] = (y, 1)    
    else:        
        for y in range(1,Y+1):            
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, [st for st in range(ST)][i+1])                
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, ST)   
    tup_list = [[] for i in range(ST-1)]  
    for i in range(0,ST-1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]      


    #%% Investment cost
    "Total"
    Grid_Investment = (instance.Grid_Connection_Cost.value * instance.Grid_Connection.value * instance.Grid_Distance.value)/(1 + instance.Discount_Rate.value)**(instance.Year_Grid_Connection.value-1)
    Total_Investment_Cost = pd.DataFrame(['Total Investment cost', 'System', '-', 'kUSD', (instance.Investment_Cost.value + Grid_Investment)/1e3]).T.set_index([0,1,2,3])
    Total_Investment_Cost.columns = ['Total']

    if instance.MILP_Formulation.value:
     "Renewable sources"
     RES_Units_milp = instance.RES_Units_milp.get_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
     RES_capacity = instance.RES_capacity.extract_values()
     RES_Inv_Specific_Cost = instance.RES_Specific_Investment_Cost.extract_values()
     RES_Investment_Cost = pd.DataFrame()
     for r in range(1,R+1):
        r_inv = ((RES_Units_milp[1,r]*RES_Nominal_Capacity[r])-RES_capacity[r])*RES_Inv_Specific_Cost[r]
        res_inv = pd.DataFrame(['Investment cost', RES_Names[r], '-', 'kUSD', r_inv/1e3]).T.set_index([0,1,2,3]) 
        if ST == 1:
            res_inv.columns = ['Total']
        else:
            res_inv.columns = ['Step 1']
        res_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv], axis=1).fillna(0)
        for (y,st) in tup_list:
            r_inv = (RES_Units_milp[st,r]-RES_Units_milp[st-1,r])*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]/((1+Discount_Rate)**(y-1))
            res_inv = pd.DataFrame(['Investment cost', RES_Names[r], '-', 'kUSD', r_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                res_inv.columns = ['Total']
            else:
                res_inv.columns = ['Step '+str(st)]
            res_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv], axis=1).fillna(0)
     RES_Investment_Cost = RES_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
     res_inv_tot = RES_Investment_Cost.sum(1).to_frame()
     res_inv_tot.columns = ['Total']
     if ST != 1:
        RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv_tot],axis=1)
        
     "Battery Bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Units = instance.Battery_Units.get_values()
         BESS_Nominal_Capacity_milp = instance.Battery_Nominal_Capacity_milp.value
         BESS_capacity = instance.Battery_capacity.value
         BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
         BESS_Investment_Cost = pd.DataFrame()
         b_inv = ((BESS_Units[1]*BESS_Nominal_Capacity_milp)-BESS_capacity)*BESS_Inv_Specific_Cost
         bess_inv = pd.DataFrame(['Investment cost', 'Battery bank', '-', 'kUSD', b_inv/1e3]).T.set_index([0,1,2,3]) 
         if ST == 1:
            bess_inv.columns = ['Total']
         else:
            bess_inv.columns = ['Step 1']
         bess_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
         BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv], axis=1).fillna(0)
         for (y,st) in tup_list:
            b_inv = (BESS_Units[st]-BESS_Units[st-1])*BESS_Nominal_Capacity_milp*BESS_Inv_Specific_Cost/((1+Discount_Rate)**(y-1))
            bess_inv = pd.DataFrame(['Investment cost', 'Battery bank', '-', 'kUSD', b_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                bess_inv.columns = ['Total']
            else:
                bess_inv.columns = ['Step '+str(st)]
            bess_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv], axis=1).fillna(0)
         BESS_Investment_Cost = BESS_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
         bess_inv_tot = BESS_Investment_Cost.sum(1).to_frame()
         bess_inv_tot.columns = ['Total']
         if ST != 1:
            BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv_tot],axis=1)
        
     "Generator"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Units = instance.Generator_Units.get_values()   
         Generator_Inv_Specific_Cost = instance.Generator_Specific_Investment_Cost.extract_values()
         Generator_capacity = instance.Generator_capacity.extract_values()
         Generator_Nominal_Capacity_milp = instance.Generator_Nominal_Capacity_milp.extract_values()    
         Generator_Investment_Cost = pd.DataFrame()
         for g in range(1,G+1):
            g_inv = ((Generator_Units[1,g]*Generator_Nominal_Capacity_milp[g])-Generator_capacity[g])*Generator_Inv_Specific_Cost[g]
            gen_inv = pd.DataFrame(['Investment cost', Generator_Names[g], '-', 'kUSD', g_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                gen_inv.columns = ['Total']
            else:
                gen_inv.columns = ['Step 1']
            gen_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv], axis=1).fillna(0)
            for (y,st) in tup_list:
                g_inv = ((Generator_Units[st,g]-Generator_Units[st-1,g])*Generator_Nominal_Capacity_milp[g])*Generator_Inv_Specific_Cost[g]/((1+Discount_Rate)**(y-1))
                gen_inv = pd.DataFrame(['Investment cost', Generator_Names[g], '-', 'kUSD', g_inv/1e3]).T.set_index([0,1,2,3]) 
                if ST == 1:
                    gen_inv.columns = ['Total']
                else:
                    gen_inv.columns = ['Step '+str(st)]
                gen_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
                Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv], axis=1).fillna(0)
         Generator_Investment_Cost = Generator_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
         gen_inv_tot = Generator_Investment_Cost.sum(1).to_frame()
         gen_inv_tot.columns = ['Total']
         if ST != 1:
            Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv_tot],axis=1)
        
    else:
        
     "Renewable sources"
     RES_Units = instance.RES_Units.get_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
     RES_capacity = instance.RES_capacity.extract_values()
     RES_Inv_Specific_Cost = instance.RES_Specific_Investment_Cost.extract_values()
     RES_Investment_Cost = pd.DataFrame()
     for r in range(1,R+1):
        r_inv = ((RES_Units[1,r]*RES_Nominal_Capacity[r])-RES_capacity[r])*RES_Inv_Specific_Cost[r]
        res_inv = pd.DataFrame(['Investment cost', RES_Names[r], '-', 'kUSD', r_inv/1e3]).T.set_index([0,1,2,3]) 
        if ST == 1:
            res_inv.columns = ['Total']
        else:
            res_inv.columns = ['Step 1']
        res_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv], axis=1).fillna(0)
        for (y,st) in tup_list:
            r_inv = (RES_Units[st,r]-RES_Units[st-1,r])*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]/((1+Discount_Rate)**(y-1))
            res_inv = pd.DataFrame(['Investment cost', RES_Names[r], '-', 'kUSD', r_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                res_inv.columns = ['Total']
            else:
                res_inv.columns = ['Step '+str(st)]
            res_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv], axis=1).fillna(0)
     RES_Investment_Cost = RES_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
     res_inv_tot = RES_Investment_Cost.sum(1).to_frame()
     res_inv_tot.columns = ['Total']
     if ST != 1:
        RES_Investment_Cost = pd.concat([RES_Investment_Cost, res_inv_tot],axis=1)
        
     "Battery bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()
         BESS_capacity = instance.Battery_capacity.value
         BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
         BESS_Investment_Cost = pd.DataFrame()
         b_inv = (BESS_Nominal_Capacity[1]-BESS_capacity)*BESS_Inv_Specific_Cost
         bess_inv = pd.DataFrame(['Investment cost', 'Battery bank', '-', 'kUSD', b_inv/1e3]).T.set_index([0,1,2,3]) 
         if ST == 1:
            bess_inv.columns = ['Total']
         else:
            bess_inv.columns = ['Step 1']
         bess_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
         BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv], axis=1).fillna(0)
         for (y,st) in tup_list:
            b_inv = (BESS_Nominal_Capacity[st]-BESS_Nominal_Capacity[st-1])*BESS_Inv_Specific_Cost/((1+Discount_Rate)**(y-1))
            bess_inv = pd.DataFrame(['Investment cost', 'Battery bank', '-', 'kUSD', b_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                bess_inv.columns = ['Total']
            else:
                bess_inv.columns = ['Step '+str(st)]
            bess_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv], axis=1).fillna(0)
         BESS_Investment_Cost = BESS_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
         bess_inv_tot = BESS_Investment_Cost.sum(1).to_frame()
         bess_inv_tot.columns = ['Total']
         if ST != 1:
            BESS_Investment_Cost = pd.concat([BESS_Investment_Cost, bess_inv_tot],axis=1)
        
     "Generator"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Capacity = instance.Generator_Nominal_Capacity.get_values()   
         Generator_Inv_Specific_Cost = instance.Generator_Specific_Investment_Cost.extract_values()
         Generator_capacity = instance.Generator_capacity.extract_values()     
         Generator_Investment_Cost = pd.DataFrame()
         for g in range(1,G+1):
            g_inv = (Generator_Capacity[1,g]-Generator_capacity[g])*Generator_Inv_Specific_Cost[g]
            gen_inv = pd.DataFrame(['Investment cost', Generator_Names[g], '-', 'kUSD', g_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                gen_inv.columns = ['Total']
            else:
                gen_inv.columns = ['Step 1']
            gen_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv], axis=1).fillna(0)
            for (y,st) in tup_list:
                g_inv = (Generator_Capacity[st,g]-Generator_Capacity[st-1,g])*Generator_Inv_Specific_Cost[g]/((1+Discount_Rate)**(y-1))
                gen_inv = pd.DataFrame(['Investment cost', Generator_Names[g], '-', 'kUSD', g_inv/1e3]).T.set_index([0,1,2,3]) 
                if ST == 1:
                    gen_inv.columns = ['Total']
                else:
                    gen_inv.columns = ['Step '+str(st)]
                gen_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
                Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv], axis=1).fillna(0)
         Generator_Investment_Cost = Generator_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
         gen_inv_tot = Generator_Investment_Cost.sum(1).to_frame()
         gen_inv_tot.columns = ['Total']
         if ST != 1:
            Generator_Investment_Cost = pd.concat([Generator_Investment_Cost, gen_inv_tot],axis=1)

    "National Grid"
    if instance.Grid_Connection.value == 1:
        Grid_Connection_Specific_Cost = instance.Grid_Connection_Cost.extract_values()  
        Grid_Distance = instance.Grid_Distance.extract_values()   
        Grid_Investment_Cost = pd.DataFrame()
        gr_inv = Grid_Distance[None]*Grid_Connection_Specific_Cost[None]*instance.Grid_Connection.value
        grid_inv = pd.DataFrame(['Investment cost', 'National Grid', '-', 'kUSD', gr_inv/1e3]).T.set_index([0,1,2,3]) 
        if ST == 1:
            grid_inv.columns = ['Total']
        else:
            grid_inv.columns = ['Step 1']
        grid_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        Grid_Investment_Cost = pd.concat([Grid_Investment_Cost, grid_inv], axis=1).fillna(0)
        for (y,st) in tup_list:
            gr_inv = (Grid_Distance[None]*Grid_Connection_Specific_Cost[None]*instance.Grid_Connection.value)/((1+Discount_Rate)**(y-1))
            grid_inv = pd.DataFrame(['Investment cost', 'National Grid', '-', 'kUSD', gr_inv/1e3]).T.set_index([0,1,2,3]) 
            if ST == 1:
                grid_inv.columns = ['Total']
            else:
                grid_inv.columns = ['Step '+str(st)]
            grid_inv.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            Grid_Investment_Cost = pd.concat([Grid_Investment_Cost, grid_inv], axis=1).fillna(0)
        Grid_Investment_Cost = Grid_Investment_Cost.groupby(level=[0], axis=1, sort=False).sum()
        grid_inv_tot = Grid_Investment_Cost.sum(1).to_frame()
        grid_inv_tot.columns = ['Total']
        if ST != 1:
            Grid_Investment_Cost = pd.concat([Grid_Investment_Cost, grid_inv_tot],axis=1)
 

    #%% Fixed costs  
    
    "Renewable sources"    
    RES_OM_Specific_Cost = instance.RES_Specific_OM_Cost.extract_values()
    RES_Fixed_Cost = pd.DataFrame()
    for r in range(1,R+1):
        r_fc = 0
        for (y,st) in yu_tuples_list:
            if instance.MILP_Formulation.value:
               r_fc += RES_Units_milp[st,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]*RES_OM_Specific_Cost[r]/((1+Discount_Rate)**(y))
            else:
               r_fc += RES_Units[st,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]*RES_OM_Specific_Cost[r]/((1+Discount_Rate)**(y))
        res_fc = pd.DataFrame(['Fixed cost', RES_Names[r], '-', 'kUSD', r_fc/1e3]).T.set_index([0,1,2,3]) 
        res_fc.columns = ['Total']
        res_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        RES_Fixed_Cost = pd.concat([RES_Fixed_Cost, res_fc], axis=1).fillna(0)
    RES_Fixed_Cost = RES_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()

    "Battery bank"
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        BESS_OM_Specific_Cost = instance.Battery_Specific_OM_Cost.value    
        BESS_Fixed_Cost = pd.DataFrame()
        b_fc = 0
        for (y,st) in yu_tuples_list:
            if instance.MILP_Formulation.value:
               b_fc += BESS_Units[st]*BESS_Nominal_Capacity_milp*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/((1+Discount_Rate)**(y))
            else:
               b_fc += BESS_Nominal_Capacity[st]*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/((1+Discount_Rate)**(y))
        bess_fc = pd.DataFrame(['Fixed cost', 'Battery bank', '-', 'kUSD', b_fc/1e3]).T.set_index([0,1,2,3]) 
        bess_fc.columns = ['Total']
        bess_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        BESS_Fixed_Cost = pd.concat([BESS_Fixed_Cost, bess_fc], axis=1).fillna(0) 
        BESS_Fixed_Cost = BESS_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()
        
    "Generators"
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        Generator_OM_Specific_Cost = instance.Generator_Specific_OM_Cost.extract_values()     
        Generator_Fixed_Cost = pd.DataFrame()
        for g in range(1,G+1):
            g_fc = 0
            for (y,st) in yu_tuples_list:
                if instance.MILP_Formulation.value:
                   g_fc += (Generator_Units[st,g]*Generator_Nominal_Capacity_milp[g])*Generator_Inv_Specific_Cost[g]*Generator_OM_Specific_Cost[g]/((1+Discount_Rate)**(y))
                else:
                    g_fc += Generator_Capacity[st,g]*Generator_Inv_Specific_Cost[g]*Generator_OM_Specific_Cost[g]/((1+Discount_Rate)**(y))
            gen_fc = pd.DataFrame(['Fixed cost', Generator_Names[g], '-', 'kUSD', g_fc/1e3]).T.set_index([0,1,2,3]) 
            gen_fc.columns = ['Total']
            gen_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
            Generator_Fixed_Cost = pd.concat([Generator_Fixed_Cost, gen_fc], axis=1).fillna(0)
        Generator_Fixed_Cost = Generator_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()

    "National Grid"
    if instance.Grid_Connection.value == 1:
        Grid_OM_Cost = (instance.Grid_Connection_Cost.value * instance.Grid_Connection.value * instance.Grid_Distance.value)* instance.Grid_Maintenance_Cost.value   
        Grid_Fixed_Cost = pd.DataFrame()
        g_fc = 0
        for (y,st) in yu_tuples_list:
            if y < instance.Year_Grid_Connection.extract_values()[None]:
                g_fc += (0)/((1+Discount_Rate)**(y))
            else:
                g_fc += (Grid_OM_Cost)/((1+Discount_Rate)**(y))
        grid_fc = pd.DataFrame(['Fixed cost', 'National Grid', '-', 'kUSD', g_fc/1e3]).T.set_index([0,1,2,3]) 
        grid_fc.columns = ['Total']
        grid_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        Grid_Fixed_Cost = pd.concat([Grid_Fixed_Cost, grid_fc], axis=1).fillna(0)
        Grid_Fixed_Cost = Grid_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()
        
    "Total"
    if instance.Grid_Connection.value == 1:
        Fixed_Costs_Act = pd.DataFrame(['Total fixed O&M cost', 'System', '-', 'kUSD', (instance.Operation_Maintenance_Cost_Act.value + Grid_Fixed_Cost.iloc[0]['Total']*1000)/1e3]).T.set_index([0,1,2,3])
    if instance.Grid_Connection.value == 0:
        Fixed_Costs_Act = pd.DataFrame(['Total fixed O&M cost', 'System', '-', 'kUSD', (instance.Operation_Maintenance_Cost_Act.value)/1e3]).T.set_index([0,1,2,3])
    Fixed_Costs_Act.columns = ['Total']     
    #%% Variable costs

    "Grid electricity cost and revenue"  
    if instance.Grid_Connection.value == 1:
        Grid_El_Cost = pd.DataFrame()
        Grid_El_Rev = pd.DataFrame()
        for s in range(1,S+1):
            Grid_Cost = pd.DataFrame(['Grid electricity cost', "National Grid", s , 'kUSD', instance.Total_Electricity_Cost_Act.get_values()[s]/1e3]).T
            Grid_Rev = pd.DataFrame(['Grid electricity revenue', "National Grid", s , 'kUSD', instance.Total_Revenues_Act.get_values()[s]/1e3]).T
            Grid_El_Cost = pd.concat([Grid_El_Cost, Grid_Cost], axis=0)
            Grid_El_Rev = pd.concat([Grid_El_Rev, Grid_Rev], axis=0)
        Grid_El_Cost = Grid_El_Cost.set_index([0,1,2,3])
        Grid_El_Rev = Grid_El_Rev.set_index([0,1,2,3])
        Grid_El_Cost.columns = ['Total']
        Grid_El_Rev.columns = ['Total']    
    
    "Total"
    Variable_Costs_Act = pd.DataFrame()
    for s in range(1,S+1):
        if instance.Grid_Connection.value == 1:
            Variable_Cost = pd.DataFrame(['Total variable O&M cost', 'System', s, 'kUSD', (instance.Total_Scenario_Variable_Cost_Act.get_values()[s] - instance.Operation_Maintenance_Cost_Act.value +
                                          Grid_El_Rev.iloc[0]['Total']*1000)/1e3]).T
        if instance.Grid_Connection.value == 0:
            Variable_Cost = pd.DataFrame(['Total variable O&M cost', 'System', s, 'kUSD', (instance.Total_Scenario_Variable_Cost_Act.get_values()[s] - instance.Operation_Maintenance_Cost_Act.value)/1e3]).T
        Variable_Costs_Act = pd.concat([Variable_Costs_Act, Variable_Cost], axis=0)
    Variable_Costs_Act = Variable_Costs_Act.set_index([0,1,2,3])
    Variable_Costs_Act.columns = ['Total']      

    "Replacement cost"
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        BESS_Replacement_Cost = pd.DataFrame()
        for s in range(1,S+1):
            BESS_Rep = pd.DataFrame(['Replacement cost', 'Battery bank', s, 'kUSD', instance.Battery_Replacement_Cost_Act.get_values()[s]/1e3]).T
            BESS_Replacement_Cost = pd.concat([BESS_Replacement_Cost, BESS_Rep], axis=0)
        BESS_Replacement_Cost = BESS_Replacement_Cost.set_index([0,1,2,3])
        BESS_Replacement_Cost.columns = ['Total']

    "Fuel cost" 
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        Fuel_Cost = pd.DataFrame()
        for g in range(1,G+1):   
            for s in range(1,S+1):
                fc = pd.DataFrame(['Fuel cost', Fuel_Names[g], s, 'kUSD', instance.Total_Fuel_Cost_Act.get_values()[s,g]/1e3]).T
                Fuel_Cost = pd.concat([Fuel_Cost, fc], axis=0)
        Fuel_Cost = Fuel_Cost.set_index([0,1,2,3])
        Fuel_Cost.columns = ['Total']
    
    "Lost load cost"
    LostLoad_Cost = pd.DataFrame()        
    for s in range(1,S+1):
        LostLoad = pd.DataFrame(['Lost load cost', 'System', s, 'kUSD', instance.Scenario_Lost_Load_Cost_Act.get_values()[s]/1e3]).T
        LostLoad_Cost = pd.concat([LostLoad_Cost, LostLoad], axis=0)
    LostLoad_Cost = LostLoad_Cost.set_index([0,1,2,3])
    LostLoad_Cost.columns = ['Total']


    #%% Salvage value
    Salvage_Value = pd.DataFrame(['Salvage value', 'System', '-', 'kUSD', -instance.Salvage_Value.value/1e3]).T.set_index([0,1,2,3])
    Salvage_Value.columns = ['Total']      
    
    #%% Emission
    CO2_out = pd.DataFrame()  
    for s in range(1,S+1):
        CO = pd.DataFrame(['TOTAL CO2 emission', 'System', s, 'ton', instance.Scenario_CO2_emission.get_values()[s]/1e3]).T
        CO2_out = pd.concat([CO2_out, CO], axis=0)
    CO2_out = CO2_out.set_index([0,1,2,3])
    CO2_out.columns = ['Total']
    
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        CO2_fuel = pd.DataFrame()  
        for s in range(1,S+1):
            CO = pd.DataFrame(['Fuel CO2 emission', 'System', s, 'ton', instance.Scenario_FUEL_emission.get_values()[s]/1e3]).T
            CO2_fuel = pd.concat([CO2_fuel, CO], axis=0)
        CO2_fuel = CO2_fuel.set_index([0,1,2,3])
        CO2_fuel.columns = ['Total']
    
    RES_emission = pd.DataFrame(['RES CO2 emission', 'RES', '-', 'ton', instance.RES_emission.value/1e3]).T.set_index([0,1,2,3])
    RES_emission.columns = ['Total']
    RES_emission.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        GEN_emission = pd.DataFrame(['GEN CO2 emission', 'GEN', '-', 'ton', instance.GEN_emission.value/1e3]).T.set_index([0,1,2,3])
        GEN_emission.columns = ['Total']
        GEN_emission.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
   
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        BESS_emission = pd.DataFrame(['BESS CO2 emission', 'BESS', '-', 'ton', instance.BESS_emission.value/1e3]).T.set_index([0,1,2,3])
        BESS_emission.columns = ['Total']
        BESS_emission.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    
    if instance.Grid_Connection.value == 1:
        CO2_grid = pd.DataFrame()  
        for s in range(1,S+1):
            CO_grid = pd.DataFrame(['Grid CO2 emission', 'System', s, 'ton', instance.Scenario_GRID_emission.get_values()[s]/1e3]).T
            CO2_grid = pd.concat([CO2_grid, CO_grid], axis=0)
        CO2_grid = CO2_grid.set_index([0,1,2,3])
        CO2_grid.columns = ['Total']   
     #%% Net present cost
    if Optimization_Goal == 1:              
        if instance.Grid_Connection.value == 1:
            Net_Present_Cost = pd.DataFrame(['Weighted Net present cost', 'System', '-', 'kUSD', (instance.ObjectiveFuntion.expr() + Grid_Investment + Grid_Fixed_Cost.iloc[0]['Total']*1000)/1e3]).T.set_index([0,1,2,3])
        if instance.Grid_Connection.value == 0:
            Net_Present_Cost = pd.DataFrame(['Weighted Net present cost', 'System', '-', 'kUSD', (instance.ObjectiveFuntion.expr())/1e3]).T.set_index([0,1,2,3])
        Net_Present_Cost.columns = ['Total']
        Net_Present_Cost.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
                                    
    elif Optimization_Goal == 2:
        if instance.Grid_Connection.value == 1:
            Net_Present_Cost = pd.DataFrame(['Weighted Net present cost', 'System', '-', 'kUSD', (instance.ObjectiveFuntion.expr() + Grid_Investment + Grid_Fixed_Cost.iloc[0]['Total']*1000)/1e3]).T.set_index([0,1,2,3])
        if instance.Grid_Connection.value == 0:
            Net_Present_Cost = pd.DataFrame(['Weighted Net present cost', 'System', '-', 'kUSD', (instance.ObjectiveFuntion.expr())/1e3]).T.set_index([0,1,2,3])
        Net_Present_Cost.columns = ['Total']
        Net_Present_Cost.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    
    NPC = pd.DataFrame()
    for s in range (1,S+1):
        if instance.Grid_Connection.value == 1:
            Net_Present_Cost_sc = pd.DataFrame(['Net present cost ', 'System',s, 'kUSD', (instance.Scenario_Net_Present_Cost.get_values()[s] + Grid_Investment + Grid_Fixed_Cost.iloc[0]['Total']*1000)/1e3]).T
        if instance.Grid_Connection.value == 0:
            Net_Present_Cost_sc = pd.DataFrame(['Net present cost ', 'System',s, 'kUSD', (instance.Scenario_Net_Present_Cost.get_values()[s])/1e3]).T
        NPC = pd.concat([NPC,Net_Present_Cost_sc], axis=0)
    NPC = NPC.set_index([0,1,2,3])
    NPC.columns = ['Total']
    #%%LCOE
    Electric_Demand = pd.DataFrame.from_dict(instance.Energy_Demand.extract_values(), orient='index') #[Wh]
    Electric_Demand.index = pd.MultiIndex.from_tuples(list(Electric_Demand.index))
    Electric_Demand = Electric_Demand.groupby(level=[1], axis=0, sort=False).sum()
    Energy_Demand = instance.Energy_Demand.extract_values()
    
    LCOE_scenarios = pd.DataFrame()
    for s in range(1,S+1):
        LC = pd.DataFrame(['Levelized Cost of Energy scenarios','System',s,'USD/kWh',(instance.Scenario_Net_Present_Cost.get_values()[s]/sum(sum(Energy_Demand[s,i,t] for t in range(1,P+1))/(1+Discount_Rate)**i for i in range(1,(Y+1))))*1e3 ]).T
        LCOE_scenarios = pd.concat([LCOE_scenarios, LC], axis=0)
    LCOE_scenarios = LCOE_scenarios.set_index([0,1,2,3])
    LCOE_scenarios.columns = ['Total']
    
    Net_Present_Demand = sum(Electric_Demand.iloc[i-1,0]/(1+Discount_Rate)**i for i in range(1,(Y+1)))    #[Wh]
    if instance.Grid_Connection.value == 1:
        LCOE = pd.DataFrame([(Net_Present_Cost.iloc[0,0] + Grid_El_Rev.iloc[0]['Total']*1000/1e3)/Net_Present_Demand])*1e6    #[USD/KWh]
    if instance.Grid_Connection.value == 0:
        LCOE = pd.DataFrame([(Net_Present_Cost.iloc[0,0])/Net_Present_Demand])*1e6    #[USD/KWh]
    LCOE.index = pd.MultiIndex.from_arrays([['Levelized Cost of Energy '],['System'],['-'],['USD/kWh']])
    LCOE.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    LCOE.columns = ['Total']
    #%% Concatenating
    if instance.Model_Components.value == 0:
        if instance.Grid_Connection.value == 1:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(BESS_Investment_Cost.astype(float),3),
                                    round(Generator_Investment_Cost.astype(float),3),
                                    round(Grid_Investment_Cost.astype(float),3),
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(BESS_Fixed_Cost.astype(float),3),
                                    round(Generator_Fixed_Cost.astype(float),3),
                                    round(Grid_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(BESS_Replacement_Cost.astype(float),3),
                                    round(Fuel_Cost.astype(float),3),
                                    round(Grid_El_Cost.astype(float),3),
                                    round(Grid_El_Rev.astype(float),3),
                                    round(CO2_fuel.astype(float),3),
                                    round(CO2_grid.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(GEN_emission.astype(float),3),
                                    round(BESS_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
        if instance.Grid_Connection.value == 0:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(BESS_Investment_Cost.astype(float),3),
                                    round(Generator_Investment_Cost.astype(float),3),
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(BESS_Fixed_Cost.astype(float),3),
                                    round(Generator_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(BESS_Replacement_Cost.astype(float),3),
                                    round(Fuel_Cost.astype(float),3),
                                    round(CO2_fuel.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(GEN_emission.astype(float),3),
                                    round(BESS_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
    
    if instance.Model_Components.value == 1:
        if instance.Grid_Connection.value == 1:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(BESS_Investment_Cost.astype(float),3),                      
                                    round(Grid_Investment_Cost.astype(float),3),
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(BESS_Fixed_Cost.astype(float),3),
                                    round(Grid_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(BESS_Replacement_Cost.astype(float),3),
                                    round(Grid_El_Cost.astype(float),3),
                                    round(Grid_El_Rev.astype(float),3),
                                    round(CO2_grid.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(BESS_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
        if instance.Grid_Connection.value == 0:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(BESS_Investment_Cost.astype(float),3),                                                        
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(BESS_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(BESS_Replacement_Cost.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(BESS_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
    
    if instance.Model_Components.value == 2:
        if instance.Grid_Connection.value == 1:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(Generator_Investment_Cost.astype(float),3),
                                    round(Grid_Investment_Cost.astype(float),3),
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(Generator_Fixed_Cost.astype(float),3),
                                    round(Grid_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(Fuel_Cost.astype(float),3),
                                    round(Grid_El_Cost.astype(float),3),
                                    round(Grid_El_Rev.astype(float),3),
                                    round(CO2_fuel.astype(float),3),
                                    round(CO2_grid.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(GEN_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
        if instance.Grid_Connection.value == 0:
            SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                                    round(NPC.astype(float),3),
                                    round(Total_Investment_Cost.astype(float),3),
                                    round(Fixed_Costs_Act.astype(float),3),
                                    round(Variable_Costs_Act.astype(float),3),
                                    round(Salvage_Value.astype(float),3),                           
                                    round(LCOE.astype(float),4),
                                    round(LCOE_scenarios.astype(float),4),
                                    round(RES_Investment_Cost.astype(float),3),
                                    round(Generator_Investment_Cost.astype(float),3),
                                    round(RES_Fixed_Cost.astype(float),3),
                                    round(Generator_Fixed_Cost.astype(float),3),
                                    round(LostLoad_Cost.astype(float),3),
                                    round(Fuel_Cost.astype(float),3),
                                    round(CO2_fuel.astype(float),3),
                                    round(RES_emission.astype(float),3),
                                    round(GEN_emission.astype(float),3),
                                    round(CO2_out.astype(float),3)], axis=0).fillna('-')
            
    return  SystemCost   


#%% Plant size output
def EnergySystemSize(instance):

    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names = instance.Fuel_Names.extract_values()
    
    upgrade_years_list = [1 for i in range(ST)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur    
    yu_tuples_list = [0 for i in range(1,Y+1)]    
    if ST == 1:    
        for y in range(1,Y+1):            
            yu_tuples_list[y-1] = (y, 1)    
    else:        
        for y in range(1,Y+1):            
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, [st for st in range(ST)][i+1])                
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, ST)   
    tup_list = [[] for i in range(ST-1)]  
    for i in range(0,ST-1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]
        
    #%%
    if instance.MILP_Formulation.value:
     "Renewable sources"
     RES_Units_milp = instance.RES_Units_milp.get_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
     RES_Size = pd.DataFrame()
     for r in range(1,R+1):
        # r_size = RES_Units_milp[1,r]*RES_Nominal_Capacity[r]/1e3
        # res_size = pd.DataFrame([RES_Names[r], 'kW', r_size]).T.set_index([0,1])
        r_size = RES_Units_milp[1,r]
        res_size = pd.DataFrame([RES_Names[r], '-', r_size]).T.set_index([0,1])
        if ST == 1 :
            res_size.columns = ['Total']
        else:
            res_size.columns = ['Step 1']
        res_size.index.names = ['Component', 'Unit']
        RES_Size = pd.concat([RES_Size,res_size], axis=1).fillna(0)
        for (y,st) in tup_list:
            # res_size = pd.DataFrame([RES_Names[r], 'kW', ((RES_Units_milp[st,r]-RES_Units_milp[st-1,r])*RES_Nominal_Capacity[r])/1e3]).T.set_index([0,1])
            res_size = pd.DataFrame([RES_Names[r], '-', (RES_Units_milp[st,r]-RES_Units_milp[st-1,r])]).T.set_index([0,1])
            if ST == 1:
                res_size.columns = ['Total']
            else:
                res_size.columns = ['Step '+str(st)]
            res_size.index.names = ['Component', 'Unit']
            RES_Size = pd.concat([RES_Size,res_size], axis=1).fillna(0)
     RES_Size = RES_Size.groupby(level=[0], axis=1, sort=False).sum()
     res_size_tot = RES_Size.sum(1).to_frame()
     res_size_tot.columns = ['Total']
     if ST != 1:
        RES_Size = pd.concat([RES_Size, res_size_tot],axis=1)
        
     "Battery Bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Nominal_Capacity_milp = instance.Battery_Nominal_Capacity_milp.value
         BESS_Units = instance.Battery_Units.get_values()
         BESS_Size = pd.DataFrame()
         # bess_size = pd.DataFrame(['Battery bank', 'kWh', (BESS_Units[1]*BESS_Nominal_Capacity_milp)/1e3]).T.set_index([0,1])
         bess_size = pd.DataFrame(['Battery bank', '-', (BESS_Units[1])]).T.set_index([0,1])
         
         if ST == 1:
            bess_size.columns = ['Total']
         else:
            bess_size.columns = ['Step 1']
         bess_size.index.names = ['Component', 'Unit']
         BESS_Size = pd.concat([BESS_Size, bess_size], axis=1).fillna(0)
         for (y,st) in tup_list:
            # bess_size = pd.DataFrame(['Battery bank', 'kWh', ((BESS_Units[st]-BESS_Units[st-1])*BESS_Nominal_Capacity_milp)/1e3]).T.set_index([0,1])
            bess_size = pd.DataFrame(['Battery bank', '-', (BESS_Units[st]-BESS_Units[st-1])]).T.set_index([0,1])
            
            if ST == 1:
                bess_size.columns = ['Total']
            else:
                bess_size.columns = ['Step '+str(st)]
            bess_size.index.names = ['Component', 'Unit']
            BESS_Size = pd.concat([BESS_Size, bess_size], axis=1).fillna(0)     
         BESS_Size = BESS_Size.groupby(level=[0], axis=1, sort=False).sum()
         bess_size_tot = BESS_Size.sum(1).to_frame()
         bess_size_tot.columns = ['Total']
         if ST != 1:
            BESS_Size = pd.concat([BESS_Size, bess_size_tot],axis=1)
        
     "Generator"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Units = instance.Generator_Units.get_values()
         Generator_Nominal_Capacity_milp = instance.Generator_Nominal_Capacity_milp.extract_values() 
         Generator_Size = pd.DataFrame()
         for g in range(1,G+1):
            # gen_size = pd.DataFrame([Generator_Names[g], 'kW', (Generator_Units[1,g]*Generator_Nominal_Capacity_milp[g])/1e3]).T.set_index([0,1])
            gen_size = pd.DataFrame([Generator_Names[g], '-', (Generator_Units[1,g])]).T.set_index([0,1])
            
            if ST == 1:
                gen_size.columns = ['Total']
            else:
                gen_size.columns = ['Step 1']
            gen_size.index.names = ['Component', 'Unit']
            Generator_Size = pd.concat([Generator_Size, gen_size], axis=1).fillna(0)
            for (y,st) in tup_list:
                # gen_size = pd.DataFrame([Generator_Names[g], 'kW', ((Generator_Units[st,g]-Generator_Units[st-1,g])*Generator_Nominal_Capacity_milp[g])/1e3]).T.set_index([0,1])
                gen_size = pd.DataFrame([Generator_Names[g], '-', (Generator_Units[st,g]-Generator_Units[st-1,g])]).T.set_index([0,1])
                
                if ST == 1:
                    gen_size.columns = ['Total']
                else:
                    gen_size.columns = ['Step '+str(st)]
                gen_size.index.names = ['Component', 'Unit']
                Generator_Size = pd.concat([Generator_Size, gen_size], axis=1).fillna(0)
         Generator_Size = Generator_Size.groupby(level=[0], axis=1, sort=False).sum()
         gen_size_tot = Generator_Size.sum(1).to_frame()
         gen_size_tot.columns = ['Total']
         if ST != 1:
            Generator_Size = pd.concat([Generator_Size, gen_size_tot],axis=1)
         
    else:
        
     "Renewable Sources"   
     RES_Units = instance.RES_Units.get_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()    
     RES_Size = pd.DataFrame()
     for r in range(1,R+1):
        r_size = RES_Units[1,r]*RES_Nominal_Capacity[r]/1e3
        res_size = pd.DataFrame([RES_Names[r], 'kW', r_size]).T.set_index([0,1])
        if ST == 1 :
            res_size.columns = ['Total']
        else:
            res_size.columns = ['Step 1']
        res_size.index.names = ['Component', 'Unit']
        RES_Size = pd.concat([RES_Size,res_size], axis=1).fillna(0)
        for (y,st) in tup_list:
            res_size = pd.DataFrame([RES_Names[r], 'kW', ((RES_Units[st,r]-RES_Units[st-1,r])*RES_Nominal_Capacity[r])/1e3]).T.set_index([0,1])
            if ST == 1:
                res_size.columns = ['Total']
            else:
                res_size.columns = ['Step '+str(st)]
            res_size.index.names = ['Component', 'Unit']
            RES_Size = pd.concat([RES_Size,res_size], axis=1).fillna(0)
     RES_Size = RES_Size.groupby(level=[0], axis=1, sort=False).sum()
     res_size_tot = RES_Size.sum(1).to_frame()
     res_size_tot.columns = ['Total']
     if ST != 1:
        RES_Size = pd.concat([RES_Size, res_size_tot],axis=1)

     "Battery bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()
         BESS_Size = pd.DataFrame()
         bess_size = pd.DataFrame(['Battery bank', 'kWh', BESS_Nominal_Capacity[1]/1e3]).T.set_index([0,1])
         if ST == 1:
            bess_size.columns = ['Total']
         else:
            bess_size.columns = ['Step 1']
         bess_size.index.names = ['Component', 'Unit']
         BESS_Size = pd.concat([BESS_Size, bess_size], axis=1).fillna(0)
         for (y,st) in tup_list:
            bess_size = pd.DataFrame(['Battery bank', 'kWh', (BESS_Nominal_Capacity[st]-BESS_Nominal_Capacity[st-1])/1e3]).T.set_index([0,1])
            if ST == 1:
                bess_size.columns = ['Total']
            else:
                bess_size.columns = ['Step '+str(st)]
            bess_size.index.names = ['Component', 'Unit']
            BESS_Size = pd.concat([BESS_Size, bess_size], axis=1).fillna(0)     
         BESS_Size = BESS_Size.groupby(level=[0], axis=1, sort=False).sum()
         bess_size_tot = BESS_Size.sum(1).to_frame()
         bess_size_tot.columns = ['Total']
         if ST != 1:
            BESS_Size = pd.concat([BESS_Size, bess_size_tot],axis=1)

     "Generators"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Capacity = instance.Generator_Nominal_Capacity.get_values()   
         Generator_Size = pd.DataFrame()
         for g in range(1,G+1):
            gen_size = pd.DataFrame([Generator_Names[g], 'kW', Generator_Capacity[1,g]/1e3]).T.set_index([0,1])
            if ST == 1:
                gen_size.columns = ['Total']
            else:
                gen_size.columns = ['Step 1']
            gen_size.index.names = ['Component', 'Unit']
            Generator_Size = pd.concat([Generator_Size, gen_size], axis=1).fillna(0)
            for (y,st) in tup_list:
                gen_size = pd.DataFrame([Generator_Names[g], 'kW', (Generator_Capacity[st,g]-Generator_Capacity[st-1,g])/1e3]).T.set_index([0,1])
                if ST == 1:
                    gen_size.columns = ['Total']
                else:
                    gen_size.columns = ['Step '+str(st)]
                gen_size.index.names = ['Component', 'Unit']
                Generator_Size = pd.concat([Generator_Size, gen_size], axis=1).fillna(0)
         Generator_Size = Generator_Size.groupby(level=[0], axis=1, sort=False).sum()
         gen_size_tot = Generator_Size.sum(1).to_frame()
         gen_size_tot.columns = ['Total']
         if ST != 1:
            Generator_Size = pd.concat([Generator_Size, gen_size_tot],axis=1)
               
    #%% Concatenating
    if instance.Model_Components.value == 0:
        SystemSize = pd.concat([round(RES_Size.astype(float),2),
                                round(BESS_Size.astype(float),2),
                                round(Generator_Size.astype(float),2)], axis=0).fillna('-')
    if instance.Model_Components.value == 1:
        SystemSize = pd.concat([round(RES_Size.astype(float),2),
                                round(BESS_Size.astype(float),2)], axis=0).fillna('-')
    if instance.Model_Components.value == 2:
        SystemSize = pd.concat([round(RES_Size.astype(float),2),
                                round(Generator_Size.astype(float),2)], axis=0).fillna('-')
        
        
    if instance.Multiobjective_Optimization == 1:
        if instance.Pareto_solution == 1: 
            print("\nMULTI-OBJECTIVE OPTMIZATION: Solution for MINIMUM CO2 EMISSIONS and MAXIMUM COSTS")
        elif instance.Pareto_solution == instance.Pareto_points:
            print("\nMULTI-OBJECTIVE OPTMIZATION: Solution for MINIMUM COSTS and MAXIMUM CO2 EMISSIONS")
        else:
            print("\nMULTI-OBJECTIVE OPTMIZATION: Intermediate Solution along Pareto Curve Optimal Front")
    else: print("\nSINGLE-OBJECTIVE OPTMIZATION: Solution for MINIMUM COSTS")

    print("\n------------------------------------------------------------------------------------")
    print(SystemSize)
    print("\n------------------------------------------------------------------------------------")
    return SystemSize
#%% Yearly costs
def YearlyCosts(instance):

    "Importing parameters"
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names = instance.Fuel_Names.extract_values()

    "Generating years-steps tuples list"
    steps = [i for i in range(1, ST+1)]
    
    years_steps_list = [1 for i in range(1, ST+1)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        years_steps_list[i] = years_steps_list[i-1] + s_dur
    ys_tuples_list = [[] for i in range(1, Y+1)]
    for y in range(1, Y+1):  
        if len(years_steps_list) == 1:
            ys_tuples_list[y-1] = (y,1)
        else:
            for i in range(len(years_steps_list)-1):
                if y >= years_steps_list[i] and y < years_steps_list[i+1]:
                    ys_tuples_list[y-1] = (y, steps[i])       
                elif y >= years_steps_list[-1]:
                    ys_tuples_list[y-1] = (y, len(steps)) 

    #%% Fixed costs
    
    if instance.MILP_Formulation.value:
     "Renewable sources"
     RES_Units_milp = instance.RES_Units_milp.get_values()
     RES_Sources = instance.RES_Sources.value
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()    
     RES_Inv_Specific_Cost = instance.RES_Specific_Investment_Cost.extract_values()
     RES_OM_Specific_Cost = instance.RES_Specific_OM_Cost.extract_values()
     RES_Yearly_Cost = pd.DataFrame()
     for r in range(1,RES_Sources+1):
        res_yc_source =  pd.DataFrame()
        for (y,st) in ys_tuples_list:
            res_yc = pd.DataFrame(['Year '+str(y), RES_Units_milp[st,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]*RES_OM_Specific_Cost[r]/1e3]).T.set_index([0]) 
            res_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],[RES_Names[r]],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
            res_yc_source = pd.concat([res_yc_source,res_yc], axis=0)
        RES_Yearly_Cost = pd.concat([RES_Yearly_Cost,res_yc_source], axis=1)
        
     "Battery bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Nominal_Capacity_milp = instance.Battery_Nominal_Capacity_milp.value
         BESS_Units = instance.Battery_Units.get_values() 
         BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
         BESS_OM_Specific_Cost = instance.Battery_Specific_OM_Cost.value
         BESS_Yearly_Cost = pd.DataFrame()
         for (y,st) in ys_tuples_list:
            bess_yc = pd.DataFrame(['Year '+str(y), BESS_Units[st]*BESS_Nominal_Capacity_milp*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/1e3]).T.set_index([0]) 
            bess_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],['Battery bank'],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
            BESS_Yearly_Cost = pd.concat([BESS_Yearly_Cost,bess_yc], axis=0)
        
     "Generator"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Types = instance.Generator_Types.value
         Generator_Units = instance.Generator_Units.get_values()
         Generator_Nominal_Capacity_milp = instance.Generator_Nominal_Capacity_milp.extract_values()  
         Generator_Inv_Specific_Cost = instance.Generator_Specific_Investment_Cost.extract_values()
         Generator_OM_Specific_Cost = instance.Generator_Specific_OM_Cost.extract_values()
         Generator_Yearly_Cost = pd.DataFrame()
         for g in range(1,Generator_Types+1):
            gen_yc_types =  pd.DataFrame()
            for (y,st) in ys_tuples_list:
                gen_yc = pd.DataFrame(['Year '+str(y), (Generator_Units[st,g]*Generator_Nominal_Capacity_milp[g])*Generator_Inv_Specific_Cost[g]*Generator_OM_Specific_Cost[g]/1e3]).T.set_index([0]) 
                gen_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],[Generator_Names[g]],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
                gen_yc_types = pd.concat([gen_yc_types,gen_yc], axis=0)
            Generator_Yearly_Cost = pd.concat([Generator_Yearly_Cost,gen_yc_types], axis=1)
    else:  
     "Renewable Sources"
     RES_Units = instance.RES_Units.get_values()
     RES_Sources = instance.RES_Sources.value
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()    
     RES_Inv_Specific_Cost = instance.RES_Specific_Investment_Cost.extract_values()
     RES_OM_Specific_Cost = instance.RES_Specific_OM_Cost.extract_values()
     RES_Yearly_Cost = pd.DataFrame()
     for r in range(1,RES_Sources+1):
        res_yc_source =  pd.DataFrame()
        for (y,st) in ys_tuples_list:
            res_yc = pd.DataFrame(['Year '+str(y), RES_Units[st,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]*RES_OM_Specific_Cost[r]/1e3]).T.set_index([0]) 
            res_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],[RES_Names[r]],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
            res_yc_source = pd.concat([res_yc_source,res_yc], axis=0)
        RES_Yearly_Cost = pd.concat([RES_Yearly_Cost,res_yc_source], axis=1)
        
     "Battery bank"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
         BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.extract_values()    
         BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
         BESS_OM_Specific_Cost = instance.Battery_Specific_OM_Cost.value
         BESS_Yearly_Cost = pd.DataFrame()
         for (y,st) in ys_tuples_list:
            bess_yc = pd.DataFrame(['Year '+str(y), BESS_Nominal_Capacity[st]*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/1e3]).T.set_index([0]) 
            bess_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],['Battery bank'],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
            BESS_Yearly_Cost = pd.concat([BESS_Yearly_Cost,bess_yc], axis=0)

     "Generator"
     if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
         Generator_Types = instance.Generator_Types.value
         Generator_Nominal_Capacity = instance.Generator_Nominal_Capacity.get_values()    
         Generator_Inv_Specific_Cost = instance.Generator_Specific_Investment_Cost.extract_values()
         Generator_OM_Specific_Cost = instance.Generator_Specific_OM_Cost.extract_values()
         Generator_Yearly_Cost = pd.DataFrame()
         for g in range(1,Generator_Types+1):
            gen_yc_types =  pd.DataFrame()
            for (y,st) in ys_tuples_list:
                gen_yc = pd.DataFrame(['Year '+str(y), Generator_Nominal_Capacity[st,g]*Generator_Inv_Specific_Cost[g]*Generator_OM_Specific_Cost[g]/1e3]).T.set_index([0]) 
                gen_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],[Generator_Names[g]],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
                gen_yc_types = pd.concat([gen_yc_types,gen_yc], axis=0)
            Generator_Yearly_Cost = pd.concat([Generator_Yearly_Cost,gen_yc_types], axis=1)

    "National Grid"     
    if instance.Grid_Connection.value == 1:
        Grid_Connection_Specific_Cost = instance.Grid_Connection_Cost.extract_values()  
        Grid_Distance = instance.Grid_Distance.extract_values() 
        Grid_OM_Specific_Cost = instance.Grid_Maintenance_Cost.extract_values()
        Grid_Connection = instance.Grid_Connection.extract_values()  
        Grid_Yearly_Fixed_Cost = pd.DataFrame()
        for (y,st) in ys_tuples_list:
            if y < instance.Year_Grid_Connection.extract_values()[None]:
                grid_yc = pd.DataFrame(['Year '+str(y), 0]).T.set_index([0]) 
            else:
                grid_yc = pd.DataFrame(['Year '+str(y), Grid_Distance[None]*Grid_Connection_Specific_Cost[None]*Grid_OM_Specific_Cost[None]*Grid_Connection[None]/1e3]).T.set_index([0]) 
            grid_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],['Grid'],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
            Grid_Yearly_Fixed_Cost = pd.concat([Grid_Yearly_Fixed_Cost,grid_yc], axis=0)
        "Grid costs and revenues"  
        Energy_From_Grid = instance.Energy_From_Grid.get_values()    
        El_Purchased_Price = instance.Grid_Purchased_El_Price
        Grid_Yearly_Cost = pd.DataFrame()    
        for s in range(1, S+1):
            grid_s = pd.DataFrame()
            for (y, st) in ys_tuples_list:
                grid_yc = pd.DataFrame(['Year ' + str(y), sum(Energy_From_Grid[(s, y, t)] for t in range(1, P+1)) * El_Purchased_Price / 1e6]).T.set_index([0])
                grid_yc.columns = pd.MultiIndex.from_arrays([['Grid cost'], ['Grid'], [s], ['kUSD']], names=['', 'Component', 'Scenario', 'Unit'])
                grid_s = pd.concat([grid_s, grid_yc], axis=0)
            Grid_Yearly_Cost = pd.concat([Grid_Yearly_Cost, grid_s], axis=1)
       
        if instance.Grid_Connection_Type.value == 0:
            Energy_To_Grid = instance.Energy_To_Grid.get_values()    
            El_Sold_Price = instance.Grid_Sold_El_Price
            Grid_Yearly_Rev = pd.DataFrame()    
            for s in range(1, S+1):
                grid_s = pd.DataFrame()
                for (y, st) in ys_tuples_list:
                    grid_yc = pd.DataFrame(['Year ' + str(y), sum(Energy_To_Grid[(s, y, t)] for t in range(1, P+1)) * El_Sold_Price / 1e6]).T.set_index([0])
                    grid_yc.columns = pd.MultiIndex.from_arrays([['Grid revenue'], ['Grid'], [s], ['kUSD']], names=['', 'Component', 'Scenario', 'Unit'])
                    grid_s = pd.concat([grid_s, grid_yc], axis=0)
                Grid_Yearly_Rev = pd.concat([Grid_Yearly_Rev, grid_s], axis=0)
   

    #%% Variable costs
    
    "Lost Load"    
    Lost_Load = instance.Lost_Load.get_values()    
    Lost_Load_Specific_Cost = instance.Lost_Load_Specific_Cost.value
    Lost_Load_Yearly_Cost = pd.DataFrame()
    for s in range(1,S+1):
        lost_load_s = pd.DataFrame()
        for (y,st) in ys_tuples_list:
            lost_load_yc = pd.DataFrame(['Year '+str(y), sum(Lost_Load[(s,y,t)] for t in range(1,P+1))*Lost_Load_Specific_Cost/1e3]).T.set_index([0]) 
            lost_load_yc.columns = pd.MultiIndex.from_arrays([['Lost load cost'],['System'],[s],['kUSD']], names=['','Component','Scenario','Unit'])
            lost_load_s = pd.concat([lost_load_s,lost_load_yc], axis=0)
        Lost_Load_Yearly_Cost = pd.concat([Lost_Load_Yearly_Cost,lost_load_s], axis=1)

    "BESS Replacement Cost"
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        BESS_Inflow = instance.Battery_Inflow.get_values()    
        BESS_Outflow = instance.Battery_Outflow.get_values()    
        BESS_Unit_Repl_Cost = instance.Unitary_Battery_Replacement_Cost.value
        BESS_Replacement_Yearly_Cost = pd.DataFrame()    
        for s in range(1,S+1):
            Battery_cost_in = [0 for y in range(1,Y+1)]
            Battery_cost_out = [0 for y in range(1,Y+1)]
            Battery_Yearly_cost = [0 for y in range(1,Y+1)]    
            for y in range(1,Y+1):    
                Battery_cost_in[y-1] = sum(BESS_Inflow[s,y,t]*BESS_Unit_Repl_Cost for t in range(1,P+1))
                Battery_cost_out[y-1] = sum(BESS_Outflow[s,y,t]*BESS_Unit_Repl_Cost for t in range(1,P+1))
                Battery_Yearly_cost[y-1] = Battery_cost_in[y-1] + Battery_cost_out[y-1]
            Battery_Yearly_cost = pd.DataFrame(Battery_Yearly_cost)/1e3
            Battery_Yearly_cost.index = Lost_Load_Yearly_Cost.index
            Battery_Yearly_cost.columns = pd.MultiIndex.from_arrays([['Replacement cost'],['Battery bank'],[s],['kUSD']], names=['','Component','Scenario','Unit']) 
            BESS_Replacement_Yearly_Cost = pd.concat([BESS_Replacement_Yearly_Cost, Battery_Yearly_cost], axis=1)
    
    "Fuel cost"
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        if instance.MILP_Formulation.value:
         Generator_Energy_Partial = instance.Generator_Energy_Partial.get_values()
         Generator_Energy_Total = instance.Generator_Energy_Total.get_values()
         Generator_Full = instance.Generator_Full.get_values()
         Generator_Partial = instance.Generator_Partial.get_values()
         Generator_Marginal_Cost = instance.Generator_Marginal_Cost.extract_values()
         Generator_Marginal_Cost_1 = instance.Generator_Marginal_Cost_1.extract_values()
         Generator_Marginal_Cost_milp = instance.Generator_Marginal_Cost_milp.extract_values()
         Generator_Marginal_Cost_milp_1 = instance.Generator_Marginal_Cost_milp_1.extract_values()
         Generator_Nominal_Capacity_milp = instance.Generator_Nominal_Capacity_milp.extract_values()
         Generator_Start_Cost = instance.Generator_Start_Cost.extract_values()
         Generator_Start_Cost_1 = instance.Generator_Start_Cost_1.extract_values()
         Fuel_Cost_Yearly_Cost = pd.DataFrame()
         for s in range(1,S+1):
            fuel_s = pd.DataFrame()
            for g in range(1,Generator_Types+1):
                fuel_yc_types = pd.DataFrame()
                for (y,st) in ys_tuples_list:
                    if instance.Generator_Partial_Load.value == 1 and instance.Fuel_Specific_Cost_Calculation.value == 1:
                       fuel_yc = pd.DataFrame(['Year '+str(y), (sum(Generator_Full[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost[g,y]*Generator_Nominal_Capacity_milp[g]/1e3) + (sum(Generator_Energy_Partial[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost_milp[g,y]/1e3) + (sum(Generator_Partial[(s,y,g,t)] for t in range(1,P+1))*Generator_Start_Cost[g,y])/1e3]).T.set_index([0])
                    elif instance.Generator_Partial_Load.value == 1 and instance.Fuel_Specific_Cost_Calculation.value == 0:
                        fuel_yc = pd.DataFrame(['Year '+str(y), (sum(Generator_Full[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost_1[g]*Generator_Nominal_Capacity_milp[g]/1e3) + (sum(Generator_Energy_Partial[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost_milp_1[g]/1e3) + (sum(Generator_Partial[(s,y,g,t)] for t in range(1,P+1))*Generator_Start_Cost_1[g])/1e3]).T.set_index([0])
                    elif instance.Generator_Partial_Load.value == 0 and instance.Fuel_Specific_Cost_Calculation.value == 1:
                       fuel_yc = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Total[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost[g,y]/1e3]).T.set_index([0])
                    else:
                        fuel_yc = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Total[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost_1[g]/1e3]).T.set_index([0]) 
                    fuel_yc.columns = pd.MultiIndex.from_arrays([['Fuel cost'],[Fuel_Names[g]],[s],['kUSD']], names=['','Component','Scenario','Unit'])
                    fuel_yc_types = pd.concat([fuel_yc_types,fuel_yc], axis=0)
                fuel_s = pd.concat([fuel_s,fuel_yc_types], axis=0)            
            Fuel_Cost_Yearly_Cost = pd.concat([Fuel_Cost_Yearly_Cost,fuel_s], axis=1).fillna(0)
         Fuel_Cost_Yearly_Cost = Fuel_Cost_Yearly_Cost.groupby(level=[0],axis=0,sort=False).sum()
        else:
         Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
         Generator_Marginal_Cost = instance.Generator_Marginal_Cost.extract_values()
         Generator_Marginal_Cost_1 = instance.Generator_Marginal_Cost_1.extract_values()
         Fuel_Cost_Yearly_Cost = pd.DataFrame()
         for s in range(1,S+1):
            fuel_s = pd.DataFrame()
            for g in range(1,Generator_Types+1):
                fuel_yc_types = pd.DataFrame()
                for (y,st) in ys_tuples_list:
                    if instance.Fuel_Specific_Cost_Calculation.value == 1:
                     fuel_yc = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost[g,y]/1e3]).T.set_index([0]) 
                    else: fuel_yc = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost_1[g]/1e3]).T.set_index([0]) 
                    fuel_yc.columns = pd.MultiIndex.from_arrays([['Fuel cost'],[Fuel_Names[g]],[s],['kUSD']], names=['','Component','Scenario','Unit'])
                    fuel_yc_types = pd.concat([fuel_yc_types,fuel_yc], axis=0)
                fuel_s = pd.concat([fuel_s,fuel_yc_types], axis=0)            
            Fuel_Cost_Yearly_Cost = pd.concat([Fuel_Cost_Yearly_Cost,fuel_s], axis=1).fillna(0)
         Fuel_Cost_Yearly_Cost = Fuel_Cost_Yearly_Cost.groupby(level=[0],axis=0,sort=False).sum()
    


    #%% Concatenating
    if instance.Model_Components.value == 0:
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Rev.astype(float),2)], axis=1) 
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 1:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2)], axis=1) 
            
    if instance.Model_Components.value == 1:
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2), 
                                    round(Grid_Yearly_Rev.astype(float),2)], axis=1) 
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 1:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(BESS_Yearly_Cost.astype(float),2),
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(BESS_Replacement_Yearly_Cost.astype(float),2)], axis=1)
            
    if instance.Model_Components.value == 2:
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2), 
                                    round(Grid_Yearly_Rev.astype(float),2)], axis=1) 
        if instance.Grid_Connection.value == 1 and instance.Grid_Connection_Type == 1:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Fixed_Cost.astype(float),2), 
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2),
                                    round(Grid_Yearly_Cost.astype(float),2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                                    round(Generator_Yearly_Cost.astype(float),2),
                                    round(Lost_Load_Yearly_Cost.astype(float),2),
                                    round(Fuel_Cost_Yearly_Cost.astype(float),2)], axis=1)  

    return YearlyCost

#%% Yearly energy parameters
def YearlyEnergyParams(instance, TimeSeries):
    
    "Importing parameters"
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names = instance.Fuel_Names.extract_values()
    idx = pd.IndexSlice
    
    #%% Data preparation
    gen_load  = pd.DataFrame()
    res_load  = pd.DataFrame()
    curt_load = pd.DataFrame()
    res_pen   = pd.DataFrame()
    battery_usage = pd.DataFrame()
    grid_usage = pd.DataFrame()   
    for y in range(1,Y+1):
        demand = 0
        curtailment = 0
        renewables  = 0
        generators  = 0
        battery_out = 0
        grid_in = 0   
        grid_out = 0
        for s in range(1,S+1):
            demand += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Electric Demand',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            curtailment += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Curtailment',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            renewables  += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'RES Production',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
                generators  += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Generator Production',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
                battery_out += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Battery Discharge',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            if instance.Grid_Connection.value == 1:
                grid_in += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Electricity from grid',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]   
                if instance.Grid_Connection_Type.value == 0:
                    grid_out += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Electricity to grid',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
                
        if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
            gen_load  = pd.concat([gen_load, pd.DataFrame(['Year '+str(y), generators/demand]).T.set_index([0])], axis=0)
        res_load  = pd.concat([res_load, pd.DataFrame(['Year '+str(y), (renewables-curtailment)/demand]).T.set_index([0])], axis=0)
        curt_load = pd.concat([curt_load, pd.DataFrame(['Year '+str(y), curtailment/(generators+renewables)]).T.set_index([0])], axis=0)
        if instance.Grid_Connection.value == 1:
            grid_usage = pd.concat([grid_usage, pd.DataFrame(['Year '+str(y), grid_in/demand]).T.set_index([0])], axis=0)    
        res_pen   = pd.concat([res_pen, pd.DataFrame(['Year '+str(y), renewables/(renewables+generators+grid_in)]).T.set_index([0])], axis=0)
        if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
            battery_usage = pd.concat([battery_usage, pd.DataFrame(['Year '+str(y), battery_out/demand]).T.set_index([0])], axis=0)  
    gen_load  = round(gen_load.astype(float)*100,2)
    res_load  = round(res_load.astype(float)*100,2)
    res_pen   = round(res_pen.astype(float)*100,2)
    curt_load = round(curt_load.astype(float)*100,2)
    battery_usage = round(battery_usage.astype(float)*100,2)
    grid_usage = round(grid_usage.astype(float)*100,2)   

    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        gen_load.columns  = pd.MultiIndex.from_arrays([['Generators share'],['%']], names=['',' '])
    curt_load.columns = pd.MultiIndex.from_arrays([['Curtailment share'],['%']], names=['',' '])
    res_pen.columns   = pd.MultiIndex.from_arrays([['Renewables penetration'],['%']], names=['',' '])
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        battery_usage.columns = pd.MultiIndex.from_arrays([['Battery usage'],['%']], names=['',' '])
    if instance.Grid_Connection.value == 1:
        grid_usage.columns = pd.MultiIndex.from_arrays([['Grid usage'],['%']], names=['',' ']) 
    
    #%% Concatenating
    if instance.Model_Components.value == 0:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParams = pd.concat([gen_load,
                                            res_pen,
                                            curt_load,
                                            battery_usage,
                                            grid_usage], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParams = pd.concat([gen_load,
                                            res_pen,
                                            curt_load,
                                            battery_usage], axis=1)          
    if instance.Model_Components.value == 1:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParams = pd.concat([res_pen,
                                            curt_load,
                                            battery_usage,
                                            grid_usage], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParams = pd.concat([res_pen,
                                            curt_load,
                                            battery_usage], axis=1)
    if instance.Model_Components.value == 2:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParams = pd.concat([gen_load,
                                            res_pen,
                                            curt_load,
                                            grid_usage], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParams = pd.concat([gen_load,
                                            res_pen,
                                            curt_load], axis=1)
            
    return YearlyEnergyParams, res_pen

#%% Yearly energy parameters
def YearlyEnergyParamsSC(instance, TimeSeries):
    
    "Importing parameters"
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names = instance.Fuel_Names.extract_values()
    idx = pd.IndexSlice
    
    "Generating years-steps tuples list"
    steps = [i for i in range(1, ST+1)]
    
    years_steps_list = [1 for i in range(1, ST+1)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        years_steps_list[i] = years_steps_list[i-1] + s_dur
    ys_tuples_list = [[] for i in range(1, Y+1)]
    for y in range(1, Y+1):  
        if len(years_steps_list) == 1:
            ys_tuples_list[y-1] = (y,1)
        else:
            for i in range(len(years_steps_list)-1):
                if y >= years_steps_list[i] and y < years_steps_list[i+1]:
                    ys_tuples_list[y-1] = (y, steps[i])       
                elif y >= years_steps_list[-1]:
                    ys_tuples_list[y-1] = (y, len(steps))

#%% Data preparation
     
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
        if instance.MILP_Formulation.value:
         "Generator"
         Generator_Names = instance.Generator_Names.extract_values()
         Generator_Energy_Total = instance.Generator_Energy_Total.get_values()
         Energy_Demand = instance.Energy_Demand.extract_values()
         Generator_Types = instance.Generator_Types.value
         gen_load_sc  = pd.DataFrame()
         for s in range(1,S+1):
            gen_load = pd.DataFrame()
            for g in range(1,Generator_Types+1):
                gen_load_types = pd.DataFrame()
                for (y,st) in ys_tuples_list:
                    gen_load_scenarios = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Total[(s,y,g,t)] for t in range(1,P+1))/sum(Energy_Demand[s,y,t] for t in range(1,P+1))]).T.set_index([0])
                    gen_load_scenarios.columns  = pd.MultiIndex.from_arrays([['Generator share'],[Generator_Names[g]],[s],['%']], names=['','Component','Scenario',' ']) 
                    gen_load_types = pd.concat([gen_load_types, gen_load_scenarios], axis=0)
                gen_load = pd.concat([gen_load, gen_load_types], axis=0)
            gen_load_sc = pd.concat([gen_load_sc, gen_load], axis=1).fillna(0)
         gen_load_sc = gen_load_sc.groupby(level=[0],axis=0,sort=False).sum()
        else:
         Generator_Names = instance.Generator_Names.extract_values()
         Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
         Energy_Demand = instance.Energy_Demand.extract_values()
         Generator_Types = instance.Generator_Types.value
         gen_load_sc  = pd.DataFrame()
         for s in range(1,S+1):
            gen_load = pd.DataFrame()
            for g in range(1,Generator_Types+1):
                gen_load_types = pd.DataFrame()
                for (y,st) in ys_tuples_list:
                    gen_load_scenarios = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1))/sum(Energy_Demand[s,y,t] for t in range(1,P+1))]).T.set_index([0])
                    gen_load_scenarios.columns  = pd.MultiIndex.from_arrays([['Generator share'],[Generator_Names[g]],[s],['%']], names=['','Component','Scenario',' ']) 
                    gen_load_types = pd.concat([gen_load_types, gen_load_scenarios], axis=0)
                gen_load = pd.concat([gen_load, gen_load_types], axis=0)
            gen_load_sc = pd.concat([gen_load_sc, gen_load], axis=1).fillna(0)
         gen_load_sc = gen_load_sc.groupby(level=[0],axis=0,sort=False).sum()

    RES_Names = instance.RES_Names.extract_values()
    RES_Energy_Production = instance.RES_Energy_Production.get_values()
    Curtailment = instance.Energy_Curtailment.get_values()
    Energy_Demand = instance.Energy_Demand.extract_values()
    RES_Sources = instance.RES_Sources.value
    res_load_sc  = pd.DataFrame()
    for s in range(1,S+1):
        res_load = pd.DataFrame()
        for r in range(1,RES_Sources+1):
            res_load_types = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                res_load_scenarios = pd.DataFrame(['Year '+str(y), sum(RES_Energy_Production[(s,y,r,t)]-Curtailment[(s,y,t)] for t in range(1,P+1))/sum(Energy_Demand[s,y,t] for t in range(1,P+1))]).T.set_index([0])
                res_load_scenarios.columns  = pd.MultiIndex.from_arrays([['RES load'],[RES_Names[r]],[s],['%']], names=['','Component','Scenario',' ']) 
                res_load_types = pd.concat([res_load_types, res_load_scenarios], axis=0)
            res_load = pd.concat([res_load, res_load_types], axis=0)
        res_load_sc = pd.concat([res_load_sc, res_load], axis=1).fillna(0)
    res_load_sc = res_load_sc.groupby(level=[0],axis=0,sort=False).sum()
    
    if instance.MILP_Formulation.value:
     RES_Names = instance.RES_Names.extract_values()
     RES_Energy_Production = instance.RES_Energy_Production.get_values()
     Generator_Energy_Total = instance.Generator_Energy_Total.get_values()
     Electricity_From_Grid = instance.Energy_From_Grid.get_values() 
     res_pen_sc  = pd.DataFrame()
     for s in range(1,S+1):
        res_pen = pd.DataFrame()
        for r in range(1,RES_Sources+1):
            res_pen_types = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                
                if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
                    if instance.Grid_Connection.value == 1:
                        res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + sum(Generator_Energy_Total[(s,y,g,t)] for g in range(1,G+1)) + Electricity_From_Grid[(s,y,t)] for t in range(1,P+1)))]).T.set_index([0])
                    if instance.Grid_Connection.value == 0:
                        res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + sum(Generator_Energy_Total[(s,y,g,t)] for g in range(1,G+1)) for t in range(1,P+1)))]).T.set_index([0])
                   
                if instance.Model_Components.value == 1:
                    if instance.Grid_Connection.value == 1:
                        res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + Electricity_From_Grid[(s,y,t)] for t in range(1,P+1)))]).T.set_index([0])
                    if instance.Grid_Connection.value == 0:
                        res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) for t in range(1,P+1)))]).T.set_index([0])
     
                res_pen_scenarios.columns  = pd.MultiIndex.from_arrays([['Renewable penetration'],[RES_Names[r]],[s],['%']], names=['','Component','Scenario',' ']) 
                res_pen_types = pd.concat([res_pen_types, res_pen_scenarios], axis=0)
            res_pen = pd.concat([res_pen, res_pen_types], axis=0)
        res_pen_sc = pd.concat([res_pen_sc, res_pen], axis=1).fillna(0)
     res_pen_sc = res_pen_sc.groupby(level=[0],axis=0,sort=False).sum()
    else:
     RES_Names = instance.RES_Names.extract_values()
     RES_Energy_Production = instance.RES_Energy_Production.get_values()
     Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
     Electricity_From_Grid = instance.Energy_From_Grid.get_values() 
     res_pen_sc  = pd.DataFrame()
     for s in range(1,S+1):
        res_pen = pd.DataFrame()
        for r in range(1,RES_Sources+1):
            res_pen_types = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                
                if instance.Model_Components.value == 0 or instance.Model_Components.value == 2:
                    if instance.Grid_Connection.value == 1:
                            res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + sum(Generator_Energy_Production[(s,y,g,t)] for g in range(1,G+1)) + Electricity_From_Grid[(s,y,t)] for t in range(1,P+1)))]).T.set_index([0])
                    if instance.Grid_Connection.value == 0:
                            res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + sum(Generator_Energy_Production[(s,y,g,t)] for g in range(1,G+1)) for t in range(1,P+1)))]).T.set_index([0])
                if instance.Model_Components.value == 1:
                    if instance.Grid_Connection.value == 1:
                            res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) + Electricity_From_Grid[(s,y,t)] for t in range(1,P+1)))]).T.set_index([0])
                    if instance.Grid_Connection.value == 0:
                            res_pen_scenarios = pd.DataFrame(['Year '+str(y), (sum(RES_Energy_Production[(s,y,r,t)] for t in range(1,P+1)))/(sum(sum(RES_Energy_Production[(s,y,r,t)] for r in range(1,R+1)) for t in range(1,P+1)))]).T.set_index([0])
                    
                res_pen_scenarios.columns  = pd.MultiIndex.from_arrays([['Renewable penetration'],[RES_Names[r]],[s],['%']], names=['','Component','Scenario',' ']) 
                res_pen_types = pd.concat([res_pen_types, res_pen_scenarios], axis=0)
            res_pen = pd.concat([res_pen, res_pen_types], axis=0)
        res_pen_sc = pd.concat([res_pen_sc, res_pen], axis=1).fillna(0)
     res_pen_sc = res_pen_sc.groupby(level=[0],axis=0,sort=False).sum()
    
    curt_load_sc = pd.DataFrame()
    for s in range(1, S+1):
        curt_sc = pd.DataFrame()
        for (y, st) in ys_tuples_list:
            if instance.MILP_Formulation.value:
                total_energy_production = sum(
                    sum(RES_Energy_Production[(s, y, r, t)] if RES_Energy_Production.get((s, y, r, t)) is not None else 0 for r in range(1, R+1)) +
                    sum(Generator_Energy_Total[(s, y, g, t)] if Generator_Energy_Total.get((s, y, g, t)) is not None else 0 for g in range(1, G+1))
                    for t in range(1, P+1)
                )
            else:
                total_energy_production = sum(
                    sum(RES_Energy_Production[(s, y, r, t)] if RES_Energy_Production.get((s, y, r, t)) is not None else 0 for r in range(1, R+1)) +
                    sum(Generator_Energy_Production[(s, y, g, t)] if Generator_Energy_Production.get((s, y, g, t)) is not None else 0 for g in range(1, G+1))
                    for t in range(1, P+1)
                )
                
            if total_energy_production > 0:
                curt_load = pd.DataFrame(
                    ['Year ' + str(y), sum(Curtailment.get((s, y, t), 0) for t in range(1, P+1)) / total_energy_production]
                ).T.set_index([0])
            else:
                curt_load = pd.DataFrame(['Year ' + str(y), 0]).T.set_index([0])  # Set a default value (e.g., 0) when there's no production

            curt_load.columns = pd.MultiIndex.from_arrays([['Curtailment share'], ['-'], [s], ['%']], names=['', 'Component', 'Scenario', ' '])
            curt_sc = pd.concat([curt_sc, curt_load], axis=0)
        curt_load_sc = pd.concat([curt_load_sc, curt_sc], axis=1).fillna(0)

    
    if instance.Model_Components.value == 0 or instance.Model_Components.value == 1:
        BESS_Outflow = instance.Battery_Outflow.get_values()    
        battery_usage_sc = pd.DataFrame()
        for s in range(1,S+1):
            battery_sc = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                batt_sc = pd.DataFrame(['Year '+str(y), sum(BESS_Outflow[s,y,t] for t in range(1,P+1))/sum(Energy_Demand[s,y,t] for t in range(1,P+1))]).T.set_index([0]) 
                batt_sc.columns  = pd.MultiIndex.from_arrays([['Battery usage'],['Battery bank'],[s],['%']], names=['','Component','Scenario',' '])
                battery_sc = pd.concat([battery_sc, batt_sc], axis=0)
            battery_usage_sc = pd.concat([battery_usage_sc, battery_sc], axis=1).fillna(0)
    
    if instance.Grid_Connection.value == 1:
        Electricity_From_Grid = instance.Energy_From_Grid.get_values() 
        grid_usage_sc = pd.DataFrame()
        for s in range(1,S+1):
            grid_el_sc = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                grid_sc = pd.DataFrame(['Year '+str(y), sum(Electricity_From_Grid[s,y,t] for t in range(1,P+1))/sum(Energy_Demand[s,y,t] for t in range(1,P+1))]).T.set_index([0]) 
                grid_sc.columns  = pd.MultiIndex.from_arrays([['Grid usage'],['Grid'],[s],['%']], names=['','Component','Scenario',' '])
                grid_el_sc = pd.concat([grid_el_sc, grid_sc], axis=0)
            grid_usage_sc = pd.concat([grid_usage_sc, grid_el_sc], axis=1).fillna(0)
        
    #%% Concatenating
    if instance.Model_Components.value == 0:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParamsSC = pd.concat([round(gen_load_sc.astype(float)*100,2),
                                              round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2),
                                              round(battery_usage_sc.astype(float)*100,2),
                                              round(grid_usage_sc.astype(float)*100,2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParamsSC = pd.concat([round(gen_load_sc.astype(float)*100,2),
                                              round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2),
                                              round(battery_usage_sc.astype(float)*100,2)], axis=1)       
    if instance.Model_Components.value == 1:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParamsSC = pd.concat([round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2),
                                              round(battery_usage_sc.astype(float)*100,2),
                                              round(grid_usage_sc.astype(float)*100,2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParamsSC = pd.concat([round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2),
                                              round(battery_usage_sc.astype(float)*100,2)], axis=1)
    if instance.Model_Components.value == 2:
        if instance.Grid_Connection.value == 1:
            YearlyEnergyParamsSC = pd.concat([round(gen_load_sc.astype(float)*100,2),
                                              round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2),
                                              round(grid_usage_sc.astype(float)*100,2)], axis=1)
        if instance.Grid_Connection.value == 0:
            YearlyEnergyParamsSC = pd.concat([round(gen_load_sc.astype(float)*100,2),
                                              round(res_pen_sc.astype(float)*100,2),
                                              round(curt_load_sc.astype(float)*100,2)], axis=1)

    
    return YearlyEnergyParamsSC, res_pen_sc    

def EnergySystemLandUse(instance):

    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])

    RES_Names = instance.RES_Names.extract_values()
    
    upgrade_years_list = [1 for i in range(ST)]
    s_dur = instance.Step_Duration.value
    for i in range(1, ST): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur    
    yu_tuples_list = [0 for i in range(1,Y+1)]    
    if ST == 1:    
        for y in range(1,Y+1):            
            yu_tuples_list[y-1] = (y, 1)    
    else:        
        for y in range(1,Y+1):            
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, [st for st in range(ST)][i+1])                
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, ST)   
    tup_list = [[] for i in range(ST-1)]  
    for i in range(0,ST-1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]
        
    #%%
    if instance.MILP_Formulation.value:
     "Renewable sources"
     RES_Units_milp = instance.RES_Units_milp.get_values()
     RES_Specific_Area = instance.RES_Specific_Area.extract_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
     RES_Land = pd.DataFrame()
     for r in range(1,R+1):
        r_land = (RES_Specific_Area[r]/1000)*RES_Units_milp[1,r]*RES_Nominal_Capacity[r]
        res_land = pd.DataFrame([RES_Names[r], 'm2', r_land]).T.set_index([0,1])
        if ST == 1 :
            res_land.columns = ['Total']
        else:
            res_land.columns = ['Step 1']
        res_land.index.names = ['Component', 'Unit']
        RES_Land = pd.concat([RES_Land,res_land], axis=1).fillna(0)
        for (y,st) in tup_list:
            res_land = pd.DataFrame([RES_Names[r], 'm2', ((RES_Specific_Area[r]/1000)*(RES_Units_milp[st,r]-RES_Units_milp[st-1,r])*RES_Nominal_Capacity[r])]).T.set_index([0,1])
            if ST == 1:
                res_land.columns = ['Total']
            else:
                res_land.columns = ['Step '+str(st)]
            res_land.index.names = ['Component', 'Unit']
            RES_Land = pd.concat([RES_Land,res_land], axis=1).fillna(0)
     RES_Land = RES_Land.groupby(level=[0], axis=1, sort=False).sum()
     res_land_tot = RES_Land.sum(1).to_frame()
     res_land_tot.columns = ['Total']
     if ST != 1:
        RES_Land = pd.concat([RES_Land, res_land_tot],axis=1)
         
    else:
        
     "Renewable Sources"   
     RES_Units = instance.RES_Units.get_values()
     RES_Specific_Area = instance.RES_Specific_Area.extract_values()
     RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
     RES_Land = pd.DataFrame()
     for r in range(1,R+1):
        r_land = (RES_Specific_Area[r]/1000)*RES_Units[1,r]*RES_Nominal_Capacity[r]
        res_land = pd.DataFrame([RES_Names[r], 'm2', r_land]).T.set_index([0,1])
        if ST == 1 :
            res_land.columns = ['Total']
        else:
            res_land.columns = ['Step 1']
        res_land.index.names = ['Component', 'Unit']
        RES_Land = pd.concat([RES_Land,res_land], axis=1).fillna(0)
        for (y,st) in tup_list:
            res_land = pd.DataFrame([RES_Names[r], 'm2', ((RES_Specific_Area[r]/1000)*(RES_Units[st,r]-RES_Units[st-1,r])*RES_Nominal_Capacity[r])]).T.set_index([0,1])
            if ST == 1:
                res_land.columns = ['Total']
            else:
                res_land.columns = ['Step '+str(st)]
            res_land.index.names = ['Component', 'Unit']
            RES_Land = pd.concat([RES_Land,res_land], axis=1).fillna(0)
     RES_Land = RES_Land.groupby(level=[0], axis=1, sort=False).sum()
     res_land_tot = RES_Land.sum(1).to_frame()
     res_land_tot.columns = ['Total']
     if ST != 1:
        RES_Land = pd.concat([RES_Land, res_land_tot],axis=1)

               
    #%% Concatenating
    SystemLand = pd.concat([round(RES_Land.astype(float),2)], axis=0).fillna('-')
    print("\nSystem Land Use [m2]")
    print(SystemLand)
    print("\n------------------------------------------------------------------------------------")
    return SystemLand   
                  
#%%
def PrintResults(instance, Results, callback=None):

    Y = int(instance.Years.extract_values()[None])
    
    if int(instance.WACC_Calculation.extract_values()[None]) == 1:
        wacc_value = float(instance.Discount_Rate.extract_values()[None])
        print(f'\n\nWACC = {wacc_value:.4f} [-]')

    npc = float(Results['Costs'].iloc[0, 0])
    print(f'\nNPC = {round(npc, 2)} kUSD')

    total_investment_cost = float(Results['Costs'].iloc[2, 0])
    print(f'Total actualized Investment Cost = {round(total_investment_cost, 2)} kUSD')

    operation_cost = float(Results['Costs'].iloc[3, 0]) + float(Results['Costs'].iloc[4, 0])
    print(f'Total actualized Operation Cost = {round(operation_cost, 2)} kUSD')

    if instance.Grid_Connection.value == 1:
        electricity_revenues = float(Results['Costs'].iloc[20, 0])
        print(f'Total actualized Electricity Selling Revenues = {round(electricity_revenues, 2)} kUSD')

    salvage_value = float(Results['Costs'].iloc[5, 0])
    print(f'Salvage Value = {round(salvage_value, 2)} kUSD')

    lcoe = float(Results['Costs'].iloc[6, 0])
    print(f'LCOE = {lcoe} USD/kWh')
    
    print("\n------------------------------------------------------------------------------------")

    renewable_penetration = Results['Renewables Penetration'].sum().sum() / Y
    print(f'\nAverage renewable penetration per year = {round(renewable_penetration, 2)} %')
    
    if instance.Model_Components.value == 1 and instance.Grid_Connection == 1:
        battery_usage = Results['Yearly energy parameters']['Battery usage'].sum().sum() / Y
        print(f'Average battery usage per year = {round(battery_usage, 2)} %')
        grid_usage = Results['Yearly energy parameters']['Grid usage'].sum().sum() / Y
        print(f'Average national grid usage per year = {round(grid_usage, 2)} %')
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')

    if instance.Model_Components.value == 1 and instance.Grid_Connection == 0:
        battery_usage = Results['Yearly energy parameters']['Battery usage'].sum().sum() / Y
        print(f'Average battery usage per year = {round(battery_usage, 2)} %')
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')
    
    if instance.Model_Components.value == 2 and instance.Grid_Connection == 1:
        generator_share = Results['Yearly energy parameters']['Generators share'].sum().sum() / Y
        print(f'Average generator share per year = {round(generator_share, 2)} %')
        grid_usage = Results['Yearly energy parameters']['Grid usage'].sum().sum() / Y
        print(f'Average national grid usage per year = {round(grid_usage, 2)} %')      
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')

    if instance.Model_Components.value == 2 and instance.Grid_Connection == 0:
        generator_share = Results['Yearly energy parameters']['Generators share'].sum().sum() / Y
        print(f'Average generator share per year = {round(generator_share, 2)} %')
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')

    if instance.Model_Components.value == 0 and instance.Grid_Connection == 1:
        generator_share = Results['Yearly energy parameters']['Generators share'].sum().sum() / Y
        print(f'Average generator share per year = {round(generator_share, 2)} %')
        battery_usage = Results['Yearly energy parameters']['Battery usage'].sum().sum() / Y
        print(f'Average battery usage per year = {round(battery_usage, 2)} %')
        grid_usage = Results['Yearly energy parameters']['Grid usage'].sum().sum() / Y
        print(f'Average national grid usage per year = {round(grid_usage, 2)} %')
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')

    if instance.Model_Components.value == 0 and instance.Grid_Connection == 0:
        generator_share = Results['Yearly energy parameters']['Generators share'].sum().sum() / Y
        print(f'Average generator share per year = {round(generator_share, 2)} %')
        battery_usage = Results['Yearly energy parameters']['Battery usage'].sum().sum() / Y
        print(f'Average battery usage per year = {round(battery_usage, 2)} %')
        curtailment = Results['Yearly energy parameters']['Curtailment share'].sum().sum() / Y
        print(f'Average curtailment per year = {round(curtailment, 2)} %')
            
    if instance.Land_Use.value == 1:
        total_land_use = Results['Land Use']['Total'].sum()
        share_land_use = (total_land_use / instance.Renewables_Total_Area.value)*100
        print(f'Renewables Land Use = {round(share_land_use, 2)} %')


