"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

Authors: 
    Giulia Guidicini   - Department of Energy, Politecnico di Milano 
    Lorenzo Rinaldi    - Department of Energy, Politecnico di Milano
    Nicolò Stevanato   - Department of Energy, Politecnico di Milano / Fondazione Eni Enrico Mattei
    Francesco Lombardi - Department of Energy, Politecnico di Milano
    Emanuela Colombo   - Department of Energy, Politecnico di Milano
Based on the original model by:
    Sergio Balderrama  - Department of Mechanical and Aerospace Engineering, University of Liège / San Simon University, Centro Universitario de Investigacion en Energia
    Sylvain Quoilin    - Department of Mechanical Engineering Technology, KU Leuven
"""



import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from pandas import ExcelWriter
import warnings; warnings.simplefilter(action='ignore', category=FutureWarning)


#%% Results summary
def ResultsSummary(instance, Optimization_Goal, TimeSeries):

    from Results import EnergySystemCost, EnergySystemSize, YearlyCosts, YearlyEnergyParams
    
    print('Results: exporting economic results...')
    EnergySystemCost = EnergySystemCost(instance, Optimization_Goal)
    YearlyCost       = YearlyCosts(instance) 
    print('         exporting technical results...')
    EnergySystemSize   = EnergySystemSize(instance)        
    YearlyEnergyParams, RenewablePenetration = YearlyEnergyParams(instance, TimeSeries)
        
    "Exporting excel"
    Excel = ExcelWriter('Results/Results_Summary.xlsx')
    EnergySystemSize.to_excel(Excel, sheet_name='Size')
    EnergySystemCost.to_excel(Excel, sheet_name='Cost')
    YearlyCost.to_excel(Excel, sheet_name='Yearly cash flows')
    YearlyEnergyParams.to_excel(Excel, sheet_name='Yearly energy parameters')
    
    Excel.save()

    Results = {
               'Costs': EnergySystemCost,
               'Size': EnergySystemSize,
               'Yearly cash flows': YearlyCost,
               'Yearly energy parameters': YearlyEnergyParams,
               'Renewables Penetration': RenewablePenetration
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
    
    # print('    Number of scenarios = '+str(S))
    # print('    Number of years = '+str(Y))

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
    Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
    Curtailment                 = instance.Energy_Curtailment.get_values()
    Lost_Load                   = instance.Lost_Load.get_values()
    Electric_Demand             = instance.Energy_Demand.extract_values()    
    
    BESS_SOC                    = instance.Battery_SOC.get_values()
    LHV                         = instance.Fuel_LHV.extract_values()
    Generator_Efficiency        = instance.Generator_Efficiency.extract_values()
    
    "Creating TimeSeries dictionary and exporting excel"
    TimeSeries = {}
    TS_excel = ExcelWriter('Results/Time_Series.xlsx')
    
    for s in range(1,S+1):
        TimeSeries[s] = {}
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

            for g in range(1,G+1):
                GEN = pd.DataFrame([Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1)])
                TimeSeries[s][y] = pd.concat([TimeSeries[s][y], GEN], axis=1)
                scenario_header  += ['Scenario ' + str(s)]
                flow_header      += ['Generator Production']
                component_header += [Generator_Names[g]]
                unit_header      += ['Wh']
                
            BESS_OUT = pd.DataFrame([BESS_Outflow[(s,y,t)] for t in range(1,P+1)])
            BESS_IN  = pd.DataFrame([BESS_Inflow[(s,y,t)] for t in range(1,P+1)])
            LL       = pd.DataFrame([Lost_Load[(s,y,t)] for t in range(1,P+1)])
            CURTAIL  = pd.DataFrame([Curtailment[(s,y,t)] for t in range(1,P+1)])
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

            for g in range(1,G+1):
                FUEL             = pd.DataFrame([Generator_Energy_Production[(s,y,g,t)]/LHV[g]/Generator_Efficiency[g] for t in range(1,P+1)])
                TimeSeries[s][y] = pd.concat([TimeSeries[s][y], FUEL], axis=1)
                scenario_header  += ['Scenario ' + str(s)]
                flow_header      += ['Fuel Consumption']
                component_header += [Fuel_Names[g]]
                unit_header      += ['Lt']
            
            TimeSeries[s][y].columns = pd.MultiIndex.from_arrays([scenario_header, flow_header, component_header, unit_header], names=['','Flow','Component','Unit'])
            date = str(start_year+y-1)+'/'+str(start_month)+'/'+str(start_day)+' '+str(start_hour)+':'+str(start_minute)
            TimeSeries[s][y].index = pd.date_range(start=date, periods=P, freq='H')
            
            round(TimeSeries[s][y],1).to_excel(TS_excel, sheet_name='Year ' + str(y))

    TS_excel.save()
    
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

    
    #%% Net present cost
    if Optimization_Goal == 'NPC': 
        Net_Present_Cost = pd.DataFrame(['Net present cost', 'System', '-', 'kUSD', instance.ObjectiveFuntion.expr()/1e3]).T.set_index([0,1,2,3]) 
        Net_Present_Cost.columns = ['Total']
        Net_Present_Cost.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
                                        
    elif Optimization_Goal == 'Operation cost':
        # Total_Variable_Cost_NonAct = instance.ObjectiveFunction.expr()
        Net_Present_Cost = pd.DataFrame(['Net present cost', 'System', '-', 'kUSD', instance.Net_Present_Cost.value/1e3]).T.set_index([0,1,2,3]) 
        Net_Present_Cost.columns = ['Total']
        Net_Present_Cost.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']

    #%% Investment cost
    "Total"
    Total_Investment_Cost = pd.DataFrame(['Total Investment cost', 'System', '-', 'kUSD', instance.Investment_Cost.value/1e3]).T.set_index([0,1,2,3])
    Total_Investment_Cost.columns = ['Total']

    "Renewable sources"
    RES_Units = instance.RES_Units.get_values()
    RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()
    RES_Inv_Specific_Cost = instance.RES_Specific_Investment_Cost.extract_values()
    RES_Investment_Cost = pd.DataFrame()
    for r in range(1,R+1):
        r_inv = RES_Units[1,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]
        res_inv = pd.DataFrame(['Investment cost', RES_Names[r], '-', 'kUSD', r_inv/1e3]).T.set_index([0,1,2,3]) 
        if ST == 1:
            res_inv.columns = ['Total']
        else:
            res_inv.columns = ['Step 1']
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
    BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()
    BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
    BESS_Investment_Cost = pd.DataFrame()
    b_inv = BESS_Nominal_Capacity[1]*BESS_Inv_Specific_Cost
    bess_inv = pd.DataFrame(['Investment cost', 'Battery bank', '-', 'kUSD', b_inv/1e3]).T.set_index([0,1,2,3]) 
    if ST == 1:
        bess_inv.columns = ['Total']
    else:
        bess_inv.columns = ['Step 1']
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

    "Generator capacity"
    Generator_Capacity = instance.Generator_Nominal_Capacity.get_values()   
    Generator_Inv_Specific_Cost = instance.Generator_Specific_Investment_Cost.extract_values()     
    Generator_Investment_Cost = pd.DataFrame()
    for g in range(1,G+1):
        g_inv = Generator_Capacity[1,g]*Generator_Inv_Specific_Cost[g]
        gen_inv = pd.DataFrame(['Investment cost', Generator_Names[g], '-', 'kUSD', g_inv/1e3]).T.set_index([0,1,2,3]) 
        if ST == 1:
            gen_inv.columns = ['Total']
        else:
            gen_inv.columns = ['Step 1']
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


    #%% Fixed costs
    "Total"
    Fixed_Costs_Act = pd.DataFrame(['Total fixed O&M cost', 'System', '-', 'kUSD', instance.Operation_Maintenance_Cost_Act.value/1e3]).T.set_index([0,1,2,3])
    Fixed_Costs_Act.columns = ['Total']          
    
    "Renewable sources"    
    RES_OM_Specific_Cost = instance.RES_Specific_OM_Cost.extract_values()
    RES_Fixed_Cost = pd.DataFrame()
    for r in range(1,R+1):
        r_fc = 0
        for (y,st) in yu_tuples_list:
            r_fc += RES_Units[st,r]*RES_Nominal_Capacity[r]*RES_Inv_Specific_Cost[r]*RES_OM_Specific_Cost[r]/((1+Discount_Rate)**(y))
        res_fc = pd.DataFrame(['Fixed cost', RES_Names[r], '-', 'kUSD', r_fc/1e3]).T.set_index([0,1,2,3]) 
        res_fc.columns = ['Total']
        res_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        RES_Fixed_Cost = pd.concat([RES_Fixed_Cost, res_fc], axis=1).fillna(0)
    RES_Fixed_Cost = RES_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()

    "Battery bank"
    BESS_OM_Specific_Cost = instance.Battery_Specific_OM_Cost.value    
    BESS_Fixed_Cost = pd.DataFrame()
    b_fc = 0
    for (y,st) in yu_tuples_list:
        b_fc += BESS_Nominal_Capacity[st]*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/((1+Discount_Rate)**(y))
    bess_fc = pd.DataFrame(['Fixed cost', 'Battery bank', '-', 'kUSD', (BESS_Nominal_Capacity[st]*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost)/1e3]).T.set_index([0,1,2,3]) 
    bess_fc.columns = ['Total']
    bess_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    BESS_Fixed_Cost = pd.concat([BESS_Fixed_Cost, bess_fc], axis=1).fillna(0)

    "Generators"
    Generator_OM_Specific_Cost = instance.Generator_Specific_OM_Cost.extract_values()     
    Generator_Fixed_Cost = pd.DataFrame()
    for g in range(1,G+1):
        g_fc = 0
        for (y,st) in yu_tuples_list:
            g_fc += Generator_Capacity[st,g]*Generator_Inv_Specific_Cost[g]*Generator_OM_Specific_Cost[g]/((1+Discount_Rate)**(y))
        gen_fc = pd.DataFrame(['Fixed cost', Generator_Names[g], '-', 'kUSD', g_fc/1e3]).T.set_index([0,1,2,3]) 
        gen_fc.columns = ['Total']
        gen_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
        Generator_Fixed_Cost = pd.concat([Generator_Fixed_Cost, gen_fc], axis=1).fillna(0)
    Generator_Fixed_Cost = Generator_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()


    #%% Variable costs

    "Total"        
    Variable_Costs_Act = pd.DataFrame(['Total variable O&M cost', 'System', '-', 'kUSD', (instance.Total_Variable_Cost_Act.value - instance.Operation_Maintenance_Cost_Act.value)/1e3]).T.set_index([0,1,2,3])
    Variable_Costs_Act.columns = ['Total']      

    "Replacement cost" 
    for s in range(1,S+1):
        BESS_Replacement_Cost = pd.DataFrame(['Replacement cost', 'Battery bank', s, 'kUSD', instance.Battery_Replacement_Cost_Act.get_values()[s]/1e3]).T.set_index([0,1,2,3])
        BESS_Replacement_Cost.columns = ['Total']

    "Fuel cost" 
    Fuel_Cost = pd.DataFrame()
    for g in range(1,G+1):   
        for s in range(1,S+1):
            fc = pd.DataFrame(['Fuel cost', Fuel_Names[g], s, 'kUSD', instance.Total_Fuel_Cost_Act.get_values()[s,g]/1e3]).T
            Fuel_Cost = pd.concat([Fuel_Cost, fc], axis=0)
    Fuel_Cost = Fuel_Cost.set_index([0,1,2,3])
    Fuel_Cost.columns = ['Total']

    "Lost load cost"        
    for s in range(1,S+1):
        LostLoad_Cost = pd.DataFrame(['Lost load cost', 'System', s, 'kUSD', instance.Scenario_Lost_Load_Cost_Act.get_values()[s]/1e3]).T.set_index([0,1,2,3])
        LostLoad_Cost.columns = ['Total']


    #%% Salvage value
    Salvage_Value = pd.DataFrame(['Salvage value', 'System', '-', 'kUSD', -instance.Salvage_Value.value/1e3]).T.set_index([0,1,2,3])
    Salvage_Value.columns = ['Total']      


    #%%LCOE
    Electric_Demand = pd.DataFrame.from_dict(instance.Energy_Demand.extract_values(), orient='index') #[Wh]
    Electric_Demand.index = pd.MultiIndex.from_tuples(list(Electric_Demand.index))
    Electric_Demand = Electric_Demand.groupby(level=[1], axis=0, sort=False).sum() 
        
    Net_Present_Demand = sum(Electric_Demand.iloc[i-1,0]/(1+Discount_Rate)**i for i in range(1,(Y+1)))    #[Wh]
    LCOE = pd.DataFrame([Net_Present_Cost.iloc[0,0]/Net_Present_Demand])*1e6    #[USD/KWh]
    LCOE.index = pd.MultiIndex.from_arrays([['Levelized Cost of Energy '],['System'],['-'],['USD/kWh']])
    LCOE.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']
    LCOE.columns = ['Total'] 
    

    #%% Concatenating
    SystemCost = pd.concat([round(Net_Present_Cost.astype(float),3),
                            round(Total_Investment_Cost.astype(float),3),
                            round(Fixed_Costs_Act.astype(float),3),
                            round(Variable_Costs_Act.astype(float),3),
                            round(Salvage_Value.astype(float),3),                           
                            round(LCOE.astype(float),4),
                            round(RES_Investment_Cost.astype(float),3),
                            round(BESS_Investment_Cost.astype(float),3),
                            round(Generator_Investment_Cost.astype(float),3),
                            round(RES_Fixed_Cost.astype(float),3),
                            round(BESS_Fixed_Cost.astype(float),3),
                            round(Generator_Fixed_Cost.astype(float),3),
                            round(LostLoad_Cost.astype(float),3),
                            round(BESS_Replacement_Cost.astype(float),3),
                            round(Fuel_Cost.astype(float),3)], axis=0).fillna('-')
    
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
        
#%%
    "Renewable sources" 
    RES_Units = instance.RES_Units.get_values()
    RES_Nominal_Capacity = instance.RES_Nominal_Capacity.extract_values()    
    RES_Size = pd.DataFrame()
    for r in range(1,R+1):
        for st in range(1,ST+1):
            res_size = pd.DataFrame([RES_Names[r], 'kW', (RES_Units[st,r]*RES_Nominal_Capacity[r])/1e3]).T.set_index([0,1]) 
            if ST == 1:
                res_size.columns = ['Total']
            else:
                res_size.columns = ['Step '+str(st)]
            res_size.index.names = ['Component', 'Unit']
            RES_Size = pd.concat([RES_Size, res_size], axis=1).fillna(0)
    RES_Size = RES_Size.groupby(level=[0], axis=1, sort=False).sum()
    res_size_tot = RES_Size.sum(1).to_frame()
    res_size_tot.columns = ['Total']
    if ST != 1:
        RES_Size = pd.concat([RES_Size, res_size_tot],axis=1)
    
    "Battery bank"
    BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.get_values()
    BESS_Size = pd.DataFrame()
    for st in range(1,ST+1):
        if st == 1:
            bess_size = pd.DataFrame(['Battery bank', 'kWh', BESS_Nominal_Capacity[st]/1e3]).T.set_index([0,1]) 
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
    Generator_Capacity = instance.Generator_Nominal_Capacity.get_values()   
    Generator_Size = pd.DataFrame()
    for g in range(1,G+1):
        for st in range(1,ST+1):
            if st==1:
                gen_size = pd.DataFrame([Generator_Names[g], 'kW', Generator_Capacity[st,g]/1e3]).T.set_index([0,1]) 
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
    SystemSize = pd.concat([round(RES_Size.astype(float),2),
                            round(BESS_Size.astype(float),2),
                            round(Generator_Size.astype(float),2)], axis=0).fillna('-')
    
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
    "Renewable sources"
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
    BESS_Nominal_Capacity = instance.Battery_Nominal_Capacity.extract_values()    
    BESS_Inv_Specific_Cost = instance.Battery_Specific_Investment_Cost.value
    BESS_OM_Specific_Cost = instance.Battery_Specific_OM_Cost.value
    BESS_Yearly_Cost = pd.DataFrame()
    for (y,st) in ys_tuples_list:
        bess_yc = pd.DataFrame(['Year '+str(y), BESS_Nominal_Capacity[st]*BESS_Inv_Specific_Cost*BESS_OM_Specific_Cost/1e3]).T.set_index([0]) 
        bess_yc.columns = pd.MultiIndex.from_arrays([['Fixed costs'],['Battery bank'],['-'],['kUSD']], names=['','Component','Scenario','Unit'])
        BESS_Yearly_Cost = pd.concat([BESS_Yearly_Cost,bess_yc], axis=0)

    "Generator sources"
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
    Generator_Energy_Production = instance.Generator_Energy_Production.get_values()
    Generator_Marginal_Cost = instance.Generator_Marginal_Cost.extract_values()
    Fuel_Cost_Yearly_Cost = pd.DataFrame()
    for s in range(1,S+1):
        fuel_s = pd.DataFrame()
        for g in range(1,Generator_Types+1):
            fuel_yc_types = pd.DataFrame()
            for (y,st) in ys_tuples_list:
                fuel_yc = pd.DataFrame(['Year '+str(y), sum(Generator_Energy_Production[(s,y,g,t)] for t in range(1,P+1))*Generator_Marginal_Cost[(s,y,g)]/1e3]).T.set_index([0]) 
                fuel_yc.columns = pd.MultiIndex.from_arrays([['Fuel cost'],[Fuel_Names[g]],[s],['kUSD']], names=['','Component','Scenario','Unit'])
                fuel_yc_types = pd.concat([fuel_yc_types,fuel_yc], axis=0)
            fuel_s = pd.concat([fuel_s,fuel_yc_types], axis=0)            
        Fuel_Cost_Yearly_Cost = pd.concat([Fuel_Cost_Yearly_Cost,fuel_s], axis=1).fillna(0)
    Fuel_Cost_Yearly_Cost = Fuel_Cost_Yearly_Cost.groupby(level=[0],axis=0,sort=False).sum()
    
    #%% Concatenating
    YearlyCost = pd.concat([round(RES_Yearly_Cost.astype(float),2),
                            round(BESS_Yearly_Cost.astype(float),2),
                            round(Generator_Yearly_Cost.astype(float),2),
                            round(Lost_Load_Yearly_Cost.astype(float),2),
                            round(BESS_Replacement_Yearly_Cost.astype(float),2),
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
    for y in range(1,Y+1):
        curtailment = 0
        renewables  = 0
        generators  = 0
        battery_out = 0
        for s in range(1,S+1):
            curtailment += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Curtailment',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            renewables  += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'RES Production',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            generators  += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Generator Production',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
            battery_out += TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Battery Discharge',:,:]].sum().sum()*instance.Scenario_Weight.extract_values()[s]
        demand = TimeSeries[s][y].loc[:,idx['Scenario '+str(s),'Electric Demand',:,:]].sum().sum()
        
        gen_load  = pd.concat([gen_load, pd.DataFrame(['Year '+str(y), generators/demand]).T.set_index([0])], axis=0)
        res_load  = pd.concat([res_load, pd.DataFrame(['Year '+str(y), (renewables-curtailment)/demand]).T.set_index([0])], axis=0)
        curt_load = pd.concat([curt_load, pd.DataFrame(['Year '+str(y), curtailment/(generators+renewables)]).T.set_index([0])], axis=0)
        res_pen   = pd.concat([res_pen, pd.DataFrame(['Year '+str(y), renewables/(renewables+generators)]).T.set_index([0])], axis=0)
        battery_usage = pd.concat([battery_usage, pd.DataFrame(['Year '+str(y), battery_out/demand]).T.set_index([0])], axis=0)
    
    gen_load  = round(gen_load.astype(float)*100,2)
    res_load  = round(res_load.astype(float)*100,2)
    res_pen   = round(res_pen.astype(float)*100,2)
    curt_load = round(curt_load.astype(float)*100,2)
    battery_usage = round(battery_usage.astype(float)*100,2)

    gen_load.columns  = pd.MultiIndex.from_arrays([['Generators share'],['%']], names=['',' '])
    curt_load.columns = pd.MultiIndex.from_arrays([['Curtailment share'],['%']], names=['',' '])
    res_pen.columns   = pd.MultiIndex.from_arrays([['Renewables penetration'],['%']], names=['',' '])
    battery_usage.columns = pd.MultiIndex.from_arrays([['Battery usage'],['%']], names=['',' '])
    
    #%% Concatenating
    YearlyEnergyParams = pd.concat([gen_load,
                                    res_pen,
                                    curt_load,
                                    battery_usage], axis=1)
    
    return YearlyEnergyParams, res_pen

                   
#%%
def PrintResults(instance, Results):

    Y  = int(instance.Years.extract_values()[None])

    print('\n\nNPC = '+str(round(Results['Costs'].iloc[0,-1],2))+' kUSD')
    print('Total actualized Investment Cost = '+str(round(Results['Costs'].iloc[1,-1],2))+' kUSD')
    print('Total actualized Operation Cost = '+str(round(Results['Costs'].iloc[2,-1]+Results['Costs'].iloc[3,-1],2))+' kUSD')
    print('Salvage Value = '+str(round(Results['Costs'].iloc[4,-1],2))+' kUSD')
    print('LCOE = '+str(Results['Costs'].iloc[5,-1])+' USD/kWh')
    print('\nAverage renewable penetration per year = '+ str(round(Results['Renewables Penetration'].sum().sum()/Y,2))+' %')
    print('Average battery usage per year = '+str(round(Results['Yearly energy parameters'].iloc[:,-1].sum().sum()/Y,2))+' %')
    print('Average curtailment per year = '+str(round(Results['Yearly energy parameters'].iloc[:,-2].sum().sum()/Y,2))+' %')
            
                
        


