# utils.py
import streamlit as st
import duckdb

# 1. Shared Database Connection
@st.cache_resource
def get_connection():
    token = st.secrets["MOTHERDUCK_TOKEN"]
    # Connect explicitly to your database
    return duckdb.connect(f"md:attica_traffic?motherduck_token={token}")

@st.cache_data(ttl=3600)
def get_traffic_data():
    con = get_connection()
    # Simple aggregation query (replace with your Mart later)
    query = """
        SELECT *
        FROM attica_traffic.prod.fct_hourly_road
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_hourly_daily_data():
    con = get_connection()
    # Simple aggregation query (replace with your Mart later)
    query = """
        SELECT *
        FROM attica_traffic.prod.fct_hourly_daily_road_heatmap
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_volatility_data():
    con = get_connection()
    # Simple aggregation query (replace with your Mart later)
    query = """
        SELECT *
        FROM attica_traffic.prod.fct_road_reliability
    """
    return con.execute(query).df()


@st.cache_data(ttl=3600)
def get_homepage_data():
    con = get_connection()
    
    # Map your desired output keys to the database table names
    sources = {
        "busiest_times": "fct_last_30_days_busiest_times",
        "daily_speed_count":   "fct_last_30_days_daily_speed_count",
        "last_kpi":      "fct_last_30_days_KPI",
        "previous_kpi":  "fct_previous_30_days_KPI",
    }

    # Dynamically fetch all tables in one pass
    return {
        key: con.execute(f"SELECT * FROM attica_traffic.prod.{table}").df()
        for key, table in sources.items()
    }