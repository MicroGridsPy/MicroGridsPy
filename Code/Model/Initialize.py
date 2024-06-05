"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

Authors: 
    Alessandro Onori   - Department of Energy, Politecnico di Milano
    Giulia Guidicini   - Department of Energy, Politecnico di Milano 
    Lorenzo Rinaldi    - Department of Energy, Politecnico di Milano
    Nicolò Stevanato   - Department of Energy, Politecnico di Milano / Fondazione Eni Enrico Mattei
    Francesco Lombardi - Department of Energy, Politecnico di Milano
    Emanuela Colombo   - Department of Energy, Politecnico di Milano
    
Based on the original model by:
    Sergio Balderrama  - Department of Mechanical and Aerospace Engineering, University of Liège / San Simon University, Centro Universitario de Investigacion en Energia
    Sylvain Quoilin    - Department of Mechanical Engineering Technology, KU Leuven
"""


import pandas as pd
import re
import os
from RE_calculation import RE_supply
from Demand import demand_generation
from Grid_Availability import grid_availability as grid_avail


#%% This section extracts the values of Scenarios, Periods, Years from data.dat and creates ranges for them


current_directory = os.path.dirname(os.path.abspath(__file__))
inputs_directory = os.path.join(current_directory, '..', 'Inputs')
data_file_path = os.path.join(inputs_directory, 'Parameters.dat')
demand_file_path = os.path.join(inputs_directory, 'Demand.csv')
res_file_path = os.path.join(inputs_directory, 'RES_Time_Series.csv')
fuel_file_path = os.path.join(inputs_directory, 'Fuel Specific Cost.csv')
grid_file_path = os.path.join(inputs_directory, 'Grid Availability.csv')
results_directory = os.path.join(current_directory, '..', 'Results')
plot_path = os.path.join(results_directory, '..', 'Plots')

Data_import = open(data_file_path).readlines()

Fuel_Specific_Start_Cost = []
Fuel_Specific_Cost_Rate = []

for i in range(len(Data_import)):
    if "param: Scenarios" in Data_import[i]:
        n_scenarios = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Years" in Data_import[i]:
        n_years = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Periods" in Data_import[i]:
        n_periods = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Generator_Types" in Data_import[i]:      
        n_generators = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Step_Duration" in Data_import[i]:
        step_duration = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Min_Last_Step_Duration" in Data_import[i]:
        min_last_step_duration = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Battery_Independence" in Data_import[i]:      
        Battery_Independence = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Renewable_Penetration" in Data_import[i]:      
        Renewable_Penetration = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: Greenfield_Investment" in Data_import[i]:      
        Greenfield_Investment = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Multiobjective_Optimization" in Data_import[i]:      
        Multiobjective_Optimization = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Optimization_Goal" in Data_import[i]:      
        Optimization_Goal = int((re.findall('\d+',Data_import[i])[0]))
    if "param: MILP_Formulation" in Data_import[i]:      
        MILP_Formulation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Generator_Partial_Load" in Data_import[i]:      
        Generator_Partial_Load = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Plot_Max_Cost" in Data_import[i]:      
        Plot_Max_Cost = int((re.findall('\d+',Data_import[i])[0]))
    if "param: RE_Supply_Calculation" in Data_import[i]:      
        RE_Supply_Calculation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Demand_Profile_Generation" in Data_import[i]:      
        Demand_Profile_Generation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Fuel_Specific_Cost_Calculation" in Data_import[i]:      
        Fuel_Specific_Cost_Calculation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Fuel_Specific_Cost_Import" in Data_import[i]:      
        Fuel_Specific_Cost_Import = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Grid_Average_Number_Outages" in Data_import[i]:      
        average_n_outages = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Grid_Average_Outage_Duration" in Data_import[i]:       
        average_outage_duration = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Grid_Connection " in Data_import[i]:      
        Grid_Connection = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Grid_Availability_Simulation" in Data_import[i]:      
        Grid_Availability_Simulation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Year_Grid_Connection " in Data_import[i]:      
        year_grid_connection = int((re.findall('\d+',Data_import[i])[0]))
    if "param: Model_Components " in Data_import[i]:      
        Model_Components = int((re.findall('\d+',Data_import[i])[0]))
    if "param: WACC_Calculation " in Data_import[i]:      
        WACC_Calculation = int((re.findall('\d+',Data_import[i])[0]))
    if "param: cost_of_equity" in Data_import[i]:      
        cost_of_equity = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: cost_of_debt" in Data_import[i]:      
        cost_of_debt = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: tax" in Data_import[i]:      
        tax = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: equity_share" in Data_import[i]:      
        equity_share = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: debt_share" in Data_import[i]:      
        debt_share = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
    if "param: Real_Discount_Rate" in Data_import[i]:      
        Discount_Rate_default = float((re.findall("\d+\.\d+|\d+|\d+",Data_import[i])[0]))
    if "param: Fuel_Specific_Start_Cost" in Data_import[i]:
        for j in range(n_generators):
            Fuel_Specific_Start_Cost.append(float((re.findall("\d+\s+(\d+\.\d+|\d+)",Data_import[i+1+j])[0])))
    if "param: Fuel_Specific_Cost_Rate" in Data_import[i]:      
        for j in range(n_generators):
            Fuel_Specific_Cost_Rate.append(float((re.findall("\d+\s+(\d+\.\d+|\d+)",Data_import[i+1+j])[0])))


scenario = [i for i in range(1,n_scenarios+1)]
year = [i for i in range(1,n_years+1)]
period = [i for i in range(1,n_periods+1)]
generator = [i for i in range(1,n_generators+1)]

#%% This section imports, generates and plots the different types of demands

if Demand_Profile_Generation:
    Demand = demand_generation()
    Demand.columns = Demand.columns.map(str)
    print("Electric demand data generated endogenously using archetypes")
else:
    delimiters = [(',', '.'), (';', ','), (';', '.')]
    loaded_successfully = False
    for delimiter, decimal in delimiters:
        try:
            # Set index_col to 0 if the first column is the index
            Demand = pd.read_csv(demand_file_path, delimiter=delimiter, decimal=decimal, header=0, index_col=0)
            print(f"Demand data loaded exogenously using delimiter '{delimiter}' and decimal '{decimal}'")
            loaded_successfully = True
            break
        except pd.errors.ParserError:
            print(f"Failed to load with delimiter '{delimiter}' and decimal '{decimal}'. Trying next combination...")
        except FileNotFoundError:
            print(f"File not found: {demand_file_path}. Please check the file path and try again.")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Trying next combination...")
    
    if not loaded_successfully:
        print("Error during import of Demand.csv: unable to automatically detect delimiter and decimal. Please try again using delimiter ';' or ',' and decimal ',' or '.'.")
        raise ValueError("Failed to load demand data with all provided delimiter and decimal combinations.")

# Validate DataFrame dimensions against expected years and periods
expected_columns = len(year)  # Expected number of data columns, excluding the index
expected_rows = len(period)

# Validate columns
if Demand.shape[1] < expected_columns:
    raise ValueError(f"Number of columns in the file ({Demand.shape[1]}) is less than the expected number of years ({expected_columns}): unable to proceed. Please check the Demand.csv file.")
elif Demand.shape[1] > expected_columns:
    print(f"Warning: Number of columns in the file ({Demand.shape[1]}) exceeds the expected number of years ({expected_columns}). Considering only the first {expected_columns} columns.")
    Demand = Demand.iloc[:, :expected_columns]

# Validate rows
if Demand.shape[0] < expected_rows:
    raise ValueError(f"Number of rows in the file ({Demand.shape[0]}) is less than the expected number of periods ({expected_rows}): unable to proceed.Please check the Demand.csv file.")

Electric_Energy_Demand_Series = pd.Series(dtype=float)
# Iterate over actual column names in the DataFrame

for col in Demand.columns:
    dum = Demand[col].reset_index(drop=True)
    Electric_Energy_Demand_Series = pd.concat([Electric_Energy_Demand_Series, dum])

frame = [scenario, year, period]
index = pd.MultiIndex.from_product(frame, names=['scenario', 'year', 'period'])
Electric_Energy_Demand = pd.DataFrame(Electric_Energy_Demand_Series)
Electric_Energy_Demand.index = index

Electric_Energy_Demand_2 = pd.DataFrame()
# Iterate over scenarios and years, assuming scenario and year are defined and match the CSV structure
for s in scenario:
    Electric_Energy_Demand_Series_2 = pd.Series()
    for y in year:
        # Construct the column name as it appears in the CSV headers
        column_name = f'{(s-1)*len(year) + y}'
        if column_name in Demand.columns:
            dum_2 = Demand[column_name].dropna().reset_index(drop=True)
            Electric_Energy_Demand_Series_2 = pd.concat([Electric_Energy_Demand_Series_2, dum_2], ignore_index=True)
        else:
            print(f"Warning: Column '{column_name}' does not exist in the Demand DataFrame")
    Electric_Energy_Demand_2[s] = Electric_Energy_Demand_Series_2

# Create a RangeIndex for Electric_Energy_Demand_2
index_2 = pd.RangeIndex(1, len(year) * len(period) + 1)
Electric_Energy_Demand_2.index = index_2

"Electric Demand"
def Initialize_Demand(model, s, y, t):
    """
    Initializes electric demand based on the scenario, year, and period.

    Parameters:
    model (object): The model for which to initialize electric demand.
    s (int): Scenario number.
    y (int): Year.
    t (int): Time period.

    Returns:
    float: The electric demand.
    """
    return float(Electric_Energy_Demand[0][(s, y, t)])

#%% This section imports or generates the renewables and temperature time series data 

if RE_Supply_Calculation == 0: 
    delimiters = [(',', '.'), (';', ','), (';', '.')]
    loaded_successfully = False
    for delimiter, decimal in delimiters:
        try:
            # Set index_col to 0 if the first column is the index
            Renewable_Energy = pd.read_csv(res_file_path, delimiter=delimiter, decimal=decimal, header=0, index_col=0)
            print(f"Renewables Time Series data loaded exogenously using delimiter '{delimiter}' and decimal '{decimal}'")
            loaded_successfully = True
            break
        except pd.errors.ParserError:
            print(f"Failed to load with delimiter '{delimiter}' and decimal '{decimal}'. Trying next combination...")
        except FileNotFoundError:
            print(f"File not found: {res_file_path}. Please check the file path and try again.")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Trying next combination...")
    
    if not loaded_successfully:
        print("Error during import of RES_Time_Series.csv: unable to automatically detect delimiter and decimal. Please try again using delimiter ';' or ',' and decimal ',' or '.'.")
        raise ValueError("Failed to load renewables data with all provided delimiter and decimal combinations.")
    
    plot_path = os.path.join(results_directory, 'Renewables Availability.png')
else:
    Renewable_Energy = RE_supply()
    Renewable_Energy = Renewable_Energy.set_index(pd.Index(range(1, n_periods+1)), inplace=False)
    print("Renewables Time Series data generated endogenously using NASA POWER")

def Initialize_RES_Energy(model, s, r, t):
    """
    Initializes renewable energy supply based on the specified scenario, resource, and time period.

    Parameters:
    model (object): The model for which the renewable energy supply is initialized.
    scenario (int): The scenario number.
    resource (int): The resource index.
    time_period (int): The time period index.

    Returns:
    float: The amount of renewable energy supplied.
    """
    column = (s - 1) * model.RES_Sources + r
    return float(Renewable_Energy.iloc[t - 1, column]) 

#%% This section defines the number of investment steps as well as assigns each year to its corresponding step

def Initialize_Upgrades_Number(model):
    """
    Calculates the number of upgrades for the given model.

    Parameters:
    model (object): The model for which to calculate upgrades.

    Returns:
    int: Number of upgrades.
    """
    if n_years % step_duration == 0:
        n_upgrades = n_years/step_duration
        return n_upgrades
    
    else:
        n_upgrades = 1
        for y in  range(1, n_years + 1):
            if y % step_duration == 0 and n_years - y > min_last_step_duration:
                n_upgrades += 1
        return int(n_upgrades)

def Initialize_YearUpgrade_Tuples(model):
    """
    Initializes year-upgrade tuples for the model.

    Parameters:
    model (object): The model for which to initialize year-upgrade tuples.

    Returns:
    list: List of year-upgrade tuples.
    """
    upgrade_years_list = [1 for i in range(len(model.steps))]
    s_dur = model.Step_Duration   
    for i in range(1, len(model.steps)): 
        upgrade_years_list[i] = upgrade_years_list[i-1] + s_dur    
    yu_tuples_list = [0 for i in model.years]    
    if model.Steps_Number == 1:    
        for y in model.years:            
            yu_tuples_list[y-1] = (y, 1)    
    else:        
        for y in model.years:            
            for i in range(len(upgrade_years_list)-1):
                if y >= upgrade_years_list[i] and y < upgrade_years_list[i+1]:
                    yu_tuples_list[y-1] = (y, model.steps[i+1])                
                elif y >= upgrade_years_list[-1]:
                    yu_tuples_list[y-1] = (y, len(model.steps))   
    print('\nTime horizon (year,investment-step): ' + str(yu_tuples_list))
    return yu_tuples_list


#%% This section initializes economic parameters related to the project

def Initialize_Discount_Rate(model):
    """
    Calculates and initializes the discount rate for the model.

    Parameters:
    model (object): The model for which to calculate the discount rate.

    Returns:
    float: The calculated discount rate.
    """
    if WACC_Calculation:
        if equity_share == 0:
            discount_rate = cost_of_debt*(1-tax)
        else:
           # Definition of Leverage (L): risk perceived by investors, or viceversa as the attractiveness of the investment to external debtors.
           L = debt_share/equity_share 
           discount_rate = cost_of_debt*(1-tax)*L/(1+L) + cost_of_equity*1/(1+L)
           print("Weighted Average Cost of Capital calculation completed")
    else:
        discount_rate = Discount_Rate_default
    return discount_rate

################################################################## ELECTRICITY PRODUCTION ##########################################################################

#%% This section initializes parameters related to the battery bank

def Initialize_Battery_Unit_Repl_Cost(model):
    """
    Initializes the unit replacement cost of the battery based on the model parameters.

    Parameters:
    model (object): The model containing parameters related to battery cost and performance.

    Returns:
    float: The calculated unit replacement cost of the battery.
    """
    Unitary_Battery_Cost = model.Battery_Specific_Investment_Cost - model.Battery_Specific_Electronic_Investment_Cost
    return Unitary_Battery_Cost/(model.Battery_Cycles*2*(model.Battery_Depth_of_Discharge))
      

def Initialize_Battery_Minimum_Capacity(model,ut): 
    """
    Calculates the minimum capacity required for the battery bank based on the model's demand profile and battery independence criteria.

    Parameters:
    model (object): The model containing parameters and configurations for battery and demand.
    ut (int): The current upgrade step in the model.

    Returns:
    float: The minimum required battery capacity to ensure the desired level of battery independence.
    """
    if model.Battery_Independence == 0: 
        return 0
    else:
        Periods = model.Battery_Independence*24
        Len =  int(model.Periods*model.Years/Periods)
        Grouper = 1
        index = 1
        for i in range(1, Len+1):
            for j in range(1,Periods+1):      
                Electric_Energy_Demand_2.loc[index, 'Grouper'] = Grouper
                index += 1      
            Grouper += 1
    
        upgrade_years_list = [1 for i in range(len(model.steps))]
        
        for u in range(1, len(model.steps)):
            upgrade_years_list[u] =upgrade_years_list[u-1] + model.Step_Duration
        if model.Steps_Number ==1:
            Electric_Energy_Demand_Upgrade = Electric_Energy_Demand_2    
        else:
            if ut==1:
                start = 0
                Electric_Energy_Demand_Upgrade = Electric_Energy_Demand_2.loc[start : model.Periods*(upgrade_years_list[ut]-1), :]       
            elif ut == len(model.steps):
                start = model.Periods*(upgrade_years_list[ut-1] -1)+1
                Electric_Energy_Demand_Upgrade = Electric_Energy_Demand_2.loc[start :, :]       
            else:
                start = model.Periods*(upgrade_years_list[ut-1] -1)+1
                Electric_Energy_Demand_Upgrade = Electric_Energy_Demand_2.loc[start : model.Periods*(upgrade_years_list[ut]-1), :]
        
        Period_Energy = Electric_Energy_Demand_Upgrade.groupby(['Grouper']).sum()        
        Period_Average_Energy = Period_Energy.mean()
        Available_Energy = sum(Period_Average_Energy[s]*model.Scenario_Weight[s] for s in model.scenarios) 
        
        return Available_Energy/(model.Battery_Depth_of_Discharge)


#%% This section initializes parameters related to generators and fuels

def Initialize_Fuel_Specific_Cost(model, g, y):
    """
    Initializes the specific cost of fuel for a generator type and a specific year. The function supports
    importing data from a file or calculating the cost based on a rate of increase.

    Parameters:
    model (object): The model for which the fuel cost is being initialized.
    g (int): The generator type index.
    y (int): The year index.

    Returns:
    float: The specific fuel cost for the given generator type and year.
    """
    if Fuel_Specific_Cost_Calculation == 1 and Fuel_Specific_Cost_Import == 1:
        delimiters = [(',', '.'), (';', ','), (';', '.')]
        loaded_successfully = False
        for delimiter, decimal in delimiters:
            try:
                # Set index_col to 0 if the first column is the index
                fuel_cost_data = pd.read_csv(res_file_path, delimiter=delimiter, decimal=decimal, header=0)
                print(f"Diesel Fuel prices loaded exogenously using delimiter '{delimiter}' and decimal '{decimal}'")
                loaded_successfully = True
                break
            except pd.errors.ParserError:
                print(f"Failed to load with delimiter '{delimiter}' and decimal '{decimal}'. Trying next combination...")
            except FileNotFoundError:
                print(f"File not found: {res_file_path}. Please check the file path and try again.")
                raise
            except Exception as e:
                print(f"An unexpected error occurred: {e}. Trying next combination...")
    
        if not loaded_successfully:
            print("Error during import of Fuel_Costs.csv: unable to automatically detect delimiter and decimal. Please try again using delimiter ';' or ',' and decimal ',' or '.'.")
            raise ValueError("Failed to load fuel cost data with all provided delimiter and decimal combinations.")

        # Create a dictionary for fuel costs
        fuel_cost_dict = {(int(gen_type), int(year)): fuel_cost_data.at[year, gen_type]
                      for gen_type in fuel_cost_data.columns
                      for year in fuel_cost_data.index}
        return fuel_cost_dict[(g, y)]
    elif Fuel_Specific_Cost_Calculation == 1 and Fuel_Specific_Cost_Import == 0:
        years = range(1, n_years+1)
        fuel_cost_dict = {}
        for gen_type in range(n_generators):
            previous_cost = Fuel_Specific_Start_Cost[gen_type]
            for year in years:
                if year == 1: 
                    cost = previous_cost
                else: cost = previous_cost * (1 + Fuel_Specific_Cost_Rate[gen_type])
                fuel_cost_dict[(gen_type + 1, year)] = cost
                previous_cost = cost
        return fuel_cost_dict[(g, y)]
        
def Initialize_Fuel_Specific_Cost_1(model, g):
    """
    Initializes the starting specific cost of fuel for a generator type. This function is used when
    the fuel cost is fixed and not subject to annual variation.

    Parameters:
    model (object): The model for which the fuel cost is being initialized.
    g (int): The generator type index.

    Returns:
    float: The starting specific fuel cost for the given generator type.
    """
    return model.Fuel_Specific_Start_Cost[g] 

def Initialize_Generator_Marginal_Cost(model,g,y):
    """
    Initializes the marginal cost of operation for a generator type considering fuel cost, heating value of the fuel,
    and generator efficiency. This function is applicable when the fuel cost varies annually.

    Parameters:
    model (object): The model for which the marginal cost is being initialized.
    g (int): The generator type index.
    y (int): The year index.

    Returns:
    float: The marginal cost of operation for the specified generator type and year.
    """
    if Fuel_Specific_Cost_Calculation == 1: 
        return model.Fuel_Specific_Cost[g,y]/(model.Fuel_LHV[g]*model.Generator_Efficiency[g])
    else: None

def Initialize_Generator_Marginal_Cost_1(model,g):
    """
    Calculates the marginal cost of operation for a generator type with a fixed fuel cost,
    taking into account the heating value of the fuel and generator efficiency.

    Parameters:
    model (object): The model for which the marginal cost is being initialized.
    g (int): The generator type index.

    Returns:
    float: The marginal cost of operation for the specified generator type.
    """
    if Fuel_Specific_Cost_Calculation == 0: 
        return model.Fuel_Specific_Cost_1[g]/(model.Fuel_LHV[g]*model.Generator_Efficiency[g])
    else: None
    
def Initialize_Generator_Start_Cost(model,g,y):
    """
    Initializes the start-up cost of a generator for a given year. This cost is based on the generator's marginal cost,
    nominal capacity, and a part-load operation parameter. Applicable in dynamic fuel cost scenarios and MILP formulation.

    Parameters:
    model (object): The model for which the start-up cost is being initialized.
    g (int): The generator type index.
    y (int): The year index.

    Returns:
    float: The start-up cost for the specified generator type and year.
    """
    if Fuel_Specific_Cost_Calculation == 1 and MILP_Formulation == 1: 
        return model.Generator_Marginal_Cost[g,y]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_pgen[g]
    else: None

def Initialize_Generator_Start_Cost_1(model,g):
    """
    Initializes the start-up cost of a generator in a scenario with fixed fuel cost and considering MILP formulation.
    This cost is derived from the generator's marginal cost, nominal capacity, and part-load operation parameter.

    Parameters:
    model (object): The model for which the start-up cost is being initialized.
    g (int): The generator type index.

    Returns:
    float: The start-up cost for the specified generator type.
    """
    if Fuel_Specific_Cost_Calculation == 0 and MILP_Formulation == 1 and Generator_Partial_Load == 1: 
        return model.Generator_Marginal_Cost_1[g]*model.Generator_Nominal_Capacity_milp[g]*model.Generator_pgen[g]
    else: None

def Initialize_Generator_Marginal_Cost_milp(model,g,y):
    """
    Calculates the marginal cost for a generator under MILP formulation for dynamic fuel cost scenarios. 
    This cost accounts for the generator's operational characteristics, including nominal capacity and start-up costs.

    Parameters:
    model (object): The model for which the marginal cost is being initialized.
    g (int): The generator type index.
    y (int): The year index.

    Returns:
    float: The marginal cost for the specified generator type and year under MILP formulation.
    """
    if Fuel_Specific_Cost_Calculation == 1 and MILP_Formulation == 1: 
        return ((model.Generator_Marginal_Cost[g,y]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_Start_Cost[g,y])/model.Generator_Nominal_Capacity_milp[g] 
    else: None

def Initialize_Generator_Marginal_Cost_milp_1(model,g):
    """
    Determines the marginal cost for a generator in scenarios with fixed fuel costs and MILP formulation. 
    This cost calculation considers the generator's nominal capacity and start-up cost.

    Parameters:
    model (object): The model for which the marginal cost is being initialized.
    g (int): The generator type index.

    Returns:
    float: The marginal cost for the specified generator type under MILP formulation with fixed fuel costs.
    """
    if Fuel_Specific_Cost_Calculation == 0 and MILP_Formulation == 1 and Generator_Partial_Load == 1: 
        return ((model.Generator_Marginal_Cost_1[g]*model.Generator_Nominal_Capacity_milp[g])-model.Generator_Start_Cost_1[g])/model.Generator_Nominal_Capacity_milp[g] 
    else: None
    
#%% This section initializes parameters related to grid connection

# Reading grid availability data
if Grid_Connection == 1:
    if Grid_Availability_Simulation: 
        grid_avail(average_n_outages, average_outage_duration, n_years, year_grid_connection, n_scenarios, n_periods)
        availability = pd.read_csv(grid_file_path, delimiter=';', header=0)
    else:
        availability = pd.read_csv(grid_file_path, delimiter=';', header=0)

    # Create grid_availability Series
    grid_availability_Series = pd.Series()
    for i in range(1, n_years * n_scenarios + 1):
        dum = availability[str(i)]
        grid_availability_Series = pd.concat([s for s in [grid_availability_Series, dum] if not s.empty])

    grid_availability = pd.DataFrame(grid_availability_Series)

    # Create a MultiIndex
    frame = [scenario, year, period]
    index = pd.MultiIndex.from_product(frame, names=['scenario', 'year', 'period'])
    grid_availability.index = index

    # Normalize the column name to 0 for consistency
    if grid_availability.columns[0] != 0:
        grid_availability.columns = [0]

    # Create grid_availability_2 DataFrame
    grid_availability_2 = pd.DataFrame()
    for s in scenario:
        grid_availability_Series_2 = pd.Series()
        for y in year:
            if Grid_Connection: 
                dum_2 = availability[str((s - 1) * n_years + y)]
            else: 
                dum_2 = availability[(s - 1) * n_years + y]
            grid_availability_Series_2 = pd.concat([s for s in [grid_availability_Series_2, dum_2] if not s.empty])
        grid_availability_2[s] = grid_availability_Series_2

    # Create a RangeIndex
    index_2 = pd.RangeIndex(1, n_years * n_periods + 1)
    grid_availability_2.index = index_2

def Initialize_Grid_Availability(model, s, y, t): 
    """
    Initializes the grid availability based on the specified scenario, year, and time period.

    Parameters:
    model (object): The model for which the grid availability is being initialized.
    s (int): The scenario number.
    y (int): The year.
    t (int): The time period.

    Returns:
    float: The grid availability for the specified scenario, year, and time period.
    """
    if Grid_Connection: 
        try:
            return float(grid_availability[list(grid_availability.columns)[0]][(s, y, t)])
        except KeyError:
            return 0
    else:
        return 0

def Initialize_National_Grid_Inv_Cost(model):
    """
    Calculates the initial investment cost of connecting to the national grid,
    considering the distance to the grid, specific connection cost, and discount rate.

    Parameters:
    model (object): The model for which the grid investment cost is being initialized.

    Returns:
    float: The total investment cost for connecting to the national grid.
    """
    if Grid_Connection: return model.Grid_Distance*model.Grid_Connection_Cost* model.Grid_Connection/((1+model.Discount_Rate)**(model.Year_Grid_Connection-1))
    else: 0
    
def Initialize_National_Grid_OM_Cost(model):
    """
    Calculates the operation and maintenance cost for the national grid connection,
    accounting for the specific connection cost, grid maintenance cost, and discount rate over the project lifetime.

    Parameters:
    model (object): The model for which the grid O&M cost is being initialized.

    Returns:
    float: The total operation and maintenance cost for the national grid connection.
    """
    Grid_OM_Cost = (model.Grid_Connection_Cost * model.Grid_Connection * model.Grid_Distance) * model.Grid_Maintenance_Cost
    Grid_Fixed_Cost = pd.DataFrame()
    g_fc = 0

    for y in model.year:  # Assuming 'year' is a member of 'model'
        if y < model.Year_Grid_Connection[None]:
            g_fc += (0) / ((1 + model.Discount_Rate) ** (y))
        else:
            g_fc += (Grid_OM_Cost) / ((1 + model.Discount_Rate) ** (y))

    grid_fc = pd.DataFrame({'Total': g_fc}, index=pd.MultiIndex.from_tuples([("Fixed cost", "National Grid", "-", "kUSD")]))
    grid_fc.index.names = ['Cost item', 'Component', 'Scenario', 'Unit']

    Grid_Fixed_Cost = pd.concat([Grid_Fixed_Cost, grid_fc], axis=1).fillna(0)
    Grid_Fixed_Cost = Grid_Fixed_Cost.groupby(level=[0], axis=1, sort=False).sum()

    if Grid_Connection: return Grid_Fixed_Cost.iloc[0]['Total']
    else: 0
