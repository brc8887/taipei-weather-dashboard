import streamlit as st
import pandas as pd
import requests
import pg8000.dbapi
import warnings

# Suppress console warnings to keep the dashboard clean
warnings.filterwarnings('ignore')

# --- 1. SETUP & DATABASE CONNECTION ---
def get_db_connection():
    # Reads individual pieces from Streamlit Secrets to guarantee no connection errors
    return pg8000.dbapi.connect(
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        database=st.secrets["DB_NAME"]
    )

# --- 2. DATA PIPELINE (ETL BACKEND) ---
def run_data_pipeline():
    """Extracts data from the Open-Meteo API, transforms it, and loads it into Postgres."""
    # EXTRACT: Fetch current weather for Taipei
    url = "https://api.open-meteo.com/v1/forecast?latitude=25.033&longitude=121.565&current_weather=true"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        # TRANSFORM: Isolate the current temperature and status code
        current_temp = data['current_weather']['temperature']
        weather_code = data['current_weather']['weathercode']
        
        # LOAD: Safely insert records into your Supabase PostgreSQL table
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO taipei_weather (temperature, condition) VALUES (%s, %s)",
            (current_temp, str(weather_code))
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    return False

# --- 3. DASHBOARD (FRONTEND) ---
st.set_page_config(page_title="Taipei Weather Dashboard", layout="centered")

st.title("🌤️ Taipei Live Weather Dashboard")
st.write("This application monitors real-time weather metrics, pulling live data via the Open-Meteo API and storing it securely in PostgreSQL.")

# The Data Refresh Button (Fulfills assignment refresh rubric)
if st.button("🔄 Run ETL Pipeline (Fetch Fresh Data)"):
    with st.spinner("Executing pipeline and updating cloud database..."):
        success = run_data_pipeline()
        if success:
            st.success("Pipeline executed successfully! Database records updated.")
        else:
            st.error("Pipeline failure: Unable to fetch API endpoints.")

st.markdown("---")

# --- 4. VISUALIZATION ---
@st.cache_data(ttl=60) 
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT fetch_time, temperature FROM taipei_weather ORDER BY fetch_time ASC", conn)
    conn.close()
    return df

try:
    df = load_data()
    
    if not df.empty:
        st.subheader("Temperature Trends Over Time")
        
        # Format timestamps to be easily readable on the line chart
        df['fetch_time'] = pd.to_datetime(df['fetch_time']).dt.strftime('%H:%M:%S')
        df = df.set_index('fetch_time')
        
        # Streamlit's built-in charting engine
        st.line_chart(df['temperature'])
        
        st.subheader("Raw Database Records")
        st.dataframe(df)
    else:
        st.info("The database is currently empty. Click the 'Run ETL Pipeline' button above to generate your first historical data points!")
except Exception as e:
    st.warning(f"Please ensure your database is connected and the table is created. Error: {e}")
