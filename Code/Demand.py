''' Imports input data from "Demand.dat"'''

import re, time, pandas as pd, numpy as np

def data_import(data_demand, data):
    for value in data_demand:
        if "param: lat" in value:
            lat = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
            if  10 <= lat <=20:
                F = 'F1'
            elif -10 <= lat < 10:
                F = 'F2'
            elif -20 <= lat < -10:
                F = 'F3'
            elif -30<= lat < -20:
                F = 'F4'
            elif lat < -30:
                F = 'F5'
        if "param: cooling_period" in value:
            cooling_period = value[value.index('=')+1:value.index(';')].replace(' ','').replace("'","")
        if "param: h_tier1" in value:
            h_tier1 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: h_tier2" in value:
            h_tier2 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: h_tier3" in value:
            h_tier3 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: h_tier4" in value:
            h_tier4 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: h_tier5" in value:
            h_tier5 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: schools" in value:
            num_schools = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: hospital_1" in value:
            num_hosp_1 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: hospital_2" in value:
            num_hosp_2 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: hospital_3" in value:
            num_hosp_3 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: hospital_4" in value:
            num_hosp_4 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: hospital_5" in value:
            num_hosp_5 = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: demand_growth" in value:
            demand_growth = float(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
    for value in data:
        
        if "param: Years" in value:
            years = int(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
    
    return F, cooling_period, [h_tier1, h_tier2, h_tier3, h_tier4, h_tier5], [num_hosp_1, num_hosp_2, num_hosp_3, num_hosp_4, num_hosp_5,num_schools], demand_growth, years

#%% Calculates the load demand given as input the latitude, cooling period and number of households for each wealth tier and number of services (schools and hospitals)

def demand_calculation():
    
    data_demand = open("Inputs/Demand_data.dat").readlines()
    data = open("Inputs/Model_data.dat").readlines()
    
    num_h_tier = []
    
    F, cooling_period, num_h_tier, num_services, demand_growth, years = data_import(data_demand,data)
    
    class household:
      def __init__(self, zone, wealth, cooling, number):
        self.zone = zone
        self.wealth = wealth
        self.cooling = cooling
        self.number = number
    
      def load_demand(self, h_load):
          load = self.number/100 * h_load
          return load
      
    class service:
        def __init__(self, structure, number):
            self.structure = structure
            self.number = number
        
        def load_demand(self, h_load):
            load = self.number * h_load
            return load
        
    households = []
    load_households = []  
    for ii in range(1,len(num_h_tier)+1):
        households.append(household(F, ii, cooling_period, num_h_tier[ii-1]))
        h_load_name = households[ii-1].cooling + '_' + F + '_Tier-' + str(ii)
        h_load = pd.DataFrame(pd.read_excel("Demand_archetypes/" + h_load_name +".xlsx", skiprows = 0, usecols = "B")) 
        load_households.append(household.load_demand(households[ii-1], h_load))
        
    load_households = pd.concat([sum(load_households)]*years, axis = 1, ignore_index = True)       
            
    #%% Load demand of services    
    services = []
    load_tot_services = []
    for ii in range(1,len(num_services)+1):
        services.append(service(ii, num_services[ii-1]))
        if ii < 6:
            service_load_name = "HOSPITAL_Tier-"+str(ii)
        else: service_load_name = "SCHOOL" 
        service_load = pd.DataFrame(pd.read_excel("Demand_archetypes/"+service_load_name+".xlsx", skiprows = 0, usecols = "B"))
        load_tot_services.append(services[ii-1].load_demand(service_load))
    
    load_tot_services = pd.concat([sum(load_tot_services)]*years, axis = 1, ignore_index = True) 
    
    # Total load demand (households + services)   
    
    load_total = load_tot_services + load_households
    for column in load_total:
        if column == 0:
            continue
        else: 
            load_total[column] = load_total[column-1]*(1+demand_growth/100)    # yearly demand growth 

    return load_total
    
    #%% Export results to excel
def excel_export(load, n_years):
    
    load = load.set_axis(np.arange(1,n_years+1), axis=1, inplace=False)
    
    load.to_excel("Inputs/Demand.xlsx")


#%% Calculates and export the load demand  time series of households and services for 20 years to Demand.xlsx

def demand_generation(n_years):
    start = time.time()
        
    print("Load demand calculation started, please remember to close Demand.xlsx... \n")
    load_tot = demand_calculation()
    load_tot = load_tot.set_axis(np.arange(1,n_years+1), axis=1, inplace=False)
    excel_export(load_tot, n_years)
    
    
    end = time.time()
    elapsed = end - start
    print('\n\nLoad demand calculation completed (overall time: ',round(elapsed,0),'s,', round(elapsed/60,1),' m)\n')
    return load_tot

if __name__ == "__Demand__":
    demand_calculation()
    demand_generation(n_years)

