# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 19:43:20 2023

@author: costa

ROUTING FUNCTIONS -> check con trials 

"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import nearest_points
import networkx as nx
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from sklearn.preprocessing import MinMaxScaler
from geopy.distance import lonlat, distance, great_circle
import plotly.express as px
import plotly.io as pio
from plotly.offline import plot
from Functions_def import tier_assignment



def routing_simple(crs, gdf_users):

    
    """ Calculating the distance matrix and normalizing it  """
    
    coord = np.column_stack((gdf_users.geometry.x, gdf_users.geometry.y))
    dist_matrix = cdist(coord, coord)
    
    # Normalization of the matrix
    dist_matrix_normalized = (dist_matrix - dist_matrix.min()) / (dist_matrix.max() - dist_matrix.min())
    
    
    """ Grid Routing """
    
    # Create the graph
    graph = nx.from_numpy_array(dist_matrix)
    
    # Assign the positions of the nodes in the graph
    pos = dict(zip(graph.nodes, gdf_users[['lon', 'lat']].values))
    
    
    # Assign weights to the edges 
    for y, z, w in graph.edges(data=True):
        norm_dist = dist_matrix_normalized[y,z]
        w['weight'] = norm_dist
        
    # graph.edges(data=True) # to check if weights were assigned correctly 
    
    # Evaluate the MST 
    tree = nx.minimum_spanning_tree(graph, weight='weight')

    # MST Plot    
    plt.figure()
    plt.title('Grid Routing')
    nx.draw(tree, pos, node_size=5, node_color='darkorange')
    plt.savefig('Results/Plots/Network_Plot.png' , dpi=600)
    # plt.show()

 
    """ Length of the Line """
    
    length_list = []

    for u, v in tree.edges():
        
        node_u = (gdf_users.loc[u, 'lon'], gdf_users.loc[u, 'lat'])
        node_v = (gdf_users.loc[v, 'lon'], gdf_users.loc[v, 'lat'])
        
        # Calculate the geodetic distance between the two nodes
        dist = distance(lonlat(*node_u), lonlat(*node_v)).km
 
        length_list.append(dist)
        
    tot_grid_length = sum(length_list)
        

    """ Map Plot  """
    
    #Get the tree edges and make a gdf with LineString object to have a shapefile and put it in a plotly map
    lines =  list(tree.edges)          
    length_of_lines = len(lines)
    
    gdf_lines = gpd.GeoDataFrame(index=range(0, len(lines)),
                            columns=['Point1', 'Point2', 'geometry'],
                            crs = crs) 

    for h in range(0, length_of_lines):
        
        gdf_lines.at[h, 'geometry'] = LineString(
            [(gdf_users.loc[lines[h][0], 'lon'], 
              gdf_users.loc[lines[h][0], 'lat']),
              (gdf_users.loc[lines[h][1], 'lon'], 
                gdf_users.loc[lines[h][1], 'lat'])])
    
        gdf_lines.at[h, 'Point1'] = int(gdf_users.loc[lines[h][0], 'index'])
        gdf_lines.at[h, 'Point2'] = int(gdf_users.loc[lines[h][1], 'index'])
    
                   
    gdf_lines.to_file('Shapefiles/network.shp') #Not strictly necessary
 
    # Extracting lat and lon of the edges to put in the map 
    lats = []
    lons = []
    # names = []
    
    for feature in list(gdf_lines.geometry):
        if isinstance(feature, LineString):
            linestrings = [feature]
        elif isinstance(feature, MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            lats = np.append(lats, None)
            lons = np.append(lons, None)
        
    
    # Map the nodes
    map_nodes = px.scatter_mapbox(gdf_users,
                            lat=gdf_users.geometry.y,
                            lon=gdf_users.geometry.x,
                            # color = 'Power_installed',
                            hover_name="Village",
                            # hover_data = ['Power_installed'],
                            # size = 'Power_installed', 
                            size_max = 10,
                            color_discrete_sequence= px.colors.sequential.Sunsetdark, 
                            opacity = 1
                            )
    
    map_nodes.update_layout(mapbox_style="carto-positron")
    
    # plot(map_nodes)
    
    # Map the edges of the network
    map_edges = px.line_mapbox(gdf_lines, lat=lats, lon=lons)
    
    map_edges.update_layout(mapbox_style='carto-positron')
    
    # plot(map_edges)    
    
    # Add the map of the edges to the one of the nodes
    map_nodes.add_trace(map_edges.data[0])
    # plot(map_nodes)
    
    pio.write_html(map_nodes, file='Results/Plots/Network_Map.html', auto_open=False)


    return  tot_grid_length



def routing_roads_no_P(crs, gdf_users, roads_multipoints):
    

    """ Geodataframes and nearest road points """
    
    gdf_users['Distance_to_nearest_road'] = ""
    
    df_nn_roads = pd.DataFrame(columns=['lon', 'lat'])
    
    
    for i,row in gdf_users.iterrows():
       
        # Find the nearest road_point to each user_point
        near_pts = nearest_points(Point(row.lon, row.lat), roads_multipoints)
        
        # Store the distances from nearest points in gdf_users
        gdf_users.loc[i, 'Distance_to_nearest_road'] = near_pts[0].distance(near_pts[1])
       
        # Store the nearest road points in df_nn_roads
        x, y = near_pts[1].coords[0]
        df_nn_roads.loc[i, 'lon'] = x
        df_nn_roads.loc[i, 'lat'] = y
    
    
    # Create nn road points gdf
    gdf_nn_roads = gpd.GeoDataFrame(df_nn_roads, geometry=gpd.points_from_xy(x = df_nn_roads.lon, 
                                                            y = df_nn_roads.lat, crs = crs))
    
    
    # Concatenate nn_roads and users gdf
    points_mix = pd.concat([gdf_users.geometry, gdf_nn_roads.geometry])
    
    # Create complete gdf 
    gdf = gpd.GeoDataFrame(columns = ['lon', 'lat'], geometry=points_mix.geometry, crs =crs)
    gdf['lon'] = points_mix.geometry.x
    gdf['lat'] = points_mix.geometry.y
    
    gdf.reset_index(inplace=True)
    

    """ Distance matrices """
    
    # 2D arrys of the coordinates 
    coord_users = np.column_stack((gdf_users.geometry.x, gdf_users.geometry.y))
    coord_nn_roads = np.column_stack((gdf_nn_roads.geometry.x, gdf_nn_roads.geometry.y))
    
    # Matrix gdf_users-gdf_users
    dist_matrix_users = cdist(coord_users, coord_users)
    
    # Normalization of the distance matrix with values in the range 0.5-1
    dist_matrix_users_norm = MinMaxScaler(feature_range = (0.5, 1)).fit_transform(dist_matrix_users)
    
    # Matrix gdf_users-gdf_nn_roads
    dist_matrix_mix = cdist(coord_users, coord_nn_roads)
    
    # Normalization of the distance matrix with values in the range 0.5-1
    dist_matrix_mix_norm = MinMaxScaler(feature_range = (0.5, 1)).fit_transform(dist_matrix_mix)
    
    # Matrix gdf_nn_roads-gdf_nn_roads
    dist_matrix_roads = cdist(coord_nn_roads, coord_nn_roads)
    
    # Normalization of the distance matrix with values in the range 0-0.5
    dist_matrix_roads_norm = MinMaxScaler(feature_range = (0, 0.5)).fit_transform(dist_matrix_roads)

    
    """ Grid Routing """
        
    graph = nx.Graph()
    
    # Nodes
    for i, row in gdf.iterrows():
        graph.add_node(i, geometry = row.geometry, pos = (row.geometry.x, row.geometry.y))
        
    pos = nx.get_node_attributes(graph, 'pos')
   
    # Edges weighting
    for i in range(len(gdf_users)):
        for j in range(i+1, len(gdf_users)):
            graph.add_edge(i, j, weight=dist_matrix_users_norm[i, j])
    

    for i in range(len(gdf_nn_roads), len(gdf_nn_roads)*2):
        for j in range(i+1, len(gdf_nn_roads)*2):
            graph.add_edge(i, j, weight=dist_matrix_roads_norm[i-len(gdf_nn_roads), j-len(gdf_nn_roads)])
    

    for i in range(len(gdf_users)):
        for j in range(len(gdf_users), len(gdf)):
            graph.add_edge(i, j, weight=dist_matrix_mix_norm[i, j-len(gdf_users)])
    
    # Minimum Spanning Tree
    tree = nx.minimum_spanning_tree(graph, weight='weight')
    
    # MST Plot
    plt.figure()
    plt.title('Grid Routing')
    nx.draw(tree, pos, node_size=5, node_color = 'darkorange')
    plt.savefig('Results/Plots/Network_Plot.png' , dpi=600)
    # plt.show()   
    
 
    """ Length of the Line """
    
    length_list = []

    for u, v in tree.edges():
        
        node_u = (gdf.loc[u, 'lon'], gdf.loc[u, 'lat'])
        node_v = (gdf.loc[v, 'lon'], gdf.loc[v, 'lat'])
        
        # Calculate the geodetic distance between the two nodes
        dist = distance(lonlat(*node_u), lonlat(*node_v)).km
 
        length_list.append(dist)
        
    tot_grid_length = sum(length_list)
    

    """ Map Plot  """
    
    #Get the tree edges and make a gdf with LineString object to have a shapefile and put it in a plotly map 
    lines =  list(tree.edges)
    length_of_lines = len(lines)
    
    gdf_lines = gpd.GeoDataFrame(index=range(0, len(lines)),
                            columns=['Point1', 'Point2', 'geometry'],
                            crs = crs)

    for h in range(0, length_of_lines):
        
        gdf_lines.at[h, 'geometry'] = LineString(
            [(gdf.loc[lines[h][0], 'lon'], 
              gdf.loc[lines[h][0], 'lat']),
              (gdf.loc[lines[h][1], 'lon'], 
                gdf.loc[lines[h][1], 'lat'])])
    
        gdf_lines.at[h, 'Point1'] = int(gdf.loc[lines[h][0], 'index'])
        gdf_lines.at[h, 'Point2'] = int(gdf.loc[lines[h][1], 'index'])
                   
    gdf_lines.to_file('Shapefiles/network.shp') #Not strictly necessary
    
 
    # Extracting lat and lon of the edges to put in the map 
    lats = []
    lons = []
    # names = []
    
    for feature in list(gdf_lines.geometry):
        if isinstance(feature, LineString):
            linestrings = [feature]
        elif isinstance(feature, MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            
    # Map the nodes
    map_nodes = px.scatter_mapbox(gdf_users,
                            lat=gdf_users.geometry.y,
                            lon=gdf_users.geometry.x,
                            # color = 'Tier',
                            hover_name="Village",
                            # hover_data = ['Power_installed', 'Tier'],
                            # size = 'Size', 
                            size_max = 10,
                            color_discrete_sequence= px.colors.sequential.Sunsetdark, 
                            opacity = 1
                            )
    
    map_nodes.update_layout(mapbox_style="carto-positron")
    
    # plot(map_nodes)
    
    # Map the edges of the network
    map_edges= px.line_mapbox(gdf_lines, lat=lats, lon=lons)
    
    map_edges.update_layout(mapbox_style='carto-positron')
    
    # plot(map_edge)    
    
    # Add the map of the edges to the one of the nodes
    map_nodes.add_trace(map_edges.data[0]) 
    
    # plot(map_nodes)
    
    pio.write_html(map_nodes, file='Results/Plots/Network_Map.html', auto_open=False)


    return  tot_grid_length



def routing_roads_P(crs, gdf_users, roads_multipoints):

    
    """ Geodataframes and nearest road points """
    
    gdf_users['Distance_to_nearest_road'] = ""

    df_nn_roads = pd.DataFrame(columns=['lon', 'lat'])
    
    for i,row in gdf_users.iterrows():
       
        # find the nearest road_point to each user_point
        near_pts = nearest_points(Point(row.lon, row.lat), roads_multipoints)
        
        # store the distances from nearest points in the gdf
        gdf_users.loc[i, 'Distance_to_nearest_road'] = near_pts[0].distance(near_pts[1])
       
        # store the nearest road points in a dataframe
        x, y = near_pts[1].coords[0]
        df_nn_roads.loc[i, 'lon'] = x
        df_nn_roads.loc[i, 'lat'] = y
    

    """ Wheighting of the user points """
    
    # Weight assignment to nodes
    gdf_users['weight'] = 0.5 + 0.5 * (1 - ((gdf_users['Power_installed']-gdf_users['Power_installed'].min()) / (gdf_users['Power_installed'].max() - gdf_users['Power_installed'].min())))

    # Create nn road points gdf and assigning weights
    gdf_nn_roads = gpd.GeoDataFrame(df_nn_roads, geometry=gpd.points_from_xy(x = df_nn_roads.lon, 
                                                            y = df_nn_roads.lat, crs = crs))
    
   
    gdf_nn_roads['weight'] = 0

    # Concatenate nn_roads and users gdf
    points_mix = pd.concat([gdf_users.geometry, gdf_nn_roads.geometry])
    
    # Create complete gdf from the concatenated series 
    gdf = gpd.GeoDataFrame(columns = ['lon', 'lat'], geometry=points_mix.geometry, crs =crs)
    gdf['lon'] = points_mix.geometry.x
    gdf['lat'] = points_mix.geometry.y
    
    gdf.reset_index(inplace=True)


    """ Distance matrices """
    
    # 2D arrays of the coordinates 
    coord_users = np.column_stack((gdf_users.geometry.x, gdf_users.geometry.y))
    coord_nn_roads = np.column_stack((gdf_nn_roads.geometry.x, gdf_nn_roads.geometry.y))
    
    # Distance matrix gdf_users-gdf_users
    dist_matrix_users = cdist(coord_users, coord_users)
    
    # Normalization of the distance matrix with values in the range 0.5-1
    dist_matrix_users_norm = MinMaxScaler(feature_range = (0.5, 1)).fit_transform(dist_matrix_users)
    
    
    # Matrix of the user nodes weight
    weight_matrix_users = pd.DataFrame(0, columns = gdf_users.index, index = gdf_users.index, dtype = float)
    
    weights_users = gdf_users['weight'].values
    
    for i in range(len(gdf_users)):
        weight_matrix_users.loc[i] = weights[i]
    
    # Distance matrix gdf_users-gdf_nn_roads
    dist_matrix_mix = cdist(coord_users, coord_nn_roads)
    
    # Normalization of the distance matrix with values in the range 0.5-1
    dist_matrix_mix_norm = MinMaxScaler(feature_range = (0.5, 1)).fit_transform(dist_matrix_mix)
    
    hybrid_matrix = (dist_matrix_mix_norm + weight_matrix_users) / 3
    
    
    # Distance matrix gdf_nn_roads-gdf_nn_roads
    dist_matrix_roads = cdist(coord_nn_roads, coord_nn_roads)
    
    # Normalization of the distance matrix with values in the range 0-0.5
    dist_matrix_roads_norm = MinMaxScaler(feature_range = (0, 0.5)).fit_transform(dist_matrix_roads)


    """ Grid Routing """
    
    graph = nx.Graph()
    
    # Nodes
    for i, row in gdf.iterrows():
        graph.add_node(i, geometry = row.geometry, pos = (row.geometry.x, row.geometry.y))
        
    pos = nx.get_node_attributes(graph, 'pos')
    
    
    # Edges weighting
    for i in range(len(gdf_users)):
        for j in range(i+1, len(gdf_users)):
            graph.add_edge(i, j, weight= (dist_matrix_users_norm[i, j]))
    
    for i in range(len(gdf_nn_roads), len(gdf_nn_roads)*2):
        for j in range(i+1, len(gdf_nn_roads)*2):
            graph.add_edge(i, j, weight=dist_matrix_roads_norm[i-len(gdf_nn_roads), j-len(gdf_nn_roads)])
    
    for i in range(len(gdf_users)):
        for j in range(len(gdf_users), len(gdf)):
            graph.add_edge(i, j, weight=hybrid_matrix.iloc[i, j-len(gdf_users)])

    
    # Minimum Spanning Tree
    tree = nx.minimum_spanning_tree(graph, weight='weight')
    
    # MST Plot
    plt.figure()
    plt.title('Grid Routing')
    nx.draw(tree, pos, node_size=5, node_color = 'darkorange')
    plt.savefig('Results/Plots/Network_Plot.png' , dpi=600)
    # plt.show()


    """ Length of the line """
    
    length_list = []

    for u, v in tree.edges():
        
        node_u = (gdf.loc[u, 'lon'], gdf.loc[u, 'lat'])
        node_v = (gdf.loc[v, 'lon'], gdf.loc[v, 'lat'])
        
        # Calculate the geodetic distance between the two nodes
        dist_ = distance(lonlat(*node_u), lonlat(*node_v)).km
 
        length_list.append(dist_)
        
    tot_grid_length = sum(length_list)

    
    """ Map Plot  """
    
    #Get the tree edges and make a gdf with LineString object to have a shapefile and put it in a plotly map 
    lines =  list(tree.edges)
    length_of_lines = len(lines)
    
    gdf_lines = gpd.GeoDataFrame(index=range(0, len(lines)),
                            columns=['Point1', 'Point2', 'geometry'],
                            crs = crs) 
    
    for h in range(0, length_of_lines):
        
        gdf_lines.at[h, 'geometry'] = LineString(
            [(gdf.loc[lines[h][0], 'lon'], 
              gdf.loc[lines[h][0], 'lat']),
              (gdf.loc[lines[h][1], 'lon'], 
                gdf.loc[lines[h][1], 'lat'])])
    
        gdf_lines.at[h, 'Point1'] = int(gdf.loc[lines[h][0], 'index'])
        gdf_lines.at[h, 'Point2'] = int(gdf.loc[lines[h][1], 'index'])
    
                   
    gdf_lines.to_file('Shapefiles/network.shp') #Not strictly necessary
    
    
    # Extract lat and lon of the edges to put in the map 
    lats = []
    lons = []
    # names = []
    
    for feature in list(gdf_lines.geometry):
        if isinstance(feature, LineString):
            linestrings = [feature]
        elif isinstance(feature, MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            

    # Tier Assignment
    
    gdf_users_tiers = tier_assignment(gdf_users)
    
    
    # Map the nodes
    map_nodes = px.scatter_mapbox(gdf_users_tiers,
                            lat=gdf_users_tiers.geometry.y,
                            lon=gdf_users_tiers.geometry.x,
                            color = 'Tier',
                            hover_name="Village",
                            hover_data = {'Power_installed':True,
                                          'Tier':True,
                                          'Size':False},
                            size = 'Size', 
                            size_max = 10,
                            color_discrete_sequence= px.colors.sequential.Sunsetdark, 
                            opacity = 1
                            )
    
    map_nodes.update_layout(mapbox_style="carto-positron")
    
    # plot(map_nodes)
    
    # Map the edges of the network
    map_edges = px.line_mapbox(gdf_lines, lat=lats, lon=lons)
    
    map_edges.update_layout(mapbox_style='carto-positron')
    
    # plot(map_edges)    
      
    # Add the map of the edges to the one of the nodes
    map_nodes.add_trace(map_edges.data[0]) 
    
    plot(map_nodes)
    
    pio.write_html(map_nodes, file='Results/Plots/Network_Map.html', auto_open=False)

    return  tot_grid_length






