# -*- coding: utf-8 -*-

#%% Definition of the inputs
'''
Input data definition
'''

from core import User, np, pd
User_list = []


'''
This example input file represents a single household user whose only load
is the "hairdryer". The example showcases how to model multi-year loads,
appliances that appear only after a certain minimum time threshold.
'''

#Create new user classes
HI = User("High Income Households",45,3)
User_list.append(HI)

MI = User("Medium Income Households",64,3)
User_list.append(MI)

LI = User("Low Income Households",15,3)
User_list.append(LI)

HO1 = User("Hotel Old 1",1)
User_list.append(HO1)

HO2 = User("Hotel Old 2",1)
User_list.append(HO2)

HO3 = User("Hotel Old 3",1)
User_list.append(HO3)

HO4 = User("Hotel Old 4",1)
User_list.append(HO4)

TO = User("Tourist Office",1)
User_list.append(TO)

EC = User("Electrical Committee",1)
User_list.append(EC)

AL = User("Artisanal Lab",1)
User_list.append(AL)

#High-Income

HI_bulb = HI.Appliance(HI,5,12,2,360,0.2,2)
HI_bulb.windows([480,600],[1140,1440],0.4)

HI_bulb_new = HI.Appliance(HI,3,12,2,360,0.2,2,year_min=10,initial_share=0)
HI_bulb_new.windows([480,600],[1140,1440],0.4)

HI_radio = HI.Appliance(HI,1,7,2,240,0.1,30)
HI_radio.windows([480,660],[1020,1320],0.33)

HI_Freezer = HI.Appliance(HI,1,250,1,1440,0,30,'yes',3)
HI_Freezer.windows([0,1440],[0,0])
HI_Freezer.specific_cycle_1(200,20,5,10)
HI_Freezer.specific_cycle_2(200,15,5,15)
HI_Freezer.specific_cycle_3(200,10,5,20)
HI_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

HI_microwave = HI.Appliance(HI,1,1000,2,10,0.2,2,thermal_P_var=0.4)
HI_microwave.windows([780,840],[1140,1200],0.4)

HI_WMachine = HI.Appliance(HI,1,500,2,90,0,1,occasional_use=0.14)
HI_WMachine.windows([540,720],[1080,1260],0.35)
HI_WMachine.specific_cycle_1(500,5,5,20)
HI_WMachine.specific_cycle_2(400,5,5,30)
HI_WMachine.specific_cycle_2(400,5,5,30)
HI_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

HI_ElHeater = HI.Appliance(HI,1,1500,2,360,0.2,30, thermal_P_var=0.4)
HI_ElHeater.windows([300,480],[1080,1380],0.25)

HI_PC = HI.Appliance(HI,1,70,1,90,0.1,30)
HI_PC.windows([960,1440],[0,0],0.35)

HI_Phone_charger = HI.Appliance(HI,2,5,2,480,0.2,60)
HI_Phone_charger.windows([1200,1440],[0,420],0.35)

HI_Phone_charger_new = HI.Appliance(HI,2,5,2,480,0.2,60,year_min=14,initial_share=0)
HI_Phone_charger_new.windows([1200,1440],[0,420],0.35)

HI_TV = HI.Appliance(HI,2,150,2,360,0.1,30)
HI_TV.windows([600,780],[1140,1380],0.4)

HI_breakfast_coffee = HI.Appliance(HI,1,1800,1,5,0.15,2, thermal_P_var = 0.2, pref_index =0)
HI_breakfast_coffee.windows([6*60,9*60],[0,0],0.15)

HI_mate = HI.Appliance(HI,1,1600,1,30,0.3,2, thermal_P_var = 0.2, pref_index =0)
HI_mate.windows([7*60,20*60],[0,0],0.15)


#Medium-Income

MI_bulb = MI.Appliance(MI,5,12,2,360,0.2,2)
MI_bulb.windows([480,600],[1140,1440],0.4)

MI_bulb_new = MI.Appliance(MI,3,12,2,360,0.2,2,year_min=15,initial_share=0)
MI_bulb_new.windows([480,600],[1140,1440],0.4)

MI_radio_new = MI.Appliance(MI,1,7,2,240,0.1,30,year_min=8,initial_share=0)
MI_radio_new.windows([480,660],[1020,1320],0.33)

