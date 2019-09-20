############################################# Objective funtion ######################################################

def Net_Present_Cost(model): # OBJETIVE FUNTION: MINIMIZE THE NPC FOR THE SISTEM
    '''
    This function computes the Net Present Cost for the life time of the project, taking in account that the 
    cost are fix for each year.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
            # This element of the objective function represent the part of the total investment that is Porcentage_Funded with the the resources of the project owners.  

    # Operation Cost
    # Generator operation cost
    foo = []
    for g in range(1,model.Generator_Type+1):
        for s in model.scenario:
            for t in range(1,model.Periods+1):
                foo.append((s,g,t))

        
    Generator_Cost =  sum(model.Generator_Energy_Integer[g,t]*model.Start_Cost_Generator[g] + 
                             model.Marginal_Cost_Generator[g]*model.Generator_Energy[g,t]
                             for g,t in foo)     
    Operation_Cost = Generator_Cost   
    # Battery opereation cost
    foo=[]
    for s in model.scenario:
        for t in range(1,model.Periods+1):
            foo.append((s,t))    
            
    Battery_cost_in = sum(model.Energy_Battery_Flow_In[s,t]*model.Unitary_Battery_Reposition_Cost
                          *model.Scenario_Weight[s]  for s,t in foo)
    Battery_cost_out = sum(model.Energy_Battery_Flow_Out[s,t]*model.Unitary_Battery_Reposition_Cost
                           *model.Scenario_Weight[s] for s,t in foo)
    Operation_Cost += Battery_cost_in + Battery_cost_out
    
    
    # Cost of the Lost load
    if model.Lost_Load_Probability > 0:
        Lost_Load_Cost =  sum(model.Lost_Load[s,t]*model.Value_Of_Lost_Load
                              *model.Scenario_Weight[s] for t in model.periods)
        Operation_Cost +=  Lost_Load_Cost
        
    # Curtailment cost
    
    if model.Curtailment_Unitary_Cost > 0:
        Curtailment_Cost =  sum(model.Energy_Curtailment[t]*model.Curtailment_Unitary_Cost
                                for t in model.periods)
        Operation_Cost +=  Curtailment_Cost
    
    return Operation_Cost

############################################# Diesel generator constraints ###########################################

def Generator_Bounds_Min_Integer(model,s, g,t): # Maximun energy output of the diesel generator
    ''' 
    This constraint ensure that each segment of the generator does not pass a 
    minimun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Nominal_Capacity[g]*model.Generator_Min_Out_Put[g] + (model.Generator_Energy_Integer[s,g,t]-1)*model.Generator_Nominal_Capacity[g] <= model.Generator_Energy[s,g,t]                                                                                                
                                                                                                                             
def Generator_Bounds_Max_Integer(model,s, g,t): # Maximun energy output of the diesel generator
    ''' 
    This constraint ensure that each segment of the generator does not pass a 
    minimun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Generator_Energy_Integer[s,g,t]                                                                                                



def Energy_Genarator_Energy_Max_Integer(model,s,g,t):
    ''' 
    This constraint ensure that the total energy in the generators does not  pass
    a maximun value.
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Integer_generator[g]        


############################################# Battery constraints ####################################################

def State_of_Charge(model,t): # State of Charge of the battery
    '''
    This constraint calculates the State of charge of the battery (State_Of_Charge) for each period 
    of analysis. The State_Of_Charge is in the period 't' is equal to the State_Of_Charge in period 
    't-1' plus the energy flow into the battery, minus the energy flow out of the battery. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    if t==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
        return model.State_Of_Charge_Battery[t] == model.Battery_Nominal_Capacity*model.Battery_Initial_SOC - model.Energy_Battery_Flow_Out[t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[t]*model.Charge_Battery_Efficiency
    if t>1:  
        return model.State_Of_Charge_Battery[t] == model.State_Of_Charge_Battery[t-1] - model.Energy_Battery_Flow_Out[t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[t]*model.Charge_Battery_Efficiency    

def Maximun_Charge(model, t): # Maximun state of charge of the Battery
    '''
    This constraint keeps the state of charge of the battery equal or under the size of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[t] <= model.Battery_Nominal_Capacity

def Minimun_Charge(model, t): # Minimun state of charge
    '''
    This constraint maintains the level of charge of the battery above the deep of discharge.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[t] >= model.Battery_Nominal_Capacity*model.Deep_of_Discharge

def Max_Power_Battery_Charge(model): 
    '''
    This constraint calculates the Maximum power of charge of the battery. Taking in account the 
    capacity of the battery and a time frame in which the battery has to be fully loaded for 
    each scenario.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Maximun_Charge_Power== model.Battery_Nominal_Capacity/model.Maximun_Battery_Charge_Time

def Max_Power_Battery_Discharge(model):
    '''
    This constraint calculates the Maximum power of discharge of the battery. for 
    each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Maximun_Discharge_Power == model.Battery_Nominal_Capacity/model.Maximun_Battery_Discharge_Time



def Max_Bat_in(model, t): # Minimun flow of energy for the charge fase
    '''
    This constraint maintains the energy in to the battery, below the maximum power of charge of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_In[t] <= model.Maximun_Charge_Power*model.Delta_Time

def Max_Bat_out(model, t): #minimun flow of energy for the discharge fase
    '''
    This constraint maintains the energy from the battery, below the maximum power of discharge of the battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_Out[t] <= model.Maximun_Discharge_Power*model.Delta_Time


def Battery_Reposition_Cost(model):
    '''
    This funtion calculate the reposition of the battery after a stated time of use. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    
    '''
    foo=[]
    for t in range(1,model.Periods+1):
            foo.append((t))    
            
    Battery_cost_in = sum(model.Energy_Battery_Flow_In[t]*model.Unitary_Battery_Reposition_Cost for t in range(1,model.Periods+1))
    Battery_cost_out = sum(model.Energy_Battery_Flow_Out[t]*model.Unitary_Battery_Reposition_Cost for t in range(1,model.Periods+1))
     
    return  model.Battery_Yearly_cost == Battery_cost_out + Battery_cost_in 
  


############################################# Energy Constraints #####################################################

def Energy_balance(model, t): # Energy balance
    '''
    This constraint ensures the perfect match between the energy energy demand of the 
    system and the differents sources to meet the energy demand each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    Foo = []
    for r in model.renewable_source:
        Foo.append((r,t))

    Energy_Sources = sum(model.Renewable_Energy_Production[r,t]*model.Renewable_Inverter_Efficiency[r]
                                 *model.Renewable_Units[r] for r,t in Foo)
    
    foo=[]
    for g in model.generator_type:
        foo.append((g,t))
        
    Energy_Sources = sum(model.Generator_Energy[i] for i in foo)  
        
    if model.Lost_Load_Probability > 0:
        Energy_Sources += model.Lost_Load[t]
    
    
    return model.Energy_Demand[t] == (Energy_Sources - model.Energy_Battery_Flow_In[t] 
                              + model.Energy_Battery_Flow_Out[t] - model.Energy_Curtailment[t])

def Maximun_Lost_Load(model): # Maximum permissible lost load
    '''
    This constraint ensures that the ratio between the lost load and the energy Energy_Demand does not 
    exceeds the value of the permisible lost load. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
   
    Total_Demand = sum(model.Lost_Load[t] for t in model.periods)
    Total_Lost_Load = sum(model.Energy_Demand[t] for t in model.periods)
    
    return model.Lost_Load_Probability >= (Total_Demand/Total_Lost_Load)