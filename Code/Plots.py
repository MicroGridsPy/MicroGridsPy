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
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import pyplot

#%%
def DispatchPlot(instance,TimeSeries,PlotScenario,PlotDate,PlotTime,PlotResolution,PlotFormat):

    print('\nPlots: plotting energy dispatch...')
    fontticks = 18
    fonttitles = 16
    fontaxis = 14
    fontlegend = 14
    
    idx = pd.IndexSlice
    
    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])
    
    RES_Names       = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names      = instance.Fuel_Names.extract_values()
    BESSNominalCapacity = instance.Battery_Nominal_Capacity.get_values()
    
    PlotYear  = pd.to_datetime(PlotDate).year - pd.to_datetime(instance.StartDate()).year +1
    
    # PlotDate_text = str(pd.to_datetime(PlotDate).day) + '/' + str(pd.to_datetime(PlotDate).month) + '/' + str(pd.to_datetime(PlotDate).year)
    
    Series = TimeSeries[PlotScenario][PlotYear].copy()

    #%% Generating years-steps tuples list
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
    
    #%% Identifying in which investment step the selected year is
    for (y,st) in ys_tuples_list:
        if y==PlotYear:
            PlotStep = st
    
    #%% Series preparation
    pDay = 24/instance.Delta_Time()                       # Periods in a day
    foo = pd.date_range(start=PlotDate,periods=1,freq='1h')      # Assign the start date of the graphic to a dumb variable
    for x in range(0, instance.Periods()):                       # Find the position from which the plot will start in the Time_Series dataframe
        if foo == Series.index[x]: 
           Start_Plot = x                                        # assign the value of x to the position where the plot will start 
           break
    End_Plot     = Start_Plot + PlotTime*pDay # Create the end of the plot position inside the time_series
    Series.index = range(1,(len(Series)+1))
    Series       = Series[Start_Plot:int(End_Plot)] # Extract the data between the start and end position from the Time_Series
    Series.index = pd.date_range(start=PlotDate, periods=PlotTime*pDay, freq=('1h')) 
   
    y_RES = {}
    for r in range(1,R+1):
        y_RES[r]  = Series.loc[:,idx[:,'RES Production',RES_Names[r],:]].values.flatten()/1e3 
    y_BESS_out    = Series.loc[:,idx[:,'Battery Discharge',:,:]].values.flatten()/1e3 
    y_BESS_in     = -1*Series.loc[:,idx[:,'Battery Charge',:,:]].values.flatten()/1e3 
    y_Genset = {}
    for g in range(1,G+1):
        y_Genset[g] = Series.loc[:,idx[:,'Generator Production',Generator_Names[g],:]].values.flatten()/1e3 
    y_LostLoad    = Series.loc[:,idx[:,'Lost Load',:,:]].values.flatten()/1e3 
    y_Curtailment = -1*Series.loc[:,idx[:,'Curtailment',:,:]].values.flatten()/1e3 

    x_Plot = np.arange(len(y_BESS_out))
    
    deltaBESS_pos = y_BESS_out + y_BESS_in
    deltaBESS_neg = y_BESS_out + y_BESS_in
    
    for i in range(deltaBESS_pos.shape[0]):
        if deltaBESS_pos[i] < 0:   
            deltaBESS_pos[i] *= 0
        if deltaBESS_neg[i] > 0:   
            deltaBESS_neg[i] *= 0
    
    y_Stacked_pos = []
    for r in range(1,R+1):
        y_Stacked_pos += [y_RES[r]]
    y_Stacked_pos += [deltaBESS_pos]  
    for g in range(1,G+1):
        y_Stacked_pos += [y_Genset[g]]
    y_Stacked_pos += [y_LostLoad]  
    y_Stacked_pos += [y_Curtailment]  
                         
    y_Stacked_neg = [deltaBESS_neg]
    
    y_Demand   = Series.loc[:,idx[:,'Electric Demand',:,:]].values.flatten()/1e3 
    y_BESS_SOC = Series.loc[:,idx[:,'Battery SOC',:,:]].values.flatten()/BESSNominalCapacity[PlotStep]*100


    #%% Plotting
    RES_Colors  = instance.RES_Colors.extract_values()
    BESS_Color  = instance.Battery_Color()
    Generator_Colors = instance.Generator_Colors.extract_values()
    Lost_Load_Color = instance.Lost_Load_Color()
    Curtailment_Color = instance.Curtailment_Color()

    Colors_pos = []
    for r in range(1,R+1):
         Colors_pos += ['#'+RES_Colors[r]]
    Colors_pos += ['#'+BESS_Color]  
    for g in range(1,G+1):
         Colors_pos += ['#'+Generator_Colors[g]]
    Colors_pos += ['#'+Lost_Load_Color]  
    Colors_pos += ['#'+Curtailment_Color]  
   
    Colors_neg = ['#'+BESS_Color,]

    Labels_pos = []
    for r in range(1,R+1):
         Labels_pos += [RES_Names[r]]
    Labels_pos += ['Battery']  
    for g in range(1,G+1):
         Labels_pos += [Generator_Names[g]]
    Labels_pos += ['Lost load']  
    Labels_pos += ['Curtailment']  
      
    Labels_neg = ['_nolegend_'] 


    fig,ax1 = plt.subplots(nrows=1,ncols=1,figsize = (12,8))

    ax1.stackplot(x_Plot, y_Stacked_pos, labels=Labels_pos, colors=Colors_pos, zorder=2)
    ax1.stackplot(x_Plot, y_Stacked_neg, labels=Labels_neg, colors=Colors_neg, zorder=2)
    ax1.plot(x_Plot, y_Demand, linewidth=4, color='black', label='Demand', zorder=2)
    ax1.plot(x_Plot, np.zeros((len(x_Plot))), color='black', label='_nolegend_', zorder=2)
 
    ax1.set_xlabel('Time [Hours]', fontsize=fontaxis)
    ax1.set_ylabel('Power [kW]', fontsize=fontaxis)
        
    "x axis"
    xticks_position = [0]
    ticks = []
    for i in range(1,PlotTime+1):
        ticks = [d*6 for d in range(PlotTime*4+1)]
        xticks_position += [d*6-1 for d in range(1,PlotTime*4+1)]
            
    ax1.set_xticks(xticks_position)
    # ax1.set_xticklabels(ticks, fontsize=fontticks)
    ax1.set_xlim(xmin=0)
    ax1.set_xlim(xmax=xticks_position[-1])
    ax1.margins(x=0)
        
    "primary y axis"
    # ax1.set_yticklabels(ax1.get_yticks(), fontsize=fontticks) 
    ax1.margins(y=0)
    ax1.grid(True, zorder=2)
       
    "secondary y axis"
    if BESSNominalCapacity[PlotStep] < 1:
        ax2=ax1.twinx()
        ax2.plot(x_Plot, y_BESS_SOC, '--', color='black', label='Battery state\nof charge', zorder=2)
        ax2.set_ylabel('Battery state of charge [%]', fontsize=fontaxis)

        ax2.set_yticks(np.arange(0,100.00000001,20))
        # ax2.set_yticklabels(np.arange(0,100.00000001,20), fontsize=fontticks)
        ax2.set_ylim(ymin=0)
        ax2.set_ylim(ymax=100.00000001)
        ax2.margins(y=0)

    # ax1.text((ax1.get_xticks()[0] + ax1.get_xticks()[1])/4 ,ax1.get_yticks()[-2], 'Plot start at\n'+PlotDate, fontsize=fontlegend)

    fig.legend(bbox_to_anchor=(1.19,0.98), ncol=1, fontsize=fontlegend, frameon=True)
    fig.tight_layout()    
    
    fig.savefig('Results/Plots/DispatchPlot.'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')



#%%
def CashFlowPlot(instance,Results,PlotResolution,PlotFormat):

    print('       plotting yearly cash flows...')
    fontticks = 18
    fontaxis = 20
    fontlegend = 20
    
    idx = pd.IndexSlice
    
    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])
    
    RES_Names       = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names      = instance.Fuel_Names.extract_values()
    
    
    #%% Investment cash flows
    "Generating years-steps tuples list"
    upgrade_years_list = [1 for i in range(ST)]
    s_dur = instance.Step_Duration.value
    for i in range(ST): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur  
    yu_tuples_list = [[] for i in range(1,Y+1)]  
    for y in range(1,Y+1):      
        for i in range(len(upgrade_years_list)-1):
            if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                yu_tuples_list[y-1] = (y, [n for n in range(ST)][i+1])          
            elif y >= upgrade_years_list[-1]:
                yu_tuples_list[y-1] = (y, ST)            
    tup_list = [[] for i in range(ST-1)]  
    for i in range(0, ST-1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]      
    
    Investment_BESS = [0 for y in range(Y)]
    Investment_RES = {}
    for r in range(1,R+1):
        Investment_RES[RES_Names[r]] = [0 for y in range(Y)]
    Investment_Gen = {}
    for g in range(1,G+1):
        Investment_Gen[Generator_Names[g]] = [0 for y in range(Y)]

    if ST == 1:
        Investment_BESS[0] = Results['Costs'].loc[idx['Investment cost','Battery bank',:,:],'Total'].values[0]
        for r in range(1,R+1):
            Investment_RES[RES_Names[r]][0] = Results['Costs'].loc[idx['Investment cost',RES_Names[r],:,:],'Total'].values[0]
        for g in range(1,G+1):
            Investment_Gen[Generator_Names[g]][0] = Results['Costs'].loc[idx['Investment cost',Generator_Names[g],:,:],'Total'].values[0]
    else:
        for st in range(1,ST+1):
            for y in range(1,Y+1):
                if y==1:
                    Investment_BESS[y-1] = Results['Costs'].loc[idx['Investment cost','Battery bank',:,:],'Step 1'].values[0]
                    for r in range(1,R+1):
                        Investment_RES[RES_Names[r]][y-1] = Results['Costs'].loc[idx['Investment cost',RES_Names[r],:,:],'Step 1'].values[0]
                    for g in range(1,G+1):
                        Investment_Gen[Generator_Names[g]][y-1] = Results['Costs'].loc[idx['Investment cost',Generator_Names[g],:,:],'Step 1'].values[0]                
                if st!=1:
                    if y==tup_list[st-2][0]:
                        Investment_BESS[y-1] = Results['Costs'].loc[idx['Investment cost','Battery bank',:,:],'Step '+str(st)].values[0]
                        for r in range(1,R+1):
                            Investment_RES[RES_Names[r]][y-1] = Results['Costs'].loc[idx['Investment cost',RES_Names[r],:,:],'Step '+str(st)].values[0]
                        for g in range(1,G+1):
                            Investment_Gen[Generator_Names[g]][y-1] = Results['Costs'].loc[idx['Investment cost',Generator_Names[g],:,:],'Step '+str(st)].values[0]
    