MI_Freezer = MI.Appliance(MI,1,250,1,1440,0,30,'yes',3)
MI_Freezer.windows([0,1440],[0,0])
MI_Freezer.specific_cycle_1(200,20,5,10)
MI_Freezer.specific_cycle_2(200,15,5,15)
MI_Freezer.specific_cycle_3(200,10,5,20)
MI_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

MI_microwave = MI.Appliance(MI,1,1000,2,10,0.2,2,thermal_P_var=0.4)
MI_microwave.windows([780,840],[1140,1200],0.4)

MI_WMachine = MI.Appliance(MI,1,500,2,90,0,1,occasional_use=0.14)
MI_WMachine.windows([540,720],[1080,1260],0.35)
MI_WMachine.specific_cycle_1(500,5,5,20)
MI_WMachine.specific_cycle_2(400,5,5,30)
MI_WMachine.specific_cycle_2(400,5,5,30)
MI_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

MI_ElHeater_new = MI.Appliance(MI,1,1500,2,360,0.2, 30,thermal_P_var=0.4,year_min=8,initial_share=0)
MI_ElHeater_new.windows([300,480],[1080,1380],0.25)

MI_PC_new = MI.Appliance(MI,1,70,1,90,0.1,30,year_min=15,initial_share=0)
MI_PC_new.windows([960,1440],[0,0],0.35)

MI_Phone_charger = MI.Appliance(MI,2,5,2,480,0.2,60)
MI_Phone_charger.windows([1200,1440],[0,420],0.35)

MI_Phone_charger_new = MI.Appliance(MI,2,5,2,480,0.2,60,year_min=17,initial_share=0)
MI_Phone_charger_new.windows([1200,1440],[0,420],0.35)

MI_TV = MI.Appliance(MI,1,150,2,360,0.1,30)
MI_TV.windows([600,780],[1140,1380],0.4)

MI_breakfast_coffee = MI.Appliance(MI,1,1800,1,5,0.15,2, thermal_P_var = 0.2, pref_index =0)
MI_breakfast_coffee.windows([6*60,9*60],[0,0],0.15)

MI_mate = MI.Appliance(MI,1,1600,1,30,0.3,2, thermal_P_var = 0.2, pref_index =0)
MI_mate.windows([7*60,20*60],[0,0],0.15)


#Low-Income

LI_bulb = LI.Appliance(LI,2,12,2,360,0.2,2)
LI_bulb.windows([480,600],[1140,1440],0.4)

LI_bulb_new = LI.Appliance(LI,2,12,2,360,0.2,2,year_min=4,initial_share=0)
LI_bulb_new.windows([480,600],[1140,1440],0.4)

LI_Freezer_new = LI.Appliance(LI,1,250,1,1440,0,30,'yes',3, year_min = 5, initial_share=0)
LI_Freezer_new.windows([0,1440],[0,0])
LI_Freezer_new.specific_cycle_1(200,20,5,10)
LI_Freezer_new.specific_cycle_2(200,15,5,15)
LI_Freezer_new.specific_cycle_3(200,10,5,20)
LI_Freezer_new.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

LI_radio_new = LI.Appliance(LI,1,7,2,240,0.1,30,year_min=4,initial_share=0)
LI_radio_new.windows([480,660],[1020,1320],0.33)

LI_WMachine = LI.Appliance(LI,1,500,2,90,0,1,occasional_use=0.14)
LI_WMachine.windows([540,720],[1080,1260],0.35)
LI_WMachine.specific_cycle_1(500,5,5,20)
LI_WMachine.specific_cycle_2(400,5,5,30)
LI_WMachine.specific_cycle_2(400,5,5,30)
LI_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

LI_PC_new = LI.Appliance(LI,1,70,1,90,0.1,30,year_min=15,initial_share=0)
LI_PC_new.windows([960,1440],[0,0],0.35)

LI_Phone_charger = LI.Appliance(LI,1,5,2,480,0.2,60)
LI_Phone_charger.windows([1200,1440],[0,420],0.35)

LI_Phone_charger_new = LI.Appliance(LI,2,5,2,480,0.2,60,year_min=10,initial_share=0)
LI_Phone_charger_new.windows([1200,1440],[0,420],0.35)

