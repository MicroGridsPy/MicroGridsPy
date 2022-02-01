import pandas as pd, math, numpy as np, re


#%% Import URL components for the POWER API by NASA and generate the URL (two different functions depending on time resolution)

def URL_creation_d(Data_import):
    for value in Data_import:
        if "param: base_URL" in value:
            base_URL = value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: loc_id" in value:
            loc_id = '/' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: parameters_1" in value:
            parameters = '?parameters=' + (value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: date_start" in value:
            date_start = (('&start=' + str(value[value.index('=')+1:value.index(';')])).replace(' ','')).replace("'","")
        if "param: date_end" in value:
            date_end = (('&end=' + str(value[value.index('=')+1:value.index(';')])).replace(' ','')).replace("'","")
        if "param: community" in value:
            community = '&community=' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: temp_res_1" in value:
            temp_res =  value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: output_format" in value:
            output_format = '&format' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: lat" in value:
            lat = value[value.index('=')+1:value.index(';')]
            numbers = re.compile('-?\d+')
            lat = list(map(int, numbers.findall(lat)))
        if "param: lon" in value:
            lon = value[value.index('=')+1:value.index(';')]
            numbers = re.compile('-?\d+')
            lon = list(map(int, numbers.findall(lon)))
        if "param: time_zone" in value:
            time_zone = int(value[value.index('=')+1:value.index(';')].replace(' ',''))
            standard_lon = 15*time_zone
    URL = []
    ''' Converts geographical coordinates in decimals'''       
    if float(lat[0])!= 0:    
        lat = lat[0] + np.sign(lat[0])*(lat[1]/60 + lat[2]/3600)
    else:
        lat = lat[0]+ lat[1]/60 + lat[2]/3600
    if float(lon[0])!= 0:    
        lon = lon[0] + np.sign(lon[0])*(lon[1]/60 + lon[2]/3600)
    else:
        lon = lon[0] + lon[1]/60 + lon[2]/3600 
    lat_ext = [math.floor(lat), math.ceil(lat)]
    lon_ext = [math.floor(lon), math.ceil(lon)]
    '''Generates a daily URL for each node of the square'''
    for ii in range(2):
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[0]) + date_start + date_end +  output_format).replace("'",""))
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[1]) + date_start + date_end +  output_format).replace("'",""))

    return date_start, date_end, lat, lon, lat_ext, lon_ext, standard_lon, URL

def URL_creation_h(Data_import):
    for value in Data_import:
        if "param: base_URL" in value:
            base_URL = value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: loc_id" in value:
            loc_id = '/' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: parameters_2" in value:
            parameters = '?parameters=' + (value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: date_start" in value:
            date_start = (('&start=' + str(value[value.index('=')+1:value.index(';')])).replace(' ','')).replace("'","")
        if "param: date_end" in value:
            date_end = (('&end=' + str(value[value.index('=')+1:value.index(';')])).replace(' ','')).replace("'","")
        if "param: community" in value:
            community = '&community=' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: temp_res_2" in value:
            temp_res =  value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: output_format" in value:
            output_format = '&format' + value[value.index('=')+1:value.index(';')].replace(' ','')
        if "param: lat" in value:
            lat = value[value.index('=')+1:value.index(';')]
            numbers = re.compile('-?\d+')
            lat = list(map(int, numbers.findall(lat)))
        if "param: lon" in value:
            lon = value[value.index('=')+1:value.index(';')]
            numbers = re.compile('-?\d+')
            lon = list(map(int, numbers.findall(lon)))
    URL = []
    ''' Converts geographical coordinates from in decimal degrees'''
    if float(lat[0])!= 0:    
        lat = lat[0] + np.sign(lat[0])*(lat[1]/60 + lat[2]/3600)
    else:
        lat = lat[0]+ lat[1]/60 + lat[2]/3600
    if float(lon[0])!= 0:    
        lon = lon[0] + np.sign(lon[0])*(lon[1]/60 + lon[2]/3600)
    else:
        lon = lon[0] + lon[1]/60 + lon[2]/3600 
    lat_ext = [math.floor(lat), math.ceil(lat)]
    lon_ext = [math.floor(lon), math.ceil(lon)]
    # generates a daily URL for each node of the square
    for ii in range(2):
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[0]) + date_start + date_end +  output_format).replace("'",""))
        URL.append((base_URL + temp_res + loc_id + parameters + community + '&longitude=' + str(lon_ext[ii]) + '&latitude=' + str(lat_ext[1]) + date_start + date_end +  output_format).replace("'",""))


    return URL

#%% Import data about technology

# Solar PV parameters
def solarPV_parameters(Data_import):
    for value in Data_import:
        
        if "param: nom_power" in value:
            nom_power = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: G_NMOT" in value:
            G_NMOT = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: T_NMOT" in value:
            T_NMOT = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: NMOT" in value:
            NMOT = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: tilt" in value:
            tilt = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: k_T" in value:
            k_T = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: azim" in value:
            azim = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
        if "param: ro_ground" in value:
            ro_ground = float(value[value.index('=')+1:value.index(';')].replace(' ',''))
    
    return nom_power,tilt,azim,ro_ground, k_T, NMOT, T_NMOT, G_NMOT

# Wind turbine parameters        
def wind_parameters(Data_import):
    for value in Data_import:
        if "param: turbine_type" in value:
            type_turb = value[value.index('=')+1:value.index(';')].replace(' ','').replace("'","")
        if "param: turbine_model" in value:
            turb_model = value[value.index('=')+1:value.index(';')].replace(' ','').replace("'","")    
    if type_turb == 'HA':
        skipf = 93-47
        skiprow = 0
    elif type_turb == 'VA':
        skipf = 0
        skiprow = 47
    data1 = pd.read_excel('Inputs/Power_curve.xlsx', skiprows = skiprow,  skipfooter = skipf) 
    df = pd.DataFrame(data1, columns= [turb_model])
    power_curve = (df[turb_model][4:45]).values.tolist()
    rot_diam = df[turb_model][1]
    rot_height = df[turb_model][2]
    if type_turb == 'HA':
        surface_area = math.pi * rot_diam**2 /4
    else:
        surface_area = rot_height*math.pi*rot_diam
    
    return  power_curve, surface_area, rot_height, data1, df


#%% Retrieves JSON daily and hourly data from POWER API 
def get_data(URL):
    import urllib.request, urllib.parse, urllib.error
    
    URL_handle = urllib.request.urlopen(URL)
    jsdata = URL_handle.read().decode()
    return jsdata











