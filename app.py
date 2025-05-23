import streamlit as st
import folium
import requests
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
from streamlit_folium import st_folium
import os

# Load API keys securely from Streamlit secrets
OPENCAGE_API = st.secrets["OPENCAGE_API"]
WEATHER_API = st.secrets["WEATHER_API"]

MOON_PHASE_EMOJIS = {
    "New Moon": "🌑", "Waxing Crescent": "🌒", "First Quarter": "🌓",
    "Waxing Gibbous": "🌔", "Full Moon": "🌕", "Waning Gibbous": "🌖",
    "Last Quarter": "🌗", "Waning Crescent": "🌘"
}

def geocode_city(city):
    res = requests.get(f'https://api.opencagedata.com/geocode/v1/json?q={city}&key={OPENCAGE_API}').json()
    if res['results']:
        loc = res['results'][0]['geometry']
        return loc['lat'], loc['lng']
    return None

def get_weather(lat, lon):
    res = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API}&units=metric').json()
    if res.get("cod") != 200:
        return None
    return {
        'temp': int(res['main']['temp']),
        'feels_like': int(res['main']['feels_like']),
        'condition': res['weather'][0]['main'],
        'icon': res['weather'][0]['icon'],
        'humidity': res['main']['humidity'],
        'wind': res['wind']['speed'],
        'wind_deg': res['wind']['deg'],
        'pressure': res['main']['pressure'],
        'visibility': res.get('visibility', 0) // 1000,
        'sunrise': res['sys']['sunrise'],
        'sunset': res['sys']['sunset']
    }

def get_moon_phase():
    date = datetime.utcnow()
    y, m, d = date.year, date.month, date.day
    if m < 3:
        y -= 1
        m += 12
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d - 1524.5
    phase_index = int((jd - 2451550.1) / 29.53058867 % 1 * 8) % 8
    phases = [
        "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
        "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"
    ]
    return phases[phase_index]

def wind_direction(degrees):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = round(degrees / 45) % 8
    return dirs[ix]

# Streamlit layout
st.set_page_config(layout="wide", page_title="Weather Dashboard 🌦️")
st.markdown("<h3 style='text-align: left;'>🌦️ Weather Dashboard</h3>", unsafe_allow_html=True)
st.markdown('<style>div.block-container {padding-top: 3rem; padding-bottom: 0rem;}</style>', unsafe_allow_html=True)

if "selected_city" not in st.session_state:
    st.session_state.selected_city = "Warsaw"

with st.sidebar:
    st.header("🌍 City Selection")
    city_input = st.text_input("Enter a city", st.session_state.selected_city)
    if st.button("Get Weather"):
        st.session_state.selected_city = city_input

city = st.session_state.selected_city
coords = geocode_city(city)

if not coords:
    st.error("City not found")
else:
    lat, lon = coords
    tz = TimezoneFinder().timezone_at(lat=lat, lng=lon)
    timezone = pytz.timezone(tz) if tz else pytz.utc
    now = datetime.now(timezone)
    weather = get_weather(lat, lon)
    moon = get_moon_phase()

    if not weather:
        st.error("Weather data could not be retrieved.")
    else:
        sunrise = datetime.fromtimestamp(weather['sunrise'], tz=timezone).strftime('%I:%M %p')
        sunset = datetime.fromtimestamp(weather['sunset'], tz=timezone).strftime('%I:%M %p')

        col1, col2, col3 = st.columns([1.4, 1.6, 1.4])

        with col1:
            col1a, col1b = st.columns(2)
            with col1a:
                st.markdown(f"#### 📍 {city.title()}")
                st.markdown(f"🕓 **{now.strftime('%A, %I:%M %p')}**")
                st.image(f"https://openweathermap.org/img/wn/{weather['icon']}@2x.png", width=80)
                st.metric(label="🌡 Temperature", value=f"{weather['temp']}°C",
                          delta=f"Feels like {weather['feels_like']}°C")

            with col1b:
                st.markdown("#### 🔍 Conditions")
                st.markdown(f"- 💧 **Humidity:** {weather['humidity']}%")
                st.markdown(f"- 🌬️ **Wind:** {weather['wind']} km/h {wind_direction(weather['wind_deg'])}")
                st.markdown(f"- 🌄 **Sunrise:** {sunrise}")
                st.markdown(f"- 🌇 **Sunset:** {sunset}")
                st.markdown(f"- 📏 **Pressure:** {weather['pressure']} hPa")
                st.markdown(f"- 👁️ **Visibility:** {weather['visibility']} km")
                st.markdown(f"- 🌎 **Lat/Lon:** {lat:.2f}, {lon:.2f}")

        with col2:
            m = folium.Map(location=[lat, lon], zoom_start=10, tiles='CartoDB dark_matter')
            folium.Marker([lat, lon], popup=city.title()).add_to(m)
            st_folium(m, width=640, height=360)

        with col3:
            st.markdown("#### 🔎 Additional Insights")
            comfort = "Moderate"
            if weather['temp'] > 30 and weather['humidity'] > 60:
                comfort = "Uncomfortable"
            elif 20 <= weather['temp'] <= 26 and weather['humidity'] < 70:
                comfort = "Comfortable"

            wind_chill = None
            if weather['temp'] < 10 and weather['wind'] > 5:
                v = weather['wind']
                t = weather['temp']
                wind_chill = round(13.12 + 0.6215 * t - 11.37 * v**0.16 + 0.3965 * t * v**0.16, 1)

            vis_cat = "Excellent" if weather['visibility'] >= 10 else "Moderate" if weather['visibility'] >= 5 else "Poor"
            length_sec = weather['sunset'] - weather['sunrise']
            hours = length_sec // 3600
            minutes = (length_sec % 3600) // 60
            day_length = f"{hours}h {minutes}m"

            st.success(f"🧘 **Comfort Level:** {comfort}")
            if wind_chill:
                st.info(f"🌬️ Wind Chill: {wind_chill}°C")
            st.warning(f"🚗 Visibility: {vis_cat}")
            st.markdown(f"⏳ **Day Length:** `{day_length}`")

            # Show moon image instead of emoji
            image_name = moon.lower().replace(" ", "_") + ".png"
            image_path = f"moon_phases/{image_name}"
            if os.path.exists(image_path):
                st.image(image_path, width=100, caption=moon)
            else:
                st.markdown(f"🌕 **Moon:** {moon}")

        st.markdown("### 📊 KPIs")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Pressure", f"{weather['pressure']} hPa")
        kpi2.metric("Humidity", f"{weather['humidity']}%")
        kpi3.metric("Wind", f"{weather['wind']} km/h")
        kpi4.metric("Visibility", f"{weather['visibility']} km")
