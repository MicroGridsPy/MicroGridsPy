import time, urllib.parse, urllib.error    
import pandas as pd, math, numpy as np, json
import os
import requests
from config.path_manager import PathManager

# Wind turbine parameters        
def wind_parameters(turbine_model: str, type_turb: str) -> tuple[list[float], float, float]:
    
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

#%% Data processing
### Download JSON data
def data_download(URL: str) -> dict:
    """
    Downloads data from the given URL and returns it as a JSON object.
    Args:
        URL (str): The URL from which to download the data.
    Returns:
        dict: The JSON data retrieved from the URL if the request is successful.
        None: If the request fails (i.e., status code is not 200).
    """
    # Make the request
    response = requests.get(URL)

    # Check the response status
    if response.status_code == 200:
        return response.json()  # Parse and return JSON data
    else:
        raise ValueError(f"Response error {response.status_code}: {response.text}")


#%% Correlations for solar radiation data

### Returns the hourly irradiation on a tilted surface given total and diffuse irradiation and geometrical parameters

def I_tilt_f(beta: float, I_tot: float, I_diff: float, ro_g: float, theta_z: float, theta_i: float) -> float:
    I_tilt_iso = I_diff * (1+ math.cos(beta))/2 + I_tot*ro_g*(1-math.cos(beta))/2 + (I_tot - I_diff)*math.cos(theta_i)/math.cos(theta_z)
    if I_tilt_iso <= 0:
        I_tilt_iso = 0
    return I_tilt_iso

### Define the function hourly_solar to obtain the hourly solar radiation on a tilted surface from daily GHI data

def hourly_solar(
    H_lst: list[float], 
    I_diff_lst: list[float], 
    lat: float, 
    lon: float, 
    day_year: int, 
    tilt: float, 
    azimuth: float, 
    albedo: float
) -> list[float]:
    B = (day_year-1)*2*math.pi/365
    delta = math.radians(23.45*(math.sin(math.radians((day_year+284)*360/365))))  # declination angle in radians
    phi = lat * math.pi/180
    beta = tilt * math.pi/180
    gamma = azimuth * math.pi/180  # sunset hour angle

    # Calculation of diffuse and total hourly irradiation with LJ and CPR correlation
    EoT = 229.2 * (0.000075 + 0.001868 * math.cos(B) - 0.032077 * math.sin(B) - 0.014615 * math.cos(2*B) - 0.04089 * math.sin(2*B))  # equation of time [min]
    I_tilt = []
    ro_g = albedo
    for hour_day in range(0, 24):
        utc_time = hour_day
        t_s = utc_time + 4 * (lon) / 60 + EoT / 60
        omega = (math.pi / 180) * 15 * (t_s - 12)
        I_tot = H_lst[hour_day]
        I_diff = I_diff_lst[hour_day]  # diffuse hourly irradiation
        if I_tot - I_diff < 0:
            I_tot = I_diff
        theta_z = abs(math.acos(math.cos(phi) * math.cos(delta) * math.cos(omega) + math.sin(phi) * math.sin(delta)))  # zenith angle
        gamma_s = np.sign(omega) * abs((math.acos((math.cos(theta_z) * math.sin(phi) - math.sin(delta)) / (math.sin(theta_z) * math.cos(phi)))))  # solar azimuth angle
        theta_i = math.acos(math.cos(theta_z) * math.cos(beta) + math.sin(theta_z) * math.sin(beta) * math.cos(gamma_s - gamma))  # angle of incidence
        if math.cos(theta_z) < 0.1:
            theta_i = math.pi / 2
        I_tilt.append(I_tilt_f(beta, I_tot, I_diff, ro_g, theta_z, theta_i))
    return I_tilt
        

#%% Correlations for wind turbine production

### Calculate the wind speed at rotor height   
def rotor_wind_speed(wind_speed_10m: list[float], alpha: float, Z_rot: float) -> list[float]: 
    U_rotor = []
    for i in range(len(wind_speed_10m)):
        U_rotor.append(wind_speed_10m[i] * (Z_rot / 10) ** alpha)  # Wind speed at rotor height
    return U_rotor

### Calculate the daily average air density at rotor height

def air_density(Z: float, T2M: list[float]) -> list[float]:
    DT = -0.0066 * (Z - 2)  # [°C/m] Change of temperature from measurement height (2 m) to height Z (standard lapse rate expression)
    P = 101.29 - (0.011837) * Z + (4.793 * (10**-7)) * Z**2  # [kPa] Pressure at height Z
    MM = 28.96  # [kg/kmol] molar mass of dry air
    R = 8.314  # [kJ/K kmol] gas constant
    R_molar = R / MM
    ro_air = []
    for ii in range(len(T2M)):
        ro_air.append(P / (R_molar * (T2M[ii] + 273.15 + DT)))  # find air density at hub height    
    return ro_air

           
