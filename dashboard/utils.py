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
        FROM attica_traffic.dev.fct_hourly_road
    """
    return con.execute(query).df()