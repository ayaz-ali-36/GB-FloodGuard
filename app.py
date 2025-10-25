# app.py - FINAL VERSION WITH .env
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
import os

# === LOAD .env FILE ===
load_dotenv()  # This reads .env and loads variables

# === GET API KEY FROM .env ===
api_key = os.getenv("OPENWEATHER_API_KEY")

if not api_key:
    st.error("API Key not found! Check your `.env` file.")
    st.info("Create `.env` file with: `OPENWEATHER_API_KEY=your_key`")
    st.stop()

# === TITLE ===
st.set_page_config(page_title="GB FloodGuard", page_icon="Warning", layout="wide")
st.title("GB FloodGuard: Early Warning System")
st.markdown("**Real-time flood alerts for Gilgit-Baltistan**")

# === CITIES ===
CITIES = {
    "Gilgit": (35.9208, 74.3083),
    "Skardu": (35.2971, 75.6333),
    "Hunza": (36.3167, 74.65)
}

RAIN_THRESHOLD = 30

# === GET WEATHER ===
@st.cache_data(ttl=1800)
def get_weather(city):
    lat, lon = CITIES[city]
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        data = requests.get(url).json()
        if data.get("cod") != "200":
            return None, data.get("message")

        rain_3h = sum(entry.get("rain", {}).get("3h", 0) for entry in data["list"][:3])
        temp = data["list"][0]["main"]["temp"]
        desc = data["list"][0]["weather"][0]["description"].title()

        return {
            "city": city,
            "temp": round(temp, 1),
            "desc": desc,
            "rain_3h": round(rain_3h, 1),
            "risk": "HIGH" if rain_3h > RAIN_THRESHOLD else "LOW"
        }, None
    except Exception as e:
        return None, f"Error: {str(e)}"

# === UI ===
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Select Location")
    city = st.selectbox("City", list(CITIES.keys()))
    
    if st.button("Check Flood Risk"):
        with st.spinner("Fetching data..."):
            result, error = get_weather(city)
            if error:
                st.error(f"{error}")
            else:
                st.session_state.current = result
                st.success("Updated!")

if 'current' in st.session_state and st.session_state.current["city"] == city:
    w = st.session_state.current
    color = "red" if w["risk"] == "HIGH" else "green"
    
    st.markdown(f"### {w['city']} - Live")
    st.metric("Temperature", f"{w['temp']}°C")
    st.metric("Rain (3h)", f"{w['rain_3h']} mm")
    st.markdown(f"**Risk:** <span style='color:{color}; font-size:24px'>{w['risk']} RISK</span>", 
                unsafe_allow_html=True)
    
    if w["risk"] == "HIGH":
        st.error("**FLOOD ALERT!** Evacuate low areas!")
    else:
        st.success("Safe for now.")

# === MAP ===

   # === MAP ===
with col2:
    st.subheader("Live Risk Map")
    m = folium.Map(
        location=[35.9, 74.3],
        zoom_start=8,
        tiles="https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://stamen.com/">Stamen Design</a>, &copy; <a href="https://openstreetmap.org/">OpenStreetMap</a> contributors'
    )
    
    # Add city markers
    for city_name, (lat, lon) in CITIES.items():
        weather_data, error = get_weather(city_name)
        if weather_data:
            color = "red" if weather_data["risk"] == "HIGH" else "green"
            folium.CircleMarker(
                location=[lat, lon],
                radius=22 if weather_data["risk"] == "HIGH" else 14,
                color=color,
                fill=True,
                fill_color=color,
                popup=folium.Popup(
                    f"<b>{city_name}</b><br>"
                    f"Rain (3h): {weather_data['rain_3h']} mm<br>"
                    f"Risk: <span style='color:{color}'>{weather_data['risk']} RISK</span>",
                    max_width=300
                )
            ).add_to(m)
    
    # Display map in Streamlit
    st_folium(m, width=700, height=500)
# === FOOTER ===
st.markdown("---")
st.markdown("**Final Year IT Project** | Made for Gilgit-Baltistan")
st.caption("Data: OpenWeatherMap | Key stored securely in `.env`")