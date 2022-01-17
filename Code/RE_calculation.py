from Windrose import WindroseAxes
import time, sys
from Input_data import *
from Solar_PV_calculation import hourly_solar
from Typical_year import *
from Wind_calculation import shear_exp, air_density, wind_distr, P_turb
from Excel_export import excel_export

def RE_supply():
    
    start = time.time()
    
    print("Renewable energy time series calculation started, please remember to close Renewable_energy.xlsx... \n")
    
    #%% Reads .dat file, saves input data and creates the lists of daily and hourly URLs
    
    data_file = "Inputs/RES_data.dat"
    data_import = open(data_file).readlines()
    (date_start, date_end, lat, lon, lat_ext,lon_ext, standard_lon, URL_d) = URL_creation_d(data_import)
    URL_h = URL_creation_h(data_import)
    URL_list = URL_d + URL_h
    print("Input file reading completed\n")
    print("Downloading data from NASA POWER...\n")
    try:
        jsdata = multithread_data_download(URL_list) 
        param_daily_interp, param_hourly_interp = data_2D_interpolation(jsdata, date_start, date_end,lat, lon, lat_ext, lon_ext)
    except:
        print("POWER server response error, please try again")
        sys.exit(1)        
    print("Completed\n")
    
    #%% Calculate the typical year using the daily parameters 
    
    print("Calculating the typical meteorological year...\n")
    (best_years,param_typical_daily) = typical_year_daily(param_daily_interp, date_start, date_end)
    param_typical_hourly = typical_year_hourly(best_years, param_hourly_interp)
    
    print("Completed \n") 
    
    #%% Import technological parameters of RE technologies
    
    (num_mod, area_module,nom_power,tilt,azim,ro_ground, k_T, NMOT, T_NMOT, G_NMOT) = solarPV_parameters(data_import)  #PV param.
    (power_curve, surface_area, rot_height, data1, df) = wind_parameters(data_import)
    
    #%% Find the vector of hourly irradiation on a tilted surface for all days of the year [W/m^2 h] and K_T for power calculation
    print("Calculating the solar PV production in the typical year... \n")      
    I_tilt = [[] for i in range(len(param_typical_daily[0]))]        #[KWh/m^2]
    day = 1
    for month in range(len(param_typical_daily[0])):
        for day_year in range(len(param_typical_hourly[0][month])):     
            I_tilt[month].append(hourly_solar(param_typical_daily[0][month][day_year],lat,lon, standard_lon, day,tilt, azim, ro_ground))   #hourly irradiation [kWh/m^2] on tilted surface
            day = day + 1
             
    #%% Calculate electricity production from the PV system
    
    T_amb = param_typical_hourly[3]                               #[°C]
    T_cell = [[] for ii in range(len(T_amb))]    
    energy_PV = [[] for ii in range(len(T_amb))]
    
    for ii in range(len(T_amb)):   
        T_cell[ii] = [[] for ii in range(len(T_amb[ii]))]
        energy_PV[ii] = [[] for ii in range(len(T_amb[ii]))]   
        for jj in range(len(T_amb[ii])):
            for kk in range(len(T_amb[ii][jj])):
                T_cell[ii][jj].append(T_amb[ii][jj][kk] + ((NMOT - T_NMOT)/G_NMOT)*I_tilt[ii][jj][kk]*1000)          #find the vector of hourly average cell T using T2M
                energy_PV[ii][jj].append((I_tilt[ii][jj][kk])*num_mod* nom_power * (1+(k_T/100)*(T_cell[ii][jj][kk]-25)))                #[Wh/module]
     
    print("Completed\n")  
    
    #%% Wind turbine electricity production calculation
    
    print("Calculating the wind turbine production in the typical year... \n")  
    
    param_hourly_str = ['WS50M', 'WS2M', 'WD10M']
    (WS_rotor,alpha) = shear_exp(param_typical_hourly,int(param_hourly_str[0][2:4]), int(param_hourly_str[1][2:3]), rot_height) 
    ro_air = air_density(rot_height,param_typical_hourly)
    prob_density = wind_distr(WS_rotor)
    (energy_WT, energy_wind, Cp) = P_turb(power_curve, ro_air, prob_density, surface_area)             #hourly energy production of 1 wind turbine [kWh]
    
    print("Completed\n ")            
    
    #%% Display the windrose (This library is released under dual licensing: CECILL-B , BSD-3-Clause)
    
    wind_speed_lst = []
    wind_direction_lst = []
    
    for ii in range(len(param_typical_hourly[0])):
        for jj in range(len(param_typical_hourly[0][ii])):
            wind_speed_lst.extend(param_typical_hourly[0][ii][jj])
            wind_direction_lst.extend(param_typical_hourly[2][ii][jj])
    
    ax = WindroseAxes.from_ax()
    ax.bar(wind_direction_lst, wind_speed_lst, normed=True, opening=0.8, edgecolor='white')
    ax.set_legend()
    
    print("Windrose generated \n")  
    
    #%% Report results on excel sheet 'RES_supply'
    "Exporting time series to Renewable_energy.xlsx... \n"
    dataf = excel_export(energy_PV,energy_WT)
    
    # Timing
    end = time.time()
    elapsed = end - start
    print('\n\nRES time series calculation completed (overall time: ',round(elapsed,0),'s,', round(elapsed/60,1),' m)\n')

    return 



        
 
    