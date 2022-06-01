import math, numpy as np, pandas as pd
import matplotlib.pyplot as plt

#%% Function returning as output a logical matrix (0 and 1) representing the availability of the grid, at hourly resolution

def Weibull_CDF(x,a,b):
    
    y = 1-math.exp(-(x/a)**b)
    return y

def Weibull_distrib(x,a,b):
    y = (b/(a**b)) * x**(b-1) * math.exp(-(x/a)**b)
    return y

     

def grid_availability(average_n_outages, average_outage_duration, project_lifetime, year_grid_connection):  

    grid_lifetime = project_lifetime - year_grid_connection + 1                                   
    lambda_TBO = 1620/60                                                                                #Weibull scale factor for Time Between Outages distrib. (would need to be found from fitting with historical data, here taken from Kebede et al.)
    k_TBO = 0.77                                                                                        #Weibull shape factor for TBO distrib. (would need to be found from fitting with historical data, here taken from Kebede et al.)
    lambda_OD = 36/60                                                                                   #Weibull scale factor for Outage Duration distrib. (would need to be found from fitting with historical data, here taken from Kebede et al.)
    k_OD = 0.56                                                                                         #Weibull shape factor for OD distrib. (would need to be found from fitting with historical data, here taken from Kebede et al.)
    times1 = np.linspace(0.00001,math.ceil(lambda_TBO*((-math.log(1-0.9999))**(1/k_TBO))),num = 5*10**3)   #creates a vector of times between 0 and the time at which CDF= 0.9999
    times2 = np.linspace(0.0001,math.ceil(lambda_OD*((-math.log(1-0.9999))**(1/k_OD))),num = 2*10**4)
    CDF_TBO = [Weibull_CDF(x,lambda_TBO,k_TBO) for x in times1]                                     
    CDF_OD = [Weibull_CDF(x,lambda_OD,k_OD) for x in times2]
    distrib_TBO = [Weibull_distrib(x,lambda_TBO,k_TBO) for x in times1]
    distrib_OD = [Weibull_distrib(x,lambda_OD,k_OD) for x in times2]
    
    PlotFormat = 'png'                  
    PlotResolution = 400  
    '''
    fig1 = plt.figure(dpi = 1000)
    plt.plot(times1, CDF_TBO , 'r-', markersize=1)
    x1,x2,y1,y2 = plt.axis()  
    plt.axis((0,500, 0, max(CDF_TBO)))
    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Time Between Outages [h]',fontsize=10)
    plt.title('Weibull Cumulative Distribution Function (TBO)',fontsize=10)
    plt.autoscale()
    fig1.savefig('Results/Plots/Weibull Cumulative Distribution Function (TBO).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
    
    fig2 = plt.figure(dpi = 1000)
    plt.plot(times2, CDF_OD , 'r-', markersize=1)
    x1,x2,y1,y2 = plt.axis()  
    plt.axis((0,20, y1,y2))
    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Outage Duration [h]',fontsize=10)
    plt.title('Weibull Cumulative Distribution Function (OD)',fontsize=10)
    plt.autoscale()
    fig2.savefig('Results/Plots/Weibull Cumulative Distribution Function (OD).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
    
    fig3 = plt.figure(dpi = 1000)
    plt.plot(times1, distrib_TBO , 'r-', markersize=1)
    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Time Between Outages [h]',fontsize=10)
    plt.title('Weibull Distribution (TBO)',fontsize=10)
    
    fig3.savefig('Results/Plots/Weibull Distribution (TBO).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
    
    fig4 = plt.figure(dpi = 1000)
    plt.plot(times2, distrib_OD , 'r-', markersize=1)
    x1,x2,y1,y2 = plt.axis()  
    plt.axis((0,max(times2), y1,y2))
    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Outage Duration [h]',fontsize=10)
    plt.title('Weibull Distribution (OD)',fontsize=10)
    fig4.savefig('Results/Plots/Weibull Distribution (OD).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
    '''
    #%% Make random sampling based on the obtained Weibull distributions and construct grid availability matrix
    if average_n_outages == 0 and average_outage_duration == 0:
         grid_availability_lifetime = pd.concat([pd.DataFrame(np.zeros((8760,project_lifetime-grid_lifetime))), pd.DataFrame(np.ones((8760,grid_lifetime)))], axis = 1)
         grid_availability_lifetime = grid_availability_lifetime.set_axis(range(1,project_lifetime+1), axis=1, inplace=False)
    else:
        rng = np.random.default_rng()
        OD_tot = grid_lifetime * average_n_outages * average_outage_duration/60 
        TBO_tot =  grid_lifetime*8760 - OD_tot
        samples_OD = []
        while sum(samples_OD) < OD_tot:                     #construct samples from OD distribution until the sum is equal to OD_tot
            spl = lambda_OD * rng.weibull(k_OD,size = 1)[0]
            samples_OD.append(spl)                       
            if sum(samples_OD) > OD_tot:
                samples_OD[-1] = math.ceil(samples_OD[-1] - (sum(samples_OD)-OD_tot))
        samples_TBO = []
        while len(samples_TBO) < len(samples_OD):                    #construct samples from TBO distribution until the sum is equal to TBO_tot
            spl = lambda_TBO * rng.weibull(k_TBO,size = 1)[0]
            samples_TBO.append(spl)                            
        k = abs(TBO_tot/(sum(samples_TBO)))
        samples_TBO = np.multiply(samples_TBO,k).tolist()
        n_samples = len(samples_OD)       
        
        
        grid = []
        for ii in range(0,n_samples):                               #populate the grid availability list [length 8760*20]
                TBO = int(round(samples_TBO[ii]))
                OD = int(round(samples_OD[ii]))
                grid.extend([ii for ii in np.ones(TBO)])
                grid.extend([ii for ii in np.zeros(OD)])
                if len(grid) >= grid_lifetime * 8760:
                    for ii in range(len(grid)-grid_lifetime * 8760):
                        grid.pop(-ii)
                    break
           
    
        '''
        density_TBO, bins_TBO = np.histogram(samples_TBO, bins = 500, density = True)    
        distrib_TBO_scaled = [Weibull_distrib(x,lambda_TBO*k,k_TBO) for x in times1]
        fig5 = plt.figure(dpi = 1000) 
        plt.bar(bins_TBO[:-1],density_TBO,  width = (bins_TBO[1] - bins_TBO[0]), label='Samples', edgecolor = 'w')
        plt.grid(axis='y', alpha=0.5)
        plt.xlim([min(bins_TBO), 100])
        plt.ylim(0,max(density_TBO))
        plt.xlabel('Time Between Outages [h]',fontsize=10)
        plt.title('Samples Distribution vs. Weibull distribution (TBO)',fontsize=10) 
        plt.plot(times1, distrib_TBO_scaled , 'r--', linewidth=1, label='Weibull distrib.')
        plt.legend(loc = 'upper right')
        fig5.savefig('Results/Plots/Samples Distribution (TBO).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
        
        
        density_OD, bins_OD = np.histogram(samples_OD, bins = 500, density = True)
        fig6 = plt.figure(dpi = 1000)
        plt.bar(bins_OD[:-1],density_OD,  width = (bins_OD[1] - bins_OD[0]), label='Samples',edgecolor = 'w')
        plt.grid(axis='y', alpha=0.75)
        plt.xlim([min(bins_OD), 2])
        plt.ylim(0,max(density_OD))
        plt.xlabel('Outage Duration [h]',fontsize=10)
        plt.title('Samples distribution vs. Weibull distribution (OD)',fontsize=10)
        plt.plot(times2, distrib_OD, 'r--', linewidth = 1, label='Weibull distrib.')
        plt.legend(loc = 'upper right')
        fig6.savefig('Results/Plots/Samples distribution (OD).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight')
        '''
                
        grid_matrix = np.ones((8760, grid_lifetime))
        year_count = 0
        ff = 0
        for ii in range(len(grid)):
            if year_count == grid_lifetime:
                break
            grid_matrix[ff,year_count] = grid[ii]
            ff = ff + 1
            if ff == 8759:
                year_count = year_count +1
                ff = 0
        
        grid_availability_lifetime = pd.concat([pd.DataFrame(np.zeros((8760,project_lifetime-grid_lifetime))), pd.DataFrame(grid_matrix)], axis = 1)
        grid_availability_lifetime = grid_availability_lifetime.set_axis(range(1,project_lifetime+1), axis=1, inplace=False)
    '''
    fig7 = plt.figure(dpi=1000)
    plt.plot(range(len(grid_matrix[:,0])), grid_matrix[:,0] , 'b.-', linewidth=0.1, markersize = 0.5)   
    plt.xlabel('Time [h]',fontsize=10)
    plt.title('Grid availability (for 1st year of grid connection)',fontsize=10) 
    fig7.savefig('Results/Plots/Grid availability (for 1st year of grid connection).'+PlotFormat, dpi=PlotResolution, bbox_inches='tight') 
    '''
    
    print("Calculation of Grid Availability Matrix for " + str(grid_lifetime) + " years of grid connection completed" )
    grid_availability_lifetime.to_excel("Inputs/Grid_availability.xlsx")
    return 
    
    
    






