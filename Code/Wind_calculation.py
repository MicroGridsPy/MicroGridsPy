import math, numpy as np

            
#%% Calculate the Hellmann coefficient and the wind speed at rotor height given the wind speed measurements at two different heights


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
        
#%% Calculate the daily average air density at rotor height

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

#%% Returns wind speed, direction and air density at rotor height as list of 8760 elements

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

           
#%% Extrapolate power curve of the turbine from Power_curves excel file and calculate wind power hourly production     #QUI MANCA IL CALCOLO PER TURBINE AD ASSE ORIZZONTALE

def P_turb(power_curve, WS_rotor_lst, ro_air_lst, surface_area, drivetrain_efficiency):
    
    En_wind = []
    En_WT = []
    Cp = []
    for ii in range(len(WS_rotor_lst)):
        En_wind.append(0.5 * ro_air_lst[ii] * surface_area * WS_rotor_lst[ii]**3)                         #compute hourly ideal wind energy 
        En_WT.append(np.interp(WS_rotor_lst[ii], range(0,30), power_curve)*1000)                          #compute hourly energy production
        Cp.append(En_WT[ii]/(En_wind[ii]))                                                               #compute hourly turbine power coefficient  
    return En_WT, Cp    
  



            


             
    
    
    
    