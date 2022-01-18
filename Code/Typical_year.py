from collections import defaultdict
import operator, numpy as np, json, pandas as pd

#%% Download JSON data for the 4 URLs of daily and hourly parameters using multiple threads

import concurrent.futures
from RE_input_data import get_data
def multithread_data_download(URL_list):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        jsdata = list(executor.map(get_data, URL_list)) 
    return jsdata

#%% Function for bilinear interpolation 

def bilinear_interpolation(x, y, points):
    '''Interpolate (x,y) from values associated with four points.

    The four points are a list of four triplets:  (x, y, value)'''

      
    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)

#%% Converts JSON data into lists and applies 2D interpolation 
import math
def data_2D_interpolation(jsdata, date_start, date_end, lat, lon,lat_ext, lon_ext):
    ''' Here converting JSON daily data into daily annidated list param_daily_list '''
    jsdata_daily = jsdata[0:4]
    jsdata_hourly = jsdata[4:8]
    param_daily_list = []
    for jsdata_d in jsdata_daily:
        pydata_d = json.loads(jsdata_d)
        param_daily = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(4)]
        param_daily_str = ['ALLSKY_SFC_SW_DWN','T2MWET','T2M','WS50M']    
        keys = pydata_d['properties']['parameter'][param_daily_str[0]].keys()
        for pp in range(len(param_daily_str)):   
            jj = int(date_start[7:11])
            month = 1
            year = 0
            for key in keys:
                if pydata_d['properties']['parameter'][param_daily_str[pp]][key] < -990:             #check for missing values (equal to 0)
                   pydata_d['properties']['parameter'][param_daily_str[pp]][key] = 0
                
                if month>=10:
                    mm = str(month)
                else: 
                    mm = '0' + str(month)
                         
                if jj == int(key[0:4]) and mm == key[4:6]:
                    param_daily[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str[pp]][key]) 
                                
                elif jj == int(key[0:4]) and mm != key[4:6]:
                    month = month + 1
                    param_daily[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str[pp]][key])
                                  
                elif jj != int(key[0:4]):
                    month = 1 
                    year = year+1   
                    param_daily[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str[pp]][key])
                    jj = jj+1
        param_daily_list.append(param_daily)
    ''' Here converting JSON hourly data into hourly annidated list param_hourly_list'''   
    param_hourly_list = [] 
    for jsdata_h in jsdata_hourly:
        pydata = json.loads(jsdata_h)
        param_hourly = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(4)]
        for ii in range(len(param_hourly)):
            for jj in range(len(param_hourly[ii])):
                for kk in range(len(param_daily[ii][jj])):
                    param_hourly[ii][jj][kk] = [[] for ii in range(len(param_daily[ii][jj][kk]))]
        param_hourly_str = ['WS50M','WS2M', 'WD50M','T2M']    
        keys = pydata['properties']['parameter'][param_hourly_str[0]].keys()
        for param in range(len(param_hourly_str)):  
            jj = int(date_start[7:11])
            day_counter = 1
            month_counter = 1
            year_counter = 0
            for key in keys:
                if pydata['properties']['parameter'][param_hourly_str[param]][key] < -990:             
                   pydata['properties']['parameter'][param_hourly_str[param]][key] = 0
                
                if month_counter>=10:
                    mm = str(month_counter)
                else: 
                    mm = '0' + str(month_counter)
                if day_counter>=10:
                    dd = str(day_counter)
                else:
                    dd = '0' + str(day_counter)
                         
                if jj == int(key[0:4]) and mm == key[4:6] and dd == key[6:8]:
                    param_hourly[param][year_counter][month_counter-1][day_counter-1].append(pydata['properties']['parameter'][param_hourly_str[param]][key]) 
                elif jj == int(key[0:4]) and mm == key[4:6] and dd != key[6:8]:
                    day_counter = day_counter + 1
                    param_hourly[param][year_counter][month_counter-1][day_counter-1].append(pydata['properties']['parameter'][param_hourly_str[param]][key])
                elif jj == int(key[0:4]) and mm != key[4:6]:
                    day_counter = 1
                    month_counter = month_counter + 1
                    param_hourly[param][year_counter][month_counter-1][day_counter-1].append(pydata['properties']['parameter'][param_hourly_str[param]][key])
                elif jj != int(key[0:4]):
                    day_counter = 1
                    month_counter = 1 
                    year_counter = year_counter+1   
                    param_hourly[param][year_counter][month_counter-1][day_counter-1].append(pydata['properties']['parameter'][param_hourly_str[param]][key])
                    jj = jj+1
                    
        param_hourly_list.append(param_hourly)
        
    ''' Here applies bilinear interpolation function to daily and hourly lists '''
    lat_min = lat_ext[0]
    lat_max = lat_ext[1]
    lon_min = lon_ext[0]
    lon_max = lon_ext[1]
    param_daily_interp = param_daily_list[0]
    param_hourly_interp = param_hourly_list[0]
    ''' Check if coordinates coincide with a point covered by data (interpolation would fail)'''
    if math.modf(lat)[0] == 0 and math.modf(lon)[0] == 0:       
       return param_daily_interp, param_hourly_interp
    else:    
        for param in range(len(param_hourly_list[0])):
            for year in range(len(param_hourly_list[0][param])):
                for month in range(len(param_hourly_list[0][param][year])):
                    for day in range(len(param_hourly_list[0][param][year][month])):
                        points_daily = [(lat_min, lon_min, param_daily_list[0][param][year][month][day]), (lat_min, lon_max, param_daily_list[1][param][year][month][day]), (lat_max, lon_min, param_daily_list[2][param][year][month][day]), (lat_max, lon_max, param_daily_list[3][param][year][month][day])]
                        param_daily_interp[param][year][month][day] = bilinear_interpolation(lat, lon, points_daily)
                        for hour in range(len(param_hourly_list[0][param][year][month][day])):
                            points_hourly = [(lat_min, lon_min, param_hourly_list[0][param][year][month][day][hour]), (lat_max, lon_min, param_hourly_list[1][param][year][month][day][hour]), (lat_min, lon_max, param_hourly_list[2][param][year][month][day][hour]), (lat_max, lon_max, param_hourly_list[3][param][year][month][day][hour])]
                            param_hourly_interp[param][year][month][day][hour] = bilinear_interpolation(lat, lon, points_hourly)
                        
        return param_daily_interp, param_hourly_interp

