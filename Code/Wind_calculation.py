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
                ro_air[ii][jj].append(P/(R_molar*(T2M_hourly[ii][jj][kk] + 273.15 + DT)))
             
        
    return ro_air

#%% Estimation of wind speed probability distribution: probability distribution is obtained from hourly average values of wind speed at rotor height

def rayleigh_cumul_distr(x):
    F = 1 -math.exp((-math.pi/4) * x**2)                #Rayleigh cumulative distribution function 
    return F

def wind_distr(U_rotor):
    WS_range = range(1,31)
    cumul_distr_function = [[] for i in range(len(U_rotor))]
    prob_density_function = [[] for i in range(len(U_rotor))]
    for ii in range(len(U_rotor)):
        cumul_distr_function[ii] = [[[] for i in range(24)] for i in range(len(U_rotor[ii]))]
        prob_density_function[ii] = [[[] for i in range(24)] for i in range(len(U_rotor[ii]))]
        for jj in range(len(U_rotor[ii])):
            for hh in range(len(U_rotor[ii][jj])):
                for kk in range(len(WS_range)):
                    cumul_distr_function[ii][jj][hh].append(rayleigh_cumul_distr(WS_range[kk]/U_rotor[ii][jj][hh]))
                    if WS_range[kk] == 1:
                        prob_density_function[ii][jj][hh].append(cumul_distr_function[ii][jj][hh][kk])
                    else:
                        prob_density_function[ii][jj][hh].append(cumul_distr_function[ii][jj][hh][kk]-cumul_distr_function[ii][jj][hh][kk-1])
                
    return prob_density_function

           
#%% Extrapolate power curve of the turbine from Power_curves excel file and calculate daily energy production of the turbine     

def P_turb(power_curve, ro_air, prob_density, surface_area):
    
    U = np.arange(0.5, 30.5, 1)
    En_wind = [[] for i in range(len(prob_density))]
    En_WT = [[] for i in range(len(prob_density))]
    Cp = [[] for i in range(len(prob_density))]
    for month in range(len(prob_density)):
        En_WT[month] = [[[] for i in range(24)] for i in range(len(prob_density[month]))]
        En_wind[month] = [[[] for i in range(24)] for i in range(len(prob_density[month]))]
        Cp[month] = [[[] for i in range(24)] for i in range(len(prob_density[month]))]
        
        for day in range(len(prob_density[month])):
            for hour in range(len(prob_density[month][day])):
                for velocity in range(len(prob_density[month][day][hour])):
                    if prob_density[month][day][hour][velocity] == []:
                        continue
                    else:
                        En_wind[month][day][hour].append((0.5 * surface_area*ro_air[month][day][hour]*prob_density[month][day][hour][velocity]*U[velocity]**3))
                        En_WT[month][day][hour].append(power_curve[velocity] * 1000* prob_density[month][day][hour][velocity])
                En_wind[month][day][hour] = sum(En_wind[month][day][hour])              #hourly wind energy [Wh]
                En_WT[month][day][hour] = sum(En_WT[month][day][hour])                  #hourly energy production by the turbine [Wh]
                if En_wind[month][day][hour] == 0:
                    Cp[month][day][hour] = 0
                else:
                    Cp[month][day][hour] = En_WT[month][day][hour]/En_wind[month][day][hour]      #hourly Cp
                                                                                     
    return En_WT, En_wind, Cp
    
  



            


             
    
    
    
    