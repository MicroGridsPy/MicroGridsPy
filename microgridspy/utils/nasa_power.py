from collections import defaultdict
import time, sys, concurrent.futures, urllib.request, urllib.parse, urllib.error    
import pandas as pd, math, numpy as np, bisect, json, operator
import os
from config.path_manager import PathManager

### Import URL components for the POWER API by NASA and generate the URL (two different functions depending on time resolution)
def URL_creation_d(base_URL: str, loc_id: str, parameters_1: str, parameters_2: str, date_start: str, date_end: str, community: str, temp_res: str, output_format: str, time_zone: int, lat: float, lon: float):
    """Generates the URLs for daily data retrieval from the POWER API by NASA."""
    loc_id = '/' + loc_id
    parameters_1 = '?parameters=' + parameters_1
    parameters_2 = '?parameters=' + parameters_2
    date_start = '&start=' + date_start
    date_end = '&end=' + date_end
    community = '&community=' + community
    temp_res = temp_res
    output_format = '&format' + output_format
    standard_lon = 15*time_zone

    URL_1 = []
    URL_2 = []

    lat_ext_1 = [math.floor(lat), math.ceil(lat)]        #grid boundaries of 1° x 1° spatial grid
    lon_ext_1 = [math.floor(lon), math.ceil(lon)]
    
    lat_grid_2 =  np.arange(-90, 90, 0.5)             
    lon_grid_2 = np.arange(-180,180,0.625)
    
    lat_ext_2 = [lat_grid_2[bisect.bisect_left(lat_grid_2.tolist(),lat)-1], lat_grid_2[bisect.bisect_left(lat_grid_2,lat)]]  #here finds the 
    lon_ext_2 = [lon_grid_2[bisect.bisect_left(lon_grid_2.tolist(),lon)-1], lon_grid_2[bisect.bisect_left(lon_grid_2,lon)]]
    
    '''Generates a daily URL for each node of the square'''
    for ii in range(2):
        URL_1.append((base_URL + temp_res + loc_id + parameters_1 + community + '&longitude=' + str(lon_ext_1[ii]) + '&latitude=' + str(lat_ext_1[0]) + date_start + date_end +  output_format).replace("'","") + "&time-standard=utc")
        URL_1.append((base_URL + temp_res + loc_id + parameters_1 + community + '&longitude=' + str(lon_ext_1[ii]) + '&latitude=' + str(lat_ext_1[1]) + date_start + date_end +  output_format).replace("'","")+ "&time-standard=utc")

    for ii in range(2):
        URL_2.append((base_URL + temp_res + loc_id + parameters_2 + community + '&longitude=' + str(lon_ext_2[ii]) + '&latitude=' + str(lat_ext_2[0]) + date_start + date_end +  output_format).replace("'","")+ "&time-standard=utc")
        URL_2.append((base_URL + temp_res + loc_id + parameters_2 + community + '&longitude=' + str(lon_ext_2[ii]) + '&latitude=' + str(lat_ext_2[1]) + date_start + date_end +  output_format).replace("'","")+ "&time-standard=utc")
    
    return date_start, date_end, lat, lon, lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2, standard_lon, URL_1, URL_2


def URL_creation_h(base_URL: str, loc_id: str, parameters: str, date_start: str, date_end: str, community: str, temp_res: str, output_format: str, lat: float, lon: float) -> list:
    """Generates the URLs for hourly data retrieval from the POWER API by NASA."""
    loc_id = '/' + loc_id
    parameters = '?parameters=' + parameters
    date_start = '&start=' + date_start
    date_end = '&end=' + date_end
    community = '&community=' + community
    temp_res = temp_res
    output_format = '&format' + output_format

    URL = []

    lat_grid =  np.arange(-90, 90, 0.5)             
    lon_grid = np.arange(-180,180,0.625)
    lat_ext = [lat_grid[bisect.bisect_left(lat_grid.tolist(),lat)-1], lat_grid[bisect.bisect_left(lat_grid,lat)]]  #here finds the 
    lon_ext = [lon_grid[bisect.bisect_left(lon_grid.tolist(),lon)-1], lon_grid[bisect.bisect_left(lon_grid,lon)]]
    
    # generates a daily URL for each node of the square
    for ii in range(2):
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[0]) + date_start + date_end +  output_format).replace("'","")+ "&time-standard=utc")
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[1]) + date_start + date_end +  output_format).replace("'","")+ "&time-standard=utc")

    return URL

