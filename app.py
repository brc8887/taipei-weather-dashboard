import streamlit as st
import pandas as pd
import requests
import pg8000.dbapi
from urllib.parse import urlparse
import warnings

# Suppress console warnings to keep your app clean
warnings.filterwarnings('ignore')

# --- 1. SETUP & DATABASE CONNECTION ---
DB_URL = st.secrets["DATABASE_URL"]

def get_db_connection():
    # pg8000 needs the URL broken into pieces to connect safely
    parsed = urlparse(DB_URL)
    return pg8000.dbapi.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/') # removes the slash from the db name
    )

# --- 2. DATA PIPELINE (ETL BACKEND) ---
def run_data_pipeline():
    """Extracts epidemiological data from API, Transforms it, and Loads it into Postgres."""
    url = "https://disease.sh/v3/covid-19/all"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        active_cases = data['active']
        recovered_cases = data['recovered']
        
        conn = get_db_connection()
        cur = conn.cursor()
        # The %s are placeholders for our new data
        cur.execute(
            "INSERT INTO global_health_metrics (active_cases, recovered_cases) VALUES (%s, %s)",
            (active_cases, recovered_cases)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    return False

# --- 3. DASHBOARD (FRONTEND) ---
st.set_page_config(page_title="Health Informatics Dashboard", layout="centered")

st.title("🏥 Global Health Informatics Dashboard")
st.write("This application monitors epidemiological data, pulling live global metrics via the Disease.sh open API and storing them securely in a PostgreSQL database.")

if st.button("🔄 Run ETL Pipeline (Update Health Metrics)"):
    with st.spinner("Pulling epidemiological data from API and updating database..."):
        success = run_data_pipeline()
        if success:
            st.success("Pipeline ran successfully! Database updated.")
        else:
            st.error("Failed to fetch data.")

st.markdown("---")

# --- 4. VISUALIZATION ---
@st.cache_data(ttl=60) 
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT fetch_time, active_cases, recovered_cases FROM global_health_metrics ORDER BY fetch_time ASC", conn)
    conn.close()
    return df

try:
    df = load_data()
    
    if not df.empty:
        st.subheader("Epidemiological Trends Over Time")
        
        df['fetch_time'] = pd.to_datetime(df['fetch_time']).dt.strftime('%H:%M:%S')
        df = df.set_index('fetch_time')
        
        st.line_chart(df[['active_cases', 'recovered_cases']])
        
        st.subheader("Raw Database Records")
        st.dataframe(df)
    else:
        st.info("The database is currently empty. Click the 'Run ETL Pipeline' button above to fetch your first data point!")
except Exception as e:
    st.warning(f"Please ensure your database is connected and the table is created. Error: {e}")
