from pyomo.environ import  Constraint

############################################# Objective funtion ######################################################

def Net_Present_Cost(model): # OBJETIVE FUNTION: MINIMIZE THE NPC FOR THE SISTEM
    '''
    This function computes the Net Present Cost for the life time of the project, taking in account that the 
    cost are fix for each year.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    foo=[]
    for s in range(1, model.Scenarios + 1):
        for t in range(1,model.Periods+1):
            foo.append((s,t))        
    Foo=[]
    for s in range(1, model.Scenarios + 1):
        for g in range(1, model.Generator_Type+1):
            for t in range(1,model.Periods+1):
                Foo.append((s,g,t))    
        
    return  (sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r] for r in model.renewable_source) + model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost  + sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g] *model.Integer_generator[g] for g in model.generator_type) 
             + ((sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r]*model.Maintenance_Operation_Cost_Renewable[r] for r in model.renewable_source) + model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost*model.Maintenance_Operation_Cost_Battery  + sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]*model.Integer_generator[g]*model.Maintenance_Operation_Cost_Generator[g] for g in model.generator_type)) 
             + (sum(model.Energy_Battery_Flow_In[s,t]*model.Battery_Reposition_Cost*model.Scenario_Weight[s] for s,t in foo))
             + (sum(model.Energy_Battery_Flow_Out[s,t]*model.Battery_Reposition_Cost*model.Scenario_Weight[s] for s,t in foo))  
             + (sum(model.Lost_Load[s,t]*model.Value_Of_Lost_Load*model.Scenario_Weight[s] for s,t in foo)) 
             + (sum((model.Generator_Energy_Integer[s,g,t]*model.Start_Cost_Generator[g]*model.Scenario_Weight[s] + model.Marginal_Cost_Generator[g]*model.Generator_Total_Period_Energy[s,g,t]*model.Scenario_Weight[s]) for s,g,t in Foo)))/model.Capital_Recovery_Factor)
   
############################################# Diesel generator constraints ###########################################

def Generator_Bounds_Min_Integer(model,s, g,t): # Maximun energy output of the diesel generator
    ''' 
    This constraint ensure that each segment of the generator does not pass a 
    minimun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Nominal_Capacity[g]*model.Generator_Min_Out_Put[g] + (model.Generator_Energy_Integer[s,g,t]-1)*model.Generator_Nominal_Capacity[g] <= model.Generator_Total_Period_Energy[s,g,t]                                                                                                
                                                                                               
def Generator_Bounds_Max_Integer(model,s, g,t): # Maximun energy output of the diesel generator
    ''' 
    This constraint ensure that each segment of the generator does not pass a 
    minimun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Total_Period_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Generator_Energy_Integer[s,g,t]                                                                                                


def Energy_Genarator_Energy_Max_Integer(model,s,g,t):
    ''' 
    This constraint ensure that the total energy in the generators does not  pass
    a maximun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Total_Period_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Integer_generator[g]
        


############################################# Battery constraints ####################################################

def State_of_Charge(model,s,t): # State of Charge of the battery
    '''
    This constraint calculates the State of charge of the battery (State_Of_Charge) for each period 
    of analysis. The State_Of_Charge is in the period 't' is equal to the State_Of_Charge in period 
    't-1' plus the energy flow into the battery, minus the energy flow out of the battery. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    if t==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
        return model.State_Of_Charge_Battery[s,t] == model.Battery_Nominal_Capacity - model.Energy_Battery_Flow_Out[s,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[s,t]*model.Charge_Battery_Efficiency
    if t>1:  
        return model.State_Of_Charge_Battery[s,t] == model.State_Of_Charge_Battery[s,t-1] - model.Energy_Battery_Flow_Out[s,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[s,t]*model.Charge_Battery_Efficiency    

def Maximun_Charge(model,s, t): # Maximun state of charge of the Battery
    '''
    This constraint keeps the state of charge of the battery equal or under the size of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[s,t] <= model.Battery_Nominal_Capacity

def Minimun_Charge(model,s, t): # Minimun state of charge
    '''
    This constraint maintains the level of charge of the battery above the deep of discharge.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[s,t] >= model.Battery_Nominal_Capacity*model.Deep_of_Discharge


def Max_Bat_in(model,s, t): # Minimun flow of energy for the charge fase
    '''
    This constraint maintains the energy in to the battery, below the maximum power of charge of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_In[s,t] <= (model.Battery_Nominal_Capacity/model.Maximun_Battery_Charge_Time)*model.Delta_Time

def Max_Bat_out(model,s, t): #minimun flow of energy for the discharge fase
    '''
    This constraint maintains the energy from the battery, below the maximum power of discharge of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_Out[s,t] <= (model.Battery_Nominal_Capacity/model.Maximun_Battery_Discharge_Time)*model.Delta_Time

############################################# Energy Constraints #####################################################

def Energy_balance(model,s,t): # Energy balance
    '''
    This constraint ensures the perfect match between the energy energy demand of the 
    system and the differents sources to meet the energy demand.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    foo=[]
    for g in range(1, model.Generator_Type+1):
        foo.append((s,g,t))
    
    Foo = []
    for r in model.renewable_source:
        Foo.append((s,r,t))
        
        
        
    Generator_Energy = sum(model.Generator_Total_Period_Energy[i] 
                           for i in foo)  
    
    Total_Renewable_Energy = sum(model.Renewable_Energy_Production[j]*model.Inverter_Efficiency_Renewable[j[1]]
                                                   *model.Renewable_Units[j[1]] for j in Foo)
    
    
    return model.Energy_Demand[s,t] == (Total_Renewable_Energy 
                                        + Generator_Energy 
                                        - model.Energy_Battery_Flow_In[s,t] 
                                        + model.Energy_Battery_Flow_Out[s,t] 
                                        + model.Lost_Load[s,t] 
                                        - model.Energy_Curtailment[s,t])

def Maximun_Lost_Load(model,s): # Maximum permissible lost load
    '''
    This constraint ensures that the ratio between the lost load and the energy Energy_Demand does not 
    exceeds the value of the permisible lost load. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    
    return model.Lost_Load_Probability >= (sum(model.Lost_Load[s,t] 
                                               for t in model.periods)/sum(model.Energy_Demand[s,t] for t in model.periods))

    
def Renewable_Energy_Penetration(model):
    
    Foo=[]
    for s in range(1, model.Scenarios + 1):
        for g in range(1, model.Generator_Type+1):
            for t in range(1,model.Periods+1):
                Foo.append((s,g,t))    
                
    foo=[]
    for s in range(1, model.Scenarios + 1):
        for r in range(1, model.Renewable_Source+1):
            for t in range(1,model.Periods+1):
                foo.append((s,r,t))    
    
    E_ge = sum(model.Generator_Total_Period_Energy[s,g,t]*model.Scenario_Weight[s]
                for s,g,t in Foo)
    
    E_PV = sum(model.Renewable_Energy_Production[s,r,t]*model.Inverter_Efficiency_Renewable[r]
                                                   *model.Renewable_Units[r]*model.Scenario_Weight[s]
                for s,r,t in foo)
        
    return  (1 - model.Renewable_Penetration)*E_PV >= model.Renewable_Penetration*E_ge   


def Battery_Min_Capacity(model):
    
       
    return   model.Battery_Nominal_Capacity >= model.Battery_Min_Capacity


