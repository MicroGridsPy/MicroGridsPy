import math, numpy


#%% Returns the ratio of daily diffuse irradiation to total irradiation (K_diff)

def erbs_corr(omega_s,K_T):
    import math
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

#%% Returns the hourly irradiation on a tilted surface given total and diffuse irradiation and geometrical parameters

def I_tilt_f(beta, I_tot, I_diff, ro_g, theta_z, theta_i):
    I_tilt_iso = I_diff * (1+ math.cos(beta))/2 + I_tot*ro_g*(1-math.cos(beta))/2 + (I_tot - I_diff)*math.cos(theta_i)/math.cos(theta_z)
    if I_tilt_iso <= 0:
        I_tilt_iso = 0
    return I_tilt_iso

#%% Define the function hourly_solar to obtain the hourly solar radiation on a tilted surface from daily GHI data

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
        clock_time = hour_day 
        t_s = clock_time - 4*(standard_lon - lon)/60 + EoT/60
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
        gamma_s = numpy.sign(omega) * abs((math.acos((math.cos(theta_z) * math.sin(phi) - math.sin(delta))/(math.sin(theta_z) * math.cos(phi)))))  #solar azimuth angle
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

#%% Calculation of daily extraterrestrial irradiation

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
        