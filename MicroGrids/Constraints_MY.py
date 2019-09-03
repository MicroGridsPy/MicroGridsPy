"""
MicroGridsPy - Multi-year capacity-expansion (MYCE) 2018/2019
Based on the original model by Sergio Balderrama and Sylvain Quoilin
Authors: Giulia Guidicini, Lorenzo Rinaldi - Politecnico di Milano
"""

def Net_Present_Cost_Obj(model): 
    return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))
    

def Renewable_Energy(model,s,yt,ut,r,t): # Energy output of the solar panels
    return model.Total_Renewable_Energy[s,yt,r,t] == model.Renewable_Energy_Production[s,r,t]*model.Renewable_Inverter_Efficiency[r]*model.Renewable_Units[ut,r]


def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
    if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
        return model.State_Of_Charge_Battery[s,yt,t] == model.Battery_Nominal_Capacity[ut]*model.Battery_Initial_SOC - model.Energy_Battery_Flow_Out[s,yt,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[s,yt,t]*model.Charge_Battery_Efficiency
    if t==1 and yt!=1:
        return model.State_Of_Charge_Battery[s,yt,t] == model.State_Of_Charge_Battery[s,yt-1,model.Periods] - model.Energy_Battery_Flow_Out[s,yt,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[s,yt,t]*model.Charge_Battery_Efficiency
    else:  
        return model.State_Of_Charge_Battery[s,yt,t] == model.State_Of_Charge_Battery[s,yt,t-1] - model.Energy_Battery_Flow_Out[s,yt,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[s,yt,t]*model.Charge_Battery_Efficiency    


def Maximun_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
    return model.State_Of_Charge_Battery[s,yt,t] <= model.Battery_Nominal_Capacity[ut]


def Minimun_Charge(model,s,yt,ut,t): # Minimun state of charge
    return model.State_Of_Charge_Battery[s,yt,t] >= model.Battery_Nominal_Capacity[ut]*model.Depth_of_Discharge


def Max_Power_Battery_Charge(model,ut): 
    return model.Maximum_Charge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Charge_Time


def Max_Power_Battery_Discharge(model,ut):
    return model.Maximum_Discharge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Discharge_Time


def Max_Bat_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
    return model.Energy_Battery_Flow_In[s,yt,t] <= model.Maximum_Charge_Power[ut]*model.Delta_Time


def Max_Bat_out(model,s,yt,ut,t): #minimun flow of energy for the discharge fase
    return model.Energy_Battery_Flow_Out[s,yt,t] <= model.Maximum_Discharge_Power[ut]*model.Delta_Time


def Energy_balance(model,s,yt,ut,t): # Energy balance
    Foo = []
    for r in model.renewable_sources:
        Foo.append((s,yt,r,t))    
    Total_Renewable_Energy = sum(model.Total_Renewable_Energy[j] for j in Foo)    
    foo=[]
    for g in model.generator_types:
        foo.append((s,yt,g,t))    
    Total_Generator_Energy = sum(model.Total_Generator_Energy[i] for i in foo)  
    return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy + Total_Generator_Energy 
                                      - model.Energy_Battery_Flow_In[s,yt,t] + model.Energy_Battery_Flow_Out[s,yt,t] 
                                      + model.Lost_Load[s,yt,t] - model.Energy_Curtailment[s,yt,t])


def Maximun_Lost_Load(model,s,yt): # Maximum permissible lost load
    return model.Lost_Load_Probability >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))


def Maximun_Generator_Energy(model,s,yt,ut,g,t): # Maximun energy output of the diesel generator
    return model.Total_Generator_Energy[s,yt,g,t] <= model.Generator_Nominal_Capacity[ut,g]*model.Delta_Time


def Total_Fuel_Cost(model,s,g):
    Fuel_Cost_Tot = 0
    for y in range(1, model.Years +1):
        Num = sum(model.Total_Generator_Energy[s,y,g,t]*model.Generator_Marginal_Cost[s,y,g] for t in model.periods)
        Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
    return model.Total_Fuel_Cost[s,g] == Fuel_Cost_Tot
   
    
