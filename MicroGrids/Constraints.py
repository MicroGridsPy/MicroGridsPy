

def Net_Present_Cost(model): # OBJETIVE FUNTION: MINIMIZE THE NPC FOR THE SISTEM
    '''
    This function computes the sum of the multiplication of the net present cost 
    NPC (USD) of each scenario and their probability of occurrence.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
      
    return (sum(model.Scenario_Net_Present_Cost[i]*model.Scenario_Weight[i] for i in model.scenario ))
           
##################################################### PV constraints##################################################

def Renewable_Energy(model,s,r,t): # Energy output of the solar panels
    '''
    This constraint calculates the energy produce by the solar panels taking in 
    account the efficiency of the inverter for each scenario.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Total_Energy_Renewable[s,r,t] == model.Renewable_Energy_Production[s,r,t]*model.Renewable_Inverter_Efficiency[r]*model.Renewable_Units[r]

#################################################### Battery constraints #############################################

def State_of_Charge(model,i, t): # State of Charge of the battery
    '''
    This constraint calculates the State of charge of the battery (State_Of_Charge) 
    for each period of analysis. The State_Of_Charge is in the period 't' is equal to
    the State_Of_Charge in period 't-1' plus the energy flow into the battery, 
    minus the energy flow out of the battery. This is done for each scenario i.
    In time t=1 the State_Of_Charge_Battery is equal to a fully charged battery.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    if t==1: # The state of charge (State_Of_Charge) for the period 0 is equal to the Battery size.
        return model.State_Of_Charge_Battery[i,t] == model.Battery_Nominal_Capacity*model.Battery_Initial_SOC - model.Energy_Battery_Flow_Out[i,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[i,t]*model.Charge_Battery_Efficiency
    if t>1:  
        return model.State_Of_Charge_Battery[i,t] == model.State_Of_Charge_Battery[i,t-1] - model.Energy_Battery_Flow_Out[i,t]/model.Discharge_Battery_Efficiency + model.Energy_Battery_Flow_In[i,t]*model.Charge_Battery_Efficiency    

def Maximun_Charge(model, s, t): # Maximun state of charge of the Battery
    '''
    This constraint keeps the state of charge of the battery equal or under the 
    size of the battery for each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[s,t] <= model.Battery_Nominal_Capacity

def Minimun_Charge(model,i, t): # Minimun state of charge
    '''
    This constraint maintains the level of charge of the battery above the deep 
    of discharge in each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.State_Of_Charge_Battery[i,t] >= model.Battery_Nominal_Capacity*model.Deep_of_Discharge

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

def Max_Bat_in(model, i, t): # Minimun flow of energy for the charge fase
    '''
    This constraint maintains the energy in to the battery, below the maximum power 
    of charge of the battery for each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_In[i,t] <= model.Maximun_Charge_Power*model.Delta_Time

def Max_Bat_out(model,i, t): #minimun flow of energy for the discharge fase
    '''
    This constraint maintains the energy from the battery, below the maximum power of 
    discharge of the battery for each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Energy_Battery_Flow_Out[i,t] <= model.Maximun_Discharge_Power*model.Delta_Time


############################################## Energy Constraints ##################################################

def Energy_balance(model, s, t): # Energy balance
    '''
    This constraint ensures the perfect match between the energy energy demand of the 
    system and the differents sources to meet the energy demand each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    
    Foo = []
    for r in model.renewable_source:
        Foo.append((s,r,t))
    
    Total_Renewable_Energy = sum(model.Total_Energy_Renewable[j] for j in Foo)
    
    foo=[]
    for g in model.generator_type:
        foo.append((s,g,t))
    
    Generator_Energy = sum(model.Generator_Energy[i] for i in foo)  
    
    
    return model.Energy_Demand[s,t] == (Total_Renewable_Energy + Generator_Energy 
            - model.Energy_Battery_Flow_In[s,t] + model.Energy_Battery_Flow_Out[s,t] 
            + model.Lost_Load[s,t] - model.Energy_Curtailment[s,t])

