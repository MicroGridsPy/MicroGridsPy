import re
import os

##############################################################################################################################################################
###################################################################### LP FORMULATION ########################################################################
##############################################################################################################################################################

#%%
# --- Greenfield ---

class Constraints_Greenfield():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
    Data_import = open(data_file_path).readlines()
    for i in range(len(Data_import)):
        if "param: Fuel_Specific_Cost_Calculation" in Data_import[i]:      
            Fuel_Specific_Cost_Calculation = int((re.findall('\d+',Data_import[i])[0]))
        
    "Objective function"
    def Net_Present_Cost_Obj(model): 
        return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission_Obj(model):
        return (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
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
    
    def Total_Variable_Cost(model):
        return model.Total_Variable_Cost == (sum(model.Total_Scenario_Variable_Cost_NonAct[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Net_Present_Cost(model,s): 
        return model.Scenario_Net_Present_Cost[s] == (model.Investment_Cost + model.Total_Scenario_Variable_Cost_Act[s] - model.Salvage_Value)   
    
    def CO2_emission(model):
        return model.CO2_emission == (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_CO2_emission(model,s):
        if model.Grid_Connection == 1:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission + model.Scenario_GRID_emission[s])
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
        else:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission)
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s])

        
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
        
        if model.Model_Components == 0:
            return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat    
        if model.Model_Components == 1:
            return model.Investment_Cost == Inv_Ren + Inv_Bat      
        if model.Model_Components == 2:
            return model.Investment_Cost == Inv_Ren + Inv_Gen     
    
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
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen 
    
    def Operation_Maintenance_Cost_NonAct(model):
        OyM_Ren = sum(sum((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])
                        for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
        OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])
                        for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)
                        for (yt,ut) in model.years_steps)
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen 
    
    "Variable costs"
    def Total_Variable_Cost_Act(model):
        return model.Total_Variable_Cost_Act == (sum(model.Total_Scenario_Variable_Cost_Act[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Variable_Cost_Act(model, s):
        foo = []
        for g in range(1,model.Generator_Types+1):
                foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)   
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_Act[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_Act[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
            
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
    def Scenario_Variable_Cost_NonAct(model, s): 
        foo = []
        for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_NonAct[s,g] for s,g in foo)  
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_NonAct[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_NonAct[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
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
    
    if Fuel_Specific_Cost_Calculation == 0:
        def Total_Fuel_Cost_Act(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
                Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
            return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
        
        def Total_Fuel_Cost_NonAct(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
                Fuel_Cost_Tot += Num
            return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    else:
        def Total_Fuel_Cost_Act(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
                Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
            return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
        
        def Total_Fuel_Cost_NonAct(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
                Fuel_Cost_Tot += Num
            return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot

    
    def Total_Electricity_Cost_Act(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Num = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
                Electricity_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Electricity_Cost_Act[s] == Electricity_Cost_Tot
       
    def Total_Electricity_Cost_NonAct(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Electricity_Cost_Tot += sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
        return model.Total_Electricity_Cost_NonAct[s] == Electricity_Cost_Tot
    
    
    def Total_Revenues_NonAct(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_NonAct[s] == sum(Revenues_Yearly[y - 1] for y in model.years)

    def Total_Revenues_Act(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_Act[s] == sum(Revenues_Yearly[y - 1] / ((1 + model.Discount_Rate) ** y) for y in model.years)
    
    def Battery_Replacement_Cost_Act(model,s):
        Battery_cost_in = [0 for y in model.years]
        Battery_cost_out = [0 for y in model.years]
        Battery_Yearly_cost = [0 for y in model.years]    
        for y in range(1,model.Years+1):    
            Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_Yearly_cost[y-1] = Battery_cost_out[y-1] + Battery_cost_in[y-1]
        return model.Battery_Replacement_Cost_Act[s] == sum(Battery_Yearly_cost[y-1]/((1+model.Discount_Rate)**y) for y in model.years) 
        
    def Battery_Replacement_Cost_NonAct(model,s):
        Battery_cost_in = [0 for y in model.years]
        Battery_cost_out = [0 for y in model.years]
        Battery_Yearly_cost = [0 for y in model.years]    
        for y in range(1,model.Years+1):    
            Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_Yearly_cost[y-1] = Battery_cost_out[y-1] + Battery_cost_in[y-1]
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
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection))
          
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
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
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
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
            
        if model.Model_Components == 0 or model.Model_Components == 2:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3 + SV_Grid 
        if model.Model_Components == 1:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Ren_2 + SV_Ren_3 + SV_Grid 
    
    def Energy_balance(model,s,yt,ut,t): # Energy balance
        Foo = []
        for r in model.renewable_sources:
            Foo.append((s,yt,r,t))    
        Total_Renewable_Energy = sum(model.RES_Energy_Production[j] for j in Foo)    
        foo=[]
        for g in model.generator_types:
            foo.append((s,yt,g,t))    
        Total_Generator_Energy = sum(model.Generator_Energy_Production[i] for i in foo)
        if model.Grid_Connection == 1:
            En_From_Grid = model.Energy_From_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            if model.Grid_Connection_Type == 0:
                En_To_Grid = model.Energy_To_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            else: En_To_Grid = 0
        else:
            En_From_Grid = 0
            En_To_Grid = 0
       
        if model.Model_Components == 0:
           return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Battery_Outflow[s,yt,t]
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 1:
           return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Battery_Outflow[s,yt,t]
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 2:
           return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
    
    
    "Renewable Energy Sources constraints"
    def Renewable_Energy(model,s,yt,ut,r,t): # Energy output of the RES
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
        goo=[]
        for s in range(1, model.Scenarios + 1):
            for y in years_list:
                    for t in range(1,model.Periods+1):
                        goo.append((s,y,t))
                        
        E_gen = sum(model.Generator_Energy_Production[s,y,g,t]*model.Scenario_Weight[s]
                    for s,y,g,t in Foo)
        E_ren = sum(model.RES_Energy_Production[s,y,r,t]*model.Scenario_Weight[s]
                    for s,y,r,t in foo)
        if model.Grid_Connection == 1:
            E_From_Grid = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Scenario_Weight[s]
                    for s,y,t in goo)
        else: E_From_Grid = 0
 
        return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*(E_gen + E_From_Grid)
    
    def Renewables_Min_Step_Units(model,yt,ut,r):
        if ut > 1:
            return model.RES_Units[ut,r] >= model.RES_Units[ut-1,r]
        elif ut == 1:
            return model.RES_Units[ut,r] == model.RES_Units[ut,r]
    
    "Maximum land use constraint for Renewables"
    def Renewables_Max_Land_Use(model,ut):
        return (sum((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r]*(model.RES_Specific_Area[r]/1000)) for r in model.renewable_sources)) <= model.Renewables_Total_Area
    
    "Battery Energy Storage constraints"
    def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
        if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
            return model.Battery_SOC[s,yt,t] == model.Battery_Nominal_Capacity[ut]*model.Battery_Initial_SOC - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        if t==1 and yt!=1:
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt-1,model.Periods] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        else:  
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt,t-1] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency    
    
    def Maximum_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
        return model.Battery_SOC[s,yt,t] <= model.Battery_Nominal_Capacity[ut]
    
    def Minimum_Charge(model,s,yt,ut,t): # Minimun state of charge
        return model.Battery_SOC[s,yt,t] >= model.Battery_Nominal_Capacity[ut]*(1-model.Battery_Depth_of_Discharge)
    
    def Max_Power_Battery_Charge(model,ut): 
        return model.Battery_Maximum_Charge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Charge_Time
    
    def Max_Power_Battery_Discharge(model,ut):
        return model.Battery_Maximum_Discharge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Discharge_Time
    
    def Max_Bat_flow_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
        return model.Battery_Inflow[s,yt,t] <= model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
    
    def Max_Bat_flow_out(model,s,yt,ut,t): # Minimun flow of energy for the discharge fase
        return model.Battery_Outflow[s,yt,t] <= model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
    def Max_Bat_out(model,s,yt,ut,t):
        return model.Battery_Outflow[s,yt,t] <= model.Energy_Demand[s,yt,t]
        
    def Battery_Min_Capacity(model,ut):    
        return   model.Battery_Nominal_Capacity[ut] >= model.Battery_Min_Capacity[ut]
    
    def Battery_Min_Step_Capacity(model,yt,ut):    
        if ut > 1:
            return model.Battery_Nominal_Capacity[ut] >= model.Battery_Nominal_Capacity[ut-1]
        elif ut == 1:
            return model.Battery_Nominal_Capacity[ut] == model.Battery_Nominal_Capacity[ut]
    
    def Battery_Single_Flow_Discharge(model,s,yt,ut,t):
        return   model.Battery_Outflow[s,yt,t] <= model.Single_Flow_BESS[s,yt,t]*model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
    def Battery_Single_Flow_Charge(model,s,yt,ut,t):
        return   model.Battery_Inflow[s,yt,t] <= (1-model.Single_Flow_BESS[s,yt,t])*model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time

    
    "Diesel generator constraints"
    def Maximum_Generator_Energy_1(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Production[s,yt,g,t] <= model.Generator_Nominal_Capacity[ut,g]*model.Delta_Time
    
    def Maximum_Generator_Energy_2(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Production[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
    def Generator_Min_Step_Capacity(model,yt,ut,g):
        if ut > 1:
            return model.Generator_Nominal_Capacity[ut,g] >= model.Generator_Nominal_Capacity[ut-1,g]
        elif ut ==1:
            return model.Generator_Nominal_Capacity[ut,g] == model.Generator_Nominal_Capacity[ut,g]
    
    "Lost load constraints"
    def Maximum_Lost_Load(model,s,yt): # Maximum admittable lost load
        return model.Lost_Load_Fraction >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))
    
    "Emission constraints"
    def RES_emission(model): #LCA emissions of RES
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
            
        return model.RES_emission == sum(model.RES_unit_CO2_emission[r]*model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]/1e3 for r in model.renewable_sources)+sum(sum(model.RES_unit_CO2_emission[r]*(model.RES_Units[ut,r]-model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]/1e3 for (yt,ut) in tup_list) for r in model.renewable_sources)
    
    def GEN_emission(model): #LCA emissions of generator
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
            
        return model.GEN_emission == sum(model.Generator_Nominal_Capacity[1,g]/1e3*model.GEN_unit_CO2_emission[g] for g in model.generator_types)+sum(sum((model.Generator_Nominal_Capacity[ut,g]-model.Generator_Nominal_Capacity[ut-1,g])/1e3*model.GEN_unit_CO2_emission[g] for (yt,ut) in tup_list) for g in model.generator_types)
    
    def FUEL_emission(model,s,yt,ut,g,t): #Emissions from fuel consumption
        return model.FUEL_emission[s,yt,g,t] == model.Generator_Energy_Production[s,yt,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g] 
    
    def GRID_emission(model, s, y, t):
        if y >= model.Year_Grid_Connection:
            return model.GRID_emission[s,y,t] == model.Energy_From_Grid[s,y,t] * model.National_Grid_Specific_CO2_emissions/1e3
        else:
            return model.GRID_emission[s, y, t] == 0
     
    def BESS_emission(model): #LCA emissions of battery
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
            
        return model.BESS_emission == model.Battery_Nominal_Capacity[1]/1e3*model.BESS_unit_CO2_emission+sum((model.Battery_Nominal_Capacity[ut]-model.Battery_Nominal_Capacity[ut-1])/1e3*model.BESS_unit_CO2_emission for (yt,ut) in tup_list)
        
    def Scenario_FUEL_emission(model,s): 
        return model.Scenario_FUEL_emission[s] == sum(sum(sum(model.Generator_Energy_Production[s,y,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g]  for t in model.periods) for y in model.years) for g in model.generator_types) 
    
    def Scenario_GRID_emission(model, s):
        Total_Grid_Emission = 0
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Total_Grid_Emission += sum(model.Energy_From_Grid[s, y, t] * model.National_Grid_Specific_CO2_emissions / 1e3 for t in model.periods)
        return model.Scenario_GRID_emission[s] == Total_Grid_Emission
    
    "Grid constraints" 
    def Maximum_Power_From_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_From_Grid[s,y,t] == 0
        else:
            return model.Energy_From_Grid[s,y,t] <= model.Maximum_Grid_Power*1000 
    
    def Maximum_Power_To_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Connection_Type == 1 or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_To_Grid[s, y, t] == 0
        elif model.Grid_Connection_Type == 0:
            return model.Energy_To_Grid[s, y, t] <= model.Maximum_Grid_Power*1000
        
    def Single_Flow_Energy_To_Grid(model,s,yt,ut,t):
        return model.Energy_To_Grid[s,yt,t] <= model.Single_Flow_Grid[s,yt,t]*model.Large_Constant
        
    def Single_Flow_Energy_From_Grid(model,s,yt,ut,t):
        return model.Energy_From_Grid[s,yt,t] <= (1-model.Single_Flow_Grid[s,yt,t])*model.Large_Constant
     
#%% 
# --- Brownfield ---

class Constraints_Brownfield():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
    Data_import = open(data_file_path).readlines()
    for i in range(len(Data_import)):
        if "param: Fuel_Specific_Cost_Calculation" in Data_import[i]:      
            Fuel_Specific_Cost_Calculation = int((re.findall('\d+',Data_import[i])[0]))
    
    "Objective function"
    def Net_Present_Cost_Obj(model): 
        return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission_Obj(model):
        return (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
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
    
    def Total_Variable_Cost(model):
        return model.Total_Variable_Cost == (sum(model.Total_Scenario_Variable_Cost_NonAct[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission(model):
        return model.CO2_emission == (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_CO2_emission(model,s):
        if model.Grid_Connection == 1:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission + model.Scenario_GRID_emission[s])
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
        else:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission)
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s])
    
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
          
        Inv_Ren = sum(((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r]-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r])
                        + sum((((model.RES_Units[ut,r] - model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for r in model.renewable_sources)  
        Inv_Gen = sum(((model.Generator_Nominal_Capacity[1,g]-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g])
                        + sum((((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Specific_Investment_Cost[g]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for g in model.generator_types)
        Inv_Bat = (((model.Battery_Nominal_Capacity[1]-model.Battery_capacity)*model.Battery_Specific_Investment_Cost)
                        + sum((((model.Battery_Nominal_Capacity[ut] - model.Battery_Nominal_Capacity[ut-1])*model.Battery_Specific_Investment_Cost))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list))
        
        if model.Model_Components == 0:
            return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat 
        if model.Model_Components == 1:
            return model.Investment_Cost == Inv_Ren + Inv_Bat 
        if model.Model_Components == 2:
            return model.Investment_Cost == Inv_Ren + Inv_Gen 
    
    def Investment_Cost_Limit(model):
        return model.Investment_Cost <= model.Investment_Cost_Limit
    
    "Fixed O&M costs"
    def Operation_Maintenance_Cost_Act(model):
        OyM_Ren = sum(sum(((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r])*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
        OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen 
    
    
    def Operation_Maintenance_Cost_NonAct(model):
        OyM_Ren = sum(sum(((model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r])*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])
                        for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
        OyM_Gen = sum(sum((model.Generator_Nominal_Capacity[ut,g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])
                        for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Nominal_Capacity[ut]*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)
                        for (yt,ut) in model.years_steps)
       
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen 
    
    
    "Variable costs"
    def Total_Variable_Cost_Act(model):
        return model.Total_Variable_Cost_Act == (sum(model.Total_Scenario_Variable_Cost_Act[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Variable_Cost_Act(model, s):
        foo = []
        for g in range(1,model.Generator_Types+1):
                foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)    
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_Act[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_Act[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0    
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues     
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Electricity_Cost - Electricity_Revenues     
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues     
    
    def Scenario_Variable_Cost_NonAct(model, s):
        foo = []
        for g in range(1,model.Generator_Types+1):
                foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_NonAct[s,g] for s,g in foo)    
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_NonAct[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_NonAct[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0     
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues 
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Electricity_Cost - Electricity_Revenues 
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues 
    
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
    
    if Fuel_Specific_Cost_Calculation == 0:
        def Total_Fuel_Cost_Act(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
                Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
            return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
        
        def Total_Fuel_Cost_NonAct(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
                Fuel_Cost_Tot += Num
            return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    else:
        def Total_Fuel_Cost_Act(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
                Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
            return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
        
        def Total_Fuel_Cost_NonAct(model,s,g):
            Fuel_Cost_Tot = 0
            for y in range(1, model.Years +1):
                Num = sum(model.Generator_Energy_Production[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
                Fuel_Cost_Tot += Num
            return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot

    def Total_Electricity_Cost_Act(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Num = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
                Electricity_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Electricity_Cost_Act[s] == Electricity_Cost_Tot
       
    def Total_Electricity_Cost_NonAct(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Electricity_Cost_Tot += sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
        return model.Total_Electricity_Cost_NonAct[s] == Electricity_Cost_Tot
    
    
    def Total_Revenues_NonAct(model,s): 
        Revenues_Yearly = [0 for y in model.years]
        for y in range(1, model.Years +1):
            Revenues_Yearly[y-1] = sum(model.Energy_To_Grid[s,y,t]*model.Grid_Availability[s,y,t] * model.Grid_Sold_El_Price/1000 for t in model.periods)
        return model.Total_Revenues_NonAct [s] == sum(Revenues_Yearly[y-1] for y in model.years)
    
    def Total_Revenues_Act(model,s): 
        Revenues_Yearly = [0 for y in model.years]
        for y in range(1,model.Years+1):
            Revenues_Yearly [y-1] = sum(model.Energy_To_Grid[s,y,t]*model.Grid_Availability[s,y,t] * model.Grid_Sold_El_Price/1000 for t in model.periods)
        return model.Total_Revenues_Act [s] == sum(Revenues_Yearly[y-1]/((1+model.Discount_Rate)**y)  for y in model.years)
    
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
            SV_Ren_1 = sum(((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum((model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_2 = 0 
            SV_Ren_3 = 0    
            SV_Gen_1 = sum((model.Generator_Nominal_Capacity[1,g]-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
            SV_Gen_2 = 0
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
    
        if model.Steps_Number == 2:    
            yt_last_up = upgrade_years_list[1]       
            SV_Ren_1 = sum(((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum((model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
            SV_Ren_2 = sum((model.RES_Units[2,r]-model.RES_Units[1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_3 = 0    
            SV_Gen_1 = sum((model.Generator_Nominal_Capacity[1,g]-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
            SV_Gen_2 = sum((model.Generator_Nominal_Capacity[2,g]-model.Generator_Nominal_Capacity[1,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
            
        if model.Steps_Number > 2:
            tup_list_2 = [[] for i in range(len(model.steps)-2)]
            for i in range(len(model.steps) - 2):
                tup_list_2[i] = yu_tuples_list[s_dur*i + s_dur]
            yt_last_up = upgrade_years_list[-1]
            ut_last_up = tup_list[-1][1]    
            ut_seclast_up = tup_list[-2][1]
    
            SV_Ren_1 = sum(((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum(model.RES_capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)    
            SV_Ren_2 = sum((model.RES_Units[ut_last_up,r] - model.RES_Units[ut_seclast_up,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
            SV_Ren_3 = sum(sum((model.RES_Units[ut,r] - model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for r in model.renewable_sources)        
            SV_Gen_1 = sum((model.Generator_Nominal_Capacity[1,g]-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_2 = sum((model.Generator_Nominal_Capacity[ut_last_up,g] - model.Generator_Nominal_Capacity[ut_seclast_up,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = sum(sum((model.Generator_Nominal_Capacity[ut,g] - model.Generator_Nominal_Capacity[ut-1,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for g in model.generator_types)
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
       
        if model.Model_Components == 0 or model.Model_Components == 2:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3 + SV_Grid
        if model.Model_Components == 1:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Ren_2 + SV_Ren_3 + SV_Grid
    
    def BESS_Capacity(model,ut): #Minimum battery capacity
        return model.Battery_Nominal_Capacity[1] >= model.Battery_capacity
    
    def GEN_Capacity(model,ut,g): #Minimum generator capacity
        return model.Generator_Nominal_Capacity[1,g] >= model.Generator_capacity[g]
    
    def RES_Capacity(model,s,yt,ut,r,t): #Minimum RES energy production
        return model.RES_Energy_Production[s,yt,r,t] >= model.RES_Unit_Energy_Production[s,r,t]*model.RES_Inverter_Efficiency[r]*(model.RES_capacity[r] / model.RES_Nominal_Capacity[r])
    
    def Energy_balance(model,s,yt,ut,t): # Energy balance
        Foo = []
        for r in model.renewable_sources:
            Foo.append((s,yt,r,t))    
        Total_Renewable_Energy = sum(model.RES_Energy_Production[j] for j in Foo)    
        foo=[]
        for g in model.generator_types:
            foo.append((s,yt,g,t))    
        Total_Generator_Energy = sum(model.Generator_Energy_Production[i] for i in foo)  
        if model.Grid_Connection == 1:
            En_From_Grid = model.Energy_From_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            if model.Grid_Connection_Type == 0:
                En_To_Grid = model.Energy_To_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            else: En_To_Grid = 0
        else:
            En_From_Grid = 0
            En_To_Grid = 0
        
        if model.Model_Components == 0:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Battery_Outflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 1:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Battery_Outflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )    
        if model.Model_Components == 2:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )    
    
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
        goo=[]
        for s in range(1, model.Scenarios + 1):
            for y in years_list:
                    for t in range(1,model.Periods+1):
                        goo.append((s,y,t))
                        
        E_gen = sum(model.Generator_Energy_Production[s,y,g,t]*model.Scenario_Weight[s]
                    for s,y,g,t in Foo)
        E_ren = sum(model.RES_Energy_Production[s,y,r,t]*model.Scenario_Weight[s]
                    for s,y,r,t in foo)
        if model.Grid_Connection == 1:
            E_From_Grid = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Scenario_Weight[s]
                    for s,y,t in goo)
        else: E_From_Grid = 0
 
        return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*(E_gen + E_From_Grid)   
    
    def Renewables_Min_Step_Units(model,yt,ut,r):
        if ut > 1:
            return model.RES_Units[ut,r] >= model.RES_Units[ut-1,r]
        elif ut == 1:
            return model.RES_Units[ut,r] == model.RES_Units[ut,r]
        
    "Maximum land use constraint for Renewables"
    def Renewables_Max_Land_Use(model,s,yt,ut,r,t):
        return  (sum((model.RES_existing_area[r] + (model.RES_Units[ut,r]*model.RES_Nominal_Capacity[r]*(model.RES_Specific_Area[r]/1000))) for r in model.renewable_sources)) <= model.Renewables_Total_Area
    
    "Battery Energy Storage constraints"
    def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
        if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
            return model.Battery_SOC[s,yt,t] == model.Battery_Nominal_Capacity[ut]*model.Battery_Initial_SOC - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        if t==1 and yt!=1:
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt-1,model.Periods] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        else:  
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt,t-1] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency    
    
    def Maximum_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
        return model.Battery_SOC[s,yt,t] <= model.Battery_Nominal_Capacity[ut]
    
    def Minimum_Charge(model,s,yt,ut,t): # Minimun state of charge
        return model.Battery_SOC[s,yt,t] >= model.Battery_Nominal_Capacity[ut]*(1-model.Battery_Depth_of_Discharge)
    
    def Max_Power_Battery_Charge(model,ut): 
        return model.Battery_Maximum_Charge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Charge_Time
    
    def Max_Power_Battery_Discharge(model,ut):
        return model.Battery_Maximum_Discharge_Power[ut] == model.Battery_Nominal_Capacity[ut]/model.Maximum_Battery_Discharge_Time
    
    def Max_Bat_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
        return model.Battery_Inflow[s,yt,t] <= model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
    
    def Max_Bat_out(model,s,yt,ut,t): # Minimum flow of energy for the discharge fase
        return model.Battery_Outflow[s,yt,t] <= model.Energy_Demand[s,yt,t]
        
    def Battery_Min_Capacity(model,ut):    
        return   model.Battery_Nominal_Capacity[ut] >= model.Battery_Min_Capacity[ut]
    
    def Battery_Min_Step_Capacity(model,yt,ut):    
        if ut > 1:
            return model.Battery_Nominal_Capacity[ut] >= model.Battery_Nominal_Capacity[ut-1]
        elif ut == 1:
            return model.Battery_Nominal_Capacity[ut] == model.Battery_Nominal_Capacity[ut]
        
    def Battery_Single_Flow_Discharge(model,s,yt,ut,t):
        return   model.Battery_Outflow[s,yt,t] <= model.Single_Flow_BESS[s,yt,t]*model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
    def Battery_Single_Flow_Charge(model,s,yt,ut,t):
        return   model.Battery_Inflow[s,yt,t] <= (1-model.Single_Flow_BESS[s,yt,t])*model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
        
    "Diesel generator constraints"
    def Maximum_Generator_Energy_1(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Production[s,yt,g,t] <= model.Generator_Nominal_Capacity[ut,g]*model.Delta_Time
    
    def Maximum_Generator_Energy_2(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Production[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
    def Generator_Min_Step_Capacity(model,yt,ut,g):
        if ut > 1:
            return model.Generator_Nominal_Capacity[ut,g] >= model.Generator_Nominal_Capacity[ut-1,g]
        elif ut ==1:
            return model.Generator_Nominal_Capacity[ut,g] == model.Generator_Nominal_Capacity[ut,g]
    
    "Lost load constraints"
    def Maximum_Lost_Load(model,s,yt): # Maximum admittable lost load
        return model.Lost_Load_Fraction >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))
    
    "Emission constraints"
    def RES_emission(model): #LCA emissions of RES
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
            
        return model.RES_emission == sum(model.RES_unit_CO2_emission[r]*((model.RES_Units[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])/1e3 for r in model.renewable_sources)+sum(sum(model.RES_unit_CO2_emission[r]*(model.RES_Units[ut,r]-model.RES_Units[ut-1,r])*model.RES_Nominal_Capacity[r]/1e3 for (yt,ut) in tup_list) for r in model.renewable_sources)
    
    def GEN_emission(model): #LCA emissions of generator
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
            
        return model.GEN_emission == sum((model.Generator_Nominal_Capacity[1,g]-model.Generator_capacity[g])/1e3*model.GEN_unit_CO2_emission[g] for g in model.generator_types)+sum(sum((model.Generator_Nominal_Capacity[ut,g]-model.Generator_Nominal_Capacity[ut-1,g])/1e3*model.GEN_unit_CO2_emission[g] for (yt,ut) in tup_list) for g in model.generator_types)
    
    def FUEL_emission(model,s,yt,ut,g,t): #Emissions from fuel consumption
        return model.FUEL_emission[s,yt,g,t] == model.Generator_Energy_Production[s,yt,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g] 
    
    def GRID_emission(model, s, y, t):
        if y >= model.Year_Grid_Connection:
            return model.GRID_emission[s,y,t] == model.Energy_From_Grid[s,y,t] * model.National_Grid_Specific_CO2_emissions/1e3
        else:
            return model.GRID_emission[s, y, t] == 0
    
    def BESS_emission(model): #LCA emissions of generator
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
            
        return model.BESS_emission == (model.Battery_Nominal_Capacity[1]-model.Battery_capacity)/1e3*model.BESS_unit_CO2_emission+sum((model.Battery_Nominal_Capacity[ut]-model.Battery_Nominal_Capacity[ut-1])/1e3*model.BESS_unit_CO2_emission for (yt,ut) in tup_list)
        
    def Scenario_FUEL_emission(model,s): 
        return model.Scenario_FUEL_emission[s] == sum(sum(sum(model.Generator_Energy_Production[s,y,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g]  for t in model.periods) for y in model.years) for g in model.generator_types) 
    
    def Scenario_GRID_emission(model, s):
        Total_Grid_Emission = 0
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Total_Grid_Emission += sum(model.Energy_From_Grid[s, y, t] * model.National_Grid_Specific_CO2_emissions / 1e3 for t in model.periods)
        return model.Scenario_GRID_emission[s] == Total_Grid_Emission
    
    "Grid constraints"  
    def Maximum_Power_From_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_From_Grid[s,y,t] == 0
        else:
            return model.Energy_From_Grid[s,y,t] <= model.Maximum_Grid_Power*1000 
    
    def Maximum_Power_To_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Connection_Type == 1 or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_To_Grid[s, y, t] == 0
        elif model.Grid_Connection_Type == 0:
            return model.Energy_To_Grid[s, y, t] <= model.Maximum_Grid_Power*1000
        
    def Single_Flow_Energy_To_Grid(model,s,yt,ut,t):
        return model.Energy_To_Grid[s,yt,t] <= model.Single_Flow_Grid[s,yt,t]*model.Large_Constant
        
    def Single_Flow_Energy_From_Grid(model,s,yt,ut,t):
        return model.Energy_From_Grid[s,yt,t] <= (1-model.Single_Flow_Grid[s,yt,t])*model.Large_Constant


#########################################################################################################################################################################################################
############################################### MILP FORMULATION ########################################################################################################################################
#########################################################################################################################################################################################################

     
#%% 

# --- Greenfield ---

class Constraints_Greenfield_Milp():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
    Data_import = open(data_file_path).readlines()
    for i in range(len(Data_import)):
     if "param: Generator_Partial_Load" in Data_import[i]:      
        Generator_Partial_Load = int((re.findall('\d+',Data_import[i])[0]))
     if "param: Fuel_Specific_Cost_Calculation" in Data_import[i]:      
            Fuel_Specific_Cost_Calculation = int((re.findall('\d+',Data_import[i])[0]))
        
    "Objective function"
    def Net_Present_Cost_Obj(model): 
        return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission_Obj(model):
        return (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
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
    def Total_Variable_Cost(model):
        return model.Total_Variable_Cost == (sum(model.Total_Scenario_Variable_Cost_NonAct[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Net_Present_Cost(model,s): 
        return model.Scenario_Net_Present_Cost[s] == (model.Investment_Cost + model.Total_Scenario_Variable_Cost_Act[s] - model.Salvage_Value)   
    
    def CO2_emission(model):
        return model.CO2_emission == (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_CO2_emission(model,s):
        if model.Grid_Connection == 1:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission + model.Scenario_GRID_emission[s])
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
        else:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission)
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s])
    
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
      
        Inv_Ren = sum((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r])
                        + sum((((model.RES_Units_milp[ut,r] - model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for r in model.renewable_sources)
        Inv_Gen = sum(((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g])
                        + sum(((((model.Generator_Units[ut,g]*model.Generator_Nominal_Capacity_milp[g]) - (model.Generator_Units[ut-1,g]*model.Generator_Nominal_Capacity_milp[g]))*model.Generator_Specific_Investment_Cost[g]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for g in model.generator_types)
        Inv_Bat = ((model.Battery_Units[1]*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost)
                        + sum((((model.Battery_Units[ut] - model.Battery_Units[ut-1])*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list)) 
        
        if model.Model_Components == 0:
            return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat
        if model.Model_Components == 1:
            return model.Investment_Cost == Inv_Ren + Inv_Bat
        if model.Model_Components == 2:
            return model.Investment_Cost == Inv_Ren + Inv_Gen

    def Investment_Cost_Limit(model):
        return model.Investment_Cost <= model.Investment_Cost_Limit
       
    "Fixed O&M costs"
    def Operation_Maintenance_Cost_Act(model):
        OyM_Ren = sum(sum((model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for r in model.renewable_sources)
        OyM_Gen = sum(sum(((model.Generator_Units[ut,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen  

    
    def Operation_Maintenance_Cost_NonAct(model):
        OyM_Ren = sum(sum((model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])
                        for (yt,ut) in model.years_steps)for r in model.renewable_sources)
        OyM_Gen = sum(sum(((model.Generator_Units[ut,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])
                        for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)
                        for (yt,ut) in model.years_steps)

        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen 

    "Variable costs"
    def Total_Variable_Cost_Act(model):
        return model.Total_Variable_Cost_Act == (sum(model.Total_Scenario_Variable_Cost_Act[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Variable_Cost_Act(model, s):
        foo = []
        for g in range(1,model.Generator_Types+1):
                foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)   
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_Act[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_Act[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
    def Scenario_Variable_Cost_NonAct(model, s): 
        foo = []
        for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_NonAct[s,g] for s,g in foo)  
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_NonAct[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_NonAct[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
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
    
    if Generator_Partial_Load == 1 and Fuel_Specific_Cost_Calculation == 0:
     "Partial Load Effect"
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost_1[g])+(model.Generator_Marginal_Cost_milp_1[g]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost_1[g])) for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost_1[g])+(model.Generator_Marginal_Cost_milp_1[g]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost_1[g])) for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 1 and Fuel_Specific_Cost_Calculation == 1:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost[g,y])+(model.Generator_Marginal_Cost_milp[g,y]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost[g,y])) for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost[g,y])+(model.Generator_Marginal_Cost_milp[g,y]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost[g,y])) for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 0 and Fuel_Specific_Cost_Calculation == 0:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 0 and Fuel_Specific_Cost_Calculation == 1:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot

    def Total_Electricity_Cost_Act(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Num = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
                Electricity_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Electricity_Cost_Act[s] == Electricity_Cost_Tot
       
    def Total_Electricity_Cost_NonAct(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Electricity_Cost_Tot += sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
        return model.Total_Electricity_Cost_NonAct[s] == Electricity_Cost_Tot
    
    
    def Total_Revenues_NonAct(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_NonAct[s] == sum(Revenues_Yearly[y - 1] for y in model.years)

    def Total_Revenues_Act(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_Act[s] == sum(Revenues_Yearly[y - 1] / ((1 + model.Discount_Rate) ** y) for y in model.years)
    
    def Battery_Replacement_Cost_Act(model,s):
        Battery_cost_in = [0 for y in model.years]
        Battery_cost_out = [0 for y in model.years]
        Battery_Yearly_cost = [0 for y in model.years]    
        for y in range(1,model.Years+1):    
            Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_Yearly_cost[y-1] = Battery_cost_out[y-1] + Battery_cost_in[y-1]
        return model.Battery_Replacement_Cost_Act[s] == sum(Battery_Yearly_cost[y-1]/((1+model.Discount_Rate)**y) for y in model.years) 
        
    def Battery_Replacement_Cost_NonAct(model,s):
        Battery_cost_in = [0 for y in model.years]
        Battery_cost_out = [0 for y in model.years]
        Battery_Yearly_cost = [0 for y in model.years]    
        for y in range(1,model.Years+1):    
            Battery_cost_in[y-1] = sum(model.Battery_Inflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_cost_out[y-1] = sum(model.Battery_Outflow[s,y,t]*model.Unitary_Battery_Replacement_Cost for t in model.periods)
            Battery_Yearly_cost[y-1] = Battery_cost_out[y-1] + Battery_cost_in[y-1]
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
            SV_Ren_1 = sum(model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_2 = 0 
            SV_Ren_3 = 0  
            SV_Gen_1 = sum((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_2 = 0
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
        if model.Steps_Number == 2:    
            yt_last_up = upgrade_years_list[1]       
            SV_Ren_1 = sum(model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_2 = sum((model.RES_Units_milp[2,r]-model.RES_Units_milp[1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_3 = 0
            SV_Gen_1 = sum((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
            SV_Gen_2 = sum((model.Generator_Units[2,g]-model.Generator_Units[1,g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
            
        if model.Steps_Number > 2:
            tup_list_2 = [[] for i in range(len(model.steps)-2)]
            for i in range(len(model.steps) - 2):
                tup_list_2[i] = yu_tuples_list[s_dur*i + s_dur]
            yt_last_up = upgrade_years_list[-1]
            ut_last_up = tup_list[-1][1]    
            ut_seclast_up = tup_list[-2][1]
    
            SV_Ren_1 = sum(model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)    
            SV_Ren_2 = sum((model.RES_Units_milp[ut_last_up,r] - model.RES_Units_milp[ut_seclast_up,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
            SV_Ren_3 = sum(sum((model.RES_Units_milp[ut,r] - model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for r in model.renewable_sources)
            SV_Gen_1 = sum((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_2 = sum((model.Generator_Units[ut_last_up,g] - model.Generator_Units[ut_seclast_up,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = sum(sum((model.Generator_Units[ut,g] - model.Generator_Units[ut-1,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for g in model.generator_types)
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
            
        if model.Model_Components == 0 or model.Model_Components == 2:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3 + SV_Grid 
        if model.Model_Components == 1:
            return model.Salvage_Value ==  SV_Ren_1 + SV_Ren_2 + SV_Ren_3 + SV_Grid 
    
    def Energy_balance(model,s,yt,ut,t): # Energy balance
        Foo = []
        for r in model.renewable_sources:
            Foo.append((s,yt,r,t))    
        Total_Renewable_Energy = sum(model.RES_Energy_Production[j] for j in Foo)    
        foo=[]
        for g in model.generator_types:
            foo.append((s,yt,g,t))    
        Total_Generator_Energy = sum(model.Generator_Energy_Total[i] for i in foo)
        if model.Grid_Connection == 1:
            En_From_Grid = model.Energy_From_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            if model.Grid_Connection_Type == 0:
                En_To_Grid = model.Energy_To_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            else: En_To_Grid = 0
        else:
            En_From_Grid = 0
            En_To_Grid = 0
        
        if model.Model_Components == 0:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Battery_Outflow[s,yt,t]
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 1:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Battery_Outflow[s,yt,t]
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 2:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        
    "Renewable Energy Sources constraints"
    def Renewable_Energy(model,s,yt,ut,r,t): # Energy output of the RES
        return model.RES_Energy_Production[s,yt,r,t] == model.RES_Unit_Energy_Production[s,r,t]*model.RES_Inverter_Efficiency[r]*model.RES_Units_milp[ut,r]
    
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
        goo=[]
        for s in range(1, model.Scenarios + 1):
            for y in years_list:
                    for t in range(1,model.Periods+1):
                        goo.append((s,y,t))
                        
        E_gen = sum(model.Generator_Energy_Total[s,y,g,t]*model.Scenario_Weight[s]
                    for s,y,g,t in Foo)
        E_ren = sum(model.RES_Energy_Production[s,y,r,t]*model.Scenario_Weight[s]
                    for s,y,r,t in foo)
        if model.Grid_Connection == 1:
            E_From_Grid = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Scenario_Weight[s]
                    for s,y,t in goo)
        else: E_From_Grid = 0
 
        return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*(E_gen + E_From_Grid)   
    
    def Renewables_Min_Step_Units(model,yt,ut,r):
        if ut > 1:
            return model.RES_Units_milp[ut,r] >= model.RES_Units_milp[ut-1,r]
        elif ut == 1:
            return model.RES_Units_milp[ut,r] == model.RES_Units_milp[ut,r]
        
    "Maximum land use constraint for Renewables"
    def Renewables_Max_Land_Use(model,s,yt,ut,r,t):
        return  (sum((model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r]*(model.RES_Specific_Area[r]/1000)) for r in model.renewable_sources)) <= model.Renewables_Total_Area
    
    "Battery Energy Storage constraints"
    def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
        if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
            return model.Battery_SOC[s,yt,t] == model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Initial_SOC - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        if t==1 and yt!=1:
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt-1,model.Periods] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        else:  
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt,t-1] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency    
    
    def Maximum_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
        return model.Battery_SOC[s,yt,t] <= model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp
    
    def Minimum_Charge(model,s,yt,ut,t): # Minimun state of charge
        return model.Battery_SOC[s,yt,t] >= model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*(1-model.Battery_Depth_of_Discharge)
    
    def Max_Power_Battery_Charge(model,ut): 
        return model.Battery_Maximum_Charge_Power[ut] == (model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp)/model.Maximum_Battery_Charge_Time
    
    def Max_Power_Battery_Discharge(model,ut):
        return model.Battery_Maximum_Discharge_Power[ut] == (model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp)/model.Maximum_Battery_Discharge_Time
    
    def Max_Bat_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
        return model.Battery_Inflow[s,yt,t] <= model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
    
    def Max_Bat_out(model,s,yt,ut,t): # Minimum flow of energy for the discharge fase
        return model.Battery_Outflow[s,yt,t] <= model.Energy_Demand[s,yt,t]
        
    def Battery_Min_Capacity(model,ut):    
        return   model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp >= model.Battery_Min_Capacity[ut]
    
    def Battery_Min_Step_Capacity(model,yt,ut):    
        if ut > 1:
            return model.Battery_Units[ut] >= model.Battery_Units[ut-1]
        elif ut == 1:
            return model.Battery_Units[ut] == model.Battery_Units[ut]
    
    def Battery_Single_Flow_Discharge(model,s,yt,ut,t):
        return   model.Battery_Outflow[s,yt,t] <= model.Single_Flow_BESS[s,yt,t]*model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
    def Battery_Single_Flow_Charge(model,s,yt,ut,t):
        return   model.Battery_Inflow[s,yt,t] <= (1-model.Single_Flow_BESS[s,yt,t])*model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
    
    "Diesel generator constraints"
    if Generator_Partial_Load:
     def Minimum_Generator_Energy_Partial(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Partial[s,yt,g,t] >= (model.Generator_Nominal_Capacity_milp[g]*model.Generator_Min_output[g]*model.Delta_Time)*model.Generator_Partial[s,yt,g,t]
    
     def Maximum_Generator_Energy_Partial(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Partial[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Partial[s,yt,g,t]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_1(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Units[ut,g]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_2(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
     def Generator_Energy_Total(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] == (model.Generator_Full[s,yt,g,t]*model.Generator_Nominal_Capacity_milp[g]) + model.Generator_Energy_Partial[s,yt,g,t]
    
     def Generator_Units_Total(model,s,yt,ut,g,t):
        return model.Generator_Units[ut,g] == model.Generator_Full[s,yt,g,t] + model.Generator_Partial[s,yt,g,t]
    else:
     def Maximum_Generator_Energy_Total_1(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Units[ut,g]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_2(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
    def Generator_Min_Step_Capacity(model,yt,ut,g):
        if ut > 1:
            return model.Generator_Units[ut,g] >= model.Generator_Units[ut-1,g]
        elif ut ==1:
            return model.Generator_Units[ut,g] == model.Generator_Units[ut,g]

    "Lost load constraints"
    def Maximum_Lost_Load(model,s,yt): # Maximum admittable lost load
        return model.Lost_Load_Fraction >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))
    
    "Emission constraints"
    def RES_emission(model): #LCA emissions of RES
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
            
        return model.RES_emission == sum(model.RES_unit_CO2_emission[r]*model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]/1e3 for r in model.renewable_sources)+sum(sum(model.RES_unit_CO2_emission[r]*(model.RES_Units_milp[ut,r]-model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]/1e3 for (yt,ut) in tup_list) for r in model.renewable_sources)

    def GEN_emission(model): #LCA emissions of generator
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
            
        return model.GEN_emission == sum((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])/1e3*model.GEN_unit_CO2_emission[g] for g in model.generator_types)+sum(sum(((model.Generator_Units[ut,g]-model.Generator_Units[ut-1,g])*model.Generator_Nominal_Capacity_milp[g])/1e3*model.GEN_unit_CO2_emission[g] for (yt,ut) in tup_list) for g in model.generator_types)
    
    def FUEL_emission(model,s,yt,ut,g,t): #Emissions from fuel consumption
        return model.FUEL_emission[s,yt,g,t] == model.Generator_Energy_Total[s,yt,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g] 
    
    def GRID_emission(model, s, y, t):
        if y >= model.Year_Grid_Connection:
            return model.GRID_emission[s,y,t] == model.Energy_From_Grid[s,y,t] * model.National_Grid_Specific_CO2_emissions/1e3
        else:
            return model.GRID_emission[s, y, t] == 0
     
    def BESS_emission(model): #LCA emissions of battery
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
            
        return model.BESS_emission == (model.Battery_Units[1]*model.Battery_Nominal_Capacity_milp)/1e3*model.BESS_unit_CO2_emission+sum(((model.Battery_Units[ut]-model.Battery_Units[ut-1])*model.Battery_Nominal_Capacity_milp)/1e3*model.BESS_unit_CO2_emission for (yt,ut) in tup_list)
        
    def Scenario_FUEL_emission(model,s): 
        return model.Scenario_FUEL_emission[s] == sum(sum(sum(model.Generator_Energy_Total[s,y,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g]  for t in model.periods) for y in model.years) for g in model.generator_types) 
    
    def Scenario_GRID_emission(model, s):
        Total_Grid_Emission = 0
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Total_Grid_Emission += sum(model.Energy_From_Grid[s, y, t] * model.National_Grid_Specific_CO2_emissions / 1e3 for t in model.periods)
        return model.Scenario_GRID_emission[s] == Total_Grid_Emission
    
    "Grid constraints"  
    def Maximum_Power_From_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_From_Grid[s,y,t] == 0
        else:
            return model.Energy_From_Grid[s,y,t] <= model.Maximum_Grid_Power*1000 
    
    def Maximum_Power_To_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Connection_Type == 1 or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_To_Grid[s, y, t] == 0
        elif model.Grid_Connection_Type == 0:
            return model.Energy_To_Grid[s, y, t] <= model.Maximum_Grid_Power*1000
        
    def Single_Flow_Energy_To_Grid(model,s,yt,ut,t):
        return model.Energy_To_Grid[s,yt,t] <= model.Single_Flow_Grid[s,yt,t]*model.Large_Constant
        
    def Single_Flow_Energy_From_Grid(model,s,yt,ut,t):
        return model.Energy_From_Grid[s,yt,t] <= (1-model.Single_Flow_Grid[s,yt,t])*model.Large_Constant
   
     
#%% 

# --- Brownfield ---
    
class Constraints_Brownfield_Milp():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
    Data_import = open(data_file_path).readlines()
    for i in range(len(Data_import)):
     if "param: Generator_Partial_Load" in Data_import[i]:      
        Generator_Partial_Load = int((re.findall('\d+',Data_import[i])[0]))
     if "param: Fuel_Specific_Cost_Calculation" in Data_import[i]:      
            Fuel_Specific_Cost_Calculation = int((re.findall('\d+',Data_import[i])[0]))
    "Objective function"
    def Net_Present_Cost_Obj(model): 
        return (sum(model.Scenario_Net_Present_Cost[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission_Obj(model):
        return (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
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
    
    def Total_Variable_Cost(model):
        return model.Total_Variable_Cost == (sum(model.Total_Scenario_Variable_Cost_NonAct[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def CO2_emission(model):
        return model.CO2_emission == (sum(model.Scenario_CO2_emission[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_CO2_emission(model,s):
        if model.Grid_Connection == 1:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission + model.Scenario_GRID_emission[s])
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s] + model.Scenario_GRID_emission[s])
        else:
            if model.Model_Components == 0:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.BESS_emission + model.Scenario_FUEL_emission[s])
            if model.Model_Components == 1:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.BESS_emission)
            if model.Model_Components == 2:
                return model.Scenario_CO2_emission[s] ==  (model.RES_emission + model.GEN_emission + model.Scenario_FUEL_emission[s])
    
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
          
        Inv_Ren = sum(((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r])
                        + sum((((model.RES_Units_milp[ut,r] - model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for r in model.renewable_sources)  
        Inv_Gen = sum((((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g])
                        + sum((((model.Generator_Units[ut,g] - model.Generator_Units[ut-1,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g]))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list) for g in model.generator_types)
        Inv_Bat = ((((model.Battery_Units[1]*model.Battery_Nominal_Capacity_milp)-model.Battery_capacity)*model.Battery_Specific_Investment_Cost)
                        + sum((((model.Battery_Units[ut] - model.Battery_Units[ut-1])*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost))/((1+model.Discount_Rate)**(yt-1))
                        for (yt,ut) in tup_list))
        
        if model.Model_Components == 0:
            return model.Investment_Cost == Inv_Ren + Inv_Gen + Inv_Bat 
        if model.Model_Components == 1:
            return model.Investment_Cost == Inv_Ren + Inv_Bat 
        if model.Model_Components == 2:
            return model.Investment_Cost == Inv_Ren + Inv_Gen 
    
    def Investment_Cost_Limit(model):
        return model.Investment_Cost <= model.Investment_Cost_Limit
       
    "Fixed O&M costs"
    def Operation_Maintenance_Cost_Act(model):
        OyM_Ren = sum(sum(((model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r])*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
        OyM_Gen = sum(sum((model.Generator_Units[ut,g]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)/((
                        1+model.Discount_Rate)**yt)for (yt,ut) in model.years_steps)
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_Act == OyM_Ren + OyM_Gen  
    
    def Operation_Maintenance_Cost_NonAct(model):
        OyM_Ren = sum(sum(((model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r])*model.RES_Specific_Investment_Cost[r]*model.RES_Specific_OM_Cost[r])
                        for (yt,ut) in model.years_steps)for r in model.renewable_sources)    
        OyM_Gen = sum(sum((model.Generator_Units[ut,g]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g]*model.Generator_Specific_OM_Cost[g])
                        for (yt,ut) in model.years_steps)for g in model.generator_types)
        OyM_Bat = sum((model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Specific_Investment_Cost*model.Battery_Specific_OM_Cost)
                        for (yt,ut) in model.years_steps)
        
        if model.Model_Components == 0:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen + OyM_Bat 
        if model.Model_Components == 1:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Bat 
        if model.Model_Components == 2:
            return model.Operation_Maintenance_Cost_NonAct == OyM_Ren + OyM_Gen 
    
    "Variable costs"
    def Total_Variable_Cost_Act(model):
        return model.Total_Variable_Cost_Act == (sum(model.Total_Scenario_Variable_Cost_Act[s]*model.Scenario_Weight[s] for s in model.scenarios))
    
    def Scenario_Variable_Cost_Act(model, s):
        foo = []
        for g in range(1,model.Generator_Types+1):
                foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_Act[s,g] for s,g in foo)   
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_Act[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_Act[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Battery_Replacement_Cost_Act[s] + model.Scenario_Lost_Load_Cost_Act[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_Act[s] == model.Operation_Maintenance_Cost_Act + model.Scenario_Lost_Load_Cost_Act[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
    def Scenario_Variable_Cost_NonAct(model, s): 
        foo = []
        for g in range(1,model.Generator_Types+1):
            foo.append((s,g))   
        Fuel_Cost = sum(model.Total_Fuel_Cost_NonAct[s,g] for s,g in foo)  
        if model.Grid_Connection == 1:
            Electricity_Cost = model.Total_Electricity_Cost_NonAct[s] 
            if model.Grid_Connection_Type == 0:
                Electricity_Revenues = model.Total_Revenues_NonAct[s]
            else: Electricity_Revenues = 0
        else:
            Electricity_Cost = 0
            Electricity_Revenues = 0
        
        if model.Model_Components == 0:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 1:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Battery_Replacement_Cost_NonAct[s] + model.Scenario_Lost_Load_Cost_NonAct[s] + Electricity_Cost - Electricity_Revenues
        if model.Model_Components == 2:
            return model.Total_Scenario_Variable_Cost_NonAct[s] == model.Operation_Maintenance_Cost_NonAct + model.Scenario_Lost_Load_Cost_NonAct[s] + Fuel_Cost + Electricity_Cost - Electricity_Revenues
    
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

    if Generator_Partial_Load == 1 and Fuel_Specific_Cost_Calculation == 0:
     "Partial Load Effect"
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost_1[g])+(model.Generator_Marginal_Cost_milp_1[g]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost_1[g])) for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost_1[g])+(model.Generator_Marginal_Cost_milp_1[g]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost_1[g])) for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 1 and Fuel_Specific_Cost_Calculation == 1:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost[g,y])+(model.Generator_Marginal_Cost_milp[g,y]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost[g,y])) for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(((model.Generator_Full[s,y,g,t]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Marginal_Cost[g,y])+(model.Generator_Marginal_Cost_milp[g,y]*model.Generator_Energy_Partial[s,y,g,t])+(model.Generator_Partial[s,y,g,t]*model.Generator_Start_Cost[g,y])) for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 0 and Fuel_Specific_Cost_Calculation == 0:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost_1[g] for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
    elif Generator_Partial_Load == 0 and Fuel_Specific_Cost_Calculation == 1:
     def Total_Fuel_Cost_Act(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
            Fuel_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Fuel_Cost_Act[s,g] == Fuel_Cost_Tot
       
     def Total_Fuel_Cost_NonAct(model,s,g):
        Fuel_Cost_Tot = 0
        for y in range(1, model.Years +1):
            Num = sum(model.Generator_Energy_Total[s,y,g,t]*model.Generator_Marginal_Cost[g,y] for t in model.periods)
            Fuel_Cost_Tot += Num
        return model.Total_Fuel_Cost_NonAct[s,g] == Fuel_Cost_Tot
   
    def Total_Electricity_Cost_Act(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Num = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
                Electricity_Cost_Tot += Num/((1+model.Discount_Rate)**y)
        return model.Total_Electricity_Cost_Act[s] == Electricity_Cost_Tot
       
    def Total_Electricity_Cost_NonAct(model,s): 
        Electricity_Cost_Tot = 0
        for y in range(1, model.Years +1):
            if y >= model.Year_Grid_Connection:
                Electricity_Cost_Tot += sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Grid_Purchased_El_Price/1000  for t in model.periods)
        return model.Total_Electricity_Cost_NonAct[s] == Electricity_Cost_Tot
    
    def Total_Revenues_NonAct(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_NonAct[s] == sum(Revenues_Yearly[y - 1] for y in model.years)

    def Total_Revenues_Act(model, s): 
        Revenues_Yearly = [0 for _ in model.years]
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Revenues_Yearly[y - 1] = sum(model.Energy_To_Grid[s, y, t] * model.Grid_Availability[s, y, t] * model.Grid_Sold_El_Price / 1000 for t in model.periods)
        return model.Total_Revenues_Act[s] == sum(Revenues_Yearly[y - 1] / ((1 + model.Discount_Rate) ** y) for y in model.years)
    
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
            SV_Ren_1 = sum(((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum(model.RES_capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_2 = 0 
            SV_Ren_3 = 0    
            SV_Gen_1 = sum(((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
            SV_Gen_2 = 0
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
    
        if model.Steps_Number == 2:    
            yt_last_up = upgrade_years_list[1]       
            SV_Ren_1 = sum(((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum(model.RES_capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
            SV_Ren_2 = sum((model.RES_Units_milp[2,r]-model.RES_Units_milp[1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)        
            SV_Ren_3 = 0    
            SV_Gen_1 = sum(((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)        
            SV_Gen_2 = sum((model.Generator_Units[2,g]-model.Generator_Units[1,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = 0
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
            
        if model.Steps_Number > 2:
            tup_list_2 = [[] for i in range(len(model.steps)-2)]
            for i in range(len(model.steps) - 2):
                tup_list_2[i] = yu_tuples_list[s_dur*i + s_dur]
            yt_last_up = upgrade_years_list[-1]
            ut_last_up = tup_list[-1][1]    
            ut_seclast_up = tup_list[-2][1]
    
            SV_Ren_1 = sum(((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r])-model.RES_capacity[r])*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)+sum(model.RES_capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]-model.RES_years[r]-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)    
            SV_Ren_2 = sum((model.RES_Units_milp[ut_last_up,r] - model.RES_Units_milp[ut_seclast_up,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt_last_up-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for r in model.renewable_sources)
            SV_Ren_3 = sum(sum((model.RES_Units_milp[ut,r] - model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]*model.RES_Specific_Investment_Cost[r] * (model.RES_Lifetime[r]+(yt-1)-model.Years)/model.RES_Lifetime[r] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for r in model.renewable_sources)        
            SV_Gen_1 = sum(((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_capacity[g])*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)+sum(model.Generator_capacity[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]-model.GEN_years[g]-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_2 = sum((model.Generator_Units[ut_last_up,g] - model.Generator_Units[ut_seclast_up,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt_last_up-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1 + model.Discount_Rate)**(model.Years)) for g in model.generator_types)
            SV_Gen_3 = sum(sum((model.Generator_Units[ut,g] - model.Generator_Units[ut-1,g])*model.Generator_Nominal_Capacity_milp[g]*model.Generator_Specific_Investment_Cost[g] * (model.Generator_Lifetime[g]+(yt-1)-model.Years)/model.Generator_Lifetime[g] / 
                            ((1+model.Discount_Rate)**model.Years) for (yt,ut) in tup_list_2) for g in model.generator_types)
            SV_Grid = model.Grid_Distance*model.Grid_Connection_Cost*model.Grid_Connection / ((1 + model.Discount_Rate)**(model.Years - model.Year_Grid_Connection)) 
       
        if model.Model_Components == 0 or model.Model_Components == 2:
           return model.Salvage_Value ==  SV_Ren_1 + SV_Gen_1 + SV_Ren_2 + SV_Gen_2 + SV_Ren_3 + SV_Gen_3 + SV_Grid
        if model.Model_Components == 1:
           return model.Salvage_Value ==  SV_Ren_1 + SV_Ren_2 + SV_Ren_3 + SV_Grid
    
    #%% Electricity balance constraints
    def BESS_Capacity(model,ut): #Minimum battery capacity 
        return model.Battery_Units[1]*model.Battery_Nominal_Capacity_milp >= model.Battery_capacity
    
    def GEN_Capacity(model,ut,g): #Minimum generator capacity
        return model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g] >= model.Generator_capacity[g]
    
    def RES_Capacity(model,s,yt,ut,r,t): #Minimum RES energy production
        return model.RES_Energy_Production[s,yt,r,t] >= model.RES_Unit_Energy_Production[s,r,t]*model.RES_Inverter_Efficiency[r]* (model.RES_capacity[r] / model.RES_Nominal_Capacity[r])
    
    def Energy_balance(model,s,yt,ut,t): # Energy balance
        Foo = []
        for r in model.renewable_sources:
            Foo.append((s,yt,r,t))    
        Total_Renewable_Energy = sum(model.RES_Energy_Production[j] for j in Foo)    
        foo=[]
        for g in model.generator_types:
            foo.append((s,yt,g,t))    
        Total_Generator_Energy = sum(model.Generator_Energy_Total[i] for i in foo)  
        if model.Grid_Connection == 1:
            En_From_Grid = model.Energy_From_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            if model.Grid_Connection_Type == 0:
                En_To_Grid = model.Energy_To_Grid[s,yt,t]*model.Grid_Availability[s,yt,t]
            else: En_To_Grid = 0
        else:
            En_From_Grid = 0
            En_To_Grid = 0
        
        if model.Model_Components == 0:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Battery_Outflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 1:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   - model.Battery_Inflow[s,yt,t] 
                                                   + model.Battery_Outflow[s,yt,t] 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
        if model.Model_Components == 2:
            return model.Energy_Demand[s,yt,t] == (Total_Renewable_Energy 
                                                   + Total_Generator_Energy
                                                   + En_From_Grid
                                                   - En_To_Grid 
                                                   + model.Lost_Load[s,yt,t]  
                                                   - model.Energy_Curtailment[s,yt,t] )     
    
    "Renewable Energy Sources constraints"
    def Renewable_Energy(model,s,yt,ut,r,t): # Energy output of the solar panels
        return model.RES_Energy_Production[s,yt,r,t] == model.RES_Unit_Energy_Production[s,r,t]*model.RES_Inverter_Efficiency[r]*model.RES_Units_milp[ut,r]
    
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
        goo=[]
        for s in range(1, model.Scenarios + 1):
            for y in years_list:
                    for t in range(1,model.Periods+1):
                        goo.append((s,y,t))
                        
        E_gen = sum(model.Generator_Energy_Total[s,y,g,t]*model.Scenario_Weight[s]
                    for s,y,g,t in Foo)
        E_ren = sum(model.RES_Energy_Production[s,y,r,t]*model.Scenario_Weight[s]
                    for s,y,r,t in foo)
        if model.Grid_Connection == 1:
            E_From_Grid = sum(model.Energy_From_Grid[s,y,t]*model.Grid_Availability[s,y,t]*model.Scenario_Weight[s]
                    for s,y,t in goo)
        else: E_From_Grid = 0
 
        return  (1 - model.Renewable_Penetration)*E_ren >= model.Renewable_Penetration*(E_gen + E_From_Grid)   
    
    def Renewables_Min_Step_Units(model,yt,ut,r):
        if ut > 1:
            return model.RES_Units_milp[ut,r] >= model.RES_Units_milp[ut-1,r]
        elif ut == 1:
            return model.RES_Units_milp[ut,r] == model.RES_Units_milp[ut,r]
            
    "Maximum land use constraint for Renewables"
    def Renewables_Max_Land_Use(model,s,yt,ut,r,t):
        return  (sum((model.RES_existing_area[r] + (model.RES_Units_milp[ut,r]*model.RES_Nominal_Capacity[r]*(model.RES_Specific_Area[r]/1000))) for r in model.renewable_sources)) <= model.Renewables_Total_Area
    
    
    "Battery Energy Storage constraints"
    def State_of_Charge(model,s,yt,ut,t): # State of Charge of the battery
        if t==1 and yt==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
            return model.Battery_SOC[s,yt,t] == model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*model.Battery_Initial_SOC - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        if t==1 and yt!=1:
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt-1,model.Periods] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency
        else:  
            return model.Battery_SOC[s,yt,t] == model.Battery_SOC[s,yt,t-1] - model.Battery_Outflow[s,yt,t]/model.Battery_Discharge_Battery_Efficiency + model.Battery_Inflow[s,yt,t]*model.Battery_Charge_Battery_Efficiency    
    
    def Maximum_Charge(model,s,yt,ut,t): # Maximun state of charge of the Battery
        return model.Battery_SOC[s,yt,t] <= model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp
    
    def Minimum_Charge(model,s,yt,ut,t): # Minimun state of charge
        return model.Battery_SOC[s,yt,t] >= model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp*(1-model.Battery_Depth_of_Discharge)
    
    def Max_Power_Battery_Charge(model,ut): 
        return model.Battery_Maximum_Charge_Power[ut] == (model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp)/model.Maximum_Battery_Charge_Time
    
    def Max_Power_Battery_Discharge(model,ut):
        return model.Battery_Maximum_Discharge_Power[ut] == (model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp)/model.Maximum_Battery_Discharge_Time
    
    def Max_Bat_in(model,s,yt,ut,t): # Minimun flow of energy for the charge fase
        return model.Battery_Inflow[s,yt,t] <= model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
    
    def Max_Bat_out(model,s,yt,ut,t): # Minimum flow of energy for the discharge fase
        return model.Battery_Outflow[s,yt,t] <= model.Energy_Demand[s,yt,t]
        
    def Battery_Min_Capacity(model,ut):    
        return   model.Battery_Units[ut]*model.Battery_Nominal_Capacity_milp >= model.Battery_Min_Capacity[ut]
    
    def Battery_Min_Step_Capacity(model,yt,ut):    
        if ut > 1:
            return model.Battery_Units[ut] >= model.Battery_Units[ut-1]
        elif ut == 1:
            return model.Battery_Units[ut] == model.Battery_Units[ut]
        
    def Battery_Single_Flow_Discharge(model,s,yt,ut,t):
        return   model.Battery_Outflow[s,yt,t] <= model.Single_Flow_BESS[s,yt,t]*model.Battery_Maximum_Discharge_Power[ut]*model.Delta_Time
    
    def Battery_Single_Flow_Charge(model,s,yt,ut,t):
        return   model.Battery_Inflow[s,yt,t] <= (1-model.Single_Flow_BESS[s,yt,t])*model.Battery_Maximum_Charge_Power[ut]*model.Delta_Time
        
    "Diesel generator constraints"
    if Generator_Partial_Load:
     def Minimum_Generator_Energy_Partial(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Partial[s,yt,g,t] >= (model.Generator_Nominal_Capacity_milp[g]*model.Generator_Min_output[g]*model.Delta_Time)*model.Generator_Partial[s,yt,g,t]
    
     def Maximum_Generator_Energy_Partial(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Partial[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Partial[s,yt,g,t]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_1(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Units[ut,g]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_2(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
     def Generator_Energy_Total(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] == (model.Generator_Full[s,yt,g,t]*model.Generator_Nominal_Capacity_milp[g]) + model.Generator_Energy_Partial[s,yt,g,t]
    
     def Generator_Units_Total(model,s,yt,ut,g,t):
        return model.Generator_Units[ut,g] == model.Generator_Full[s,yt,g,t] + model.Generator_Partial[s,yt,g,t]
    else:
     def Maximum_Generator_Energy_Total_1(model,s,yt,ut,g,t):
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Generator_Nominal_Capacity_milp[g]*model.Generator_Units[ut,g]*model.Delta_Time
    
     def Maximum_Generator_Energy_Total_2(model,s,yt,ut,g,t): 
        return model.Generator_Energy_Total[s,yt,g,t] <= model.Energy_Demand[s,yt,t]*model.Delta_Time
    
    def Generator_Min_Step_Capacity(model,yt,ut,g):
        if ut > 1:
            return model.Generator_Units[ut,g] >= model.Generator_Units[ut-1,g]
        elif ut ==1:
            return model.Generator_Units[ut,g] == model.Generator_Units[ut,g]

    "Lost load constraints"
    def Maximum_Lost_Load(model,s,yt): # Maximum admittable lost load
        return model.Lost_Load_Fraction >= (sum(model.Lost_Load[s,yt,t] for t in model.periods)/sum(model.Energy_Demand[s,yt,t] for t in model.periods))
    
    "Emission constraints"
    def RES_emission(model): #LCA emissions of RES
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
            
        return model.RES_emission == sum(model.RES_unit_CO2_emission[r]*((model.RES_Units_milp[1,r]*model.RES_Nominal_Capacity[r]) - model.RES_capacity[r])/1e3 for r in model.renewable_sources)+sum(sum(model.RES_unit_CO2_emission[r]*(model.RES_Units_milp[ut,r]-model.RES_Units_milp[ut-1,r])*model.RES_Nominal_Capacity[r]/1e3 for (yt,ut) in tup_list) for r in model.renewable_sources)
    
    def GEN_emission(model): #LCA emissions of generator
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
            
        return model.GEN_emission == sum(((model.Generator_Units[1,g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_capacity[g])/1e3*model.GEN_unit_CO2_emission[g] for g in model.generator_types)+sum(sum(((model.Generator_Units[ut,g]-model.Generator_Units[ut-1,g])*model.Generator_Nominal_Capacity_milp[g])/1e3*model.GEN_unit_CO2_emission[g] for (yt,ut) in tup_list) for g in model.generator_types)
    
    def FUEL_emission(model,s,yt,ut,g,t): #Emissions from fuel consumption
        return model.FUEL_emission[s,yt,g,t] == model.Generator_Energy_Total[s,yt,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g] 
    
    def GRID_emission(model, s, y, t):
        if y >= model.Year_Grid_Connection:
            return model.GRID_emission[s,y,t] == model.Energy_From_Grid[s,y,t] * model.National_Grid_Specific_CO2_emissions/1e3
        else:
            return model.GRID_emission[s, y, t] == 0    

    
    def BESS_emission(model): #LCA emissions of generator
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
            
        return model.BESS_emission == ((model.Battery_Units[1]*model.Battery_Nominal_Capacity_milp)-model.Battery_capacity)/1e3*model.BESS_unit_CO2_emission+sum(((model.Battery_Units[ut]-model.Battery_Units[ut-1])*model.Battery_Nominal_Capacity_milp)/1e3*model.BESS_unit_CO2_emission for (yt,ut) in tup_list)
        
    def Scenario_FUEL_emission(model,s): 
        return model.Scenario_FUEL_emission[s] == sum(sum(sum(model.Generator_Energy_Total[s,y,g,t]/model.Fuel_LHV[g]/model.Generator_Efficiency[g]*model.FUEL_unit_CO2_emission[g]  for t in model.periods) for y in model.years) for g in model.generator_types) 
    
    def Scenario_GRID_emission(model, s):
        Total_Grid_Emission = 0
        for y in range(1, model.Years + 1):
            if y >= model.Year_Grid_Connection:
                Total_Grid_Emission += sum(model.Energy_From_Grid[s, y, t] * model.National_Grid_Specific_CO2_emissions / 1e3 for t in model.periods)
        return model.Scenario_GRID_emission[s] == Total_Grid_Emission
    
    "Grid constraints"  
    def Maximum_Power_From_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_From_Grid[s,y,t] == 0
        else:
            return model.Energy_From_Grid[s,y,t] <= model.Maximum_Grid_Power*1000 
    
    def Maximum_Power_To_Grid(model,s,y,t):
        if y < model.Year_Grid_Connection or model.Grid_Connection_Type == 1 or model.Grid_Availability[s, y, t] == 0:
            return model.Energy_To_Grid[s, y, t] == 0
        elif model.Grid_Connection_Type == 0:
            return model.Energy_To_Grid[s, y, t] <= model.Maximum_Grid_Power*1000
        
    def Single_Flow_Energy_To_Grid(model,s,yt,ut,t):
        return model.Energy_To_Grid[s,yt,t] <= model.Single_Flow_Grid[s,yt,t]*model.Large_Constant
        
    def Single_Flow_Energy_From_Grid(model,s,yt,ut,t):
        return model.Energy_From_Grid[s,yt,t] <= (1-model.Single_Flow_Grid[s,yt,t])*model.Large_Constant   