LI_TV = LI.Appliance(LI,1,150,2,360,0.1,30)
LI_TV.windows([600,780],[1140,1380],0.4)

#LI_Class Cooking

LI_mate_new = LI.Appliance(LI,1,1600,1,30,0.3,2, thermal_P_var = 0.2, pref_index =0, year_min=17, initial_share= 0)
LI_mate_new.windows([7*60,20*60],[0,0],0.15)

#Hotel Old 1

HO1_room_bulb = HO1.Appliance(HO1,25,12,3,600,0.1,30)
HO1_room_bulb.windows([0,90],[330,510],0.1,[990,1440])

HO1_tv = HO1.Appliance(HO1,5,150,1,180,0.2,30)
HO1_tv.windows([1110,1440],[0,0],0.2)

HO1_phone_charger = HO1.Appliance(HO1,5,5,2,480,0.2,60)
HO1_phone_charger.windows([0,420],[1200,1440],0.35) 

HO1_kitch_bulb = HO1.Appliance(HO1,7,12,1,1020,0.1,30,'yes')
HO1_kitch_bulb.windows([330,1350],[0,0],0.1)

HO1_w_heater = HO1.Appliance(HO1,1,1600,1,30,0.3,2,thermal_P_var=0.2)
HO1_w_heater.windows([420,1200],[0,0],0.15)

HO1_microwave = HO1.Appliance(HO1,1,1000,3,30,0.2,2,thermal_P_var=0.4)
HO1_microwave.windows([390,510],[630,750],0.1,[1110,1230])

HO1_Freezer = HO1.Appliance(HO1,1,250,1,1440,0,30,'yes',3)
HO1_Freezer.windows([0,1440],[0,0])
HO1_Freezer.specific_cycle_1(200,20,5,10)
HO1_Freezer.specific_cycle_2(200,15,5,15)
HO1_Freezer.specific_cycle_3(200,10,5,20)
HO1_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

HO1_WMachine = HO1.Appliance(HO1,1,500,2,90,0,1,occasional_use=0.14)
HO1_WMachine.windows([540,720],[1080,1260],0.35)
HO1_WMachine.specific_cycle_1(500,5,5,20)
HO1_WMachine.specific_cycle_2(400,5,5,30)
HO1_WMachine.specific_cycle_2(400,5,5,30)
HO1_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

HO1_off_bulb = HO1.Appliance(HO1,2,12,2,360,0.1,30,'yes')
HO1_off_bulb.windows([450,630],[990,1290],0.1)

HO1_common_bulb_2 = HO1.Appliance(HO1,15,12,1,1020,0,1020,flat='yes')
HO1_common_bulb_2.windows([390,1440],[0,0],0)

HO1_common_heater = HO1.Appliance(HO1,1,1500,2,720,0.3,30, thermal_P_var=0.4)
HO1_common_heater.windows([0,630],[1050,1440],0.1)

HO1_outdoor_bulb = HO1.Appliance(HO1,6,20,2,720,0,720, 'yes', flat = 'yes')
HO1_outdoor_bulb.windows([0,430],[1130,1440],0.1)


#Hotel Old 2
HO2_room_bulb = HO2.Appliance(HO2,25,12,3,600,0.1,30)
HO2_room_bulb.windows([0,90],[330,510],0.1,[990,1440])

HO2_tv = HO2.Appliance(HO2,5,150,1,180,0.2,30)
HO2_tv.windows([1110,1440],[0,0],0.2)

HO2_phone_charger = HO2.Appliance(HO2,5,5,2,480,0.2,60)
HO2_phone_charger.windows([0,420],[1200,1440],0.35) 

HO2_kitch_bulb = HO2.Appliance(HO2,7,12,1,1020,0.1,30,'yes')
HO2_kitch_bulb.windows([330,1350],[0,0],0.1)

HO2_w_heater = HO2.Appliance(HO2,1,1600,1,30,0.3,2,thermal_P_var=0.2)
HO2_w_heater.windows([420,1200],[0,0],0.15)

HO2_microwave = HO2.Appliance(HO2,1,1000,3,30,0.2,2,thermal_P_var=0.4)
HO2_microwave.windows([390,510],[630,750],0.1,[1110,1230])