# Wind turbine parameters        
def wind_parameters(turbine_model: str, type_turb: str):
    
    # Construct the sheet name for the turbine model
    full_sheet_name = f"{turbine_model} - {type_turb}"
    
    # Read the specific sheet for the turbine model
    df = pd.read_excel(PathManager.POWER_CURVE_FILE_PATH, sheet_name=full_sheet_name)

    # Extract parameters from the first few rows and convert them to floats
    rot_diam = float(df.iloc[0, 1])
    rot_height = float(df.iloc[1, 1])

    # Extract power curve data and convert to float
    power_curve = df.iloc[3:, 1].astype(float).tolist()


    if type_turb == 'Horizontal Axis':
        surface_area = math.pi * (rot_diam ** 2) / 4
    else:
        surface_area = rot_height * math.pi * rot_diam

    return power_curve, surface_area, rot_height

# Retrieves JSON daily and hourly data from POWER API 
def get_data(URL: str):
    """Retrieves JSON data from the POWER API by NASA."""
    try:
        with urllib.request.urlopen(URL) as URL_handle:
            jsdata = URL_handle.read().decode()
        return jsdata
    except urllib.error.URLError as e:
        raise ConnectionError(f"Error retrieving data from {URL}: {e}")

#%% Data processing and typical year calculation functions

### Download JSON data for the 4 URLs of daily and hourly parameters using multiple threads

def multithread_data_download(URL_list):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        jsdata = list(executor.map(get_data, URL_list)) 
    return jsdata

### Function for bilinear interpolation 

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

### Converts JSON data into lists and applies 2D interpolation

