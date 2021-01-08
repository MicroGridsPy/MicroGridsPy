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


#%% Economic constraints

"Objective function"
def Net_Present_Cost_Obj(model): 
    return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))

def Total_Variable_Cost_Obj(model):
    return (sum(model.Total_Scenario_Variable_Cost_NonAct[s]*model.Scenario_Weight[s] for s in model.scenarios))


"Net Present Cost"
def Net_Present_Cost(model):   
    return model.Net_Present_Cost == (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))

# def Scenario_Net_Present_Cost(model,s): 
#     foo = []
#     for g in range(1,model.Generator_Types+1):
#             foo.append((s,g))            
#     Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)    
#     return model.Scenario_Net_Present_Cost[s] == (model.Investment_Cost + model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] 
#             + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost - model.Salvage_Value)   

def Scenario_Net_Present_Cost(model,s): 
    return model.Scenario_Net_Present_Cost[s] == (model.Investment_Cost + model.Total_Scenario_Variable_Cost_Act[s] - model.Salvage_Value)   


"Investment cost"
def Investment_Cost(model):  
    upgrade_years_list = [1 for i in range(len(model.steps))]
    s_dur = model.Step_Duration 
    for i in range(1, len(model.steps)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur  
    yu_tuples_list = [[] for i in model.years]  
    for y in model.years:      
        for i in range(len(upgrade_years_list)-1):
            if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                yu_tuples_list[y-1] = (y, model.steps[i+1])          
            elif y >= upgrade_years_list[-1]:
                yu_tuples_list[y-1] = (y, len(model.steps))            
    tup_list = [[] for i in range(len(model.steps)-1)]  
    for i in range(0, len(model.steps) - 1):
        tup_list[i] = yu_tuples_list[model.Step_Duration*i + model.Step_Duration]      
  
    Inv_Ren = sum((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r])
                    + sum((((model.RES_Units[ut,r] - model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list) for r in model.renewable_sources)  
    Inv_Gen = sum((model.Generator_Nominal_Capacity[1,g]*model.Generator_Specific_Investment_Cost[g])
                    + sum((((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Specific_Investment_Cost[g]))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list) for g in model.generator_types)  
    Inv_Bat = ((model.Battery_Nominal_Capacity[1]*model.Battery_Specific_Investment_Cost)
                    + sum((((model.Battery_Nominal_Capacity[ut] - model.Battery_Nominal_Capacity[ut-1])*model.Battery_Specific_Investment_Cost))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list))
    return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat

def Investment_Cost_Limit(model):
    return model.Investment_Cost <= model.Investment_Cost_Limit
   

"Fixed O&M costs"
def Operation_Maintenance_Cost_Act(model):
    OyM_Ren = sum(sum((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
    OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for g in model.generator_types)
    OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)
    return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen + OyM_Bat


def Operation_Maintenance_Cost_NonAct(model):
    OyM_Ren = sum(sum((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])
                    for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
    OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])
                    for (yt,ut) in model.years_steps)for g in model.generator_types)
    OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)
                    for (yt,ut) in model.years_steps)
    return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen + OyM_Bat


"Variable costs"
def Total_Variable_Cost_Act(model):
    return model.Total_Variable_Cost_Act == (sum(model.Total_Scenario_Variable_Cost_Act[s]*model.Scenario_Weight[s] for s in model.scenarios))

def Scenario_Variable_Cost_Act(model, s):
    foo = []
    for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
    Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)    
    return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost

def Scenario_Variable_Cost_NonAct(model, s):
    foo = []
    for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
    Fuel_Cost = sum(model.Total_Fuel_Cost_NonAct[s,g] for s,g in foo)    
    return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost

def Scenario_Lost_Load_Cost_Act(model,s):    
    Cost_Lost_Load = 0         
    for y in range(1, model.Years +1):
        Num = sum(model.Lost_Load[s,y,t]*model.Lost_Load_Specific_Cost for t in model.periods)
        Cost_Lost_Load += Num/((1+model.Discount_Rate)**y)
    return  model.Scenario_Lost_Load_Cost_Act[s] == Cost_Lost_Load

def Scenario_Lost_Load_Cost_NonAct(model,s):
    Cost_Lost_Load = 0         
    for y in range(1, model.Years +1):
        Num = sum(model.Lost_Load[s,y,t]*model.Lost_Load_Specific_Cost for t in model.periods)
        Cost_Lost_Load += Num
    return  model.Scenario_Lost_Load_Cost_NonAct[s] == Cost_Lost_Load

