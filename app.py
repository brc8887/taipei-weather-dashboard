import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime

DB_NAME = "weather.db"

def create_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS taipei_weather (
            timestamp TEXT PRIMARY KEY,
            temperature REAL,
            humidity REAL
        )
    ''')
    conn.commit()
    conn.close()

def fetch_and_save_weather():
    # Extract: Call free API for Taipei
    url = "https://api.open-meteo.com/v1/forecast?latitude=25.0478&longitude=121.5319&current=temperature_2m,relative_humidity_2m&timezone=Asia%2FTaipei"
    response = requests.get(url).json()
    
    current_data = response.get("current", {})
    temp = current_data.get("temperature_2m")
    humidity = current_data.get("relative_humidity_2m")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 2. Transform & Load: Save to SQLite
    if temp is not None and humidity is not None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO taipei_weather (timestamp, temperature, humidity) VALUES (?, ?, ?)",
            (now_str, temp, humidity)
        )
        conn.commit()
        conn.close()
        return True
    return False

# load data for visalization
def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM taipei_weather ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    return df.iloc[::-1]

# front end (streamlit)
create_db()

st.title("Taipei Weather Tracker Dashboard")
st.caption("Final Bonus Project")

# data rf
if st.button("Fetch & Refresh Latest Data"):
    if fetch_and_save_weather():
        st.success("Successfully pulled latest Taipei weather and updated SQLite!")
    else:
        st.error("Failed to fetch data.")

# load current state
df = load_data()

if not df.empty:
    # display metrics
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperature", f"{latest['temperature']} °C")
    col2.metric("Humidity", f"{latest['humidity']} %")
    col3.metric("Last Updated", latest['timestamp'].split()[1])

    # visualization temp and humidity
    st.subheader("Temperature Trend")
    st.line_chart(data=df, x="timestamp", y="temperature")
    
    st.subheader("Humidity Trend")
    st.bar_chart(data=df, x="timestamp", y="humidity")

    # 4. raw data log
    st.subheader("Raw Data Logs")
    st.dataframe(df)
else:
    st.info("No data in database yet. Click the 'Fetch & Refresh Latest Data' button above to trigger your pipeline!")
