# app.py – FINAL VERSION (works locally + Streamlit Cloud)
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
import os

# -------------------------------------------------
# 1. Load .env (local) – on Streamlit Cloud we use Secrets
# -------------------------------------------------
load_dotenv()                                   # reads .env when you run locally
api_key = os.getenv("OPENWEATHER_API_KEY")       # .env variable

# If the key is missing locally, give a helpful message
if not api_key:
    st.error("API Key not found! Check your `.env` file.")
    st.info("Create `.env` file with: `OPENWEATHER_API_KEY=your_key`")
    st.stop()

# -------------------------------------------------
# 2. Page config & title
# -------------------------------------------------
st.set_page_config(page_title="GB FloodGuard", page_icon="Warning", layout="wide")
st.title("GB FloodGuard: Early Warning System")
st.markdown("**Real-time flood alerts for Gilgit-Baltistan**")

# -------------------------------------------------
# 3. Constants
# -------------------------------------------------
CITIES = {
    "Gilgit": (35.9208, 74.3083),
    "Skardu": (35.2971, 75.6333),
    "Hunza": (36.3167, 74.65)
}
RAIN_THRESHOLD = 30   # mm in 3 h → HIGH risk

# -------------------------------------------------
# 4. Weather API (cached 30 min)
# -------------------------------------------------
@st.cache_data(ttl=1800)
def get_weather(city: str):
    lat, lon = CITIES[city]
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )
    try:
        data = requests.get(url).json()
        if data.get("cod") != "200":
            return None, data.get("message", "Unknown error")

        # Sum rain over the next 3-hour window (first 3 entries)
        rain_3h = sum(
            entry.get("rain", {}).get("3h", 0) for entry in data["list"][:3]
        )
        temp = data["list"][0]["main"]["temp"]
        desc = data["list"][0]["weather"][0]["description"].title()

        risk = "HIGH" if rain_3h > RAIN_THRESHOLD else "LOW"

        return {
            "city": city,
            "temp": round(temp, 1),
            "desc": desc,
            "rain_3h": round(rain_3h, 1),
            "risk": risk,
        }, None
    except Exception as e:
        return None, f"Request error: {e}"


# -------------------------------------------------
# 5. UI – left column
# -------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Select Location")
    city = st.selectbox("City", list(CITIES.keys()))

    if st.button("Check Flood Risk"):
        with st.spinner("Fetching data…"):
            result, err = get_weather(city)
            if err:
                st.error(err)
            else:
                st.session_state.current = result
                st.success("Updated!")

# -------------------------------------------------
# 6. Show current data (if any)
# -------------------------------------------------
if "current" in st.session_state and st.session_state.current["city"] == city:
    w = st.session_state.current
    color = "red" if w["risk"] == "HIGH" else "green"

    st.markdown(f"### {w['city']} – Live")
    st.metric("Temperature", f"{w['temp']}°C")
    st.metric("Rain (3 h)", f"{w['rain_3h']} mm")
    st.markdown(
        f"**Risk:** <span style='color:{color};font-size:24px'>{w['risk']} RISK</span>",
        unsafe_allow_html=True,
    )
    if w["risk"] == "HIGH":
        st.error("**FLOOD ALERT!** Evacuate low-lying areas!")
    else:
        st.success("Safe for now.")

# -------------------------------------------------
# 7. MAP – right column (the fix!)
# -------------------------------------------------
with col2:
    st.subheader("Live Risk Map")

    # Base map (centered on Gilgit-Baltistan)
    m = folium.Map(
        location=[35.9, 74.3],
        zoom_start=8,
        tiles="https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
        attr=(
            '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, '
            '&copy; <a href="https://stamen.com/">Stamen Design</a>, '
            '&copy; <a href="https://openstreetmap.org/">OpenStreetMap</a> contributors'
        ),
    )

    # ---- Add a marker for every city (fetch fresh data) ----
    for city_name, (lat, lon) in CITIES.items():
        weather, _ = get_weather(city_name)
        if not weather:
            continue

        marker_color = "red" if weather["risk"] == "HIGH" else "green"
        radius = 22 if weather["risk"] == "HIGH" else 14

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            popup=folium.Popup(
                f"<b>{city_name}</b><br>"
                f"Rain (3 h): {weather['rain_3h']} mm<br>"
                f"Risk: <span style='color:{marker_color}'>{weather['risk']} RISK</span>",
                max_width=300,
            ),
        ).add_to(m)

    # ---- CRITICAL FIX for Streamlit Cloud ----
    # Force Leaflet JS/CSS to load (cloud sometimes strips them)
    leaflet_css = (
        '<link rel="stylesheet" '
        'href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />'
    )
    leaflet_js = (
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
    )
    m.get_root().header.add_child(folium.Element(leaflet_css + leaflet_js))

    # ---- Render map ----
    st_folium(m, width=700, height=500)

# -------------------------------------------------
# 8. Footer
# -------------------------------------------------
st.markdown("---")
st.markdown("**Final Year IT Project** | Made for Gilgit-Baltistan")
st.caption("Data: OpenWeatherMap | Key stored securely in `.env` (local) or Streamlit Secrets (cloud)")