def Total_Fuel_Cost_Act(model,s,g):
    Fuel_Cost_Tot = 0
    for y in range(1, model.Years +1):
        Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[s,y,g] for t in model.periods)
        Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
    return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
   
def Total_Fuel_Cost_NonAct(model,s,g):
    Fuel_Cost_Tot = 0
    for y in range(1, model.Years +1):
        Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[s,y,g] for t in model.periods)
        Fuel_Cost_Tot += Num
    return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot

def Battery_Replacement_Cost_Act(model,s):
    Battery_cost_in = [0 for y in model.years]
    Battery_cost_out = [0 for y in model.years]
    Battery_Yearly_cost = [0 for y in model.years]    
    for y in range(1,model.Years+1):    
        Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
        Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
        Battery_Yearly_cost[y-1] = Battery_cost_in[y-1] + Battery_cost_out[y-1]
    return model.Battery_Replacement_Cost_Act[s] == sum(Battery_Yearly_cost[y-1]/((1+model.Discount_Rate)**y) for y in model.years) 
    
def Battery_Replacement_Cost_NonAct(model,s):
    Battery_cost_in = [0 for y in model.years]
    Battery_cost_out = [0 for y in model.years]
    Battery_Yearly_cost = [0 for y in model.years]    
    for y in range(1,model.Years+1):    
        Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
        Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
        Battery_Yearly_cost[y-1] = Battery_cost_in[y-1] + Battery_cost_out[y-1]
    return model.Battery_Replacement_Cost_NonAct[s] == sum(Battery_Yearly_cost[y-1] for y in model.years) 