#%% Finds the list of most representative year for each month (best_years) and returns the nested  list of typical daily values (param_typical_daily) given as input param_daily

def typical_year_daily(param_daily, date_start, date_end):          
    
    #the list param_daily is re-ordered and first cumulate is calculated
    param_daily_ord = [[[]for ii in range(12)]for ii in range(len(param_daily))]
    cdf_1 = [[defaultdict(list) for ii in range(0,12)]for ii in range(len(param_daily))]
    phi_1 = [[[[] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(12)]for ii in range(len(param_daily))]
    f_2 = [[[[] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(12)]for ii in range(len(param_daily))]
    fs = [[defaultdict(list) for ii in range(12)]for ii in range(len(param_daily))]
    
    
    for ii in range(len(param_daily)):
        for jj in range(len(param_daily[ii])):
            for kk in range(len(param_daily[ii][jj])):
                     param_daily_ord[ii][kk] = sorted(param_daily_ord[ii][kk] + param_daily[ii][jj][kk])
    for ii in range(len(param_daily_ord)):
        for jj in range(len(param_daily_ord[ii])):                
            for kk in range(len(param_daily_ord[ii][jj])):
                cdf_1[ii][jj][str(param_daily_ord[ii][jj][kk])].append((kk+1)/len(param_daily_ord[ii][jj]))
    
    for ii in range(len(cdf_1)):
        for jj in range(len(cdf_1[ii])):
                for kk in range(len(phi_1[ii][jj])):
                    for yy in range(len(param_daily[ii][kk][jj])):
                        for key in cdf_1[ii][jj]:
                            if str(param_daily[ii][kk][jj][yy]) == key and len(cdf_1[ii][jj][key]) == 1:
                                 phi_1[ii][jj][kk].append(cdf_1[ii][jj][key][0])
                            elif str(param_daily[ii][kk][jj][yy]) == key and len(cdf_1[ii][jj][key]) > 1:
                                 phi_1[ii][jj][kk].append(cdf_1[ii][jj][key][0])
                                 cdf_1[ii][jj][key].pop(0)
                            else:
                                 continue
    
    #the second cumulate is calculated
    param_daily_ord_2 = [[[] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(len(param_daily))]
    cdf_2 = [[defaultdict(list) for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(len(param_daily))]
    
    for ii in range(len(param_daily)):
        for jj in range(len(param_daily[ii])):
            for kk in range(len(param_daily[ii][jj])):
                param_daily_ord_2[ii][jj] = sorted(param_daily_ord_2[ii][jj] + (param_daily[ii][jj][kk]))
    
    for ii in range(len(param_daily_ord_2)):
        for jj in range(len(param_daily_ord_2[ii])):
            for kk in range(len(param_daily_ord_2[ii][jj])):
                cdf_2[ii][jj][param_daily_ord_2[ii][jj][kk]].append((kk+1)/(len(param_daily_ord_2[ii][jj])))
    
    for ii in range(len(cdf_1)):
        for jj in range(len(cdf_1[ii])):
                for kk in range(len(f_2[ii][jj])):
                    for yy in range(len(param_daily[ii][kk][jj])):
                        for key in cdf_2[ii][kk]:
                            if (param_daily[ii][kk][jj][yy]) == key and len(cdf_2[ii][kk][key]) == 1:
                                 f_2[ii][jj][kk].append(cdf_2[ii][kk][key][0])
                            elif (param_daily[ii][kk][jj][yy]) == key and len(cdf_2[ii][kk][key]) > 1:
                                 f_2[ii][jj][kk].append(cdf_2[ii][kk][key][0])
                                 cdf_2[ii][kk][key].pop(0)
                            else:
                                 continue
                
                    fs[ii][jj][str(kk)] = np.absolute(np.subtract(f_2[ii][jj][kk],phi_1[ii][jj][kk]))    #Finkelstein-Shafer statistics is applied
                    fs[ii][jj][str(kk)] = sum(fs[ii][jj][str(kk)][:])
                
                
    # choice of the best years for each month according to primary and secondary parameters
    
    sum_prim = [dict() for ii in range(len(fs[0]))]
    best_prim = [[] for ii in range(12)]
    
    #first 3 best years according to the minimum sum of primary parameters are collected into best_prim
    
    for jj in range(len(fs[0])):
        for key in fs[0][jj]:
            sum_prim[jj][key] =  fs[0][jj][key] + fs[1][jj][key] + fs[2][jj][key]
            best_prim[jj] = sorted(sum_prim[jj].items(),key=operator.itemgetter(1))[0:3]        
            
    #among the 3 best years for each month according to primary parameters, the one having the lowest deviation between monthly mean and long-term monthly mean (calc. for all years for that month) is picked
    
    diff_sec = [dict() for ii in range(12)]
    long_term_average = [[] for ii in range(12)]
    best_years = [[] for ii in range(12)]
    
    for ii in range(len(param_daily[3])):
        for jj in range(len(param_daily[3][ii])):
            long_term_average[jj].append(sum(param_daily[3][ii][jj])/len(param_daily[3][ii][jj]))
    for ii in range(len(long_term_average)):
        long_term_average[ii] = sum(long_term_average[ii])/len(long_term_average[ii])        
            
    for ii in range(len(best_prim)):
        for jj in range(len(best_prim[ii])):
            diff_sec[ii][best_prim[ii][jj][0]] = abs(np.mean(param_daily[3][int(best_prim[ii][jj][0])][ii]) - long_term_average[ii]) 
        best_years[ii] = min(diff_sec[ii], key=diff_sec[ii].get) 
    
    param_typical_daily = [[[] for ii in range(12)] for ii in range(len(param_daily))]    
    
    for ii in range(len(param_daily)):
        for jj in range(len(param_typical_daily[ii])):
            param_typical_daily[ii][jj] = param_daily[ii][int(best_years[jj])][jj]
            
            # removes data for 29 feb if TMY is a leap year
            
        if len(param_typical_daily[ii][1]) == 29:
            param_typical_daily[ii][1].remove(param_typical_daily[ii][1][28])         
    return (best_years,param_typical_daily)

#%% Returns the nested list of hourly values for the typical year (param_typical_hourly) taking as input the best_years list and param_hourly

def typical_year_hourly(best_years, param_hourly_interp):
    
    param_typical_hourly = [[[] for ii in range(12)] for ii in range(len(param_hourly_interp))]
    for param in range(len(param_hourly_interp)):    
        for month in range(12):
            for day in range(len(param_hourly_interp[param][int(best_years[month])][month])):                       
                param_typical_hourly[param][month].append(param_hourly_interp[param][int(best_years[month])][month][day])
                
                # removes data for 29 feb if TMY is a leap year
                
        if len(param_typical_hourly[param][1]) == 29:
            param_typical_hourly[param][1].remove(param_typical_hourly[param][1][28])
    return param_typical_hourly

#%% Function to export time-series to excel file

def excel_export(energy_PV,energy_WT):
    energy_PV_lst = []
    energy_WT_lst = []
    counter = 1
    matrix = []
    for months in range(0,len(energy_PV)):
        for day in range(0,len(energy_PV[months])):
            for hour in range(0,len(energy_PV[months][day])):
                energy_PV_lst.append(energy_PV[months][day][hour])           
                energy_WT_lst.append(energy_WT[months][day][hour])
                matrix.append([counter, energy_PV[months][day][hour], energy_WT[months][day][hour]])
                counter = counter +1
    dataf = pd.DataFrame(matrix)
    dataf = dataf.set_axis([None,1,2], axis=1, inplace=False)
    dataf.to_excel(r'C:\Users\ivans\Desktop\TESI\MicroGridsPy-SESAM-MYCE\Code\Inputs\Renewable_Energy.xlsx', index = False, header = True, startrow = 0, startcol = 0)

    return
                
                
    
                           
       
        
        