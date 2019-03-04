#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  4 22:26:40 2018

@author: sergio
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import matplotlib.ticker as mtick
import matplotlib.pylab as pylab
from scipy.stats import pearsonr
from mpl_toolkits.mplot3d import Axes3D
from sklearn import linear_model
from sklearn.metrics import r2_score
import statsmodels.api as sm

Data = pd.read_csv('Base_Scenario.csv',index_col=0)
Power_Data_2 = pd.read_csv('Power_Data_2.csv',index_col=0)
index_date = pd.DatetimeIndex(start='2016-01-01 00:00:00', periods=166464, 
                                   freq=('5min'))

Data.index = index_date
Data_1 =pd.DataFrame()
Power_Data_2.index = index_date

for i in index_date:    
    if Data['Irradiation 2'][i]>0:
        Data_1.loc[i,'Efficiency'] = Data.loc[i,'PV Power']/(Data.loc[i,'Irradiation 2']
                                                                    *240*1.633)
        Data_1.loc[i,'PV Power'] = Data.loc[i,'PV Power']
        Data_1.loc[i,'Irradiation'] = Data.loc[i,'Irradiation 2']
        Data_1.loc[i,'PV Temperature'] = Data.loc[i,'PV Temperature 2']

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.scatter(Data_1['Irradiation'],Data_1['PV Temperature'] ,
           Data_1['Efficiency'], c='b')

ax.set_xlabel('Irradiation (W/m^2)')
ax.set_ylabel('PV Temperature ( C)')
ax.set_zlabel('efficiency (%)')
pylab.ylim([0,70])
pylab.xlim([0,1600])
ax.set_zlim(0, 0.2)
ax.view_init(5,65)
ax.view_init(35,65)


a = np.array([200,1600])
b = np.array([0.187,0.09])
c = np.array([0,200])
d = np.array([0.16,0.187])

Delta = 0.045

foo = float(d[1]) - Delta 

f = np.array([0.07,foo])


b_1 = b - Delta

a = a.reshape((2,1))
b = b.reshape((2,1))
b_1 = b_1.reshape((2,1))

lm = linear_model.LinearRegression(fit_intercept=True)
model = lm.fit(a,b)
lm_1 = linear_model.LinearRegression(fit_intercept=True)
model = lm_1.fit(a, b_1)



c = c.reshape((2,1))
d = d.reshape((2,1))
f = f.reshape((2,1))


lm_2 = linear_model.LinearRegression(fit_intercept=True)
model = lm_2.fit(c,d)
lm_3 = linear_model.LinearRegression(fit_intercept=True)
model = lm_3.fit(c, f)

ax1 = plt.scatter(Data_1['Irradiation'], Data_1['Efficiency'])
ax1 = plt.plot(a,lm.predict(a), c='r') 
ax1 = plt.plot(c,lm_2.predict(c), c='r')

ax1 = plt.plot(a, lm_1.predict(a), c='g')
ax1 = plt.plot(c, lm_3.predict(c), c='g')

plt.xlabel('Irradiation (W/m^2)')
plt.ylabel('Efficiency (%)')
pylab.ylim([0,0.25])
pylab.xlim([0,1600])

Data_Paper_1 = pd.DataFrame()
index_regreation = []

for i in Data_1.index:
       
    if Data_1['Irradiation'][i] > 200:
        
            rad =  Data_1['Irradiation'][i]
            Upper_Limit = lm.predict(rad)
            Lower_Limit = lm_1.predict(rad)
            
            
            if Data_1['Efficiency'][i] < Upper_Limit: 
                if Data_1['Efficiency'][i] > Lower_Limit :
    
                    Data_Paper_1.loc[i,'Irradiation'] = Data_1.loc[i,'Irradiation'] 
                    Data_Paper_1.loc[i,'PV Temperature']  = Data_1.loc[i,'PV Temperature'] 
                    Data_Paper_1.loc[i,'Efficiency']  = Data_1.loc[i,'Efficiency'] 
                    index_regreation.append(i) 
    else:
        
        rad =  Data_1['Irradiation'][i]
        Upper_Limit = lm_2.predict(rad)
        Lower_Limit = lm_3.predict(rad)
        if Data_1['Efficiency'][i] < Upper_Limit:
            if Data_1['Efficiency'][i] > Lower_Limit:
                Data_Paper_1.loc[i,'Irradiation'] = Data_1.loc[i,'Irradiation'] 
                Data_Paper_1.loc[i,'PV Temperature']  = Data_1.loc[i,'PV Temperature'] 
                Data_Paper_1.loc[i,'Efficiency']  = Data_1.loc[i,'Efficiency'] 
                index_regreation.append(i)
                