HO2_Freezer = HO2.Appliance(HO2,1,250,1,1440,0,30,'yes',3)
HO2_Freezer.windows([0,1440],[0,0])
HO2_Freezer.specific_cycle_1(200,20,5,10)
HO2_Freezer.specific_cycle_2(200,15,5,15)
HO2_Freezer.specific_cycle_3(200,10,5,20)
HO2_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

HO2_WMachine = HO2.Appliance(HO2,1,500,2,90,0,1,occasional_use=0.14)
HO2_WMachine.windows([540,720],[1080,1260],0.35)
HO2_WMachine.specific_cycle_1(500,5,5,20)
HO2_WMachine.specific_cycle_2(400,5,5,30)
HO2_WMachine.specific_cycle_2(400,5,5,30)
HO2_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

HO2_off_bulb = HO2.Appliance(HO2,2,12,2,360,0.1,30,'yes')
HO2_off_bulb.windows([450,630],[990,1290],0.1)

HO2_common_bulb_2 = HO2.Appliance(HO2,15,12,1,1020,0,1020,flat='yes')
HO2_common_bulb_2.windows([390,1440],[0,0],0)

HO2_common_heater = HO2.Appliance(HO2,1,1500,2,720,0.3,30, thermal_P_var=0.4)
HO2_common_heater.windows([0,630],[1050,1440],0.1)

HO2_outdoor_bulb = HO2.Appliance(HO2,6,20,2,720,0,720, 'yes', flat = 'yes')
HO2_outdoor_bulb.windows([0,430],[1130,1440],0.1)

#Hotel Old 3

HO3_room_bulb = HO3.Appliance(HO3,25,12,3,600,0.1,30)
HO3_room_bulb.windows([0,90],[330,510],0.1,[990,1440])

HO3_tv = HO3.Appliance(HO3,5,150,1,180,0.2,30)
HO3_tv.windows([1110,1440],[0,0],0.2)

HO3_phone_charger = HO3.Appliance(HO3,5,5,2,480,0.2,60)
HO3_phone_charger.windows([0,420],[1200,1440],0.35) 

HO3_kitch_bulb = HO3.Appliance(HO3,7,12,1,1020,0.1,30,'yes')
HO3_kitch_bulb.windows([330,1350],[0,0],0.1)

HO3_w_heater = HO3.Appliance(HO3,1,1600,1,30,0.3,2,thermal_P_var=0.2)
HO3_w_heater.windows([420,1200],[0,0],0.15)

HO3_microwave = HO3.Appliance(HO3,1,1000,3,30,0.2,2,thermal_P_var=0.4)
HO3_microwave.windows([390,510],[630,750],0.1,[1110,1230])

HO3_Freezer = HO3.Appliance(HO3,1,250,1,1440,0,30,'yes',3)
HO3_Freezer.windows([0,1440],[0,0])
HO3_Freezer.specific_cycle_1(200,20,5,10)
HO3_Freezer.specific_cycle_2(200,15,5,15)
HO3_Freezer.specific_cycle_3(200,10,5,20)
HO3_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

HO3_WMachine = HO3.Appliance(HO3,1,500,2,90,0,1,occasional_use=0.14)
HO3_WMachine.windows([540,720],[1080,1260],0.35)
HO3_WMachine.specific_cycle_1(500,5,5,20)
HO3_WMachine.specific_cycle_2(400,5,5,30)
HO3_WMachine.specific_cycle_2(400,5,5,30)
HO3_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

HO3_off_bulb = HO3.Appliance(HO3,2,12,2,360,0.1,30,'yes')
HO3_off_bulb.windows([450,630],[990,1290],0.1)

HO3_common_bulb_2 = HO3.Appliance(HO3,15,12,1,1020,0,1020,flat='yes')
HO3_common_bulb_2.windows([390,1440],[0,0],0)

HO3_common_heater = HO3.Appliance(HO3,1,1500,2,720,0.3,30, thermal_P_var=0.4)
HO3_common_heater.windows([0,630],[1050,1440],0.1)

HO3_outdoor_bulb = HO3.Appliance(HO3,6,20,2,720,0,720, 'yes', flat = 'yes')
HO3_outdoor_bulb.windows([0,430],[1130,1440],0.1)

