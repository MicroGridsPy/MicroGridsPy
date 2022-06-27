"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

Authors: 
    Giulia Guidicini   - Department of Energy, Politecnico di Milano 
    Lorenzo Rinaldi    - Department of Energy, Politecnico di Milano
    Nicolò Stevanato   - Department of Energy, Politecnico di Milano / Fondazione Eni Enrico Mattei
    Francesco Lombardi - Department of Energy, Politecnico di Milano
    Emanuela Colombo   - Department of Energy, Politecnico di Milano
Based on the original model by:
    Sergio Balderrama  - Department of Mechanical and Aerospace Engineering, University of Liège / San Simon University, Centro Universitario de Investigacion en Energia
    Sylvain Quoilin    - Department of Mechanical Engineering Technology, KU Leuven
"""


from pyomo.environ import *
from pyomo.opt import SolverFactory
from Constraints_Brownfield import *
from matplotlib import pyplot as plt

def Model_Resolution_Brownfield(model, Optimization_Goal, MultiObjective_Optimization, Plot_maxCost, Renewable_Penetration, Battery_Independence,datapath="Inputs/Model_data.dat"):      
    
#%% Economic constraints
    model.NetPresentCost = Constraint(rule=Net_Present_Cost)
    model.CO2emission = Constraint(rule=CO2_emission)
        
    model.ScenarioCO2emission    = Constraint(model.scenarios, 
                                              rule=Scenario_CO2_emission)
    model.ScenarioNetPresentCost = Constraint(model.scenarios, 
                                              rule=Scenario_Net_Present_Cost)    
    model.VariableCostNonAct = Constraint(rule=Total_Variable_Cost)
    
    "Investment cost"
    model.InvestmentCost = Constraint(rule=Investment_Cost)
    if Optimization_Goal == 'Operation cost':
        model.InvestmentCostLimit = Constraint(rule=Investment_Cost_Limit)

    "Fixed costs"    
    model.OperationMaintenanceCostAct = Constraint(rule=Operation_Maintenance_Cost_Act)
    model.OperationMaintenanceCostNonAct = Constraint(rule=Operation_Maintenance_Cost_NonAct)

    "Variable costs"
    model.TotalVariableCostAct         = Constraint(rule=Total_Variable_Cost_Act)
    model.FuelCostTotalAct             = Constraint(model.scenarios, 
                                            model.generator_types,
                                            rule=Total_Fuel_Cost_Act)
    model.TotalElectricityCostAct        = Constraint(model.scenarios,
                                                      rule=Total_Electricity_Cost_Act)   
    model.TotalRevenuesAct             = Constraint(model.scenarios,
                                                    rule=Total_Revenues_Act)
    model.TotalRevenuesNonAct          = Constraint(model.scenarios,
                                                    rule=Total_Revenues_NonAct)    
    model.BatteryReplacementCostAct    = Constraint(model.scenarios,
                                                 rule=Battery_Replacement_Cost_Act) 
    model.ScenarioLostLoadCostAct      = Constraint(model.scenarios, 
                                                 rule=Scenario_Lost_Load_Cost_Act)
    model.ScenarioVariableCostAct      = Constraint(model.scenarios,
                                                 rule=Scenario_Variable_Cost_Act)    

    model.FuelCostTotalNonAct          = Constraint(model.scenarios, 
                                                    model.generator_types, 
                                                    rule=Total_Fuel_Cost_NonAct)
    model.TotalElectricityCostNonAct   = Constraint(model.scenarios,
                                                    rule=Total_Revenues_NonAct)     
    model.BatteryReplacementCostNonAct = Constraint(model.scenarios,
                                                    rule=Battery_Replacement_Cost_NonAct) 
    model.ScenarioLostLoadCostNonAct   = Constraint(model.scenarios, 
                                                    rule=Scenario_Lost_Load_Cost_NonAct)
    model.ScenarioVariableCostNonAct   = Constraint(model.scenarios,
                                                    rule=Scenario_Variable_Cost_NonAct)     

    "Salvage value"
    model.SalvageValue = Constraint(rule=Salvage_Value)


#%% Electricity generation system constraints 
    model.EnergyBalance = Constraint(model.scenarios, 
                                     model.years_steps, 
                                     model.periods, 
                                     rule=Energy_balance)

    "Renewable Energy Sources constraints"  
    
    model.REScapacity     = Constraint(model.scenarios, model.years_steps, 
                                       model.renewable_sources,
                                       model.periods, 
                                       rule=RES_Capacity)
            
    model.RenewableEnergy = Constraint(model.scenarios, model.years_steps, 
                                       model.renewable_sources,
                                       model.periods, 
                                       rule=Renewable_Energy)  # Energy output of the solar panels
    model.ResMinStepUnits = Constraint(model.years_steps,
                                       model.renewable_sources, 
                                       rule=Renewables_Min_Step_Units)
    if Renewable_Penetration > 0:
        model.RenewableEnergyPenetration = Constraint(model.steps, 
                                                      rule=Renewable_Energy_Penetration)

    "Battery Energy Storage constraints"
    
    model.BESScapacity             = Constraint(model.steps,
                                                rule=BESS_Capacity)
    model.StateOfCharge            = Constraint(model.scenarios, 
                                                model.years_steps,
                                                model.periods, 
                                                rule=State_of_Charge) # State of Charge of the battery
    model.MaximunCharge            = Constraint(model.scenarios,
                                                model.years_steps, 
                                                model.periods, 
                                                rule=Maximun_Charge) # Maximun state of charge of the Battery
    model.MinimunCharge            = Constraint(model.scenarios, 
                                                model.years_steps,
                                                model.periods,
                                                rule=Minimun_Charge) # Minimun state of charge
    model.MaxPowerBatteryCharge    = Constraint(model.steps, 
                                                rule=Max_Power_Battery_Charge)  # Max power battery charge constraint
    model.MaxPowerBatteryDischarge = Constraint(model.steps,
                                                rule=Max_Power_Battery_Discharge)    # Max power battery discharge constraint
    model.MaxBatIn                 = Constraint(model.scenarios,
                                                model.years_steps,
                                                model.periods, 
                                                rule=Max_Bat_in) # Minimun flow of energy for the charge fase
    model.Maxbatout                = Constraint(model.scenarios, 
                                                model.years_steps, 
                                                model.periods,
                                                rule=Max_Bat_out) #minimun flow of energy for the discharge fase
    model.BatteryMinStepCapacity   = Constraint(model.years_steps, 
                                                rule=Battery_Min_Step_Capacity)
    if Battery_Independence > 0:
        model.BatteryMinCapacity   = Constraint(model.steps, 
                                                rule=Battery_Min_Capacity)

    "Diesel generator constraints"
    model.GENcapacity              = Constraint(model.steps,                                                 
                                                model.generator_types,
                                                rule=GEN_Capacity)
    model.MaximunFuelEnergy        = Constraint(model.scenarios, 
                                                model.years_steps, 
                                                model.generator_types,
                                                model.periods, 
                                                rule=Maximun_Generator_Energy) # Maximun energy output of the diesel generator
    model.GeneratorMinStepCapacity = Constraint(model.years_steps, 
                                                model.generator_types, 
                                                rule=Generator_Min_Step_Capacity)
    "Grid constraints"  
    
    model.MaximumPowerFromGrid     = Constraint(model.scenarios,
                                                model.years_steps,
                                                model.periods,
                                                rule=Maximum_Power_From_Grid)
    model.MaximumPowerToGrid       = Constraint(model.scenarios,
                                                model.years_steps,
                                                model.periods,
                                                rule=Maximum_Power_To_Grid) 
    
    "Lost load constraints"
    model.MaximunLostLoad = Constraint(model.scenarios, model.years, 
                                       rule=Maximun_Lost_Load) # Maximum permissible lost load
    
    "Emission constrains"
    model.RESemission    = Constraint(rule = RES_emission)
    model.GENemission    = Constraint(rule = GEN_emission)
    model.FUELemission   = Constraint(model.scenarios, 
                                      model.years_steps, 
                                      model.generator_types,
                                      model.periods,
                                      rule = FUEL_emission)
    model.BESSemission   = Constraint(rule = BESS_emission)
    model.ScenarioFUELemission = Constraint(model.scenarios,
                                            rule=Scenario_FUEL_emission)    
    model.GRIDemission = Constraint(model.scenarios, 
                                      model.years_steps,
                                      model.periods,
                                      rule=GRID_emission)
    model.ScenarioGRIDemission = Constraint(model.scenarios,
                                            rule=Scenario_GRID_emission)
    

      
    if MultiObjective_Optimization == 'no':
        if Optimization_Goal == 'NPC':
            model.ObjectiveFuntion = Objective(rule = Net_Present_Cost_Obj, 
                                               sense = minimize)
        elif Optimization_Goal == 'Operation cost':
            model.ObjectiveFuntion = Objective(rule = Total_Variable_Cost_Obj, 
                                               sense = minimize)
        instance = model.create_instance(datapath) # load parameters
    
        print('\nInstance created')
    
        opt = SolverFactory('gurobi') # Solver use during the optimization

        opt.set_options('Method=2 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000') # !! only works with GUROBI solver   
        # opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000') # !! only works with GUROBI solver   

        print('Calling solver...')
        results = opt.solve(instance, tee=True) # Solving a model instance 
        print('Instance solved')

        instance.solutions.load_from(results)  # Loading solution into instance
        return instance
        
    elif MultiObjective_Optimization == 'yes':
        if Optimization_Goal == 'NPC':
            model.f1 = Var()
            model.C_f1 = Constraint(expr = model.f1 == model.Net_Present_Cost)
            model.ObjectiveFuntion = Objective(expr = model.f1, 
                                                  sense=minimize)
            model.f2 = Var()
            model.C_f2 = Constraint(expr = model.f2 == model.CO2_emission)
            model.ObjectiveFuntion1 = Objective(expr = model.f2, 
                                                   sense=minimize)
           
            n = int(input("please indicate how many points (n) you want to analyse: "))
            
            #NPC min and CO2 emission max calculation
            model.ObjectiveFuntion1.deactivate()
            instance = model.create_instance(datapath)
            opt = SolverFactory('gurobi')
            opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
            print('Calling solver...')
            opt.solve(instance, tee=True)
            print('Instance solved') 
            NPC_min = value(instance.ObjectiveFuntion)+value(instance.National_Grid_Investment_Cost)+value(instance.National_Grid_OM_Cost)
            CO2emission_max = value(instance.ObjectiveFuntion1)
            print('NPC_min [kUSD] =' +str(NPC_min/1e3),'CO2emission_max [ton] =' +str(CO2emission_max/1e3))
           
        
            #NPC max and CO2 emission min calculation
            model.ObjectiveFuntion.deactivate()
            model.ObjectiveFuntion1.activate()
            instance = model.create_instance(datapath)
            print('Calling solver...')
            opt.solve(instance, tee=True)
            print('Instance solved') 
            NPC_max = value(instance.ObjectiveFuntion)+value(instance.National_Grid_Investment_Cost)+value(instance.National_Grid_OM_Cost)
            CO2emission_min = value(instance.ObjectiveFuntion1)
            print('NPC_max [kUSD] =' +str(NPC_max/1e3),'CO2emission_min [ton] =' +str(CO2emission_min/1e3))
            r=CO2emission_max-CO2emission_min
            
            #normal eps method
            model.ObjectiveFuntion.activate()
            model.ObjectiveFuntion1.deactivate()

            instance = model.create_instance(datapath)
            instance.e = Param(initialize=0, mutable=True)
            instance.C_e = Constraint(expr = instance.f2 == instance.e)

            if Plot_maxCost:
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
               opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
               results = opt.solve(instance, tee=True) # Solving a model instance
               print('Instance solved')  # Loading solution into instance
               f1_l.append((value(instance.f1)+value(instance.National_Grid_Investment_Cost)+value(instance.National_Grid_OM_Cost))/1e3)
               f2_l.append(value(instance.f2)/1e3)
               instance.solutions.load_from(results)
               print('NPC [kUSD] = ' +str((value(instance.f1)+value(instance.National_Grid_Investment_Cost)+value(instance.National_Grid_OM_Cost))/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))

            if len(f1_l)<n:
                f1_l.append(NPC_min/1e3)
                f2_l.append(CO2emission_max/1e3)

            print ('\nNPC [kUSD] =' +str(f1_l))
            print ('\nCO2 emission [ton] =' +str(f2_l))
            CO2=(CO2emission_max-CO2emission_min)/1e3
            NPC=f1_l[0]*1000-NPC_min 
            print('Cost CO2 avoided [USD/ton] =' +str(round(NPC/CO2,3))) 
            plt.plot(f1_l, f2_l, 'o-', c='r', label='Pareto optimal front')
            plt.legend(loc='best')
            plt.xlabel('NPC(kUSD)')
            plt.ylabel('CO2 emission(ton)')
            plt.grid(True)
            plt.tight_layout()
            plt.show()
            
            steps = list(range(int(CO2emission_min),int(CO2emission_max),step)) 
            
            if len(steps)<=n:
                steps.append(CO2emission_max)
            
            if Plot_maxCost:
                steps.insert(0,0)  
                
            i = int(input("please indicate which solution you prefer (starting from 1 to n in CO2 emission): ")) #asks the user how many profiles (i.e. code runs) he wants
               
            instance.e = steps[i] 
            print('Calling solver...')
            results = opt.solve(instance, tee=True) # Solving a model instance
            print('Instance solved')  # Loading solution into instance
            instance.solutions.load_from(results)
            print('NPC [kUSD] = ' +str((value(instance.f1)+value(instance.National_Grid_Investment_Cost)+value(instance.National_Grid_OM_Cost))/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))
            return instance
        
        elif Optimization_Goal == 'Operation cost':
            model.f1 = Var()
            model.C_f1 = Constraint(expr = model.f1 == model.Total_Variable_Cost)
            model.ObjectiveFuntion = Objective(expr = model.f1, 
                                                  sense=minimize)
            model.f2 = Var()
            model.C_f2 = Constraint(expr = model.f2 == model.CO2_emission)
            model.ObjectiveFuntion1 = Objective(expr = model.f2, 
                                                   sense=minimize)

            n = int(input("please indicate how many points (n) you want to analyse: "))
                        
            #NPC min and CO2 emission max calculation
            model.ObjectiveFuntion1.deactivate()
            instance = model.create_instance(datapath)
            opt = SolverFactory('gurobi')
            opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
            print('Calling solver...')
            opt.solve(instance, tee=True)
            print('Instance solved') 
            OperationCost_min = value(instance.ObjectiveFuntion)
            CO2emission_max = value(instance.ObjectiveFuntion1)
            print('OperationCost_min [kUSD] =' +str(OperationCost_min/1e3),'CO2emission_max [ton] =' +str(CO2emission_max/1e3))
           
        
            #NPC max and CO2 emission min calculation
            model.ObjectiveFuntion.deactivate()
            model.ObjectiveFuntion1.activate()
            instance = model.create_instance(datapath)
            print('Calling solver...')
            opt.solve(instance, tee=True)
            print('Instance solved') 
            OperationCost_max = value(instance.ObjectiveFuntion)
            CO2emission_min = value(instance.ObjectiveFuntion1)
            print('OperationCost_max [kUSD] =' +str(OperationCost_max/1e3),'CO2emission_min [ton] =' +str(CO2emission_min/1e3))
            r=CO2emission_max-CO2emission_min
            
            #normal eps method
            model.ObjectiveFuntion.activate()
            model.ObjectiveFuntion1.deactivate()

            instance = model.create_instance(datapath)
            instance.e = Param(initialize=0, mutable=True)
            instance.C_e = Constraint(expr = instance.f2 == instance.e)
        
            if Plot_maxCost:
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
               opt.set_options('Method=2 BarHomogeneous=1 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000')
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
            plt.plot(f1_l, f2_l, 'o-', c='r', label='Pareto optimal front')
            plt.legend(loc='best')
            plt.xlabel('Operation Cost(kUSD)')
            plt.ylabel('CO2 emission(ton)')
            plt.grid(True)
            plt.tight_layout()
            plt.show()

            steps = list(range(int(CO2emission_min),int(CO2emission_max),step))
                        
            if len(steps)<=n:
                steps.append(CO2emission_max)

            if Plot_maxCost:
                steps.insert(0,0) 
                
            i = int(input("please indicate which solution you prefer (starting from 1 to n in CO2 emission): ")) #asks the user how many profiles (i.e. code runs) he wants

            instance.e = steps[i] 
            #print(value(instance.e))
            print('Calling solver...')
            results = opt.solve(instance, tee=True) # Solving a model instance
            print('Instance solved')  # Loading solution into instance
            instance.solutions.load_from(results)
            print('Operation Cost [kUSD] = ' +str(value(instance.f1)/1e3),'CO2 emission [ton] = ' +str(value(instance.f2)/1e3))
            return instance
            
       
      
    