def Scenario_Lost_Load_Cost(model,s):    
    Cost_Lost_Load = 0         
    for y in range(1, model.Years +1):
        Num = sum(model.Lost_Load[s,y,t]*model.Value_Of_Lost_Load for t in model.periods)
        Cost_Lost_Load += Num/((1+model.Discount_Rate)**y)
    return  model.Scenario_Lost_Load_Cost[s] == Cost_Lost_Load
 
     
def Investment_Cost(model):  
    upgrade_years_list = [1 for i in range(len(model.upgrades))]
    s_dur = model.Step_Duration 
    for i in range(1, len(model.upgrades)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur  
    yu_tuples_list = [[] for i in model.years]  
    for y in model.years:      
        for i in range(len(upgrade_years_list)-1):
            if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                yu_tuples_list[y-1] = (y, model.upgrades[i+1])          
            elif y >= upgrade_years_list[-1]:
                yu_tuples_list[y-1] = (y, len(model.upgrades))            
    tup_list = [[] for i in range(len(model.upgrades)-1)]  
    for i in range(0, len(model.upgrades) - 1):
        tup_list[i] = yu_tuples_list[model.Step_Duration*i + model.Step_Duration]      
  
    Inv_Ren = sum((model.Renewable_Units[1,r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r])
                    + sum((((model.Renewable_Units[ut,r] - model.Renewable_Units[ut-1,r])*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r]*model.Renewable_Inv_Cost_Reduction[r]))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list) for r in model.renewable_sources)  
    Inv_Gen = sum((model.Generator_Nominal_Capacity[1,g]*model.Generator_Investment_Cost[g])
                    + sum((((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Investment_Cost[g]))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list) for g in model.generator_types)  
    Inv_Bat = ((model.Battery_Nominal_Capacity[1]*model.Battery_Investment_Cost)
                    + sum((((model.Battery_Nominal_Capacity[ut] - model.Battery_Nominal_Capacity[ut-1])*model.Battery_Investment_Cost))/((1+model.Discount_Rate)**(yt-1))
                    for (yt,ut) in tup_list))
    
    return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat



def Salvage_Value(model):   
    upgrade_years_list = [1 for i in range(len(model.upgrades))]
    s_dur = model.Step_Duration
    for i in range(1, len(model.upgrades)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur
    yu_tuples_list = [[] for i in model.years]
    for y in model.years:    
        for i in range(len(upgrade_years_list)-1):
            if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                yu_tuples_list[y-1] = (y, model.upgrades[i+1])        
            elif y >= upgrade_years_list[-1]:
                yu_tuples_list[y-1] = (y, len(model.upgrades))          
    tup_list = [[] for i in range(len(model.upgrades)-1)]
    for i in range(0, len(model.upgrades) - 1):
        tup_list[i] = yu_tuples_list[s_dur*i + s_dur]

    if model.Upgrades_Number == 1:    
        SV_Ren_1 = sum(model.Renewable_Units[1,r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_2 = 0 
        SV_Ren_3 = 0    
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
        SV_Gen_2 = 0
        SV_Gen_3 = 0

    if model.Upgrades_Number == 2:    
        yt_last_up = upgrade_years_list[1]       
        SV_Ren_1 = sum(model.Renewable_Units[1,r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_2 = sum((model.Renewable_Units[2,r]-model.Renewable_Units[1,r])*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]+(yt_last_up-1)-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
        SV_Ren_3 = 0    
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
        SV_Gen_2 = sum((model.Generator_Nominal_Capacity[2,g]-model.Generator_Nominal_Capacity[1,g])*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_3 = 0
        
    if model.Upgrades_Number > 2:
        tup_list_2 = [[] for i in range(len(model.upgrades)-2)]
        for i in range(len(model.upgrades) - 2):
            tup_list_2[i] = yu_tuples_list[s_dur*i + s_dur]
        yt_last_up = upgrade_years_list[-1]
        ut_last_up = tup_list[-1][1]    
        ut_seclast_up = tup_list[-2][1]

        SV_Ren_1 = sum(model.Renewable_Units[1,r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)    
        SV_Ren_2 = sum((model.Renewable_Units[ut_last_up,r] - model.Renewable_Units[ut_seclast_up,r])*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]+(yt_last_up-1)-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
        SV_Ren_3 = sum(sum((model.Renewable_Units[ut,r] - model.Renewable_Units[ut-1,r])*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r] * (model.Renewable_Lifetime[r]+(yt-1)-model.Years)/model.Renewable_Lifetime[r] / 
                       ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for r in model.renewable_sources)        
        SV_Gen_1 = sum(model.Generator_Nominal_Capacity[1,g]*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_2 = sum((model.Generator_Nominal_Capacity[ut_last_up,g] - model.Generator_Nominal_Capacity[ut_seclast_up,g])*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                       ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
        SV_Gen_3 = sum(sum((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt-1)-model.Years)/model.Generator_Lifetime[g] / 
                       ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for g in model.generator_types)
        
    return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3


def Operation_Maintenance_Cost(model):
    OyM_Ren = sum(sum((model.Renewable_Units[ut,r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Investment_Cost[r]*model.Renewable_Operation_Maintenance_Cost[r])/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.yu_tup)for r in model.renewable_sources)    
    OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Investment_Cost[g]*model.Generator_Operation_Maintenance_Cost[g])/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.yu_tup)for g in model.generator_types)
    OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Investment_Cost*model.Battery_Operation_Maintenance_Cost)/((
                    1+model.Discount_Rate)**yt)for (yt,ut) in model.yu_tup)
    return model.Operation_Maintenance_Cost == OyM_Ren + OyM_Gen + OyM_Bat


def Battery_Reposition_Cost(model,s):
    Battery_cost_in = [0 for y in model.years]
    Battery_cost_out = [0 for y in model.years]
    Battery_Yearly_cost = [0 for y in model.years]    
    for y in range(1,model.Years+1):    
        Battery_cost_in[y-1] = sum(model.Energy_Battery_Flow_In[s,y,t]*model.Unitary_Battery_Reposition_Cost for t in model.periods)
        Battery_cost_out[y-1] = sum(model.Energy_Battery_Flow_Out[s,y,t]*model.Unitary_Battery_Reposition_Cost for t in model.periods)
        Battery_Yearly_cost[y-1] = Battery_cost_in[y-1] + Battery_cost_out[y-1]
    return model.Battery_Reposition_Cost[s] == sum(Battery_Yearly_cost[y-1]/((1+model.Discount_Rate)**y) for y in model.years) 
    
    
def Scenario_Net_Present_Cost(model,s): 
    foo = []
    for g in range(1,model.Generator_Types+1):
            foo.append((s,g))            
    Fuel_Cost = sum(model.Total_Fuel_Cost[s,g] for s,g in foo)    
    return model.Scenario_Net_Present_Cost[s] == (model.Investment_Cost + model.Operation_Maintenance_Cost + model.Battery_Replacement_Cost[s] 
            + model.Scenario_Lost_Load_Cost[s] + Fuel_Cost - model.Salvage_Value)   

                
def Renewable_Energy_Penetration(model,ut):    
    upgrade_years_list = [1 for i in range(len(model.upgrades))]
    s_dur = model.Step_Duration
    for i in range(1, len(model.upgrades)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur
    yu_tuples_list = [0 for i in model.years]
    if model.Upgrades_Number == 1:
        for y in model.years:        
            yu_tuples_list[y-1] = (y, 1)
    else:    
        for y in model.years:        
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, model.upgrades[i+1])            
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, len(model.upgrades))       
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
            for r in range(1, model.Renewable_Sources+1):
                for t in range(1,model.Periods+1):
                    foo.append((s,y,r,t))        
    E_gen = sum(model.Total_Generator_Energy[s,y,g,t]*model.Scenario_Weight[s]
                for s,y,g,t in Foo)    
    E_ren = sum(model.Total_Renewable_Energy[s,y,r,t]*model.Scenario_Weight[s]
                for s,y,r,t in foo)        
    return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*E_gen   

    
def Battery_Min_Capacity(model,ut):    
    return   model.Battery_Nominal_Capacity[ut] >= model.Battery_Min_Capacity[ut]


def Battery_Min_Step_Capacity(model,yt,ut):    
    if ut > 1:
        return model.Battery_Nominal_Capacity[ut] >= model.Battery_Nominal_Capacity[ut-1]
    elif ut == 1:
        return model.Battery_Nominal_Capacity[ut] == model.Battery_Nominal_Capacity[ut]
    
    
def Renewables_Min_Step_Units(model,yt,ut,r):
    if ut > 1:
        return model.Renewable_Units[ut,r] >= model.Renewable_Units[ut-1,r]
    elif ut == 1:
        return model.Renewable_Units[ut,r] == model.Renewable_Units[ut,r]
    
    
def Generator_Min_Step_Capacity(model,yt,ut,g):
    if ut > 1:
        return model.Generator_Nominal_Capacity[ut,g] >= model.Generator_Nominal_Capacity[ut-1,g]
    elif ut ==1:
        return model.Generator_Nominal_Capacity[ut,g] == model.Generator_Nominal_Capacity[ut,g]


def Scenario_Variable_Cost(model, s):
    foo = []
    for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
    Fuel_Cost = sum(model.Total_Fuel_Cost[s,g] for s,g in foo)    
    return model.Total_Scenario_Variable_Cost[s] == model.Operation_Maintenance_Cost + model.Battery_Replacement_Cost[s] + model.Scenario_Lost_Load_Cost[s] + Fuel_Cost


def Total_Variable_Cost(model):
    return model.Total_Variable_Cost == (sum(model.Total_Scenario_Variable_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))


def Battery_Replacement(model,s):
        
    Battery_Replacement_Cost = 0    
    years_list = [i for i in model.years]
    years_to_remove = []
    
    for ut in model.upgrades:
        Delta_SOC = 0
        if ut != 1:
            for (y,u) in model.yu_tup:
                if u != ut:
                    years_to_remove += [y]
        years_list = list(set(years_list).difference(set(years_to_remove)))
        
        for yt in years_list:
            for t in range(1, model.Periods+1):

                if t==1 and yt==1: 
                    Delta_SOC = 0
                if t==1 and yt!=1:
                    if ut ==1:
                        Delta_SOC += (model.State_Of_Charge_Battery[s,yt,t] - model.State_Of_Charge_Battery[s,yt-1,model.Periods])/model.Battery_Nominal_Capacity[ut]
                    else:
                        Delta_SOC += (model.State_Of_Charge_Battery[s,yt,t] - model.State_Of_Charge_Battery[s,yt-1,model.Periods])/(model.Battery_Nominal_Capacity[ut]-model.Battery_Nominal_Capacity[ut-1])
                if t!=1:  
                    if ut ==1:
                        Delta_SOC += (model.State_Of_Charge_Battery[s,yt,t] - model.State_Of_Charge_Battery[s,yt,t-1])/model.Battery_Nominal_Capacity[ut]
                    else:
                        Delta_SOC += (model.State_Of_Charge_Battery[s,yt,t] - model.State_Of_Charge_Battery[s,yt,t-1])/(model.Battery_Nominal_Capacity[ut]-model.Battery_Nominal_Capacity[ut-1])    
                
                if Delta_SOC >= (model.Battery_Cycles*2*(1-model.Depth_of_Discharge)):    
                    Battery_Replacement_Cost += model.Battery_Nominal_Capacity[ut] * (model.Battery_Investment_Cost - model.Battery_Electronic_Investment_Cost) / ((1+model.Discount_Rate)**yt)
                    Delta_SOC = 0
                    
    return model.Battery_Replacement_Cost[s] == Battery_Replacement_Cost