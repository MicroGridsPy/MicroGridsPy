# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 19:44:10 2023

@author: costa

Check commenti

"""

import geopandas as gpd
import osmnx as ox 
from shapely.geometry import MultiPoint
import numpy as np


def roads_import(crs_str, max_y, min_y, max_x, min_x): 
    
    """
    ROADS 
    imported automatically from OSM, cropped to study area and reprojected, 
    saved as shp in Imports. Then the geometry of the edges file is simplified and saved 
    in the folder input_preparation (-> mpaka -> roads) as a new shapefile named roads

    """
    
    # Data Import from OSM, following the study_area boundaries  
    osm_import = ox.graph.graph_from_bbox(max_y, min_y, max_x, min_x, network_type = 'all_private')
    osm_import_projected = ox.projection.project_graph(osm_import)
    # ox.plot.plot_graph(osm_import_projected)
    
    # Initialization 
    ox.save_graph_shapefile(osm_import_projected, filepath = 'Shapefiles')
    # saving the graph as a shapefile, two shapefiles are created: one for the edges (lines
    # representing the effective streets), and one for the nodes (those created while mapping
    # roads on OSM).
    
    
    # Simplify geometry 
    # this part of the code simplifies the 'geometry' of the roads imported from OSM: a shapefile 
    # called 'roads'' is created, which contains only the simplified edges of the OSM roads (Not sure is necessary)
    osm_import_roads = gpd.read_file('Shapefiles/edges.shp')
    osm_import_roads_simple = osm_import_roads.geometry.simplify(tolerance=0.0005)
    osm_import_roads_simple = osm_import_roads_simple.to_crs(crs_str) 
    osm_import_roads_simple.to_file('Shapefiles/roads.shp') 
    
    return




def roads_to_multipoints(roads, crs) : 
    """
    Transform the shapefile of the roads' edges of the study area (already simplified) 
    in a shapely multipoint object. Then it also creates a geodataframe with the multipoints
    and saves it into a shapefile (located in the folder 'roads' of the Inputs study_area folder),
    so that the multipoints of the roads of the study area con be visualized in qgis.

    Parameters
    ----------
    roads :
    crs : 

    Returns
    -------
    roads_multipoints 

    """

    
    """ Transforming the roads' edges shp into a MultiPoint object """
    
    # Read and reproject roads.shp (shapefile with simplified road edges)
    # roads = gpd.read_file('Shapefiles/roads.shp')
    # roads = roads.to_crs(crs)
    
    roads_points = [] 
    for line in roads['geometry']:
        for x in list(line.coords): 
            roads_points.append(x)
    roads_multipoints = MultiPoint(roads_points)
    
    # I want to put the multipoints, separated, in a gdf. To do that first extract the values of the points 
    # through the .geoms function (vedi user guide shapely) and put them in a geoseries to be passed later 
    # as the geometry of the gdf  
    geoseries = gpd.GeoSeries(roads_multipoints.geoms)
    gdf_multipoints = gpd.GeoDataFrame(geometry = geoseries, crs = crs)
    gdf_multipoints.to_file('Shapefiles/roads_multipoint.shp') #this is to visualize in qgis 

    return  roads_multipoints




def users_geodataframe_prep(crs, df_users):
    """
    This function process the dataset with the coordinates of the users.
    First it cleans the dataframe, by dropping the missing values, then creates
    a geodataframe with the coordinates as point geometries and projects it to
    the right crs. Another geodataframe is created, by clipping the coordinates 
    gdf to the study area shapefile. Both the clipped and the unclipped geodataframes
    are then saved as shapefiles.
    Parameters: 
    (- area : GeoDataFrame with the polygon of the study area)
    - crs : desired crs 
    (- out_path : string with output path to save the unclipped gdf as shapefile)
    (- out_path_clipped : string with output path to save the clipped gdf as shapefile)
    - df_users : pandas dataframe in which the coordinates csv is read 
    Returns
    - Nothing 
    - Alternatively the clipped and unclipped users coordinates geodataframes 
    """
    
    # Cleaning the dataframe by dropping the rows with missing values
    print('Missing values before cleaning' + '\n' + str(df_users.isnull().sum())) 
    df_users = df_users.dropna() 
    
    # Reassigning the indices of the dataset elements 
    df_users.reset_index(inplace = True) 
    df_users.drop(columns = ["index"])
    print('Missing values after cleaning' + '\n' + str(df_users.isnull().sum())) # just to check
    
    # Creation of the GeoDataFrame in geopandas 
    gdf_users = gpd.GeoDataFrame(df_users, geometry=gpd.points_from_xy(x = df_users.lon, 
                                                        y = df_users.lat, crs = crs))
    
    # Reprojection to specific crs -> the unit of distance will now be meters 
    gdf_users = gdf_users.to_crs(crs = crs) 
    print('CRS of the Dataset:' + '\n' + str(gdf_users.crs)) 
    
    # Create a shapefile with the elemnts of the GeoDataFrame
    gdf_users.to_file('Shapefiles/gdf_users.shp')
    
    # Clip the users coordinates shp to the study area shp and save as new shapefile -> TENEREE OPPURE NO?
    # gdf_users_clipped = gpd.clip(gdf_users, area)
    # gdf_users_clipped.to_file(out_path_clipped)
    # NB Se tengo questa parte potrei mettere una richiesta se si vuole clippare il df all'area se magari
    # si ha un dataset con più coordinate, ma potrebbe essere inutile
    
    return gdf_users


# This function takes as input the gdf_users used in the grid routing with the power installed and assigns
# the tier of consumption to each user in a new column, on the base of the values of installed power per each tier 
# given by the MultiTier Framework. Two effects: the use will know which tier to assign to every user 
# and the size of the user points in the map plot will be assigned accordingly to their tier 
def tier_assignment(gdf_users):
    
    gdf_users['Tier'] = 0
    
    for i, j in gdf_users.iterrows():
        
        # if gdf_users.loc[i, 'Power_installed'].between(0, 50, inclusive = 'right'):
        #     gdf_users.loc[i, 'Tier'] = 1
            
        # elif gdf_users.loc[i, 'Power_installed'].between(50, 200, inclusive = 'right'):
        #     gdf_users.loc[i, 'Tier'] = 2
            
        # elif gdf_users.loc[i, 'Power_installed'].between(200, 800, inclusive = 'right'):
        #     gdf_users.loc[i, 'Tier'] = 3
            
        # elif gdf_users.loc[i, 'Power_installed'].between(800, 2000, inclusive = 'right'):
        #     gdf_users.loc[i, 'Tier'] = 4
        
        if   0 < gdf_users.loc[i, 'Power_installed'] <= 50: 
            gdf_users.loc[i, 'Tier'] = '1'
        
        elif 50 < gdf_users.loc[i, 'Power_installed'] <= 200:
            gdf_users.loc[i, 'Tier'] = '2'
        
        elif  200 < gdf_users.loc[i, 'Power_installed'] <= 800 :
            gdf_users.loc[i, 'Tier'] = '3'
            
        elif  800 < gdf_users.loc[i, 'Power_installed'] <= 2000 :
            gdf_users.loc[i, 'Tier'] = '4'
                
        elif gdf_users.loc[i, 'Power_installed'] > 2000:
            gdf_users.loc[i, 'Tier'] = '5'
            
    gdf_users['Size'] = gdf_users['Tier'].str.extract('(\d+)').astype(int)
            
    return gdf_users