ax1 = plt.scatter(Data_Paper_1['Irradiation'], Data_Paper_1['Efficiency'])

ax1 = plt.plot(a,lm.predict(a), c='r') 
ax1 = plt.plot(c,lm_2.predict(c), c='r')

ax1 = plt.plot(a, lm_1.predict(a), c='g')
ax1 = plt.plot(c, lm_3.predict(c), c='g')

plt.xlabel('Irradiation (W/m^2)')
plt.ylabel('Efficiency (%)')
pylab.ylim([0,0.25])
pylab.xlim([0,1650])

X_4 = pd.DataFrame()
y_4 = pd.DataFrame()

X_4['Irradiation'] = Data_Paper_1['Irradiation']
X_4['PV Temperature'] = Data_Paper_1['PV Temperature']
y_4['Efficiency'] = Data_Paper_1['Efficiency']

lm_4 = linear_model.LinearRegression(fit_intercept=True)
model = lm_4.fit(X_4,y_4)

y_4_predictions = lm_4.predict(X_4)
print(lm_4.score(X_4,y_4))

Data_Corrected = pd.DataFrame()

for i in Data.index:
    print(i)
    rad = Data.loc[i,'Irradiation 2']
    print(rad)            
    tem = Data.loc[i,'PV Temperature 2']
    sample = np.array([rad,tem])
    sample = sample.reshape(1, -1)
    eff = lm_4.predict(sample) 
    Data_Corrected.loc[i, 'PV Corrected'] = 240*eff*rad*1.633
    Data_Corrected.loc[i, 'Radiation'] = rad
    Data_Corrected.loc[i, 'Efficiency'] = eff



Data_Corrected = Data_Corrected.drop([index_date[0]],axis=0)
Data_Corrected.loc[index_date[166463]+1, 'PV Corrected'] = 0

Power_Data_2 = Power_Data_2.drop([index_date[0]],axis=0)
Power_Data_2.loc[index_date[166463]+1] = 0


Data_Corrected.to_csv('PV_data/PV_Power_Corrected_3.csv')

Hourly_Data = pd.DataFrame()


Data_Corrected['Day'] = 0
foo = 0
iterations = int(len(Data_Corrected)/288)
for i in range(iterations):
    for j in range(288):
        index = Data_Corrected.index[foo]
        Data_Corrected.loc[index,'Day'] = i
        foo += 1
 
Data_Corrected['hour'] = 0
foo = 0
for i in range(iterations):
    for j in range(int(288/12)):
        for s in range(12):
            index = Data_Corrected.index[foo]
            Data_Corrected.loc[index,'hour'] = j
            foo += 1



Hourly_Data = Data_Corrected.groupby(['Day','hour']).mean()

index_hourly = pd.DatetimeIndex(start='2016-01-01 01:00:00', periods=13872, 
                                   freq=('1H'))

Hourly_Data.index = index_hourly

Hourly_Data.to_csv('PV_data/PV_Power_Corrected_2.csv')

#################### Plot  Paper 2d #################################

j = 0
i = 200
r = 1670

g = [float(lm_2.predict(j))*100, float(lm_2.predict(i))*100] 
h = [float(lm_1.predict(i))*100, float(lm_1.predict(r))*100]  
m = [float(lm_2.predict(i))*100, float(lm_3.predict(i))*100]
f = [float(lm.predict(i))*100, float(lm.predict(r))*100]
w = [float(lm_3.predict(j))*100, float(lm_3.predict(i))*100]
     
