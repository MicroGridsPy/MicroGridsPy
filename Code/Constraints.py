# Objective funtion
import pandas as pd

def Net_Present_Cost(model): # OBJETIVE FUNTION: MINIMIZE THE NPC FOR THE SISTEM
    '''
    This function computes the sum of the multiplication of the net present cost 
    NPC (USD) of each scenario and their probability of occurrence.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    # Operation Cost
    # Generator operation cost
    foo = []
    for g in range(1,model.Generator_Type+1):
        for s in model.scenario:
            for t in range(1,model.Periods+1):
                foo.append((s,g,t))

    if model.formulation == 'LP':
        Generator_Cost = sum(model.Generator_Energy[s,g,t]*model.Marginal_Cost_Generator_1[g]
                             *model.Scenario_Weight[s] for s,g,t in foo)
        Operation_Cost = (Generator_Cost)/model.Capital_Recovery_Factor
        
    if model.formulation == 'MILP':
       Generator_Cost =  sum(model.Generator_Energy_Integer[s,g,t]*model.Start_Cost_Generator[g]*model.Scenario_Weight[s] + 
                             model.Marginal_Cost_Generator[g]*model.Generator_Energy[s,g,t]*model.Scenario_Weight[s]
                             for s,g,t in foo)
       Operation_Cost = Generator_Cost/model.Capital_Recovery_Factor
       
       
    # Battery opereation cost
    foo=[]
    for s in model.scenario:
        for t in range(1,model.Periods+1):
            foo.append((s,t))    
            
    Battery_cost_in = sum(model.Energy_Battery_Flow_In[s,t]*model.Unitary_Battery_Reposition_Cost
                          *model.Scenario_Weight[s]  for s,t in foo)
    Battery_cost_out = sum(model.Energy_Battery_Flow_Out[s,t]*model.Unitary_Battery_Reposition_Cost
                           *model.Scenario_Weight[s] for s,t in foo)
    Battery_Yearly_cost = Battery_cost_in + Battery_cost_out
    
    Operation_Cost += Battery_Yearly_cost/model.Capital_Recovery_Factor
    
    # Cost of the Lost load
    if model.Lost_Load_Probability > 0:
        Lost_Load_Cost =  sum(model.Lost_Load[s,t]*model.Value_Of_Lost_Load
                              *model.Scenario_Weight[s] for s,t in foo)
        Operation_Cost +=  Lost_Load_Cost/model.Capital_Recovery_Factor
        
    # Curtailment cost
    
    if model.Curtailment_Unitary_Cost > 0:
        Curtailment_Cost =  sum(model.Energy_Curtailment[s,t]*model.Curtailment_Unitary_Cost
                              *model.Scenario_Weight[s] for s,t in foo)
        Operation_Cost +=  Curtailment_Cost/model.Capital_Recovery_Factor
    
    # Cost of the operation and maintenece
    
    OyM_PV = sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r]
                *model.Maintenance_Operation_Cost_Renewable[r] for r in model.renewable_source)
    if model.formulation == 'LP':
        OyM_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]
                *model.Maintenance_Operation_Cost_Generator[g] for g in model.generator_type)
    if model.formulation == 'MILP':
        OyM_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]*model.Integer_generator[g]
                *model.Maintenance_Operation_Cost_Generator[g] for g in model.generator_type)
    
    
    OyM_Bat = model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost*model.Maintenance_Operation_Cost_Battery
    OyM_Cost =  OyM_PV + OyM_Gen + OyM_Bat
    Operation_Cost += OyM_Cost/model.Capital_Recovery_Factor
    
   
    
    # Invesment cost
    Inv_PV = sum(model.Renewable_Units[r]*model.Renewable_Nominal_Capacity[r]*model.Renewable_Invesment_Cost[r]
                 for r in model.renewable_source)
    if model.formulation == 'LP':
        Inv_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]
                 for g in model.generator_type)
    if model.formulation == 'MILP':

        Inv_Gen = sum(model.Generator_Invesment_Cost[g]*model.Generator_Nominal_Capacity[g]
        *model.Integer_generator[g] for g in model.generator_type) 
        
    Inv_Bat = model.Battery_Nominal_Capacity*model.Battery_Invesment_Cost
    Initial_Inversion =  Inv_PV + Inv_Gen + Inv_Bat
    
           
    return Initial_Inversion + Operation_Cost
           
##################################################################################################
#################################################### Battery constraints #########################
##################################################################################################
    

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
        return model.State_Of_Charge_Battery[i,t] == model.Battery_Nominal_Capacity*model.Battery_Initial_SOC\
                                                    - model.Energy_Battery_Flow_Out[i,t]/model.Discharge_Battery_Efficiency\
                                                    + model.Energy_Battery_Flow_In[i,t]*model.Charge_Battery_Efficiency
    if t>1:  
        return model.State_Of_Charge_Battery[i,t] == model.State_Of_Charge_Battery[i,t-1]\
                                        - model.Energy_Battery_Flow_Out[i,t]/model.Discharge_Battery_Efficiency\
                                        + model.Energy_Battery_Flow_In[i,t]*model.Charge_Battery_Efficiency    

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

##################################################################################################
##############                    Energy Constraints                        ######################
##################################################################################################
    


def Energy_balance(model, s, t): # Energy balance
    '''
    This constraint ensures the perfect match between the energy energy demand of the 
    system and the differents sources to meet the energy demand each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    
    
    Foo = []
    for r in model.renewable_source:
        Foo.append((s,r,t))

    Energy_Sources = sum(model.Renewable_Energy_Production[s,r,t]*model.Renewable_Inverter_Efficiency[r]
                                 *model.Renewable_Units[r] for s,r,t in Foo)
    
    foo=[]
    for g in model.generator_type:
        foo.append((s,g,t))
        
    Energy_Sources += sum(model.Generator_Energy[i] for i in foo)  
        
    if model.Lost_Load_Probability > 0:
        Energy_Sources += model.Lost_Load[s,t]
        
    
    return model.Energy_Demand[s,t] == (Energy_Sources +
            - model.Energy_Battery_Flow_In[s,t] + model.Energy_Battery_Flow_Out[s,t] 
            - model.Energy_Curtailment[s,t])