def Maximun_Lost_Load(model,i): # Maximum permissible lost load
    '''
    This constraint ensures that the ratio between the lost load and the energy 
    Demand does not exceeds the value of the permisible lost load each scenario i. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Lost_Load_Probability >= (sum(model.Lost_Load[i,t] for t in model.periods)/sum(model.Energy_Demand[i,t] for t in model.periods))


######################################## Diesel generator constraints ############################        



def Maximun_Generator_Energy(model,s,g,t): # Maximun energy output of the diesel generator
    '''
    This constraint ensures that the generator will not exceed his nominal capacity 
    in each period in each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Delta_Time


########################################### Economical Constraints ###################################################

def Fuel_Cost_Total(model,s,g):
    '''
    This constraint calculate the total cost due to the used of diesel to generate 
    electricity in the generator in each scenario i. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''    
    foo=[]
    for t in range(1,model.Periods+1):
        foo.append((s,g,t))
    return model.Fuel_Cost_Total[s,g] == sum(((sum(model.Generator_Energy[s,g,t]*model.Marginal_Cost_Generator_1[g] for s,g,t in foo))/((1+model.Discount_Rate)**model.Project_Years[y])) for y in model.years) 
    
def Scenario_Lost_Load_Cost(model, i):
    '''
    This constraint calculate the cost due to the lost load in each scenario i. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    foo=[]
    for f in range(1,model.Periods+1):
        foo.append((i,f))
        
    return  model.Scenario_Lost_Load_Cost[i] == sum(((sum(model.Lost_Load[i,t]*model.Value_Of_Lost_Load for i,t in foo))/((1+model.Discount_Rate)**model.Project_Years[y])) for y in model.years) 
 
      
def Initial_Inversion(model):
    '''
    This constraint calculate the initial inversion for the system. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''    
    
    Inv_PV = sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r] for r in model.renewable_source)
    Inv_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g] for g in model.generator_type)
    return model.Initial_Inversion == ( Inv_PV + Inv_Gen
                 + model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost)

def Operation_Maintenance_Cost(model):
    '''
    This funtion calculate the operation and maintenance for the system. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''    
    OyM_PV = sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r]*model.Maintenance_Operation_Cost_Renewable[r] for r in model.renewable_source)
    OyM_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]*model.Maintenance_Operation_Cost_Generator[g] for g in model.generator_type)
    return model.Operation_Maintenance_Cost == sum(((OyM_PV + model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost*model.Maintenance_Operation_Cost_Battery+OyM_Gen)/((1+model.Discount_Rate)**model.Project_Years[y])) for y in model.years) 

    
def Battery_Reposition_Cost(model,s):
    '''
    This funtion calculate the reposition of the battery after a stated time of use. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    
    '''
    foo=[]
    for t in range(1,model.Periods+1):
            foo.append((s,t))    
            
    Battery_cost_in = sum(model.Energy_Battery_Flow_In[s,t]*model.Unitary_Battery_Reposition_Cost for s,t in foo)
    Battery_cost_out = sum(model.Energy_Battery_Flow_Out[s,t]*model.Unitary_Battery_Reposition_Cost for s,t in foo)
    Battery_Yearly_cost = Battery_cost_in + Battery_cost_out
    return model.Battery_Reposition_Cost[s] == sum(Battery_Yearly_cost/((1+model.Discount_Rate)**model.Project_Years[y]) for y in model.years) 
    
    
def Scenario_Net_Present_Cost(model, s): 
    '''
    This function computes the Net Present Cost for the life time of the project, taking in account that the 
    cost are fix for each year.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''            
    foo = []
    for g in range(1,model.Generator_Type+1):
            foo.append((s,g))
            
    Fuel_Cost = sum(model.Fuel_Cost_Total[s,g] for s,g in foo)
    
    return model.Scenario_Net_Present_Cost[s] == (model.Initial_Inversion 
            + model.Operation_Maintenance_Cost + model.Battery_Reposition_Cost[s] 
            + model.Scenario_Lost_Load_Cost[s] + Fuel_Cost)
                
    
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
    
    E_ge = sum(model.Generator_Energy[s,g,t]*model.Scenario_Weight[s]
                for s,g,t in Foo)
    
    E_PV = sum(model.Total_Energy_Renewable[s,r,t]*model.Scenario_Weight[s]
                for s,r,t in foo)
        
    return  (1 - model.Renewable_Penetration)*E_PV >= model.Renewable_Penetration*E_ge   


def Battery_Min_Capacity(model):
    
       
    return   model.Battery_Nominal_Capacity >= model.Battery_Min_Capacity