#%% Yearly cash flows
    Fixed_costs_BESS = Results['Yearly cash flows'].loc[:,idx['Fixed costs', 'Battery bank', :, :]].values
    Fixed_costs_RES = {}
    for r in range(1,R+1):
        Fixed_costs_RES[r] = Results['Yearly cash flows'].loc[:,idx['Fixed costs', RES_Names[r], :, :]].values
    Fixed_costs_Gen = {}
    for g in range(1,G+1):
        Fixed_costs_Gen[g] = Results['Yearly cash flows'].loc[:,idx['Fixed costs', Generator_Names[g], :, :]].values
    
    lostloadcost = {}
    bessreplacementcost = {}
    fuelcost = {} 
    for s in range(1,S+1):
        lostloadcost[s] = Results['Yearly cash flows'].loc[:,idx['Lost load cost', :, s, :]].values 
        bessreplacementcost[s] = Results['Yearly cash flows'].loc[:,idx['Replacement cost', 'Battery bank', s, :]].values 
        fuelcost[s] = {}
        for g in range(1,G+1):
            fuelcost[s][g] = Results['Yearly cash flows'].loc[:,idx['Fuel cost', Fuel_Names[g], s, :]].values 
    
    Lost_load_cost = np.arange(Y)*0
    BESS_replacement_cost = np.arange(Y)*0
    for s in range(1,S+1):    
        Lost_load_cost = [a+b for (a,b) in zip(Lost_load_cost,lostloadcost[s].T[0])]
        BESS_replacement_cost = [a+b for (a,b) in zip(BESS_replacement_cost,bessreplacementcost[s].T[0])]
    Lost_load_cost = [i/S for i in Lost_load_cost]
    BESS_replacement_cost = [i/S for i in BESS_replacement_cost]

    Fuel_cost = {}
    for g in range(1,G+1):
        Fuel_cost[g] = np.arange(Y)*0  
        for s in range(1,S+1):    
            Fuel_cost[g] = [a+b for (a,b) in zip(Fuel_cost[g],fuelcost[s][g].T[0])]
        Fuel_cost[g] = [i/S for i in Fuel_cost[g]]
            