fig = plt.figure()
ax = fig.add_subplot(111)
ax2 = plt.scatter(Data_1['Irradiation'], Data_1['Efficiency']*100, c='b')
# lines with slope
ax.plot([i,r],f, c='g', linewidth = 2) 
ax.plot([j,i],g, c='g', linewidth = 2)
ax.plot([i,r], h, c='g',linewidth = 2)
ax.plot([j,i], w, c='g',linewidth = 2)

# Vertical lines
ax.plot([j+2,j+2], [g[0],w[0]], c='g',linewidth = 2)
ax.plot([r, r],[f[1], h[1]] , c='g', linewidth = 2)
ax.plot([i,i], m, c='g',linewidth = 2)

ax.annotate('1', xy=(100, 13.5), xytext=(400, 20), size= 15,
            arrowprops=dict(facecolor='black', shrink=0.05),)

ax.annotate('2', xy=(900, 12.5), xytext=(1000, 16), size= 15,
            arrowprops=dict(facecolor='black', shrink=0.05),)

Limits = mlines.Line2D([], [], color='green',label='Limites')
plt.legend([(ax2), Limits],["Data", 'Limits'])
plt.xlabel('Irradiation (W/m^2)')
plt.ylabel('Efficiency (%)')
pylab.ylim([0,25])
pylab.xlim([0,1700])

################## Plot 2d with surface
   
fig = plt.figure()
ax = fig.add_subplot(111)
ax2 = plt.scatter(Data_1['Irradiation'], Data_1['Efficiency']*100, c='b')
# lines with slope
ax.plot([i,r],f, c='g', linewidth = 2) 
ax.plot([j,i],g, c='g', linewidth = 2)
ax.plot([i,r], h, c='g',linewidth = 2)
ax.plot([j,i], w, c='g',linewidth = 2)

# Vertical lines
ax.plot([j+2,j+2], [g[0],w[0]], c='g',linewidth = 2)
ax.plot([r, r],[f[1], h[1]] , c='g', linewidth = 2)
ax.plot([i,i], m, c='g',linewidth = 2)

# Surface
ax.scatter(Data_Corrected['Radiation'],Data_Corrected['Efficiency']*100,c='y')

Limits = mlines.Line2D([], [], color='green',label='Limites')
plt.legend([(ax2), Limits],["Data", 'Limits'])
plt.xlabel('Irradiation (W/m^2)')
plt.ylabel('Efficiency (%)')
pylab.ylim([0,25])
pylab.xlim([0,1700])

################################# Plot Scatter 

Plot_1 = pd.DataFrame()

for i in Data_1.index:
    if Data_1.loc[i,'Efficiency'] < 0.4:
        Plot_1.loc[i,'Efficiency'] = Data_1.loc[i,'Efficiency']*100
        Plot_1.loc[i,'Irradiation'] = Data_1.loc[i,'Irradiation']
        Plot_1.loc[i,'PV Temperature'] = Data_1.loc[i,'PV Temperature']

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.scatter(Plot_1['PV Temperature'], Plot_1['Irradiation'],
           Plot_1['Efficiency'], c='b')

ax.set_xlabel('  PV Temperature ($^\circ$C)')
ax.set_ylabel('Irradiation (W/m$^{2}$)     ')
ax.zaxis.set_rotate_label(False)  
ax.set_zlabel('Efficiency (%)', rotation=90)
pylab.ylim([0,1600])
pylab.xlim([0,80])
ax.set_zlim(0, 40)
ax.view_init(35,25)

plt.tight_layout()

################################# Plot Scatter + model surface

Paper_Plot = pd.DataFrame()
for i in Plot_1.index:
    if    Plot_1['Efficiency'][i] < 25 and Plot_1['Efficiency'][i] > 7:
        Paper_Plot.loc[i,'Efficiency'] = Plot_1['Efficiency'][i]         
        Paper_Plot.loc[i,'Irradiation'] = Plot_1['Irradiation'][i]
        Paper_Plot.loc[i,'PV Temperature'] = Plot_1['PV Temperature'][i]


