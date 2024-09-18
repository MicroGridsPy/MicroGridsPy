import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import geopandas as gpd
import zipfile
import os
from microgridspy.grid_routing.main import Distribution_Line
from config.path_manager import PathManager

def download_roads_from_bbox(north, south, east, west, crs_str='epsg:4326') -> str:
    """
    Downloads the road network for the specified bounding box from OpenStreetMap,
    reprojects and simplifies the geometry, and saves it as a shapefile.
    
    Args:
        north (float): Northern latitude.
        south (float): Southern latitude.
        east (float): Eastern longitude.
        west (float): Western longitude.
        save_dir (str): Directory where the shapefile should be saved.
        crs_str (str): Target CRS (Coordinate Reference System) in EPSG format (e.g., 'epsg:4326').
        
    Returns:
        str: The path to the shapefile zip archive.
    """
    # Data Import from OSM, cropped to the bounding box (study area)
    osm_import = ox.graph_from_bbox(north, south, east, west, network_type='all_private')
    
    # Reproject to the specified CRS
    osm_import_projected = ox.projection.project_graph(osm_import, to_crs=crs_str)
    
    # Save the graph as shapefiles (this creates nodes and edges shapefiles)
    ox.save_graph_shapefile(osm_import_projected, filepath=PathManager.SHAPEFILE_PATH)
    
    # Simplify geometry of the edges (roads)
    edges_shp_path = os.path.join(PathManager.SHAPEFILE_PATH, 'edges.shp')
    osm_import_roads = gpd.read_file(edges_shp_path)
    
    # Simplify geometry with tolerance and reproject to the CRS
    osm_import_roads_simplified = osm_import_roads.copy()
    osm_import_roads_simplified['geometry'] = osm_import_roads.geometry.simplify(tolerance=0.0005)
    osm_import_roads_simplified = osm_import_roads_simplified.to_crs(crs_str)
    
    # Save the simplified roads as a new shapefile
    roads_simplified_shp_path = os.path.join(PathManager.SHAPEFILE_PATH, 'roads_simplified.shp')
    osm_import_roads_simplified.to_file(roads_simplified_shp_path, driver='ESRI Shapefile')
    
    # Zip the shapefile components for download
    zip_path = os.path.join(PathManager.SHAPEFILE_PATH, "roads_osm_bbox.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for ext in ['shp', 'shx', 'dbf', 'cpg', 'prj']:
            zipf.write(f"{roads_simplified_shp_path[:-4]}.{ext}")
    
    return zip_path


def grid_routing() -> None:
    """Streamlit page for grid routing configuration and optimization."""
    
    st.title("Grid Routing Optimization")

    lat = st.session_state.get("lat")
    lon = st.session_state.get("lon")

    st.write("Select an Area to Download Roads from OpenStreetMap")

    # Step 1: Display interactive map with drawing tools
    m = folium.Map(location=[lat, lon])
    draw = folium.plugins.Draw(export=True)
    draw.add_to(m)

    # Display the map in Streamlit
    output = st_folium(m, width=700, height=500)

    # Step 2: Extract bounding box coordinates from the drawn area
    if output and output["all_drawings"]:
        last_drawing = output["all_drawings"][-1]
        bounds = last_drawing['geometry']['coordinates'][0]
        
        # Extract bounding box (coordinates of the drawn rectangle)
        lons = [coord[0] for coord in bounds]
        lats = [coord[1] for coord in bounds]
        west, east = min(lons), max(lons)
        south, north = min(lats), max(lats)

        st.write(f"Selected Bounding Box:\nNorth: {north}, South: {south}, East: {east}, West: {west}")
        
        # Step 3: Button to download roads from the selected area
        if st.button("Download Roads from OSM"):
            try:
                zip_path = download_roads_from_bbox(north, south, east, west)
                st.success("Roads shapefile downloaded successfully.")
            except Exception as e:
                st.error(f"Error downloading roads: {e}")
    else:
        st.info("Draw a rectangle on the map to select an area.")
