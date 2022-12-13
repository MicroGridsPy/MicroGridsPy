"""
MicroGridsPy - Multi-year capacity-expansion (MYCE)

Linear Programming framework for microgrids least-cost sizing,
able to account for time-variable load demand evolution and capacity expansion.

"""

import time
from pyomo.environ import  AbstractModel
from Model_Creation import Model_Creation
from Model_Resolution_Brownfield import Model_Resolution_Brownfield
from Model_Resolution_Greenfield import Model_Resolution_Greenfield
from Results import ResultsSummary, TimeSeries, PrintResults
from Plots import DispatchPlot, DispatchPlot1, DispatchPlot2, DispatchPlot3, CashFlowPlot, SizePlot

start = time.time()         # Start time counter
model = AbstractModel()     # Define type of optimization problem


#%% Input parameters
Optimization_Goal = 'NPC'           # Options: NPC / Operation cost. It allows to switch between a NPC-oriented optimization and a NON-ACTUALIZED Operation Cost-oriented optimization
MultiObjective_Optimization = 'no'  # yes if optimization of NPC/operation cost and CO2 emissions, no otherwise
Brownfield_Investment = 0           # 1 if Brownfield investment, 0 Greenfield investment
Plot_maxCost = 0                    # 1 if the Pareto curve has to include the point at maxNPC/maxOperationCost, 0 otherwise
Renewable_Penetration = 0           # Fraction of electricity produced by renewable sources. Number from 0 to 1.
Battery_Independence  = 0           # Number of days of battery independence


#%% Processing
Model_Creation(model, Renewable_Penetration, Battery_Independence) # Creation of the Sets, parameters and variables.

if Brownfield_Investment:
    instance = Model_Resolution_Brownfield(model, Optimization_Goal,MultiObjective_Optimization, Plot_maxCost, Renewable_Penetration, Battery_Independence) # Resolution of the instance
else:
    instance = Model_Resolution_Greenfield(model, Optimization_Goal,MultiObjective_Optimization, Plot_maxCost, Renewable_Penetration, Battery_Independence) # Resolution of the instance
     

#%% Results
TimeSeries = TimeSeries(instance)
Results    = ResultsSummary(instance, Optimization_Goal, TimeSeries, Brownfield_Investment) 


#%% Plot and print-out
PlotScenario = 1                     # Plot scenario
PlotDate = '01/01/2022 00:00:00'     # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime = 3                         # Number of days to be shown in the plot
PlotFormat = 'png'                   # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution = 400                 # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

PlotScenario1 = 1                    # Plot scenario
PlotDate1 = '01/01/2026 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime1 = 3                        # Number of days to be shown in the plot
PlotFormat1 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution1 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

PlotScenario2 = 1                    # Plot scenario
PlotDate2 = '01/01/2032 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime2 = 3                        # Number of days to be shown in the plot
PlotFormat2 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution2 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

PlotScenario3 = 1                    # Plot scenario
PlotDate3 = '01/01/2037 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime3 = 3                        # Number of days to be shown in the plot
PlotFormat3 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution3 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

DispatchPlot(instance,TimeSeries,PlotScenario,PlotDate,PlotTime,PlotResolution,PlotFormat)
#DispatchPlot1(instance,TimeSeries,PlotScenario1,PlotDate1,PlotTime1,PlotResolution1,PlotFormat1)
#DispatchPlot2(instance,TimeSeries,PlotScenario2,PlotDate2,PlotTime2,PlotResolution2,PlotFormat2)
#DispatchPlot3(instance,TimeSeries,PlotScenario3,PlotDate3,PlotTime3,PlotResolution3,PlotFormat3)
#CashFlowPlot(instance,Results,PlotResolution,PlotFormat)
#SizePlot(instance,Results,PlotResolution,PlotFormat)

PrintResults(instance, Results)  


#%% Timing
end = time.time()
elapsed = end - start
print('\n\nModel run complete (overall time: ',round(elapsed,0),'s,',round(elapsed/60,1),' m)\n')
