import time
from pyomo.environ import AbstractModel
from Model_Creation import Model_Creation
from Model_Resolution import Model_Resolution
from Results import ResultsSummary, TimeSeries, PrintResults
from Plots import DispatchPlot, SizePlot


start = time.time()         # Start time counter
model = AbstractModel()     # Define type of optimization problem

#%% Processing

Model_Creation(model) # Creation of the Sets, parameters and variables.

# Resolve the model instance
instance = Model_Resolution(model)

#%% Results

Time_Series       = TimeSeries(instance)
Optimization_Goal = instance.Optimization_Goal.extract_values()[None]
Results           = ResultsSummary(instance, Optimization_Goal,Time_Series) 

#%% Plot and print-out
PlotScenario = 1                     # Plot scenario
PlotDate = '01/01/2023 00:00:00'     # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime = 3                         # Number of days to be shown in the plot
PlotFormat = 'png'                   # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution = 400                 # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)
'''
PlotScenario1 = 1                    # Plot scenario
PlotDate1 = '01/01/2042 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime1 = 3                        # Number of days to be shown in the plot
PlotFormat1 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution1 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

PlotScenario2 = 1                    # Plot scenario
PlotDate2 = '01/01/2032 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year
PlotTime2 = 3                        # Number of days to be shown in the plot
PlotFormat2 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution2 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)

PlotScenario3 = 1                    # Plot scenario
PlotDate3 = '01/01/2038 00:00:00'    # Month-Day-Year. If devoid of meaning: Day-Month-Year 
PlotTime3 = 3                        # Number of days to be shown in the plot
PlotFormat3 = 'png'                  # Desired extension of the saved file (Valid formats: png, svg, pdf)
PlotResolution3 = 400                # Plot resolution in dpi (useful only for .png files, .svg and .pdf output a vector plot)
'''
DispatchPlot(instance,Time_Series,PlotScenario,PlotDate,PlotTime,PlotResolution,PlotFormat)
'''
DispatchPlot1(instance,TimeSeries,PlotScenario1,PlotDate1,PlotTime1,PlotResolution1,PlotFormat1)

DispatchPlot2(instance,TimeSeries,PlotScenario2,PlotDate2,PlotTime2,PlotResolution2,PlotFormat2)
DispatchPlot3(instance,TimeSeries,PlotScenario3,PlotDate3,PlotTime3,PlotResolution3,PlotFormat3)
'''
#CashFlowPlot(instance,Results,PlotResolution,PlotFormat)
SizePlot(instance,Results,PlotResolution,PlotFormat)

PrintResults(instance, Results)  


#%% Timing
end = time.time()
elapsed = end - start
print('\n\nModel run complete (overall time: ',round(elapsed,0),'s,',round(elapsed/60,1),' m)\n')