def Maximun_Lost_Load(model): # Maximum permissible lost load
    '''
    This constraint ensures that the ratio between the lost load and the energy 
    Demand does not exceeds the value of the permisible lost load each scenario i. 
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    
    
    LLP = pd.Series()
    for s in model.scenario:
        LL = sum(model.Lost_Load[s,t] for t in model.periods)
        Demand = sum(model.Energy_Demand[s,t] for t in model.periods)
        
        LLP.loc[s] = (LL/Demand)*model.Scenario_Weight[s]
    
    return model.Lost_Load_Probability >= sum(LLP[s] for s in model.scenario)

##################################################################################################
#########                          Diesel generator constraints                       ############
##################################################################################################
    
###############################    LP Model        ###############################################

def Maximun_Generator_Energy(model,s,g,t): # Maximun energy output of the diesel generator
    '''
    This constraint ensures that the generator will not exceed his nominal capacity 
    in each period in each scenario i.
    
    :param model: Pyomo model as defined in the Model_creation library.
    '''
    return model.Generator_Energy[s,g,t] <= model.Generator_Nominal_Capacity[g]*model.Delta_Time

###############################    MILP Model        ##############################################
    
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

##################################################################################################
#########                     Economical Constraints                                ##############
##################################################################################################
    
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
    E_PV = sum(model.Renewable_Energy_Production[s,r,t]*model.Renewable_Inverter_Efficiency[r]
                                 *model.Renewable_Units[r]*model.Scenario_Weight[s] for s,r,t in foo)
        
    return  (1 - model.Renewable_Penetration)*E_PV >= model.Renewable_Penetration*E_ge   


def Battery_Min_Capacity(model):
    
       
    return   model.Battery_Nominal_Capacity >= model.Battery_Min_Capacity


