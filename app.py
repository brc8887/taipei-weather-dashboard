import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
DB_NAME = "weather.db"

def init_db():
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

# --- DATA PIPELINE (ETL) & REFRESH MECHANISM ---
def fetch_and_save_weather():
    # 1. Extract: Call free API for Taipei
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

# --- LOAD DATA FOR VISUALIZATION ---
def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM taipei_weather ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    # Reverse to make time go from left to right in charts
    return df.iloc[::-1]

# --- STREAMLIT DASHBOARD FRONTEND ---
init_db()

st.title("☀️ Taipei Weather Tracker Dashboard")
st.caption("A simple automated data pipeline project using Streamlit and SQLite.")

# 1. Data Refresh Trigger
if st.button("🔄 Fetch & Refresh Latest Data"):
    if fetch_and_save_weather():
        st.success("Successfully pulled latest Taipei weather and updated SQLite!")
    else:
        st.error("Failed to fetch data.")

# Load current state from DB
df = load_data()

if not df.empty:
    # 2. Display Metrics (Most recent entry)
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperature", f"{latest['temperature']} °C")
    col2.metric("Humidity", f"{latest['humidity']} %")
    col3.metric("Last Updated", latest['timestamp'].split()[1])

    # 3. Visualization
    st.subheader("📈 Temperature Trend (Last 20 Records)")
    st.line_chart(data=df, x="timestamp", y="temperature")
    
    st.subheader("💧 Humidity Trend")
    st.bar_chart(data=df, x="timestamp", y="humidity")

    # 4. Raw Data Log Table
    st.subheader("📋 Raw Pipeline Data Logs (SQL Database)")
    st.dataframe(df)
else:
    st.info("No data in database yet. Click the 'Fetch & Refresh Latest Data' button above to trigger your pipeline!")
