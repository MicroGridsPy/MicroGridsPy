
import pandas as pd

def Initialize_years(model, i):

    '''
    This function returns the value of each year of the project. 
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The year i.
    '''    
    return i

Energy_Demand = pd.read_excel('Example/Demand.xls') # open the energy demand file

def Initialize_Demand(model, i, t):
    '''
    This function returns the value of the energy demand from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: The energy demand for the period t.     
        
    '''
    return float(Energy_Demand[i][t])

PV_Energy = pd.read_excel('Example/PV_Energy.xls') # open the PV energy yield file

def Initialize_PV_Energy(model, i, t):
    '''
    This function returns the value of the energy yield by one PV under the characteristics of the system 
    analysis for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The energy yield of one PV for the period t.
    '''
    return float(PV_Energy[i][t])

def Initialize_Demand_Dispatch(model, t):
    '''
    This function returns the value of the energy demand from a system for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
        
    :return: The energy demand for the period t.     
        
    '''
    return float(Energy_Demand[1][t])


def Initialize_PV_Energy_Dispatch(model, t):
    '''
    This function returns the value of the energy yield by one PV under the characteristics of the system 
    analysis for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The energy yield of one PV for the period t.
    '''
    return float(PV_Energy[1][t])
    
    
def Marginal_Cost_Generator_1(model,i):
    
    return model.Fuel_Cost[i]/(model.Low_Heating_Value[i]*model.Generator_Efficiency[i])

def Start_Cost(model,i):
    
    return model.Marginal_Cost_Generator_1[i]*model.Generator_Nominal_Capacity[i]*model.Cost_Increase[i]

def Marginal_Cost_Generator(model, i):
    
    return (model.Marginal_Cost_Generator_1[i]*model.Generator_Nominal_Capacity[i]-model.Start_Cost_Generator[i])/model.Generator_Nominal_Capacity[i] 


def Capital_Recovery_Factor(model):
   
    a = model.Discount_Rate*((1+model.Discount_Rate)**model.Years)
    b = ((1 + model.Discount_Rate)**model.Years)-1
    return a/b

    
def Battery_Reposition_Cost(model):
   
   
    return model.Battery_Invesment_Cost/model.Battery_Cycles
    
    
Renewable_Energy = pd.read_excel('Example/Renewable_Energy.xls') # open the PV energy yield file

def Initialize_Renewable_Energy(model, s,r,t):
    '''
    This function returns the value of the energy yield by one PV under the characteristics of the system 
    analysis for each period of analysis from a excel file.
    
    :param model: Pyomo model as defined in the Model_Creation script.
    
    :return: The energy yield of one PV for the period t.
    '''
    column = (s-1)*model.Renewable_Source + r 
    return float(PV_Energy[column][t])   
    
    
    
def Marginal_Cost_Generator_1_Dispatch(model):
    
    return model.Diesel_Cost/(model.Low_Heating_Value*model.Generator_Efficiency)

def Start_Cost_Dispatch(model):
    
    return model.Marginal_Cost_Generator_1*model.Generator_Nominal_Capacity*model.Cost_Increase

def Marginal_Cost_Generator_Dispatch(model):
    
    return (model.Marginal_Cost_Generator_1*model.Generator_Nominal_Capacity-model.Start_Cost_Generator)/model.Generator_Nominal_Capacity 