def data_2D_interpolation(jsdata, date_start, date_end, lat, lon,lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2):
    ''' Here converting JSON daily data into daily annidated list param_daily_list '''
    jsdata_daily_1 = jsdata[0:4]
    jsdata_daily_2 = jsdata[4:8]
    jsdata_hourly = jsdata[8:12]
    param_daily_list = []
    param_daily_str_1 = ['ALLSKY_SFC_SW_DWN'] 
    param_daily_str_2 = ['T2MWET','T2M','WS50M']   
    
    for jsdata_d_1 in jsdata_daily_1:
        pydata_d = json.loads(jsdata_d_1)    
        keys = pydata_d['properties']['parameter'][param_daily_str_1[0]].keys() 
        param_daily_1 = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(1)] 
        for pp in range(len(param_daily_str_1)):   
            jj = int(date_start[7:11])
            month = 1
            year = 0
            for key in keys:
                if pydata_d['properties']['parameter'][param_daily_str_1[pp]][key] < -990:             #check for missing values (equal to 0)
                   pydata_d['properties']['parameter'][param_daily_str_1[pp]][key] = 0
                
                if month>=10:
                    mm = str(month)
                else: 
                    mm = '0' + str(month)
                         
                if jj == int(key[0:4]) and mm == key[4:6]:
                    param_daily_1[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_1[pp]][key]) 
                                
                elif jj == int(key[0:4]) and mm != key[4:6]:
                    month = month + 1
                    param_daily_1[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_1[pp]][key])
                                  
                elif jj != int(key[0:4]):
                    month = 1 
                    year = year+1   
                    param_daily_1[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_1[pp]][key])
                    jj = jj+1
            param_daily_list.append(param_daily_1)
    
    for jsdata_d_2 in jsdata_daily_2:
        pydata_d = json.loads(jsdata_d_2) 
        keys = pydata_d['properties']['parameter'][param_daily_str_2[0]].keys() 
        param_daily_2 = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(3)]
        for pp in range(len(param_daily_str_2)):   
            jj = int(date_start[7:11])
            month = 1
            year = 0
            for key in keys:
                if pydata_d['properties']['parameter'][param_daily_str_2[pp]][key] < -990:             #check for missing values (equal to 0)
                   pydata_d['properties']['parameter'][param_daily_str_2[pp]][key] = 0
                
                if month>=10:
                    mm = str(month)
                else: 
                    mm = '0' + str(month)
                         
                if jj == int(key[0:4]) and mm == key[4:6]:
                    param_daily_2[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_2[pp]][key]) 
                                
                elif jj == int(key[0:4]) and mm != key[4:6]:
                    month = month + 1
                    param_daily_2[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_2[pp]][key])
                                  
                elif jj != int(key[0:4]):
                    month = 1 
                    year = year+1   
                    param_daily_2[pp][year][month-1].append(pydata_d['properties']['parameter'][param_daily_str_2[pp]][key])
                    jj = jj+1
        param_daily_list.append(param_daily_2)
    
    ''' Here converting JSON hourly data into hourly annidated list param_hourly_list'''   
    param_hourly_list = [] 
    for jsdata_h in jsdata_hourly:
        pydata = json.loads(jsdata_h)
        param_hourly = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(4)]
        for ii in range(len(param_hourly)):
            for jj in range(len(param_daily_2[0])):
                for kk in range(12):
                    param_hourly[ii][jj][kk] = [[] for yy in range(len(param_daily_2[0][jj][kk]))]
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
    lat_min_1 = lat_ext_1[0]     #1 is used for 1° x 1° resolution, 2 for 0.5° x 0.625°
    lat_max_1 = lat_ext_1[1]
    lon_min_1 = lon_ext_1[0]
    lon_max_1 = lon_ext_1[1]
    lat_min_2 = lat_ext_2[0]
    lat_max_2 = lat_ext_2[1]
    lon_min_2 = lon_ext_2[0]
    lon_max_2 = lon_ext_2[1]
    param_daily_interp = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)] for ii in range(len(param_daily_str_1 + param_daily_str_2))]
    param_hourly_interp = [[[[] for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)] for ii in range(len(param_daily_str_1 + param_daily_str_2))]
    ''' Check if coordinates coincide with a point covered by data (interpolation would fail)'''
    if math.modf(lat)[0] == 0 and math.modf(lon)[0] == 0:      
       return param_daily_interp, param_hourly_interp
    else:    
        for param in range(len(param_hourly_list[0])):
            for year in range(len(param_hourly_list[0][param])):
                for month in range(len(param_hourly_list[0][param][year])):
                    for day in range(len(param_hourly_list[0][param][year][month])):
                        param_hourly_interp[param][year][month].append([[] for ii in range(24)])
                        if param == 0:
                            points_daily_1 = [(lat_min_1, lon_min_1, param_daily_list[0][0][year][month][day]), (lat_min_1, lon_max_1, param_daily_list[1][0][year][month][day]), (lat_max_1, lon_min_1, param_daily_list[2][0][year][month][day]), (lat_max_1, lon_max_1, param_daily_list[3][0][year][month][day])]
                            param_daily_interp[param][year][month].append(bilinear_interpolation(lat, lon, points_daily_1)) 
                        else:
                            points_daily_2 = [(lat_min_2, lon_min_2, param_daily_list[4][param-1][year][month][day]), (lat_min_2, lon_max_2, param_daily_list[5][param-1][year][month][day]), (lat_max_2, lon_min_2, param_daily_list[6][param-1][year][month][day]), (lat_max_2, lon_max_2, param_daily_list[7][param-1][year][month][day])]
                            param_daily_interp[param][year][month].append(bilinear_interpolation(lat, lon, points_daily_2))
                        for hour in range(len(param_hourly_list[0][param][year][month][day])):
                            points_hourly = [(lat_min_2, lon_min_2, param_hourly_list[0][param][year][month][day][hour]), (lat_max_2, lon_min_2, param_hourly_list[1][param][year][month][day][hour]), (lat_min_2, lon_max_2, param_hourly_list[2][param][year][month][day][hour]), (lat_max_2, lon_max_2, param_hourly_list[3][param][year][month][day][hour])]
                            param_hourly_interp[param][year][month][day][hour] = bilinear_interpolation(lat, lon, points_hourly)
                        
    return param_daily_interp, param_hourly_interp

### Finds the list of most representative year for each month (best_years) and returns the nested  list of typical daily values (param_typical_daily) given as input param_daily

