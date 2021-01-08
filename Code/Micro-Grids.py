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

import time
from pyomo.environ import  AbstractModel
from Model_Creation import Model_Creation
from Model_Resolution import Model_Resolution
from Results import ResultsSummary, TimeSeries, PrintResults
from Plots import DispatchPlot#, CashFlowPlot, SizePlot

start = time.time()         # Start time counter
model = AbstractModel()     # Define type of optimization problem


#%% Input parameters
Optimization_Goal = 'NPC'   # Options: NPC / Operation cost. It allows to switch between a NPC-oriented optimization and a NON-ACTUALIZED Operation Cost-oriented optimization
Renewable_Penetration = 0   # Fraction of electricity produced by renewable sources. Number from 0 to 1.
Battery_Independence  = 0   # Number of days of battery independence


#%% Processing
Model_Creation(model, Renewable_Penetration, Battery_Independence) # Creation of the Sets, parameters and variables.
instance = Model_Resolution(model, Optimization_Goal, Renewable_Penetration, Battery_Independence) # Resolution of the instance


#%% Results
TimeSeries = TimeSeries(instance)
Results    = ResultsSummary(instance, Optimization_Goal, TimeSeries) 


#%% Plot and print-out
PlotScenario = 1                    # Plot scenario
PlotDate = '01/01/2019 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime = 3                        # Number of days to be shown in the plot
PlotFormat = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

DispatchPlot(instance,TimeSeries,PlotScenario,PlotDate,PlotTime,PlotResolution,PlotFormat)
# CashFlowPlot(instance,Results,PlotResolution,PlotFormat)
# SizePlot(instance,Results,PlotResolution,PlotFormat)

PrintResults(instance, Results)  


#%% Timing
end = time.time()
elapsed = end - start
print('\n\nModel run complete (overall time: ',round(elapsed,0),'s,',round(elapsed/60,1),' m)\n')