Plot = True
size = [20,15]
if Plot == True:    
    fig = plt.figure(figsize=size)
    ax = fig.add_subplot(111, projection='3d')
    
    ax.scatter(Paper_Plot['PV Temperature'], Paper_Plot['Irradiation'],
               Paper_Plot['Efficiency'], c='b')
    
    
    b_1 = lm_4.intercept_
    m1, m2 =lm_4.coef_[0]
    Ys = range(0,1600,5)
    Xs = range(0,70,2)
    Xs, Ys = np.meshgrid(Xs, Ys)
    Z = b_1 + m1*Ys+ m2*Xs 
    ax.plot_surface(Xs,Ys,Z*100,color='r')
    
    

    ax.tick_params(axis='x', which='major', labelsize=17)
    ax.tick_params(axis='y', which='major', labelsize=17)
    ax.tick_params(axis='z', which='major', labelsize=17)
    ax.set_xlabel('PV Temperature ($^{o}$C)', labelpad=20, size=20 )
    ax.set_ylabel('Irradiation (W/m$^{2}$)', labelpad=20, size=20)
    ax.set_zlabel('Efficiency (%)', size=20)
    pylab.ylim([0,1600])
    pylab.xlim([0,80])
    ax.set_zlim(5, 30)
    ax.view_init(0,25)
    Surface = mpatches.Patch(color='red',alpha=1, label='Superficie')
    plt.legend([(ax2),Surface],["Data", 'model'],
                bbox_to_anchor=(0.85,0.75) ,fontsize = 25)
    
    plt.tight_layout()


#################################  model surface

Plot = True
if Plot == True:
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    b_1 = lm_4.intercept_
    m1, m2 =lm_4.coef_[0]
    Ys = range(0,1600,5)
    Xs = range(0,70,2)
    Xs, Ys = np.meshgrid(Xs, Ys)
    Z = b_1 + m1*Ys+ m2*Xs 
    ax.plot_surface(Xs,Ys,Z*100,color='r')
    
    ax.set_xlabel('PV Temperature ($^{o}$C)')
    ax.set_ylabel('Irradiation (W/m$^{2}$)')
    ax.set_zlabel('Efficiency (%)')
    pylab.ylim([0,1600])
    pylab.xlim([0,80])
    ax.set_zlim(0, 40)
    ax.view_init(10,15)
    Surface = mpatches.Patch(color='red',alpha=1, label='Superficie')
    plt.legend([(ax2),Surface],["Data", 'model'],bbox_to_anchor=(0.9,0.8))
    
    plt.tight_layout()




################################################################################
#                            Gutierrez
###############################################################################

Data_2 = pd.read_excel('Data_Gutierrez.xls',index_col=0)            

index2 = pd.DatetimeIndex(start='2013-01-01 01:00:00', periods=8760, 
                                   freq=('H'))

start = index2.get_loc('2013-03-21 01:00:00')

Gut_Data_1  = Data_2[start:]
    
end = index2.get_loc('2013-03-21 01:00:00')

Gut_Data_2  = Data_2[:end]

Gut_Data =  Gut_Data_1.append(Gut_Data_2) 

index_3 = pd.DatetimeIndex(start='2016-03-21 01:00:00', periods=8760, 
                                   freq=('H'))

Gut_Data.index = index_3

#### Fix incoherent data
for i in Gut_Data.index:
    a = i.hour
    if any([a==0,a==1,a==2,a==3,a==4,a==5,a==20,a==21,a==22,a==23]):
        if Gut_Data.loc[i,'Radiation'] > 0:
            Gut_Data.loc[i,'Radiation'] = 0

for i in Hourly_Data.index:
    a = i.hour
    if a==4:
        if Hourly_Data.loc[i,'PV Corrected']>0:
             Hourly_Data.loc[i,'PV Corrected']=0

# applying the linear model to Gutierrez data    
for i in Gut_Data.index:
       
       if Gut_Data.loc[i,'Radiation'] > 0:
                    rad = Gut_Data.loc[i,'Radiation']
                    tem = Gut_Data.loc[i,'Cell Temperature']
                    sample = np.array([rad,tem])
                    sample = sample.reshape(1, -1)
                    eff = lm_4.predict(sample) 
                    Gut_Data.loc[i, 'PV Corrected'] = 240*eff*rad*1.633
                    Gut_Data.loc[i, 'Radiation'] = rad
                    Gut_Data.loc[i, 'Efficiency'] = eff

       else:
             Gut_Data.loc[i, 'PV Corrected'] = 0           