#%% Plotting
    fig = plt.figure(figsize=(20,15))

    RES_Colors  = instance.RES_Colors.extract_values()
    BESS_Color  = instance.Battery_Color()
    Generator_Colors = instance.Generator_Colors.extract_values()
    Lost_Load_Color = instance.Lost_Load_Color()

    x_positions = np.arange(Y)
    years = [pd.to_datetime(instance.StartDate()).year+y for y in range(Y)]

            
    "Investment costs"
    plt.bar(x_positions, 
            Investment_BESS, 
            color='#'+BESS_Color,
            edgecolor= 'black',
            label='Battery bank',
            zorder = 3) 
    base = Investment_BESS
    
    for r in range(1,R+1):
        plt.bar(x_positions, 
                Investment_RES[RES_Names[r]], 
                color='#'+RES_Colors[r], 
                edgecolor= 'black',
                label=RES_Names[r],
                bottom=base,
                zorder = 3)   
        base = [a+b for (a,b) in zip(base, Investment_RES[RES_Names[r]])]
            
    for g in range(1,G+1):
        plt.bar(x_positions, 
                Investment_Gen[Generator_Names[g]],
                color='#'+Generator_Colors[g], 
                edgecolor= 'black',
                label=Generator_Names[g],
                bottom=base,
                zorder = 3)   
        base = [a+b for (a,b) in zip(base, Investment_Gen[Generator_Names[g]])]

    
    "Fixed costs"
    plt.bar(x_positions, 
            [Fixed_costs_BESS[i][0] for i in range(len(Fixed_costs_BESS))], 
            color='#'+BESS_Color,
            edgecolor= 'black',
            label='_nolegend_',
            hatch='x',
            bottom = base,
            zorder = 3) 
    base = [a+b for (a,b) in zip(base, [Fixed_costs_BESS[i][0] for i in range(len(Fixed_costs_BESS))])]   
    
    for r in range(1,R+1):
        plt.bar(x_positions, 
                [Fixed_costs_RES[r][i][0] for i in range(len(Fixed_costs_RES[r]))], 
                color='#'+RES_Colors[r], 
                edgecolor= 'black',
                hatch='x',
                label='_nolegend_',
                bottom=base,
                zorder = 3)   
        base = [a+b for (a,b) in zip(base, [Fixed_costs_RES[r][i][0] for i in range(len(Fixed_costs_RES[r]))])]

    for g in range(1,G+1):
        plt.bar(x_positions, 
                [Fixed_costs_Gen[g][i][0] for i in range(len(Fixed_costs_Gen[g]))], 
                color='#'+Generator_Colors[g], 
                edgecolor= 'black',
                hatch='x',
                label='_nolegend_',
                bottom=base,
                zorder = 3)   
        base = [a+b for (a,b) in zip(base, [Fixed_costs_Gen[g][i][0] for i in range(len(Fixed_costs_Gen[g]))])]

    "Variable costs"
    plt.bar(x_positions, 
            Lost_load_cost, 
            color='#'+Lost_Load_Color,
            edgecolor= 'black',
            label='_nolegend_',
            hatch='//',
            bottom = base,
            zorder = 3) 
    base = [a+b for (a,b) in zip(base, Lost_load_cost)]        
    
    plt.bar(x_positions, 
            BESS_replacement_cost, 
            color='#'+BESS_Color,
            edgecolor= 'black',
            label='_nolegend_',
            hatch='//',                     
            bottom = base,
            zorder = 3) 
    base = [a+b for (a,b) in zip(base, BESS_replacement_cost)]        

    for g in range(1,G+1):        
        plt.bar(x_positions, 
                Fuel_cost[g], 
                color='#'+Generator_Colors[g],
                edgecolor= 'black',
                label='_nolegend_',
                hatch='//',                     
                bottom = base,
                zorder = 3) 
        base = [a+b for (a,b) in zip(base, Fuel_cost[g])]  


    "Hatch legend traces"
    plt.bar(x_positions, 
            [0 for i in range(len(x_positions))], 
            color='white',
            label=' ',
            zorder = 3) 
    plt.bar(x_positions, 
            [0 for i in range(len(x_positions))], 
            color='white',
            label='Investment cost',
            edgecolor= 'black',
            zorder = 3) 
    plt.bar(x_positions, 
            [0 for i in range(len(x_positions))], 
            color='white',
            label='Fixed O&M cost',
            edgecolor= 'black',
            hatch='x',                     
            zorder = 3) 
    plt.bar(x_positions, 
            [0 for i in range(len(x_positions))], 
            color='white',
            label='Variable O&M cost',
            edgecolor= 'black',
            hatch='//',                     
            zorder = 3) 

    plt.xlabel('Years', fontsize=fontaxis)
    plt.ylabel('Thousand USD', fontsize=fontaxis)
    plt.xticks(x_positions, years, fontsize=fontticks)
    plt.yticks(fontsize=fontticks)
    plt.grid(True, axis='y', zorder=2)
    plt.margins(x=0.009)
    
    fig.legend(bbox_to_anchor=(1.19,0.98), ncol=1, fontsize=fontlegend, frameon=True)
    fig.tight_layout()    
    
    fig.savefig('Results/Plots/CashFlowPlot.'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')



#%%
def SizePlot(instance,Results,PlotResolution,PlotFormat):

    print('       plotting components size...')
    fontticks = 18
    fontaxis = 20
    fontlegend = 20
    
    idx = pd.IndexSlice
    
    #%% Importing parameters
    S  = int(instance.Scenarios.extract_values()[None])
    P  = int(instance.Periods.extract_values()[None])
    Y  = int(instance.Years.extract_values()[None])
    ST = int(instance.Steps_Number.extract_values()[None])
    R  = int(instance.RES_Sources.extract_values()[None])
    G  = int(instance.Generator_Types.extract_values()[None])
    
    RES_Names       = instance.RES_Names.extract_values()
    Generator_Names = instance.Generator_Names.extract_values()
    Fuel_Names      = instance.Fuel_Names.extract_values()

    
#%% Plotting

    RES_Colors  = instance.RES_Colors.extract_values()
    BESS_Color  = instance.Battery_Color()
    Generator_Colors = instance.Generator_Colors.extract_values()


    if ST==1:
        fig, ax1 = plt.subplots(nrows=1,ncols=1,figsize = (20,15))
        x_positions = np.arange(R+G+1)
        x_ticks = []
        ax2 = ax1.twinx()
        
        for r in range(1,R+1):
            ax1.bar(x_positions[r-1], 
                    Results['Size'].loc[idx[RES_Names[r],:],'Total'].values[0], 
                    color='#'+RES_Colors[r],
                    edgecolor= 'black',
                    label=RES_Names[r],
                    zorder = 3)
            x_ticks += [RES_Names[r]]

        for g in range(1,G+1):
            ax1.bar(x_positions[R+g-1], 
                    Results['Size'].loc[idx[Generator_Names[g],:],'Total'].values[0], 
                    color='#'+Generator_Colors[g],
                    edgecolor= 'black',
                    label=Generator_Names[g],
                    zorder = 3)
            x_ticks += [Generator_Names[g]]

        ax2.bar(x_positions[-1], 
                Results['Size'].loc[idx['Battery bank',:],'Total'].values[0], 
                color='#'+BESS_Color,
                edgecolor= 'black',
                label='Battery bank',
                zorder = 3)
        x_ticks += ['Battery bank']

        ax1.set_xlabel('Components', fontsize=fontaxis)
        ax1.set_ylabel('Installed capacity [kW]', fontsize=fontaxis)
        ax2.set_ylabel('Installed capacity [kWh]', fontsize=fontaxis)
                            
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_ticks, fontsize=fontticks)
        ax1.margins(x=0.009)
        ax2.set_xticks(x_positions)
        ax2.set_xticklabels(x_ticks, fontsize=fontticks)
        ax2.margins(x=0.009)
            
        ax1.set_yticklabels(ax1.get_yticks(), fontsize=fontticks) 
        ax1.grid(True, zorder=2)
        ax2.set_yticklabels(ax1.get_yticks(), fontsize=fontticks) 
        
    if ST!=1:
        fig,(ax1,ax2) = plt.subplots(nrows=2,ncols=1,figsize = (20,15))
        base = [0 for i in range(1,ST+1)]
        x_positions = np.arange(ST)
        steps = ['Step '+str(st) for st in range(1,ST+1)]
        base = [0 for i in range(ST)]
        
        for r in range(1,R+1):
            ax1.bar(x_positions, 
                    Results['Size'].loc[idx[RES_Names[r],:],['Step '+str(s) for s in range(1,ST+1)]].values[0], 
                    color='#'+RES_Colors[r],
                    edgecolor= 'black',
                    label=RES_Names[r],
                    zorder = 3, 
                    bottom = base)
            base = [a+b for (a,b) in zip(base, Results['Size'].loc[idx[RES_Names[r],:],['Step '+str(s) for s in range(1,ST+1)]].values[0])]
        for g in range(1,G+1):
            ax1.bar(x_positions, 
                    Results['Size'].loc[idx[Generator_Names[g],:],['Step '+str(s) for s in range(1,ST+1)]].values[0], 
                    color='#'+Generator_Colors[g],
                    edgecolor= 'black',
                    label=Generator_Names[g],
                    zorder = 3, 
                    bottom = base)
            base = [a+b for (a,b) in zip(base, Results['Size'].loc[idx[Generator_Names[g],:],['Step '+str(s) for s in range(1,ST+1)]].values[0])]

        ax2.bar(x_positions, 
                Results['Size'].loc[idx['Battery bank',:],['Step '+str(s) for s in range(1,ST+1)]].values[0], 
                color='#'+BESS_Color,
                edgecolor= 'black',
                label='Battery bank',
                zorder = 3) 
    
        ax1.set_xlabel('Investment steps', fontsize=fontaxis)
        ax1.set_ylabel('Installed capacity [kW]', fontsize=fontaxis)
        ax2.set_xlabel('Investment steps', fontsize=fontaxis)
        ax2.set_ylabel('Installed capacity [kWh]', fontsize=fontaxis)
                            
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(steps, fontsize=fontticks)
        ax1.margins(x=0.009)
        ax2.set_xticks(x_positions)
        ax2.set_xticklabels(steps, fontsize=fontticks)
        ax2.margins(x=0.009)
            
        ax1.set_yticklabels(ax1.get_yticks(), fontsize=fontticks) 
        ax1.grid(True, axis='y', zorder=2)
        ax2.set_yticklabels(ax2.get_yticks(), fontsize=fontticks) 
        ax2.grid(True, axis='y', zorder=2)

    fig.legend(bbox_to_anchor=(1.19,0.98), ncol=1, fontsize=fontlegend, frameon=True)
    fig.tight_layout()    
    
    fig.savefig('Results/Plots/SizePlot.'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
