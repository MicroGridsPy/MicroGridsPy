"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

"""


from pyomo.environ import *
from pyomo.opt import SolverFactory
import matplotlib
from matplotlib import pyplot as plt
import re
import os

matplotlib.use('Agg')  # Switch to 'Agg' backend to prevent GUI operations

current_directory = os.path.dirname(os.path.abspath(__file__))
inputs_directory = os.path.join(current_directory, '..', 'Inputs')
data_file_path = os.path.join(inputs_directory, 'Parameters.dat')

def Model_Resolution(model, datapath=data_file_path, options_string="mipgap=0.05",
                     warmstart=False, keepfiles=False, load_solutions=False, logfile="Solver_Output.log"):  

    Data_import = open(data_file_path).readlines()

    for i in range(len(Data_import)):
        if "param: Renewable_Penetration" in Data_import[i]:
            Renewable_Penetration = float((re.findall("\d+\.\d+|\d+",Data_import[i])[0]))
        if "param: Battery_Independence" in Data_import[i]:      
            Battery_Independence = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Greenfield_Investment" in Data_import[i]:  
            Greenfield_Investment = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Multiobjective_Optimization" in Data_import[i]:      
            Multiobjective_Optimization = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Optimization_Goal" in Data_import[i]:
            Optimization_Goal = int((re.findall('\d+',Data_import[i])[0]))
        if "param: MILP_Formulation" in Data_import[i]:      
            MILP_Formulation = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Plot_Max_Cost" in Data_import[i]:      
            Plot_Max_Cost = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Generator_Partial_Load" in Data_import[i]:      
            Generator_Partial_Load = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Model_Components" in Data_import[i]:      
            Model_Components = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Land_Use" in Data_import[i]:      
            Land_Use = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Solver" in Data_import[i]:      
            Solver = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Grid_Connection " in Data_import[i]:      
            Grid_Connection = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Grid_Connection_Type " in Data_import[i]:      
            Grid_Connection_Type = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Pareto_points" in Data_import[i]:      
            n = int((re.findall('\d+',Data_import[i])[0]))
        if "param: Pareto_solution" in Data_import[i]:      
            p = int((re.findall('\d+',Data_import[i])[0]))
        

    if Greenfield_Investment == 1 and MILP_Formulation == 1 :
        from Constraints import Constraints_Greenfield_Milp as C
    if Greenfield_Investment == 0 and MILP_Formulation == 1 :
        from Constraints import Constraints_Brownfield_Milp as C
    if Greenfield_Investment == 1 and MILP_Formulation == 0 :
        from Constraints import Constraints_Greenfield as C
    if Greenfield_Investment == 0 and MILP_Formulation == 0 : 
        from Constraints import Constraints_Brownfield as C   
    
 
    
#%% Economic constraints
    model.NetPresentCost = Constraint(rule=C.Net_Present_Cost)
    model.CO2emission = Constraint(rule=C.CO2_emission)
        
    model.ScenarioCO2emission    = Constraint(model.scenarios, 
                                              rule=C.Scenario_CO2_emission)
    model.ScenarioNetPresentCost = Constraint(model.scenarios, 
                                              rule=C.Scenario_Net_Present_Cost)
    model.VariableCostNonAct = Constraint(rule=C.Total_Variable_Cost)
    
    "Investment cost"
    model.InvestmentCost = Constraint(rule=C.Investment_Cost)
    if Optimization_Goal == 0:
        model.InvestmentCostLimit = Constraint(rule=C.Investment_Cost_Limit)

    "Fixed costs"    
    model.OperationMaintenanceCostAct = Constraint(rule=C.Operation_Maintenance_Cost_Act)
    model.OperationMaintenanceCostNonAct = Constraint(rule=C.Operation_Maintenance_Cost_NonAct)

    "Variable costs"
    model.TotalVariableCostAct         = Constraint(rule=C.Total_Variable_Cost_Act)
    model.ScenarioVariableCostAct      = Constraint(model.scenarios,
                                                    rule=C.Scenario_Variable_Cost_Act)  
    model.ScenarioVariableCostNonAct   = Constraint(model.scenarios,
                                                    rule=C.Scenario_Variable_Cost_NonAct)
    # Fuel
    if Model_Components == 0 or Model_Components == 2:
        model.FuelCostTotalAct             = Constraint(model.scenarios, 
                                                model.generator_types,
                                                rule=C.Total_Fuel_Cost_Act)
        model.FuelCostTotalNonAct          = Constraint(model.scenarios, 
                                                        model.generator_types,
                                                        rule=C.Total_Fuel_Cost_NonAct)
    # Grid Connection
    if Grid_Connection == 1:
        model.TotalElectricityCostAct      = Constraint(model.scenarios,
                                                        rule=C.Total_Electricity_Cost_Act)   
        model.TotalRevenuesAct             = Constraint(model.scenarios,
                                                        rule=C.Total_Revenues_Act)
        if Grid_Connection_Type == 0:
            model.TotalRevenuesNonAct          = Constraint(model.scenarios,
                                                            rule=C.Total_Revenues_NonAct) 
            model.TotalElectricityCostNonAct   = Constraint(model.scenarios,
                                                            rule=C.Total_Electricity_Cost_NonAct) 
    # Battery Replacement
    if Model_Components == 0 or Model_Components == 1:
        
        model.BatteryReplacementCostAct    = Constraint(model.scenarios,
                                                        rule=C.Battery_Replacement_Cost_Act)
        model.BatteryReplacementCostNonAct = Constraint(model.scenarios,
                                                        rule=C.Battery_Replacement_Cost_NonAct)
    # Land Use for Renewables
    if Land_Use == 1:
        model.RenewablesMaxLandUse         = Constraint(model.steps,
                                                        rule=C.Renewables_Max_Land_Use)
    # Lost Load
    model.ScenarioLostLoadCostAct      = Constraint(model.scenarios, 
                                                    rule=C.Scenario_Lost_Load_Cost_Act)
    model.ScenarioLostLoadCostNonAct   = Constraint(model.scenarios, 
                                                    rule=C.Scenario_Lost_Load_Cost_NonAct)     

    "Salvage value"
    model.SalvageValue = Constraint(rule=C.Salvage_Value)
    
#%% Brownfield additional constraints
    
    if Greenfield_Investment == 0:
        model.REScapacity     = Constraint(model.scenarios, model.years_steps, 
                                           model.renewable_sources,
                                           model.periods,
                                           rule=C.RES_Capacity)
        if Model_Components == 0 or Model_Components == 1:
            model.BESScapacity    = Constraint(model.steps,
                                               rule=C.BESS_Capacity)
        if Model_Components == 0 or Model_Components == 2:
            model.GENcapacity     = Constraint(model.steps,                                                
                                               model.generator_types,
                                               rule=C.GEN_Capacity)


#%% Electricity generation system constraints 
    model.EnergyBalance = Constraint(model.scenarios,
                                     model.years_steps, 
                                     model.periods, 
                                     rule=C.Energy_balance)

    "Renewable Energy Sources constraints"
    model.RenewableEnergy = Constraint(model.scenarios,
                                       model.years_steps, 
                                       model.renewable_sources,
                                       model.periods, 
                                       rule=C.Renewable_Energy)  # Energy output of the solar panels
    model.ResMinStepUnits = Constraint(model.years_steps,
                                       model.renewable_sources, 
                                       rule=C.Renewables_Min_Step_Units)
    
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(model.steps, 
                                                      rule=C.Renewable_Energy_Penetration)

    "Battery Energy Storage constraints"
    if Model_Components == 0 or Model_Components == 1:
        model.StateOfCharge            = Constraint(model.scenarios, 
                                                    model.years_steps,
                                                    model.periods, 
                                                    rule=C.State_of_Charge) # State of Charge of the battery
        model.MaximumCharge            = Constraint(model.scenarios,
                                                    model.years_steps, 
                                                    model.periods, 
                                                    rule=C.Maximum_Charge) # Maximun state of charge of the Battery
        model.MinimumCharge            = Constraint(model.scenarios, 
                                                    model.years_steps,
                                                    model.periods,
                                                    rule=C.Minimum_Charge) # Minimun state of charge
        model.MaxPowerBatteryCharge    = Constraint(model.steps, 
                                                    rule=C.Max_Power_Battery_Charge)  # Max power battery charge constraint
        model.MaxPowerBatteryDischarge = Constraint(model.steps,
                                                    rule=C.Max_Power_Battery_Discharge)    # Max power battery discharge constraint

        if MILP_Formulation:
            model.BatterySingleFlowDischarge = Constraint(model.scenarios,
                                                        model.years_steps,
                                                        model.periods, 
                                                        rule=C. Battery_Single_Flow_Discharge)
            model.BatterySingleFlowCharge = Constraint(model.scenarios,
                                                        model.years_steps,
                                                        model.periods, 
                                                        rule=C. Battery_Single_Flow_Charge)
        else:
            model.BatteryFlowCharge                     = Constraint(model.scenarios,
                                                                    model.years_steps,
                                                                    model.periods, 
                                                                    rule=C.Max_Bat_flow_in) # Minimun flow of energy for the charge fase
            model.BatteryFlowDischarge                 = Constraint(model.scenarios,
                                                                    model.years_steps,
                                                                    model.periods, 
                                                                    rule=C.Max_Bat_flow_out) # Minimun flow of energy for the discharge fase
        model.Maxbatout                = Constraint(model.scenarios, 
                                                    model.years_steps, 
                                                    model.periods,
                                                    rule=C.Max_Bat_out) #minimun flow of energy for the discharge fase
        model.BatteryMinStepCapacity   = Constraint(model.years_steps,                                             
                                                    rule=C.Battery_Min_Step_Capacity)
            
        if Battery_Independence > 0:
            model.BatteryMinCapacity   = Constraint(model.steps, 
                                                    rule=C.Battery_Min_Capacity)

    "Diesel generator constraints"
    if Model_Components == 0 or Model_Components == 2:
        
        if MILP_Formulation == 1 and Generator_Partial_Load == 1:
           model.MinimumGeneratorEnergyPartial     = Constraint(model.scenarios, 
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Minimum_Generator_Energy_Partial)
           model.MaximumGeneratorEnergyPartial     = Constraint(model.scenarios, 
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Maximum_Generator_Energy_Partial)
           model.MaximumGeneratorEnergyTotal1       = Constraint(model.scenarios,
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Maximum_Generator_Energy_Total_1)
           model.MaximumGeneratorEnergyTotal2       = Constraint(model.scenarios,
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Maximum_Generator_Energy_Total_2)
           model.GeneratorEnergyTotal              = Constraint(model.scenarios,
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Generator_Energy_Total)
           model.GeneratorUnitsTotal               = Constraint(model.scenarios,
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Generator_Units_Total)
           model.GeneratorMinStepCapacity          = Constraint(model.years_steps,
                                                                model.generator_types, 
                                                                rule=C.Generator_Min_Step_Capacity)
        elif MILP_Formulation == 1 and Generator_Partial_Load == 0:
           model.MaximumGeneratorEnergyTotal1       = Constraint(model.scenarios, 
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Maximum_Generator_Energy_Total_1)
           model.MaximumGeneratorEnergyTotal2       = Constraint(model.scenarios, 
                                                                model.years_steps, 
                                                                model.generator_types,
                                                                model.periods, 
                                                                rule=C.Maximum_Generator_Energy_Total_2)
           model.GeneratorMinStepCapacity = Constraint(model.years_steps, 
                                                       model.generator_types, 
                                                       rule=C.Generator_Min_Step_Capacity)
        else:
           model.MaximumGeneratorEnergy1        = Constraint(model.scenarios, 
                                                       model.years_steps, 
                                                       model.generator_types,
                                                       model.periods, 
                                                       rule=C.Maximum_Generator_Energy_1)
           model.MaximumGeneratorEnergy2        = Constraint(model.scenarios, 
                                                       model.years_steps, 
                                                       model.generator_types,
                                                       model.periods, 
                                                       rule=C.Maximum_Generator_Energy_2)
           model.GeneratorMinStepCapacity = Constraint(model.years_steps, 
                                                       model.generator_types, 
                                                       rule=C.Generator_Min_Step_Capacity)         
    "Grid constraints" 
    if Grid_Connection == 1:
        model.MaximumPowerFromGrid     = Constraint(model.scenarios,
                                                model.years,
                                                model.periods,
                                                rule=C.Maximum_Power_From_Grid)
        if Grid_Connection_Type == 0:
            model.MaximumPowerToGrid       = Constraint(model.scenarios,
                                                model.years,
                                                model.periods,
                                                rule=C.Maximum_Power_To_Grid) 
        if MILP_Formulation:
            if Grid_Connection_Type == 0:
                model.SingleFlowEnergyToGrid      = Constraint(model.scenarios,
                                                     model.years_steps,
                                                     model.periods,
                                                     rule=C.Single_Flow_Energy_To_Grid)
            model.SingleFlowEnergyFromGrid        = Constraint(model.scenarios,
                                                     model.years_steps,
                                                     model.periods,
                                                     rule=C.Single_Flow_Energy_From_Grid)

    "Lost load constraints"
    model.MaximumLostLoad = Constraint(model.scenarios, model.years, 
                                       rule=C.Maximum_Lost_Load) # Maximum permissible lost load

    "Emission constrains"
    model.RESemission    = Constraint(rule=C.RES_emission)
    if Model_Components == 0 or Model_Components == 2:
        model.GENemission    = Constraint(rule=C.GEN_emission)
        model.FUELemission   = Constraint(model.scenarios, 
                                          model.years_steps, 
                                          model.generator_types,
                                          model.periods,
                                          rule=C.FUEL_emission)
        model.ScenarioFUELemission = Constraint(model.scenarios,
                                                rule=C.Scenario_FUEL_emission) 
    if Model_Components == 0 or Model_Components == 1:
        model.BESSemission   = Constraint(rule=C.BESS_emission)
    
    if Grid_Connection == 1:
        model.GRIDemission = Constraint(model.scenarios, 
                                    model.years,
                                    model.periods,
                                    rule=C.GRID_emission)
        model.ScenarioGRIDemission = Constraint(model.scenarios,
                                            rule=C.Scenario_GRID_emission) 

##############################################################################################################################################################
     
    if Multiobjective_Optimization == 0:
        if Optimization_Goal == 1:
            model.ObjectiveFuntion = Objective(rule=C.Net_Present_Cost_Obj, 
                                               sense = minimize)
        elif Optimization_Goal == 0:
            model.ObjectiveFuntion = Objective(rule=C.Total_Variable_Cost_Obj, 
                                               sense = minimize)

        instance = model.create_instance(datapath) # load parameters
    
        print('\nInstance created')
        

        if Solver == 0:
            opt = SolverFactory('gurobi') # Solver use during the optimization

            # Setting options for Gurobi
            if MILP_Formulation:
                opt.options['Method'] = 3
                opt.options['BarHomogeneous'] = 1
                opt.options['Crossover'] = 1
                opt.options['MIPFocus'] = 1
                opt.options['BarConvTol'] = 1e-3
                opt.options['OptimalityTol'] = 1e-3
                opt.options['FeasibilityTol'] = 1e-4
            else:
                opt.options['Method'] = 2
                opt.options['BarHomogeneous'] = 0
                opt.options['Crossover'] = 0
                opt.options['BarConvTol'] = 1e-4
                opt.options['OptimalityTol'] = 1e-4
                opt.options['FeasibilityTol'] = 1e-4
        
            opt.options['IterationLimit'] = 10000

            print('Calling GUROBI solver...')
            results = opt.solve(instance, tee=True, warmstart=warmstart, keepfiles=keepfiles,
                            load_solutions=load_solutions, logfile=logfile) # Solving a model instance 

        elif Solver == 1:
           opt = SolverFactory('glpk') # Solver use during the optimization
           timelimit = 10000
           opt.options['tmlim'] = timelimit
           if MILP_Formulation: 
               opt.options['mipgap'] = 0.01      # Set relative gap tolerance for MIP
               opt.options['clq_cuts'] = 'on'  # Enable clique cuts
           
           print('Calling GLPK solver...')
           results = opt.solve(instance, tee=True, keepfiles=keepfiles, logfile=logfile) # Solving a model instance
           
        elif Solver == 2:
            opt = SolverFactory('cplex') # Solver used during the optimization

            # Setting options for CPLEX
            if MILP_Formulation:
                opt.options['mip.tolerances.mipgap'] = 0.01
                opt.options['mip.cuts.cliques'] = 2
                opt.options['mip.tolerances.absmipgap'] = 1e-3
                opt.options['mip.tolerances.integrality'] = 1e-4
            else:
                opt.options['lpmethod'] = 2
                opt.options['barrier.convergetol'] = 1e-4
                opt.options['simplex.tolerances.optimality'] = 1e-4
                opt.options['simplex.tolerances.feasibility'] = 1e-4

            opt.options['timelimit'] = 10000

            print('Calling CPLEX solver...')
            results = opt.solve(instance, tee=True, warmstart=warmstart, keepfiles=keepfiles,
                            load_solutions=load_solutions, logfile=logfile) # Solving a model instance
           
        print('Instance solved')
        instance.solutions.load_from(results)  # Loading solution into instance
           
        return instance
        
    else:
        if Optimization_Goal == 1:
            model.f1 = Var()
            model.C_f1 = Constraint(expr = model.f1 == model.Net_Present_Cost)
            model.ObjectiveFuntion = Objective(expr = model.f1, 
                                                  sense=minimize)
            model.f2 = Var()
            model.C_f2 = Constraint(expr = model.f2 == model.CO2_emission)
            model.ObjectiveFuntion1 = Objective(expr = model.f2, 
                                                   sense=minimize)
        
            # n = int(input("please indicate how many points (n) you want to analyse: "))
            
            #NPC min and CO2 emission max calculation
            model.ObjectiveFuntion1.deactivate()
            instance = model.create_instance(datapath)
            if Solver == 0:
                opt = SolverFactory('gurobi')
                if MILP_Formulation:
                    opt.set_options('Method=3 BarHomogeneous=1 Crossover=1 MIPfocus=1 BarConvTol=1e-3 OptimalityTol=1e-3 FeasibilityTol=1e-4 TimeLimit=10000')
                else:
                    opt.set_options('Method=2 BarHomogeneous=0 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
                print('Optimizing only for minimum NPC...')
            elif Solver == 1:
                opt = SolverFactory('glpk')
                timelimit = 10000
                opt.options['tmlim'] = timelimit
                if MILP_Formulation: 
                    opt.options['mipgap'] = 0.01      # Set relative gap tolerance for MIP
                    opt.options['clq_cuts'] = 'on'    # Enable clique cuts
                
                print('Optimizing only for minimum NPC...')
            
            opt.solve(instance, tee=True)
            print('Instance solved') 
            NPC_min = value(instance.ObjectiveFuntion)
            CO2emission_max = value(instance.ObjectiveFuntion1)
            print('NPC_min [kUSD] = ' +str(NPC_min/1e3),'CO2emission_max [ton] = ' +str(CO2emission_max/1e3))
           
        
            #NPC max and CO2 emission min calculation
            model.ObjectiveFuntion.deactivate()
            model.ObjectiveFuntion1.activate()
            instance = model.create_instance(datapath)
            print('Optimizing only for minimum CO2 emissions...')
            results = opt.solve(instance, tee=True)  # Solve the model instance
            instance.solutions.load_from(results)    # Load the solution into the instance
            print('Instance solved') 

            NPC = value(instance.ObjectiveFuntion)
            CO2emission_min = value(instance.f2)
            print('NPC [kUSD] = ' +str(NPC/1e3),'CO2emission_min [ton] = ' +str(CO2emission_min/1e3))
           

            # Second Optimization: Minimize cost while constraining emissions to the minimum value found
            model.ObjectiveFuntion.activate()     # Reactivate cost minimization objective
            model.ObjectiveFuntion1.deactivate()  # Ensure emissions objective is deactivated
            instance = model.create_instance(datapath)
            instance.CO2 = Param(initialize=CO2emission_min, mutable=True)
            instance.CO2_fixed = Constraint(expr = instance.f2 == instance.CO2)

            print('Optimizing for cost with minimum CO2 emissions constraint...')
            results = opt.solve(instance, tee=True)     # Solve the model instance again with the new constraint
            instance.solutions.load_from(results)       # Load the new solution into the instance
            NPC_max = value(instance.ObjectiveFuntion)
            print('NPC_max [kUSD] = ' +str(NPC_max/1e3),'with CO2emission_fixed [ton] = ' +str(CO2emission_min/1e3))

            #normal eps method
            model.ObjectiveFuntion.activate()
            model.ObjectiveFuntion1.deactivate()        

            instance = model.create_instance(datapath)
            instance.e = Param(initialize=0, mutable=True)
            instance.C_e = Constraint(expr = instance.f2 == instance.e)
            
            if Plot_Max_Cost:
                step = int((CO2emission_max - CO2emission_min)/(n-1))
                steps = list(range(int(CO2emission_min),int(CO2emission_max),step)) 
            else:
                step = int((CO2emission_max - CO2emission_min)/n)
                steps = list(range(int(CO2emission_min),int(CO2emission_max),step)) 
                steps.pop(0)          
                
            f1_l,f2_l = [],[]
            for i in steps:  
                instance.e = i
                #print(value(instance.e))
                print('Calling solver...')
                results = opt.solve(instance, tee=True) # Solving a model instance
                print('Instance solved')  # Loading solution into instance
                f1_l.append(value(instance.f1)/1e3)
                f2_l.append(value(instance.f2)/1e3)
                instance.solutions.load_from(results)
                print('NPC [kUSD] = ' +str(value(instance.f1)/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))

            if len(f1_l)<n:
                 f1_l.append(NPC_min/1e3)
                 f2_l.append(CO2emission_max/1e3)        
            
            print ('\nNPC [kUSD] =' +str(f1_l))
            print ('\nCO2 emission [ton] =' +str(f2_l))
            CO2=(CO2emission_max-CO2emission_min)/1e3
            NPC=f1_l[0]*1000-NPC_min  
            print('Cost CO2 avoided [USD/ton] =' +str(round(NPC/CO2,3))) 
            
            ##################################################################################
            def save_pareto_curve(f1_l, f2_l, plot_title, plot_xlabel, plot_ylabel, plot_path):
                fig, ax = plt.subplots(figsize=(15, 10))
                ax.plot(f1_l, f2_l, 'o-', c='r', label='Pareto optimal front')
                ax.set_title(plot_title, fontsize=22)
                ax.set_xlabel(plot_xlabel, fontsize=20)
                ax.set_ylabel(plot_ylabel, fontsize=20)
                ax.grid(True)
                ax.legend(loc='best', fontsize=20)
                plt.tight_layout()

                # Save plot to file
                plt.savefig(plot_path, dpi=400, bbox_inches='tight')
                plt.close()
            
                
            print('Plotting Pareto curve...')

            current_directory = os.path.dirname(os.path.abspath(__file__))
            results_directory = os.path.join(current_directory, '..', 'Results/Plots')
            plot_path = os.path.join(results_directory, 'ParetoCurve.png')
            save_pareto_curve(f1_l, f2_l, "Pareto Curve - NPC", "CO2 Emissions [ton]", "Net Present Costs [kUSD]",plot_path)

            print('Pareto curve plot saved.')
            #################################################################################################
            
            # Calculate the step size
            step = int((CO2emission_max - CO2emission_min) / (n - 1))

            # Generate steps from CO2emission_min up to (but not including) CO2emission_max, with an interval of 'step'
            steps = list(range(int(CO2emission_min), int(CO2emission_max), step))

            # Insert 0 at the beginning of the list to represent the baseline or control scenario
            steps.insert(0, 0)             
                
            instance.e = steps[p] 
            print('Calling solver...')
            results = opt.solve(instance, tee=True) # Solving a model instance
            print('Instance solved')  # Loading solution into instance
            instance.solutions.load_from(results)
            print('NPC [kUSD] = ' +str(value(instance.f1)/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))
            return instance
        
        elif Optimization_Goal == 0:
            model.f1 = Var()
            model.C_f1 = Constraint(expr = model.f1 == model.Total_Variable_Cost)
            model.ObjectiveFuntion = Objective(expr = model.f1, 
                                                  sense=minimize)
            model.f2 = Var()
            model.C_f2 = Constraint(expr = model.f2 == model.CO2_emission)
            model.ObjectiveFuntion1 = Objective(expr = model.f2, 
                                                   sense=minimize)
        
            # n = int(input("please indicate how many points (n) you want to analyse: "))
                        
            #NPC min and CO2 emission max calculation
            model.ObjectiveFuntion1.deactivate()
            instance = model.create_instance(datapath)
            if Solver == 0:
                opt = SolverFactory('gurobi')
                if MILP_Formulation:
                    opt.set_options('Method=3 BarHomogeneous=1 Crossover=1 MIPfocus=1 BarConvTol=1e-3 OptimalityTol=1e-3 FeasibilityTol=1e-4 TimeLimit=10000')
                else:
                    opt.set_options('Method=2 BarHomogeneous=0 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
                print('Optimizing only for minimum Operation Costs...')
            elif Solver == 1:
                opt = SolverFactory('glpk')
                timelimit = 10000
                opt.options['tmlim'] = timelimit
                if MILP_Formulation: 
                    opt.options['mipgap'] = 0.01      # Set relative gap tolerance for MIP
                    opt.options['clq_cuts'] = 'on'    # Enable clique cuts
                
                print('Optimizing only for minimum Operation Costs...')

            OperationCost_min = value(instance.ObjectiveFuntion)
            CO2emission_max = value(instance.ObjectiveFuntion1)
            print('OperationCost_min [kUSD] = ' +str(OperationCost_min/1e3),'CO2emission_max [ton] = ' +str(CO2emission_max/1e3))
           
        
            #NPC max and CO2 emission min calculation
            model.ObjectiveFuntion.deactivate()
            model.ObjectiveFuntion1.activate()
            instance = model.create_instance(datapath)
            print('Calling solver...')
            print('Optimizing only for minimum CO2 emissions...')
            opt.solve(instance, tee=True)
            print('Instance solved') 
            OperationCost = value(instance.ObjectiveFuntion)
            CO2emission_min = value(instance.ObjectiveFuntion1)
            print('OperationCost [kUSD] = ' +str(OperationCost/1e3),'CO2emission_min [ton] = ' +str(CO2emission_min/1e3))
            r=CO2emission_max-CO2emission_min

            # Second Optimization: Minimize cost while constraining emissions to the minimum value found
            model.ObjectiveFuntion.activate()     # Reactivate cost minimization objective
            model.ObjectiveFuntion1.deactivate()  # Ensure emissions objective is deactivated
            instance = model.create_instance(datapath)
            instance.CO2 = Param(initialize=CO2emission_min, mutable=True)
            instance.CO2_fixed = Constraint(expr = instance.f2 == instance.CO2)

            print('Optimizing for cost with minimum CO2 emissions constraint...')
            results = opt.solve(instance, tee=True)     # Solve the model instance again with the new constraint
            instance.solutions.load_from(results)       # Load the new solution into the instance
            OperationCost_max = value(instance.ObjectiveFuntion)
            print('OperationCost_max [kUSD] = ' +str(OperationCost_max/1e3),'with CO2emission_fixed [ton] = ' +str(CO2emission_min/1e3))

            
            #normal eps method
            model.ObjectiveFuntion.activate()
            model.ObjectiveFuntion1.deactivate()

            instance = model.create_instance(datapath)
            instance.e = Param(initialize=0, mutable=True)
            instance.C_e = Constraint(expr = instance.f2 == instance.e)

            if Plot_Max_Cost:
                step = int((CO2emission_max - CO2emission_min)/(n-1))
                steps = list(range(int(CO2emission_min),int(CO2emission_max),step)) 
            else:
                step = int((CO2emission_max - CO2emission_min)/n)
                steps = list(range(int(CO2emission_min),int(CO2emission_max),step)) 
                steps.pop(0)     

            f1_l,f2_l = [],[]
            for i in steps:  
               instance.e = i
               #print(value(instance.e))
               print('Calling solver...')
               results = opt.solve(instance, tee=True) # Solving a model instance
               print('Instance solved')  # Loading solution into instance
               f1_l.append(value(instance.f1)/1e3)
               f2_l.append(value(instance.f2)/1e3)
               instance.solutions.load_from(results)
               print('Operation Cost [kUSD] = ' +str(value(instance.f1)/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))

            if len(f1_l)<n:
                f1_l.append(OperationCost_min/1e3)
                f2_l.append(CO2emission_max/1e3) 

            print ('\nOperation Cost [kUSD] =' +str(f1_l))
            print ('\nCO2 emission [ton] =' +str(f2_l))  

            #################################################################################################
            
            print('Plotting Pareto curve...')

            current_directory = os.path.dirname(os.path.abspath(__file__))
            results_directory = os.path.join(current_directory, '..', 'Results/Plots')
            plot_path = os.path.join(results_directory, 'ParetoCurve.png')
            save_pareto_curve(f1_l, f2_l, "Pareto Curve - Operation Costs", "CO2 Emissions [ton]", "Operation Costs [kUSD]", plot_path)

            print('Pareto curve plot saved.')

            #################################################################################################
            
            steps = list(range(int(CO2emission_min),int(CO2emission_max),step))
            
            if len(steps)<=n:
                steps.append(CO2emission_max)

            if Plot_Max_Cost:
                steps.insert(0,0) 

            # i = int(input("please indicate which solution you prefer (starting from 1 to n in CO2 emission): ")) #asks the user how many profiles (i.e. code runs) he wants
                           
            instance.e = steps[p] 
            #print(value(instance.e))
            print('Calling solver...')
            results = opt.solve(instance, tee=True) # Solving a model instance
            print('Instance solved')  # Loading solution into instance
            instance.solutions.load_from(results)
            print('Operation Cost [kUSD] = ' +str(value(instance.f1)/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))
            return instance
        


           
          
        
    
                
                    
        
                
           
