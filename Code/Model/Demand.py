import re, time, pandas as pd, numpy as np
import os

def data_import(data_demand):
    for value in data_demand:
        if "param: lat" in value:
            lat = (value[value.index('=')+1:value.index(';')])
            numbers = re.compile('-?\d+')
            lat = list(map(int, numbers.findall(lat)))[0]
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
        if "param: Years" in value:
            years = int(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
        if "param: Periods" in value:
            periods = int(value[value.index('=')+1:value.index(';')].replace(' ','').replace("'",""))
    
    return F, cooling_period, [h_tier1, h_tier2, h_tier3, h_tier4, h_tier5], [num_hosp_1, num_hosp_2, num_hosp_3, num_hosp_4, num_hosp_5,num_schools], demand_growth, years, periods

#%% Calculates the load demand given as input the latitude, cooling period and number of households for each wealth tier and number of services (schools and hospitals)

def aggregate_load(load_data, periods):
    # Number of hours in the dataset
    total_hours = len(load_data)

    # Calculate aggregation factor
    agg_factor = total_hours // periods

    # Aggregate data
    aggregated_load = load_data.groupby(load_data.index // agg_factor).sum()

    return aggregated_load

def demand_calculation():
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
    data_demand = open(data_file_path).readlines()
    
    num_h_tier = []
    
    F, cooling_period, num_h_tier, num_services, demand_growth, years, periods = data_import(data_demand)
    
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
    demand_archetypes_path = "../Demand_archetypes/"

    for ii in range(1, len(num_h_tier) + 1):
        households.append(household(F, ii, cooling_period, num_h_tier[ii - 1]))
        h_load_name = households[ii - 1].cooling + '_' + F + '_Tier-' + str(ii)
        file_path = os.path.join(demand_archetypes_path, h_load_name + ".xlsx")
        h_load = pd.DataFrame(pd.read_excel(file_path, skiprows=0, usecols="B"))
        h_load = aggregate_load(h_load, periods)
        load_households.append(household.load_demand(households[ii - 1], h_load))
        
    load_households = pd.concat([sum(load_households)]*years, axis = 1, ignore_index = True)       
            
    #%% Load demand of services    
    services = []
    load_tot_services = []
    for ii in range(1, len(num_services) + 1):
        services.append(service(ii, num_services[ii-1]))
        if ii < 6:
            service_load_name = "HOSPITAL_Tier-" + str(ii)
        else: 
            service_load_name = "SCHOOL"
        file_path = os.path.join(demand_archetypes_path, service_load_name + ".xlsx")
        service_load = pd.DataFrame(pd.read_excel(file_path, skiprows=0, usecols="B"))
        service_load = aggregate_load(service_load, periods)  # Aggregate service load data
        load_tot_services.append(services[ii-1].load_demand(service_load))
    
    load_tot_services = pd.concat([sum(load_tot_services)]*years, axis = 1, ignore_index = True) 
    
    # Total load demand (households + services)   
    
    load_total = load_tot_services + load_households
    for column in load_total:
        if column == 0:
            continue
        else: 
            load_total[column] = load_total[column-1]*(1+demand_growth/100)    # yearly demand growth 

    return load_total, years
    
    #%% Export results to excel
def excel_export(load,years):
    # Setting new column names based on the number of years
    load = load.set_axis(np.arange(1, years+1), axis=1)
    
    current_directory = os.path.dirname(os.path.abspath(__file__))
    inputs_directory = os.path.join(current_directory, '..', 'Inputs')
    demand_file_path = os.path.join(inputs_directory, 'Demand.csv')
    # Exporting the DataFrame to a CSV file
    load.to_csv(demand_file_path, sep=';', decimal=',', index=True)


#%% Calculates and export the load demand  time series of households and services for 20 years to Demand.xlsx

def demand_generation():
    start = time.time()
        
    print("Load demand calculation started, please remember to close Demand.xlsx... \n")
    load_tot, years = demand_calculation()
    excel_export(load_tot,years)
    
    
    end = time.time()
    elapsed = end - start
    load_tot = load_tot.set_axis(np.arange(1,years+1), axis=1)
    print('\n\nLoad demand calculation completed (overall time: ',round(elapsed,0),'s,', round(elapsed/60,1),' m)\n')
    return load_tot

if __name__ == "__Demand__":
    demand_calculation()
    demand_generation()

