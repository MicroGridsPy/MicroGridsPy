

from Demand_calculation import demand_calculation, excel_export
import time

#%% Calculates and export the load demand  time series of households and services for 20 years to Demand.xlsx

def demand_generation():
    start = time.time()
        
    print("Load demand calculation started, please remember to close Demand.xlsx... \n")
    
    excel_export(demand_calculation())
    
    
    end = time.time()
    elapsed = end - start
    print('\n\nLoad demand calculation completed (overall time: ',round(elapsed,0),'s,', round(elapsed/60,1),' m)\n')