### Extrapolate power curve of the turbine from Power_curves excel file and calculate wind power hourly production     #QUI MANCA IL CALCOLO PER TURBINE AD ASSE ORIZZONTALE

def P_turb(
    power_curve: list[float], 
    WS_rotor_lst: list[float], 
    ro_air_lst: list[float], 
    surface_area: float, 
    drivetrain_efficiency: float
) -> tuple[list[float], list[float]]:
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
def download_pvgis_pv_data(
    res_name: str,
    base_URL: str,
    output_format: str,
    lat: float,
    lon: float,
    nom_power: float,
    tilt: float,
    azimuth: float,
    ro_ground: float,
    k_T: float,
    NMOT: float,
    T_NMOT: float,
    G_NMOT: float,
    log_info: callable = None
    ) -> pd.DataFrame:
    """
    Downloads and processes PVGIS PV data to generate a time series of solar PV energy production.
    Parameters:
    """

    start = time.time()

    def log(message):
        if log_info:
            log_info(message)
        else:
            print(message)

    URL = base_URL + 'lat=' + str(lat) + '&lon=' + str(lon) + '&outputformat=' + output_format
    log("Downloading time-series from PVGIS...\n")
    jsdata = data_download(URL)

    if jsdata is None:
        raise ValueError("Response error, please try again")
    tmy_hourly_data = jsdata["outputs"]["tmy_hourly"]
    tmy_df = pd.DataFrame(tmy_hourly_data)

    I_tilt = [[] for _ in range(len(tmy_df) // 24)]
    for day_year in range(len(tmy_df) // 24):
        H_lst = [value / 1000 for value in tmy_df['G(h)'][day_year * 24:(day_year + 1) * 24].tolist()]
        I_diff_lst = [value / 1000 for value in tmy_df['Gd(h)'][day_year * 24:(day_year + 1) * 24].tolist()]
        I_tilt[day_year] = hourly_solar(H_lst, I_diff_lst, lat, lon, day_year+1, tilt, azimuth, ro_ground)       
             
    T_amb = [tmy_df['T2m'][i*24:(i+1)*24].tolist() for i in range(len(tmy_df) // 24)]
    T_cell = [[] for ii in range(len(T_amb))]    
    energy_PV = [[] for ii in range(len(T_amb))]

    for jj in range(len(T_amb)):
        for kk in range(len(T_amb[jj])):
            T_cell[jj].append(T_amb[jj][kk] + ((NMOT - T_NMOT) / G_NMOT) * I_tilt[jj][kk] * 1000)
            energy_PV[jj].append((I_tilt[jj][kk]) * nom_power * (1 + (k_T / 100) * (T_cell[jj][kk] - 25)))

    energy_PV_lst = [item for sublist in energy_PV for item in sublist]
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
def download_pvgis_wind_data(
    res_name: str,
    base_URL: str,
    output_format: str,
    lat: float,
    lon: float,
    turbine_model: str,
    turbine_type: str,
    drivetrain_efficiency: float,
    surface_roughness: float,
    log_info: callable = None,  # Add the logging parameter
) -> pd.DataFrame:

    start = time.time()

    def log(message: str):
        if log_info:
            log_info(message)
        else:
            print(message)

    log("Wind energy time series calculation started, please remember to close RES_Time_Series.csv ... \n")

    URL = base_URL + 'lat=' + str(lat) + '&lon=' + str(lon) + '&outputformat=' + output_format

    log("Downloading time-series from PVGIS...\n")
    jsdata = data_download(URL)

    if jsdata is None:
        raise ValueError("Response error, please try again")

    tmy_hourly_data = jsdata["outputs"]["tmy_hourly"]
    tmy_df = pd.DataFrame(tmy_hourly_data)

    log("Downloading time-series from PVGIS...\n")
    
    (power_curve, surface_area, rot_height) = wind_parameters(turbine_model, turbine_type)
    
    log("Calculating the wind turbine production in the typical year... \n")  
    

    ro_air_lst = air_density(rot_height, tmy_df['T2m'].tolist())
    WS_10m_list = tmy_df['WS10m'].tolist()
    alpha = 0.096 * math.log10(surface_roughness) + 0.16 * (math.log10(surface_roughness))**2 + 0.24
    U_rotor_lst = rotor_wind_speed(WS_10m_list, alpha, rot_height)
    wind_direction_lst = tmy_df['WD10m'].tolist()
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