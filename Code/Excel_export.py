import pandas as pd, numpy as np, xlsxwriter

def excel_export(energy_PV,energy_WT):
    energy_PV_lst = []
    energy_WT_lst = []
    counter = 1
    matrix = []
    for months in range(0,len(energy_PV)):
        for day in range(0,len(energy_PV[months])):
            for hour in range(0,len(energy_PV[months][day])):
                energy_PV_lst.append(energy_PV[months][day][hour])           #list of hourly PV en. production [kWh]
                energy_WT_lst.append(energy_WT[months][day][hour])
                matrix.append([counter, energy_PV[months][day][hour], energy_WT[months][day][hour]])
                counter = counter +1
                
    '''for months in energy_WT:
        for month in months:
            for day in month:
                energy_WT_lst.append(day)    '''                           #list of hourly WT en. production [kWh]
    '''indx = np.array(range(1,8761)).tolist()   
    dataf = pd.concat([pd.DataFrame(indx),pd.DataFrame(energy_PV_lst), pd.DataFrame(energy_WT_lst)], axis = 1) 
    df2 = pd.DataFrame([None,1,2])   '''  
    dataf = pd.DataFrame(matrix)
    dataf = dataf.set_axis([None,1,2], axis=1, inplace=False)
    dataf.to_excel(r'C:\Users\ivans\Desktop\TESI\MicroGridsPy-SESAM-MYCE\Code\Inputs\Renewable_Energy.xlsx', index = False, header = True, startrow = 0, startcol = 0)
    
    return