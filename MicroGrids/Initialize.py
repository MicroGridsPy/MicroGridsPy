
import pandas as pd

def Initialize_years(model, i):

    '''
    This function returns the value of each year of the project. 
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The year i.
    '''    
    return i

Energy_Demand = pd.read_excel('Example/Demand.xls',index_col=0,Header=None) # open the energy demand file
Energy_Demand = Energy_Demand/1000
Energy_Demand = round(Energy_Demand, 3)


def Initialize_Demand(model, i, t):
    '''
    This function returns the value of the energy demand from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: The energy demand for the period t.     
        
    '''
    
    return float(Energy_Demand[i][t])

# PV_Energy = pd.read_excel('Example/PV_Energy.xls') # open the PV energy yield file

# def Initialize_PV_Energy(model, i, t):
#     '''
#     This function returns the value of the energy yield by one PV under the characteristics of the system 
#     analysis for each period of analysis from a excel file.
    
#     :param model: Pyomo model as defined in the Model_Creation script.
    
#     :return: The energy yield of one PV for the period t.
#     '''
#     return float(PV_Energy[i][t])

def Initialize_Demand_Dispatch(model, t):
    '''
    This function returns the value of the energy demand from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: The energy demand for the period t.     
        
    '''
    return float(Energy_Demand[1][t])

# Thermal Energy Demand (JVS)
    
Thermal_Demand = pd.read_excel('Example/Thermal_Demand_Test.xls',index_col=0,Header=0) # open thermal demand file
Thermal_Demand = Thermal_Demand/1000    # Total Thermal Demand
Thermal_Demand = round(Thermal_Demand, 3)

def Initialize_Thermal_Demand(model,i, t):
    '''
    This function returns the value of thermal demand from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: Thermal demand for the period t.     
        
    '''
    
    return float(Thermal_Demand[i][t])

#def Initialize_Thermal_Dispatch(model, t):
#    '''
#     This function returns the value of thermal demand from a system for each period of analysis from a excel file.
#    
#    :param model: Pyomo model as defined in the Model_Creation script.
#        
#    :return: Thermal demand for the period t.     
#        
#    '''
#    return float (Thermal_Demand[1][t])   # Total thermal (heat) demand for the system

def Initialize_Refrigeration_Dispatch(model,s, t):
    '''
     This function returns the value of refrigeration demand of the polygeneration plant from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: Refrigeration demand for the period t.     
        
    '''
    return float (Thermal_Demand[2][t])   # Total refrigeration demand for the system

def Initialize_Thermal_Drier_Dispatch(model,s, t):
    '''
     This function returns the value of thermal demand of the bioslurry drier from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: Thermal demand of the bioslurry drier (BSD) for the period t.     
        
    '''
    return float (Thermal_Demand[4][t])   # Total thermal demand of the BSD for the system

# Thermal Energy Demand (JVS)--------------------------


# def Initialize_PV_Energy_Dispatch(model, t):
#     '''
#     This function returns the value of the energy yield by one PV under the characteristics of the system 
#     analysis for each period of analysis from a excel file.
    
#     :param model: Pyomo model as defined in the Model_Creation script.
    
#     :return: The energy yield of one PV for the period t.
#     '''
#     return float(PV_Energy[1][t])
    
    
def Marginal_Cost_Generator_1(model,g):
    
    a = model.Fuel_Cost[g]/(model.Low_Heating_Value[g]*model.Generator_Efficiency[g])
    return round(a, 3)

def Start_Cost(model,i):
    
    a = model.Marginal_Cost_Generator_1[i]*model.Generator_Nominal_Capacity[i]*model.Cost_Increase[i]
    return round(a, 3)

def Marginal_Cost_Generator(model, i):
    a = (model.Marginal_Cost_Generator_1[i]*model.Generator_Nominal_Capacity[i]-model.Start_Cost_Generator[i])/model.Generator_Nominal_Capacity[i] 
    return round(a, 3) 

#Combustor marginal cost new
def Marginal_Cost_Combustor_1(model,g,c):
    
    a = model.Fuel_Cost[g]/(model.Low_Heating_Value[g]*model.Combustor_Efficiency[c]) #
    return round(a, 3)


def Capital_Recovery_Factor(model):
   
    a = model.Discount_Rate*((1+model.Discount_Rate)**model.Years)
    b = ((1 + model.Discount_Rate)**model.Years)-1
    return a/b

    
def Battery_Reposition_Cost(model):
   
    unitary_battery_cost = model.Battery_Invesment_Cost - model.Battery_Electronic_Invesmente_Cost
    a = unitary_battery_cost/(model.Battery_Cycles*2*(1-model.Deep_of_Discharge))
    return round(a,3) 

 
   
Renewable_Energy = pd.read_excel('Example/Renewable_Energy.xls',index_col=0,Header=None) # open the PV energy yield file
Renewable_Energy = Renewable_Energy/1000
Renewable_Energy = round(Renewable_Energy, 3)

def Initialize_Renewable_Energy(model, s,r,t):
    '''
    This function returns the value of the energy yield by one PV under the characteristics of the system 
    analysis for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The energy yield of one PV for the period t.
    '''

    column = (s-1)*model.Renewable_Source + r 
    return float(Renewable_Energy[column][t])   
    
def Initialize_Renewable_Energy_Dispatch(model, r, t):
    '''
    '''
    
    return float(Renewable_Energy[r][t])    
    
def Marginal_Cost_Generator_1_Dispatch(model):
    
    return model.Diesel_Cost/(model.Low_Heating_Value*model.Generator_Efficiency)

def Start_Cost_Dispatch(model):
    
    return model.Marginal_Cost_Generator_1*model.Generator_Nominal_Capacity*model.Cost_Increase

def Marginal_Cost_Generator_Dispatch(model):
    
    return (model.Marginal_Cost_Generator_1*model.Generator_Nominal_Capacity-model.Start_Cost_Generator)/model.Generator_Nominal_Capacity 

def Min_Bat_Capacity(model):
        
    
    Periods = model.Battery_Independency*24
    Len = int(model.Periods/Periods)
    Grouper = 1
    index = 1
    for i in range(1, Len+1):
        for j in range(1,Periods+1):
            
            Energy_Demand.loc[index, 'Grouper'] = Grouper
            index += 1
            
        Grouper += 1
            
    Period_Energy = Energy_Demand.groupby(['Grouper']).sum()
    
    Period_Average_Energy = Period_Energy.mean()
    
    Available_Energy = sum(Period_Average_Energy[s]*model.Scenario_Weight[s] 
        for s in model.scenario) 
    
    a =  Available_Energy/(1-model.Deep_of_Discharge)
    return round(a,3) 

