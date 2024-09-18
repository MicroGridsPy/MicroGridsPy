# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 19:40:26 2023

@author: costa


Main da richiamare dal main di MG.py


"""

import pandas as pd
import geopandas as gpd
from microgridspy.grid_routing.functions_routing import roads_import, roads_to_multipoints, users_geodataframe_prep
from microgridspy.grid_routing.trees import routing_simple, routing_roads_no_P, routing_roads_P


def Distribution_Line(Routing_Method, model):
    
    """ Parameters Initialization """
    
    crs = model.CRS
    crs_str = r'epsg:'+str(crs)
    max_y = model.Max_y
    min_y = model.Min_y
    max_x = model.Max_x
    min_x = model.Min_x
    spec_line_cost = model.Specific_Line_Cost
    meter_cost = model.Meter_Cost
    
 
    """ Roads """
    
    roads_import(crs_str, max_y, min_y, max_x, min_x)

    roads = gpd.read_file('Shapefiles/roads.shp') 
    roads = roads.to_crs(crs)

    roads_multipoints = roads_to_multipoints(roads, crs)
    
    
    """ Users Geodataframe """

    df_users = pd.read_csv('Inputs/Users.csv', sep = ';')
    users_number = len(df_users.lon)
    
    gdf_users = users_geodataframe_prep(crs, df_users)
    # gdf_users = gpd.read_file(path + '/Intermediate/gdf_users.shp') -> non serve perchè lo faccio tornare dalla funzione
    gdf_users.to_crs(crs)
    gdf_users.crs # just to check
 
    
    """ Distribution Line Routing """
    
    if Routing_Method=='Users':
        
        tot_grid_length = routing_simple(crs, gdf_users)
    

    elif Routing_Method=='Roads':

        tot_grid_length = routing_roads_no_P(crs, gdf_users, roads_multipoints)

        
    elif Routing_Method=='Power':
        
        tot_grid_length = routing_roads_P(crs, gdf_users, roads_multipoints)


    return users_number, tot_grid_length 