def typical_year_daily(param_daily, date_start, date_end):          
    
    # the list param_daily is re-ordered and the long-term cumulate is calculated
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
    
    # the year-specific cumulate is calculated
    param_daily_ord_2 = [[[] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(len(param_daily))]
    cdf_2 = [[[defaultdict(list) for ii in range(12)] for ii in range(int(date_end[5:9])-int(date_start[7:11])+1)]for ii in range(len(param_daily))]
    
    for ii in range(len(param_daily)):
        for jj in range(len(param_daily[ii])):
            for kk in range(len(param_daily[ii][jj])):
                param_daily_ord_2[ii][jj].append(sorted(param_daily[ii][jj][kk]))  #organizing param_daily in ascending order values
    
    for ii in range(len(param_daily_ord_2)):
        for jj in range(len(param_daily_ord_2[ii])):
            for kk in range(len(param_daily_ord_2[ii][jj])):
                for day in range(len(param_daily_ord_2[ii][jj][kk])):
                    cdf_2[ii][jj][kk][param_daily_ord_2[ii][jj][kk][day]].append((day+1)/(len(param_daily_ord_2[ii][jj][kk]))) #constructing year-specific cdf
    
    for ii in range(len(cdf_1)):
        for jj in range(len(cdf_1[ii])):
                for kk in range(len(f_2[ii][jj])):
                    for yy in range(len(param_daily[ii][kk][jj])):
                        for key in cdf_2[ii][kk][jj]:
                            if (param_daily[ii][kk][jj][yy]) == key and len(cdf_2[ii][kk][jj][key]) == 1:
                                 f_2[ii][jj][kk].append(cdf_2[ii][kk][jj][key][0])                              
                            elif (param_daily[ii][kk][jj][yy]) == key and len(cdf_2[ii][kk][jj][key]) > 1:     #checking for multiple values
                                 f_2[ii][jj][kk].append(cdf_2[ii][kk][jj][key][0])                         
                                 cdf_2[ii][kk][jj][key].pop(0)
                            else:
                                 continue
    # Finkelstein-Shafer statistics is calculated
                    fs[ii][jj][str(kk)] = np.absolute(np.subtract(f_2[ii][jj][kk],phi_1[ii][jj][kk]))   #computing deviations of year-specific cdf from long-term cdf 
                    fs[ii][jj][str(kk)] = sum(fs[ii][jj][str(kk)][:])                                   #summing deviations in a month for each year
                
                
    # choice of the best years for each month according to primary and secondary parameters
    
    sum_prim = [dict() for ii in range(len(fs[0]))]
    best_prim = [[] for ii in range(12)]
    
    #first 3 best years according to the minimum sum of FS for primary parameters are collected into best_prim
    
    for jj in range(len(fs[0])):
        for key in fs[0][jj]:
            sum_prim[jj][key] =  fs[0][jj][key] + fs[1][jj][key] + fs[2][jj][key]
            best_prim[jj] = sorted(sum_prim[jj].items(),key=operator.itemgetter(1))[0:3]        
            
    #among the 3 best years for each month, the one having the lowest deviation between monthly mean and long-term monthly mean for wind speed (secondary parameter) is picked
    
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
    return best_years,param_typical_daily, fs, diff_sec

### Returns the nested list of hourly values for the typical year (param_typical_hourly) taking as input the best_years list and param_hourly

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

### Function to export results to excel file and produce windrose and plots

def concatenate_data(energy_PV, energy_WT) -> pd.DataFrame:
    """
    Concatenate energy production data into a DataFrame.

    Args:
        energy_PV: Nested list of PV energy production values.
        energy_WT: List of wind turbine energy production values.

    Returns:
        pd.DataFrame: DataFrame containing time periods, PV energy, and wind energy.
    """
    energy_PV_lst = []
    for months in range(len(energy_PV)):
        for day in range(len(energy_PV[months])):
            for hour in range(len(energy_PV[months][day])):
                energy_PV_lst.append(energy_PV[months][day][hour])

    time_periods = [i + 1 for i in range(len(energy_WT))]
    dataf = pd.DataFrame({
        'Hour': time_periods,
        'PV Energy (kWh)': energy_PV_lst,
        'Wind Energy (kWh)': energy_WT
    })

    return dataf

#%% Correlations for solar radiation data

### Returns the ratio of daily diffuse irradiation to total irradiation (K_diff)

def erbs_corr(omega_s,K_T):
    omega_s = omega_s*180/math.pi
    if omega_s <= 81.4:
        if K_T < 0.715:
            K_diff = 1 - 0.2727*K_T + 2.4495*(K_T**2) - 11.9514*(K_T**3) + 9.3879*(K_T**4)
        else: 
            K_diff = 0.143
    else:
        if K_T<0.722:
            K_diff = 1 + 0.2832*K_T-2.5557*(K_T**2)+0.8448*(K_T**3)
        else:
            K_diff = 0.175
    return K_diff

### Returns the hourly irradiation on a tilted surface given total and diffuse irradiation and geometrical parameters

def I_tilt_f(beta, I_tot, I_diff, ro_g, theta_z, theta_i):
    I_tilt_iso = I_diff * (1+ math.cos(beta))/2 + I_tot*ro_g*(1-math.cos(beta))/2 + (I_tot - I_diff)*math.cos(theta_i)/math.cos(theta_z)
    if I_tilt_iso <= 0:
        I_tilt_iso = 0
    return I_tilt_iso

### Define the function hourly_solar to obtain the hourly solar radiation on a tilted surface from daily GHI data

def hourly_solar(H_day,lat,lon, standard_lon, day_year,tilt, azimuth, albedo):
    
    B = (day_year-1)*2*math.pi/365
    delta =  math.radians(23.45*(math.sin(math.radians((day_year+284)*360/365))))               #declination angle in radians
    phi = lat * math.pi/180
    beta = tilt * math.pi/180
    gamma = azimuth*math.pi/180                                              
    
    # Calculation of daily extraterrestrial irradiation 
    if (-math.tan(phi)*math.tan(delta))>1:
        omega_s = 0.001
    elif (-math.tan(phi)*math.tan(delta))<-1:
        omega_s = math.pi
    else:
        omega_s = math.acos((-math.tan(phi)*math.tan(delta)))                                                                            #sunset hour angle
    E_0 = 1.000110 + 0.034221 * math.cos(B) + 0.001280*math.sin(B) + 0.000719*math.cos(2*B) + 0.000077*math.sin(2*B)                     #ratio between average sun-earth distance and distance in day day_year (Iqbal correlation)
    G_0n = 1.367*E_0                                                                                                                     #extraterrestrial irradiance [kW/m^2] incident on a normal surface in the day day_year
    H_extra = (24/math.pi) * G_0n * (math.cos(phi) * math.cos(delta) * math.sin(omega_s) + omega_s * math.sin(phi) * math.sin(delta))    #extraterr. daily irradiation on a normal surface [kWh/m^2]
    K_T = H_day/H_extra                                                                                                                  #daily clearness index
    
    # Calculation of diffuse daily irradiation with Erbs correlation
    
    K_diff = erbs_corr(omega_s,K_T)
    H_diff = K_diff * H_day                                                                                                              #daily diffuse irradiation on a normal surface
    
    # Calculation of diffuse and total hourly irradiation with LJ and CPR correlation 
    
    EoT = 229.2*(0.000075+0.001868*math.cos(B)-0.032077*math.sin(B)-0.014615*math.cos(2*B)-0.04089*math.sin(2*B))                        #equation of time [min]
    a_r= 0.409 + 0.5016 * math.sin(omega_s - math.pi/3)
    b_r= 0.6609 - 0.4767 * math.sin(omega_s - math.pi/3)
    I_tilt = []
    I_tot_lst = []
    I_dir_lst = []
    I_diff_lst = []
    r_d_CBR_lst = []
    t_s_lst = []
    omega_lst = []
    ro_g = albedo
    for hour_day in range(0,24):
        utc_time = hour_day
        t_s = utc_time + 4*(lon)/60 + EoT/60
        t_s_lst.append(t_s)                                                                               #solar time in hours
        omega = (math.pi/180)* 15 * (t_s - 12)  
        omega_lst.append(omega)                                                                                                      #hour angle
        r_d_lj = math.pi/24 * (math.cos(omega)-math.cos(omega_s))/(math.sin(omega_s) - omega_s * math.cos(omega_s))                                 #Liu-Jordan correlation for diffuse hourly irradiation
        r_d_CBR = (a_r + b_r * math.cos(omega)) * r_d_lj  
        r_d_CBR_lst.append(r_d_CBR)                                                                                           #Collares-Pereira-Rabl correlation for total hourly irradiation
        if r_d_lj < 0:
            I_diff = 0
        else:
            I_diff = r_d_lj * H_diff                                                                                                                    #diffuse hourly irradiation
        if r_d_CBR>0:
           I_tot = r_d_CBR * H_day                                                                          #total hourly irradiation
           if I_tot - I_diff <0:
               I_tot = I_diff
        else:
            I_tot = 0
        theta_z = abs(math.acos(math.cos(phi) * math.cos(delta)*math.cos(omega)+ math.sin(phi)*math.sin(delta)))                                    #zenith angle
        gamma_s = np.sign(omega) * abs((math.acos((math.cos(theta_z) * math.sin(phi) - math.sin(delta))/(math.sin(theta_z) * math.cos(phi)))))  #solar azimuth angle
        theta_i = math.acos(math.cos(theta_z) * math.cos(beta) + math.sin(theta_z) *math.sin(beta) * math.cos(gamma_s -  gamma))                  #angle of incidence
        I_tot_lst.append(I_tot)
        I_diff_lst.append(I_diff)
        if I_tot-I_diff>0:
            I_dir_lst.append(I_tot-I_diff)
        else:
            I_dir_lst.append(0)
        if math.cos(theta_z) < 0.1:
           theta_i = math.pi/2
        I_tilt.append(I_tilt_f(beta, I_tot, I_diff, ro_g, theta_z, theta_i))
    return I_tilt

### Calculation of daily extraterrestrial irradiation

def K_T_calc(H_day,lat,lon, standard_lon, day_year,tilt, azimuth):

    B = (day_year-1)*2*math.pi/365
    delta =  (0.006918 - 0.399912* math.cos(B) + 0.070257* math.sin(B) - 0.006758* math.cos(2*B) + 0.000907*math.sin(2*B) - 0.002697*math.cos(3*B) + 0.00148*math.sin(3*B)) #declination angle correlation by Spencer
    phi = lat * math.pi/180 
    omega_s = abs(math.acos((-math.tan(phi)*math.tan(delta))))                                                                                                              #sunset hour angle
    E_0 = 1.000110 + 0.034221 * math.cos(B) + 0.001280*math.sin(B) + 0.000719*math.cos(2*B) + 0.000077*math.sin(2*B)                                                        #ratio between average sun-earth distance and distance in day day_year (Iqbal correlation)
    G_0n = 1.367*E_0                                                                                                                                                        #extraterrestrial irradiance [kW/m^2] incident on a normal surface in the day day_year
    H_extra = (24/math.pi) * G_0n * (math.cos(phi) * math.cos(delta) * math.sin(omega_s) + omega_s * math.sin(phi) * math.sin(delta))                                       #extraterr. daily irradiation on a normal surface [kWh/m^2]
    K_T = H_day/H_extra                                                                                                                                                     #daily clearness index
    return K_T
        

#%% Correlations for wind turbine production

### Calculates the Hellmann coefficient and the wind speed at rotor height given the wind speed measurements at two different heights
def shear_exp(param_typical_hourly, Z_1, Z_0, Z_rot): 
                                                 
    w_Z1 = param_typical_hourly[0]
    w_Z0 = param_typical_hourly[1]
    alpha = [[] for ii in range(len(w_Z1))]       #Hellmann coefficient is evaluated from velocities at 2 and 50 meters on hourly basis
    U_rotor = [[] for ii in range(len(w_Z1))]
    for month in range(len(w_Z1)):
        alpha[month] = [[] for ii in range(len(w_Z1[month]))]
        U_rotor[month] = [[] for ii in range(len(w_Z1[month]))]
        for day in range(len(w_Z1[month])):
            for hour in range(len(w_Z1[month][day])):
                if w_Z1[month][day][hour] == 0 or w_Z0[month][day][hour] == 0:
                    alpha[month][day].append(0)
                else:
                    alpha[month][day].append((math.log(w_Z1[month][day][hour]) - math.log(w_Z0[month][day][hour]))/(math.log(Z_1)-math.log(Z_0)))  
                    U_rotor[month][day].append(w_Z0[month][day][hour] * (Z_rot/Z_0)**alpha[month][day][hour])
    # corrects error in wind speed dataset
    if len(U_rotor[9][21]) < 24:
        U_rotor[9][21].append(param_typical_hourly[1][9][21][23] * (40/2)**alpha[9][21][23])
    return U_rotor,alpha
        
### Calculate the daily average air density at rotor height

def air_density(Z,param_typical_hourly):
    
    T2M_hourly = param_typical_hourly[3]
    DT =  -0.0066 * (Z-2)                               #[°C/m] Change of temperature from measurement height (2 m) to height Z (standard lapse rate expression)
    P = 101.29 - (0.011837)*Z + (4.793*(10**-7))*Z**2     #[kPa] Pressure at height Z
    MM = 28.96                                          #[kg/kmol] molar mass of dry air
    R = 8.314                                           #[kJ/K kmol] gas constant
    R_molar = R/MM
    ro_air = [[] for i in range(len(T2M_hourly))]
    for ii in range(len(T2M_hourly)):
        ro_air[ii] = [[] for ii in range(len(T2M_hourly[ii]))]
        for jj in range(len(T2M_hourly[ii])):
            for kk in range(len(T2M_hourly[ii][jj])):
                ro_air[ii][jj].append(P/(R_molar*(T2M_hourly[ii][jj][kk] + 273.15 + DT)))       #find air density at hub height
             
        
    return ro_air

### Returns wind speed, direction and air density at rotor height as list of 8760 elements

def wind_lst(U_rotor, wind_direction, ro_air):
    U_rotor_lst = []
    wind_direction_lst = []
    ro_air_lst = []
    for ii in range(len(U_rotor)):
        for jj in range(len(U_rotor[ii])):
            U_rotor_lst.extend(U_rotor[ii][jj])
            wind_direction_lst.extend(wind_direction[2][ii][jj])
            ro_air_lst.extend(ro_air[ii][jj])
    return U_rotor_lst, wind_direction_lst, ro_air_lst

           
### Extrapolate power curve of the turbine from Power_curves excel file and calculate wind power hourly production     #QUI MANCA IL CALCOLO PER TURBINE AD ASSE ORIZZONTALE

def P_turb(power_curve, WS_rotor_lst, ro_air_lst, surface_area, drivetrain_efficiency):
    # Ensure power_curve is a numeric array
    # If power_curve is a list of strings, convert it to a list of floats.
    fp = np.array([float(pc) for pc in power_curve])

    # Convert range to numpy array for xp
    xp = np.array(range(0, 30))

    En_wind = []
    En_WT = []
    Cp = []
    for ii in range(len(WS_rotor_lst)):
        # Ensure WS_rotor_lst[ii] is numeric and convert it if necessary
        WS_rotor_value = float(WS_rotor_lst[ii])

        # Compute hourly ideal wind energy
        En_wind.append(0.5 * ro_air_lst[ii] * surface_area * WS_rotor_value**3)

        # Compute hourly energy production using interpolation
        interpolated_value = np.interp(WS_rotor_value, xp, fp) * 1000
        En_WT.append(interpolated_value * drivetrain_efficiency)

        # Compute hourly turbine power coefficient
        Cp.append(En_WT[ii]/(En_wind[ii])) if En_wind[ii] != 0 else Cp.append(0)

    return En_WT, Cp 

#%% Main 

# Function to calculate the PV energy supply
def download_nasa_pv_data(
    res_name,
    base_URL,
    loc_id,
    parameters_1,
    parameters_2,
    parameters_3,
    date_start,
    date_end,
    community,
    temp_res_1,
    temp_res_2,
    output_format,
    lat,
    lon,
    time_zone,
    nom_power,
    tilt,
    azimuth,
    ro_ground,
    k_T,
    NMOT,
    T_NMOT,
    G_NMOT,
    log_info=None,  # Add the logging parameter
) -> pd.DataFrame:
    
    start = time.time()

    def log(message):
        if log_info:
            log_info(message)
        else:
            print(message)

    (date_start, date_end, lat, lon, lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2, standard_lon, URL_1_d, URL_2_d) = URL_creation_d(base_URL, loc_id, parameters_1, parameters_2, date_start, date_end, community, temp_res_1, output_format, time_zone, lat, lon)
    URL_h = URL_creation_h(base_URL, loc_id, parameters_3, date_start, date_end, community, temp_res_2, output_format, lat, lon)
    URL_list = URL_1_d + URL_2_d + URL_h
    log("Downloading time-series from NASA POWER...\n")
    try:
        jsdata = multithread_data_download(URL_list) 
        param_daily_interp, param_hourly_interp = data_2D_interpolation(jsdata, date_start, date_end, lat, lon, lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2)
    except:
        log("POWER server response error, please try again")
        sys.exit(1)        
    
    log("Calculating the typical meteorological year...\n")
    (best_years, param_typical_daily, fs, diff_sec) = typical_year_daily(param_daily_interp, date_start, date_end)
    param_typical_hourly = typical_year_hourly(best_years, param_hourly_interp)
    
    log("Calculating the solar PV production in the typical year... \n")      
    I_tilt = [[] for i in range(len(param_typical_daily[0]))]
    day = 1
    for month in range(len(param_typical_daily[0])):
        for day_year in range(len(param_typical_hourly[0][month])):     
            I_tilt[month].append(hourly_solar(param_typical_daily[0][month][day_year], lat, lon, standard_lon, day, tilt, azimuth, ro_ground))
            day = day + 1
             
    T_amb = param_typical_hourly[3]
    T_cell = [[] for ii in range(len(T_amb))]    
    energy_PV = [[] for ii in range(len(T_amb))]
    
    for ii in range(len(T_amb)):   
        T_cell[ii] = [[] for ii in range(len(T_amb[ii]))]
        energy_PV[ii] = [[] for ii in range(len(T_amb[ii]))]   
        for jj in range(len(T_amb[ii])):
            for kk in range(len(T_amb[ii][jj])):
                T_cell[ii][jj].append(T_amb[ii][jj][kk] + ((NMOT - T_NMOT) / G_NMOT) * I_tilt[ii][jj][kk] * 1000)
                energy_PV[ii][jj].append((I_tilt[ii][jj][kk]) * nom_power * (1 + (k_T / 100) * (T_cell[ii][jj][kk] - 25)))
    
    energy_PV_lst = [item for sublist in energy_PV for subsublist in sublist for item in subsublist]
    time_periods = list(range(1, len(energy_PV_lst) + 1))
    
    dataf = pd.DataFrame({
        'Periods': time_periods,
        f'{res_name}': energy_PV_lst 
    })
    dataf.set_index('Periods', inplace=True)

    end = time.time()
    elapsed = end - start
    log('\n\nSolar PV time series calculation completed (overall time: {}, s, {} m)\n'.format(round(elapsed, 0), round(elapsed / 60, 1)))

    return dataf

# Function to calculate the wind energy supply
def download_nasa_wind_data(
    res_name,
    base_URL,
    loc_id,
    parameters_1,
    parameters_2,
    parameters_3,
    date_start,
    date_end,
    community,
    temp_res_1,
    temp_res_2,
    output_format,
    lat,
    lon,
    time_zone,
    turbine_model,
    turbine_type,
    drivetrain_efficiency,
    log_info=None,  # Add the logging parameter
) -> pd.DataFrame:
    
    start = time.time()

    def log(message):
        if log_info:
            log_info(message)
        else:
            print(message)

    log("Wind energy time series calculation started, please remember to close RES_Time_Series.csv ... \n")

    (date_start, date_end, lat, lon, lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2, standard_lon, URL_1_d, URL_2_d) = URL_creation_d(base_URL, loc_id, parameters_1, parameters_2, date_start, date_end, community, temp_res_1, output_format, time_zone, lat, lon)
    URL_h = URL_creation_h(base_URL, loc_id, parameters_3, date_start, date_end, community, temp_res_2, output_format, lat, lon)
    URL_list = URL_1_d + URL_2_d + URL_h
    log("Downloading time-series from NASA POWER...\n")
    try:
        jsdata = multithread_data_download(URL_list) 
        param_daily_interp, param_hourly_interp = data_2D_interpolation(jsdata, date_start, date_end, lat, lon, lat_ext_1, lon_ext_1, lat_ext_2, lon_ext_2)
    except:
        log("POWER server response error, please try again")
        sys.exit(1)        
    log("Completed\n")
    
    log("Calculating the typical meteorological year...\n")
    (best_years, param_typical_daily, fs, diff_sec) = typical_year_daily(param_daily_interp, date_start, date_end)
    param_typical_hourly = typical_year_hourly(best_years, param_hourly_interp)
    
    log("Completed \n")
    
    (power_curve, surface_area, rot_height) = wind_parameters(turbine_model, turbine_type)
    
    log("Calculating the wind turbine production in the typical year... \n")  
    
    param_hourly_str = ['WS50M', 'WS2M', 'WD10M']
    (WS_rotor, alpha) = shear_exp(param_typical_hourly, int(param_hourly_str[0][2:4]), int(param_hourly_str[1][2:3]), rot_height) 
    ro_air = air_density(rot_height, param_typical_hourly)
    U_rotor_lst, wind_direction_lst, ro_air_lst = wind_lst(WS_rotor, param_typical_hourly, ro_air)
    (energy_WT, Cp) = P_turb(power_curve, U_rotor_lst, ro_air_lst, surface_area, drivetrain_efficiency)
    
    time_periods = list(range(1, len(energy_WT) + 1))
    dataf = pd.DataFrame({
        'Periods': time_periods,
        f'{res_name}': energy_WT
    })
    dataf.set_index('Periods', inplace=True)

    end = time.time()
    elapsed = end - start
    log('\n\nWind energy time series calculation completed (overall time: {}, s, {} m)\n'.format(round(elapsed, 0), round(elapsed / 60, 1)))

    return dataf