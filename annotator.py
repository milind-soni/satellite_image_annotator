import streamlit as st
import micropip
await micropip.install("folium")
await micropip.install("streamlit_folium")
await micropip.install("geopandas")
import folium

from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import shape
from datetime import datetime
import requests
from folium.plugins import Draw
import pandas as pd

# Initialize session state
if 'drawn_features' not in st.session_state:
    st.session_state.drawn_features = []
    
if 'map_center' not in st.session_state:
    st.session_state.map_center = [37.7749, -122.4194]  # Default to San Francisco
    
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 12

# Page config
st.set_page_config(page_title="Fused YOLO Image Annotator", layout="wide")
st.title("Fused YOLO Image Annotator")

# Geocoding functionality
def geocode_location(place_name):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={place_name}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Location search
with st.sidebar:
    st.header("Search Location")
    place_name = st.text_input("Enter a location:")
    if place_name:
        results = geocode_location(place_name)
        if results:
            options = {f"{res['display_name']}": (float(res['lat']), float(res['lon'])) 
                      for res in results}
            selected_place = st.selectbox("Select location:", list(options.keys()))
            if st.button("Go to location"):
                coords = options[selected_place]
                st.session_state.map_center = [coords[0], coords[1]]
                st.session_state.map_zoom = 12

# Create map
m = folium.Map(location=st.session_state.map_center, 
               zoom_start=st.session_state.map_zoom,
               max_zoom=18)

# Add satellite layer
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite',
    overlay=False
).add_to(m)

# Add drawing tools
draw = Draw(
    export=True,
    position='topleft',
    draw_options={
        'polyline': False,
        'polygon': True,
        'rectangle': True,
        'circle': False,
        'marker': True,
        'circlemarker': False
    }
)
draw.add_to(m)

# Display map
col1, col2 = st.columns([3, 1])

with col1:
    map_data = st_folium(m, height=600, width=800)

# Process drawn features
if map_data and 'all_drawings' in map_data:
    new_features = map_data['all_drawings']
    if isinstance(new_features, list):
        for feature in new_features:
            if feature not in st.session_state.drawn_features:
                st.session_state.drawn_features.append(feature)

# Annotation panel
with col2:
    st.header("Annotations")
    
    # Display and manage annotations
    for idx, feature in enumerate(st.session_state.drawn_features):
        with st.expander(f"Annotation {idx + 1}"):
            st.write(f"Type: {feature['geometry']['type']}")
            label = st.text_input("Label", key=f"label_{idx}")
            notes = st.text_area("Notes", key=f"notes_{idx}")
            if st.button("Delete", key=f"delete_{idx}"):
                st.session_state.drawn_features.pop(idx)
                st.experimental_rerun()

    # Export functionality
    if st.session_state.drawn_features:
        st.header("Export")
        export_format = st.selectbox("Export format", ["GeoJSON", "CSV"])
        
        if st.button("Export Annotations"):
            # Convert features to GeoDataFrame
            features_with_metadata = []
            for idx, feature in enumerate(st.session_state.drawn_features):
                feature_dict = {
                    'geometry': shape(feature['geometry']),
                    'label': st.session_state[f"label_{idx}"],
                    'notes': st.session_state[f"notes_{idx}"],
                    'type': feature['geometry']['type']
                }
                features_with_metadata.append(feature_dict)
            
            gdf = gpd.GeoDataFrame(features_with_metadata)
            
            # Export based on selected format
            if export_format == "GeoJSON":
                filename = f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
                gdf.to_file(filename, driver='GeoJSON')
            else:  # CSV
                filename = f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                # Convert geometry to WKT for CSV export
                gdf['geometry'] = gdf['geometry'].apply(lambda x: x.wkt)
                gdf.to_csv(filename, index=False)
            
            st.success(f"Annotations exported to {filename}")

# Clear annotations button
if st.session_state.drawn_features:
    if st.sidebar.button("Clear All Annotations"):
        st.session_state.drawn_features = []
        st.rerun()