######## PV with curtailment from "El Espino" #################################            
PV_Espino = pd.DataFrame()

PV_Espino['PV Power'] = Power_Data_2['PV Power']

PV_Espino['Day'] = 0

foo = 0
iterations = int(len(Data_Corrected)/288)

for i in range(iterations):
    for j in range(288):
        PV_Espino.iloc[foo,1] = i
        foo += 1
 
PV_Espino['hour'] = 0

foo = 0

for i in range(iterations):
    for j in range(int(288/12)):
        for s in range(12):
            PV_Espino.iloc[foo,2] = j
            foo += 1         

PV_Espino_Hourly = pd.DataFrame()

PV_Espino_Hourly = PV_Espino.groupby(['Day','hour']).mean()

PV_Espino_Hourly.index = index_hourly

#######################  Comparation

PV_Energy = pd.DataFrame()

start = '2016-03-21 01:00:00'
end = '2017-03-21 00:00:00'

PV_Energy['PV Power Without Curtailment'] = Hourly_Data['PV Corrected'][start:end]
PV_Energy['PV Power Gutierrez'] = Gut_Data['PV Corrected'][start:end]
PV_Energy['PV Power With Curtailment'] = PV_Espino_Hourly['PV Power'][start:end]
PV_Energy['Radiation Gutierrez'] = Gut_Data['Radiation'] [start:end]
PV_Energy['Radiation Espino'] = Hourly_Data['Radiation'][start:end]

PV_Energy["hour"] = 0
            
foo = 0
iterations = int(len(PV_Energy)/24)

for i in range(iterations):
    for j in range(1,25):
        index = PV_Energy.index[foo]
        PV_Energy.loc[index,'hour'] = j
        foo += 1                     

PV_Espino_Day = PV_Energy.groupby(['hour']).mean()            
PV_Espino_Day['PV Power Without Curtailment'] = PV_Espino_Day['PV Power Without Curtailment']/1000
PV_Espino_Day['PV Power Gutierrez'] = PV_Espino_Day['PV Power Gutierrez']/1000
PV_Espino_Day['PV Power With Curtailment'] = PV_Espino_Day['PV Power With Curtailment']/1000
    

Data_Optimization = pd.DataFrame()
Data_Optimization['PV Power Without Curtailment'] = list(PV_Energy['PV Power Without Curtailment'])
Data_Optimization['PV Power Gutierrez'] = list(PV_Energy['PV Power Gutierrez'])
Data_Optimization.index = range(1,8761)
Data_Optimization.columns = [1,2]


Data_Optimization.to_excel('Scenarios/PV_PAPER_01_30.xls')


#### paper figure
size = [20,15]
plt.figure(figsize=size)


ax = PV_Espino_Day['PV Power Without Curtailment'].plot(style = '--',linewidth=5)
ax = PV_Espino_Day['PV Power With Curtailment'].plot(style = ':',linewidth=5)
ax1 = PV_Espino_Day['Radiation Espino'].plot(c='y', secondary_y=True,linewidth=5)

Espino_regression = mlines.Line2D([], [], color='blue',
                                  label='Espino regression', 
                                  linestyle='--',linewidth=5)
Espino_measurement = mlines.Line2D([], [], color='green',
                                  label='Espino measurement', 
                                  linestyle=':',linewidth=5)
Radiation = mlines.Line2D([], [], color='yellow',
                                  label='Radiation', 
                                  linestyle='-',linewidth=5)

ax.tick_params(axis='x', which='major', labelsize=30)
ax.tick_params(axis='y', which='major', labelsize=30)
ax1.tick_params(axis='y', which='major', labelsize=30)
ax.set_xlabel('hours', labelpad=20, size=40 )
ax.set_ylabel('Power (kW)', labelpad=20, size=40)
ax1.set_ylabel('Irradiation (W/m$^{2}$)', labelpad=20, size=40)


##plt.legend(bbox_to_anchor=(1, -0.1),fontsize = 12,frameon=False, ncol=2)
plt.legend(handles=[Espino_regression, Espino_measurement, Radiation],
           bbox_to_anchor=(1, -0.1),frameon=False, ncol=3
           ,fontsize = 30)