#Hotel Old 4

HO4_room_bulb = HO4.Appliance(HO4,25,12,3,600,0.1,30)
HO4_room_bulb.windows([0,90],[330,510],0.1,[990,1440])

HO4_tv = HO4.Appliance(HO4,5,150,1,180,0.2,30)
HO4_tv.windows([1110,1440],[0,0],0.2)

HO4_phone_charger = HO4.Appliance(HO4,5,5,2,480,0.2,60)
HO4_phone_charger.windows([0,420],[1200,1440],0.35) 

HO4_kitch_bulb = HO4.Appliance(HO4,7,12,1,1020,0.1,30,'yes')
HO4_kitch_bulb.windows([330,1350],[0,0],0.1)

HO4_w_heater = HO4.Appliance(HO4,1,1600,1,30,0.3,2,thermal_P_var=0.2)
HO4_w_heater.windows([420,1200],[0,0],0.15)

HO4_microwave = HO4.Appliance(HO4,1,1000,3,30,0.2,2,thermal_P_var=0.4)
HO4_microwave.windows([390,510],[630,750],0.1,[1110,1230])

HO4_Freezer = HO4.Appliance(HO4,1,250,1,1440,0,30,'yes',3)
HO4_Freezer.windows([0,1440],[0,0])
HO4_Freezer.specific_cycle_1(200,20,5,10)
HO4_Freezer.specific_cycle_2(200,15,5,15)
HO4_Freezer.specific_cycle_3(200,10,5,20)
HO4_Freezer.cycle_behaviour([480,1200],[0,0],[300,479],[0,0],[0,299],[1201,1440])

HO4_WMachine = HO4.Appliance(HO4,1,500,2,90,0,1,occasional_use=0.14)
HO4_WMachine.windows([540,720],[1080,1260],0.35)
HO4_WMachine.specific_cycle_1(500,5,5,20)
HO4_WMachine.specific_cycle_2(400,5,5,30)
HO4_WMachine.specific_cycle_2(400,5,5,30)
HO4_WMachine.cycle_behaviour([540,600],[0,0],[600,720],[0,0],[1080,1260],[0,0])

HO4_off_bulb = HO4.Appliance(HO4,2,12,2,360,0.1,30,'yes')
HO4_off_bulb.windows([450,630],[990,1290],0.1)

HO4_common_bulb_2 = HO4.Appliance(HO4,15,12,1,1020,0,1020,flat='yes')
HO4_common_bulb_2.windows([390,1440],[0,0],0)

HO4_common_heater = HO4.Appliance(HO4,1,1500,2,720,0.3,30, thermal_P_var=0.4)
HO4_common_heater.windows([0,630],[1050,1440],0.1)

HO4_outdoor_bulb = HO4.Appliance(HO4,6,20,2,720,0,720, 'yes', flat = 'yes')
HO4_outdoor_bulb.windows([0,430],[1130,1440],0.1)

#Artisanal lab
AL_indoor_bulb = AL.Appliance(AL,5,12,2,300,0.1,30,'yes', flat = 'yes')
AL_indoor_bulb.windows([450,630],[990,1230],0.1)

AL_desk_bulb = AL.Appliance(AL,10,12,2,600,0.2,120)
AL_desk_bulb.windows([450,810],[870,1230],0.1)

AL_outdoor_bulb = AL.Appliance(AL,1,20,2,720,0,720, 'yes', flat = 'yes')
AL_outdoor_bulb.windows([0,430],[1130,1440],0.1)

AL_pc = AL.Appliance(AL,2,70,1,720,0.2,60)
AL_pc.windows([450,1230],[0,0],0.1)

AL_printer = AL.Appliance(AL,1,10,1,720,0.2,1)
AL_printer.windows([450,1230],[0,0],0.1)

AL_modem = AL.Appliance(AL,1,5,1,1440,0,1440, flat = 'yes')
AL_modem.windows([0,1440],[0,0],0)

AL_ElHeater = AL.Appliance(AL,1,1500,2,360,0.3,30, thermal_P_var=0.4)
AL_ElHeater.windows([450,690],[1050,1230],0.2)