"Salvage Value"
def Salvage_Value(model):   
    upgrade_years_list = [1 for i in range(len(model.steps))]
    s_dur = model.Step_Duration
    for i in range(1, len(model.steps)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur
    yu_tuples_list = [[] for i in model.years]
    for y in model.years:    
        for i in range(len(upgrade_years_list)-1):
            if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                yu_tuples_list[y-1] = (y, model.steps[i+1])        
            elif y >= upgrade_years_list[-1]:
                yu_tuples_list[y-1] = (y, len(model.steps))          
    tup_list = [[] for i in range(len(model.steps)-1)]
    for i in range(0, len(model.steps) - 1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]

    if model.Steps_Number == 1:    
        SV_Ren_1 = sum(model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_2 = 0 
        SV_Ren_3 = 0    
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
        SV_Gen_2 = 0
        SV_Gen_3 = 0

    if model.Steps_Number == 2:    
        yt_last_up = upgrade_years_list[1]       
        SV_Ren_1 = sum(model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_2 = sum((model.RES_Units[2,r]-model.RES_Units[1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_3 = 0    
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
        SV_Gen_2 = sum((model.Generator_Nominal_Capacity[2,g]-model.Generator_Nominal_Capacity[1,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_3 = 0
        
    if model.Steps_Number > 2:
        tup_list_2 = [[] for i in range(len(model.steps)-2)]
        for i in range(len(model.steps) - 2):
            tup_list_2[i] = yu_tuples_list[s_dur*i + s_dur]
        yt_last_up = upgrade_years_list[-1]
        ut_last_up = tup_list[-1][1]    
        ut_seclast_up = tup_list[-2][1]

        SV_Ren_1 = sum(model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)    
        SV_Ren_2 = sum((model.RES_Units[ut_last_up,r] - model.RES_Units[ut_seclast_up,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
        SV_Ren_3 = sum(sum((model.RES_Units[ut,r] - model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt-1)-model.Years)/model.RES_Lifetime[r] / 
                        ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for r in model.renewable_sources)        
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_2 = sum((model.Generator_Nominal_Capacity[ut_last_up,g] - model.Generator_Nominal_Capacity[ut_seclast_up,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                        ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_3 = sum(sum((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt-1)-model.Years)/model.Generator_Lifetime[g] / 
                        ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for g in model.generator_types)
    return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3


#%% Electricity balance constraints
def Energy_balance(model,s,yt,ut,t): # Energy balance
    Foo = []
    for r in model.renewable_sources:
        Foo.append((s,yt,r,t))    
    Total_Renewable_Energy = sum(model.RES_Energy_Production[j] for j in Foo)    
    foo=[]
    for g in model.generator_types:
        foo.append((s,yt,g,t))    
    Total_Generator_Energy = sum(model.Generator_Energy_Production[i] for i in foo)  
    return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy + Total_Generator_Energy 
                                      - model.Battery_Inflow[s,yt,t] + model.Battery_Outflow[s,yt,t] 
                                      + model.Lost_Load[s,yt,t] - model.Energy_Curtailment[s,yt,t])


"Renewable Energy Sources constraints"
def Renewable_Energy(model,s,yt,ut,r,t): # Energy output of the solar panels
    return model.RES_Energy_Production[s,yt,r,t] == model.RES_Unit_Energy_Production[s,r,t]*model.RES_Inverter_Efficiency[r]*model.RES_Units[ut,r]

def Renewable_Energy_Penetration(model,ut):    
    upgrade_years_list = [1 for i in range(len(model.steps))]
    s_dur = model.Step_Duration
    for i in range(1, len(model.steps)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur
    yu_tuples_list = [0 for i in model.years]
    if model.Steps_Number == 1:
        for y in model.years:        
            yu_tuples_list[y-1] = (y, 1)
    else:    
        for y in model.years:        
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, model.steps[i+1])            
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, len(model.steps))       
    years_list = []
    for i in yu_tuples_list:
        if i[1]==ut:
            years_list += [i[0]]            
    Foo=[]
    for s in range(1, model.Scenarios + 1):
        for y in years_list:
            for g in range(1, model.Generator_Types+1):
                for t in range(1,model.Periods+1):
                    Foo.append((s,y,g,t))                        
    foo=[]
    for s in range(1, model.Scenarios + 1):
        for y in years_list:
            for r in range(1, model.RES_Sources+1):
                for t in range(1,model.Periods+1):
                    foo.append((s,y,r,t))        
    E_gen = sum(model.Generator_Energy_Production[s,y,g,t]*model.Scenario_Weight[s]
                for s,y,g,t in Foo)    
    E_ren = sum(model.RES_Energy_Production[s,y,r,t]*model.Scenario_Weight[s]
                for s,y,r,t in foo)        
    return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*E_gen   

def Renewables_Min_Step_Units(model,yt,ut,r):
    if ut > 1:
        return model.RES_Units[ut,r] >= model.RES_Units[ut-1,r]
    elif ut == 1:
        return model.RES_Units[ut,r] == model.RES_Units[ut,r]


"Battery Energy Storage constraints"
def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
    if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
        return model.Battery_SOC[s,yt,t] == model.Battery_Nominal_Capacity[ut]*model.Battery_Initial_SOC - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
    if t==1 and yt!=1:
        return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt-1,model.Periods] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
    else:  
        return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt,t-1] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency    

def Maximun_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
    return model.Battery_SOC[s,yt,t] <= model.Battery_Nominal_Capacity[ut]

def Minimun_Charge(model,s,yt,ut,t): # Minimun state of charge
    return model.Battery_SOC[s,yt,t] >= model.Battery_Nominal_Capacity[ut]*model.Battery_Depth_of_Discharge

def Max_Power_Battery_Charge(model,ut): 
    return model.Battery_Maximum_Charge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Charge_Time

def Max_Power_Battery_Discharge(model,ut):
    return model.Battery_Maximum_Discharge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Discharge_Time

def Max_Bat_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
    return model.Battery_Inflow[s,yt,t] <= model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time

def Max_Bat_out(model,s,yt,ut,t): # Minimum flow of energy for the discharge fase
    return model.Battery_Outflow[s,yt,t] <= model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
def Battery_Min_Capacity(model,ut):    
    return   model.Battery_Nominal_Capacity[ut] >= model.Battery_Min_Capacity[ut]

def Battery_Min_Step_Capacity(model,yt,ut):    
    if ut > 1:
        return model.Battery_Nominal_Capacity[ut] >= model.Battery_Nominal_Capacity[ut-1]
    elif ut == 1:
        return model.Battery_Nominal_Capacity[ut] == model.Battery_Nominal_Capacity[ut]
    

"Diesel generator constraints"
def Maximun_Generator_Energy(model,s,yt,ut,g,t): # Maximum energy output of the diesel generator
    return model.Generator_Energy_Production[s,yt,g,t] <= model.Generator_Nominal_Capacity[ut,g]*model.Delta_Time

def Generator_Min_Step_Capacity(model,yt,ut,g):
    if ut > 1:
        return model.Generator_Nominal_Capacity[ut,g] >= model.Generator_Nominal_Capacity[ut-1,g]
    elif ut ==1:
        return model.Generator_Nominal_Capacity[ut,g] == model.Generator_Nominal_Capacity[ut,g]


"Lost load constraints"
def Maximun_Lost_Load(model,s,yt): # Maximum admittable lost load
    return model.Lost_Load_Fraction >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))






 
     






    
                

    
    
    
    





