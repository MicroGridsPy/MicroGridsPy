''' Imports input data from "Demand.dat"'''

import re

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
            
            
        
        
                
    