AL_w_heater = AL.Appliance(AL,1,1600,3,30,0.3,2, thermal_P_var=0.2)
AL_w_heater.windows([450,1230],[0,0],0.15)

AL_sewing = AL.Appliance(AL,5,350,2,540,0.3,15)
AL_sewing.windows([450,810],[870,1230],0.1)

AL_saw = AL.Appliance(AL,1,1000,2,120,0.4,5, year_min = 5)
AL_saw.windows([450,810],[870,1230],0.1)

AL_drill = AL.Appliance(AL,1,600,2,60,0.3,5, year_min = 3)
AL_drill.windows([450,810],[870,1230],0.1)

AL_mill = AL.Appliance(AL,1,1200,2,120,0.4,5, year_min = 6)
AL_mill.windows([450,810],[870,1230],0.1)

AL_compress = AL.Appliance(AL,1,1800,2,30,0.4,5, year_min = 8)
AL_compress.windows([450,810],[870,1230],0.1)

AL_planer = AL.Appliance(AL,1,550,2,120,0.3,10, year_min = 4)
AL_planer.windows([450,810],[870,1230],0.1)

AL_sander = AL.Appliance(AL,1,200,2,120,0.3,10, year_min = 7)
AL_sander.windows([450,810],[870,1230],0.1)

# Tourist Office
TO_indoor_bulb = TO.Appliance(TO,8,12,2,300,0.1,30,'yes', flat = 'yes', year_min = 5)
TO_indoor_bulb.windows([450,630],[990,1230],0.1)

TO_desk_bulb = TO.Appliance(TO,3,12,2,600,0.2,120, year_min = 5)
TO_desk_bulb.windows([450,810],[870,1230],0.1)

TO_outdoor_bulb = TO.Appliance(TO,1,20,2,720,0,720, 'yes', flat = 'yes', year_min = 5)
TO_outdoor_bulb.windows([0,430],[1130,1440],0.1)

TO_pc = TO.Appliance(TO,3,70,1,720,0.2,60, year_min = 5)
TO_pc.windows([450,1230],[0,0],0.1)

TO_printer = TO.Appliance(TO,1,10,1,720,0.2,1, year_min = 5)
TO_printer.windows([450,1230],[0,0],0.1)

TO_modem = TO.Appliance(TO,1,5,1,1440,0,1440, flat = 'yes', year_min = 5)
TO_modem.windows([0,1440],[0,0],0)

TO_ElHeater = TO.Appliance(TO,1,1500,2,360,0.3,30,thermal_P_var=0.4, year_min = 5)
TO_ElHeater.windows([450,690],[1050,1230],0.2)

TO_w_heater = TO.Appliance(TO,1,1600,3,30,0.3,2, thermal_P_var=0.2, year_min = 5)
TO_w_heater.windows([450,1230],[0,0],0.15)

#Electrical committeee
EC_indoor_bulb = EC.Appliance(EC,6,12,2,300,0.1,30,'yes', flat = 'yes')
EC_indoor_bulb.windows([450,630],[990,1230],0.1)

EC_desk_bulb = EC.Appliance(EC,5,12,2,600,0.2,120)
EC_desk_bulb.windows([450,810],[870,1230],0.1)

EC_outdoor_bulb = EC.Appliance(EC,1,20,2,720,0,720, 'yes', flat = 'yes')
EC_outdoor_bulb.windows([0,430],[1130,1440],0.1)

EC_pc = EC.Appliance(EC,5,70,1,720,0.2,60)
EC_pc.windows([450,1230],[0,0],0.1)

EC_printer = EC.Appliance(EC,1,10,1,10,0.2,1)
EC_printer.windows([450,1230],[0,0],0.1)

EC_modem = EC.Appliance(EC,1,5,1,1440,0,1440, flat = 'yes')
EC_modem.windows([0,1440],[0,0],0)

EC_ElHeater = EC.Appliance(EC,1,1500,2,360,0.3,30,thermal_P_var=0.4)
EC_ElHeater.windows([450,690],[1050,1230],0.2)

EC_w_heater = EC.Appliance(EC,1,1600,3,30,0.3,2, thermal_P_var=0.2)
EC_w_heater.windows([450,1230],[0,0],0.15)
