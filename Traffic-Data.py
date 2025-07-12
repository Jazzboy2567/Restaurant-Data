''' 
Nearby Restaurants Map Project with Cuisine Filter and Debugging
'''

import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
from urllib.parse import quote

st.set_page_config(layout="centered")
st.title("🍽️ Nearby Restaurants Map with Cuisine Filter")

# ---- SESSION STATE SETUP ----
if "location_name" not in st.session_state:
    st.session_state.location_name = "Seattle, Washington, USA"
if "lat" not in st.session_state:
    st.session_state.lat = 47.6062
if "lon" not in st.session_state:
    st.session_state.lon = -122.3321
if "zoom" not in st.session_state:
    st.session_state.zoom = 12
if "restaurants" not in st.session_state:
    st.session_state.restaurants = []

# ---- FORM TO INPUT LOCATION ----
with st.form("location_form"):
    user_input = st.text_input("Enter a location (city, address, etc):", st.session_state.location_name, key="location_input")
    submitted = st.form_submit_button("Update Map")

# ---- FUNCTION TO GEOCODE LOCATION ----
def geocode_location(query):
    encoded_location = quote(query)
    nominatim_url = f"https://nominatim.openstreetmap.org/search?q={encoded_location}&format=json&limit=1"
    geo_res = requests.get(nominatim_url, headers={"User-Agent": "streamlit-app"})
    if geo_res.status_code == 200:
        geo_data = geo_res.json()
        if geo_data:
            return float(geo_data[0]["lat"]), float(geo_data[0]["lon"])
    return None, None

# ---- FUNCTION TO QUERY RESTAURANTS VIA OVERPASS API ----
def fetch_nearby_restaurants(lat, lon, radius=7500):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node
      ["amenity"="restaurant"]
      (around:{radius},{lat},{lon});
    out center tags;
    """
    try:
        response = requests.post(overpass_url, data=query, headers={"User-Agent": "streamlit-app"})
        data = response.json()
        restaurants = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "Unnamed")
            cuisine_raw = tags.get("cuisine", "Unknown cuisine")
            lat_r = element.get("lat")
            lon_r = element.get("lon")
            street = tags.get("addr:street", "")
            housenumber = tags.get("addr:housenumber", "")
            city = tags.get("addr:city", "")
            postcode = tags.get("addr:postcode", "")
            address = ", ".join(filter(None, [housenumber, street, city, postcode]))
            restaurants.append({
                "name": name,
                "lat": lat_r,
                "lon": lon_r,
                "address": address,
                "cuisine": cuisine_raw
            })
        return restaurants
    except Exception as e:
        st.error(f"Failed to fetch restaurants: {e}")
        return []

# ---- UPDATE LOCATION & FETCH RESTAURANTS ON SUBMIT ----
if submitted and user_input:
    lat, lon = geocode_location(user_input)
    if lat and lon:
        st.session_state.lat = lat
        st.session_state.lon = lon
        #st.session_state.zoom = 15  # zoom in for details
        st.session_state.location_name = user_input
        st.session_state.restaurants = fetch_nearby_restaurants(lat, lon)
    else:
        st.warning("Location not found. Keeping previous location.")
else:
    if not st.session_state.restaurants:
        # Initial fetch for default location
        st.session_state.restaurants = fetch_nearby_restaurants(
            st.session_state.lat, st.session_state.lon
        )

# ---- DEBUG: SHOW SAMPLE CUISINES ----
#sample_cuisines = [r["cuisine"] for r in st.session_state.restaurants[:20]]
#st.write("Sample cuisines from fetched restaurants:", sample_cuisines)

# ---- CUISINE FILTER ----
cuisines = set()
# Inside cuisine parsing loop:
for r in st.session_state.restaurants:
    raw_cuisine = r["cuisine"]
    parts = [c.strip() for c in raw_cuisine.replace(';', ',').split(',')]
    for c in parts:
        if c and c.lower() != "unknown cuisine":
            cuisines.add(c)

if not cuisines:
    st.warning("No cuisine types found in the current data.")

cuisine_options = ["All cuisines"] + sorted(cuisines)
selected_cuisine = st.selectbox("Filter by cuisine type:", cuisine_options)

if selected_cuisine != "All cuisines":
    filtered_restaurants = [
        r for r in st.session_state.restaurants if selected_cuisine.lower() in r["cuisine"].lower()
    ]
else:
    filtered_restaurants = st.session_state.restaurants

# ---- REMOVE EXTRA SPACING ----
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-bottom: 0rem;
    }
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ---- BUILD MAP ----
m = folium.Map(
    location=[st.session_state.lat, st.session_state.lon],
    zoom_start=st.session_state.zoom
)

# Marker for searched location
folium.Marker(
    [st.session_state.lat, st.session_state.lon],
    tooltip=f"Search Location: {st.session_state.location_name}",
    icon=folium.Icon(color="blue", icon="search")
).add_to(m)

# Markers for filtered restaurants with name, address, cuisine popup
for r in filtered_restaurants:
    popup_content = f"<b>{r['name']}</b><br>{r['address'] if r['address'] else 'Address not available'}<br><i>Cuisine: {r['cuisine']}</i>"
    folium.Marker(
        [r["lat"], r["lon"]],
        popup=folium.Popup(popup_content, max_width=300),
        icon=folium.Icon(color="red", icon="cutlery", prefix='fa')
    ).add_to(m)

# ---- SHOW MAP ----
st_folium(m, width=700, height=450, key=f"map_{st.session_state.lat}_{st.session_state.lon}_{selected_cuisine}")
