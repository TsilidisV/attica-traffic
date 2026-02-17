# utils.py
import duckdb
import streamlit as st
import pandas as pd


# 1. Shared Database Connection
@st.cache_resource
def get_connection():
    token = st.secrets["MOTHERDUCK_TOKEN"]
    # Connect explicitly to your database
    return duckdb.connect(f"md:attica_traffic?motherduck_token={token}")


@st.cache_data(ttl=3600)
def get_homepage_kpi():
    con = get_connection()

    # Map your desired output keys to the database table names
    sources = {
        "busiest_times": "fct_last_30_days_busiest_times",
        "daily_speed_count": "fct_last_30_days_daily_speed_count",
        "last_kpi": "fct_last_30_days_KPI",
        "previous_kpi": "fct_previous_30_days_KPI",
    }

    # Dynamically fetch all tables in one pass
    return {
        key: con.execute(f"SELECT * FROM attica_traffic.prod.{table}").df()
        for key, table in sources.items()
    }


@st.cache_data(ttl=3600)
def get_heatmap_last_30():
    con = get_connection()

    query = """
        SELECT
            processed_hour,
            processed_day,
            SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
        FROM attica_traffic.prod.mrt_last_30_days_traffic_road
        GROUP BY processed_hour, processed_day
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_spatiotemporal():
    con = get_connection()

    query = """
        SELECT
            road_name,
            processed_hour,
            processed_day,
            SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
            AVG(counted_cars) as avg_counted_cars
        FROM "attica_traffic"."prod"."mrt_traffic_road"
        GROUP BY road_name, processed_hour, processed_day
        ORDER BY road_name, processed_day, processed_hour
    """
    return con.execute(query).df()


@st.cache_data(ttl=3600)
def get_volatility_data_last_30():
    con = get_connection()

    query = """
        SELECT
            road_name,
            SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
            stddev(average_speed) as std_average_speed
        FROM "attica_traffic"."prod"."mrt_last_30_days_traffic_road"
        GROUP BY road_name
        ORDER BY std_average_speed DESC
    """
    return con.execute(query).df()


@st.cache_data(ttl=3600)
def get_volatility_data():
    con = get_connection()

    query = """
        SELECT
            road_name,
            SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
            stddev(average_speed) as std_average_speed
        FROM "attica_traffic"."prod"."mrt_traffic_road"
        GROUP BY road_name
        ORDER BY road_name
    """
    return con.execute(query).df()


@st.cache_data(ttl=3600)
def get_speed_count():
    con = get_connection()

    query = """
        SELECT
            road_name,
            processed_hour,
            SUM(average_speed * counted_cars * 1.0) / NULLIF(SUM(counted_cars), 0) AS weighted_avg_speed,
            AVG(counted_cars) as avg_counted_cars
        FROM "attica_traffic"."prod"."mrt_traffic_road"
        GROUP BY road_name, processed_hour
        ORDER BY road_name, processed_hour
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_health():
    con = get_connection()

    query = """
        WITH bad_data as (
        SELECT *
        FROM "attica_traffic"."prod"."fct_measurements"
        )
        SELECT
        processed_year, processed_month, 
        count(*) as readings,
        count(CASE WHEN is_dead = true THEN 1 END) as dead_count,
        100 * dead_count / readings as dead_percent,
        count(CASE WHEN is_ghost_reading = true THEN 1 END) as ghost_count,
        100 * ghost_count / readings as ghost_percent,
        count(CASE WHEN is_impossible_speed = true THEN 1 END) as impossible_speed_count,
        100 * impossible_speed_count / readings as impossible_speed_percent,
        count(CASE WHEN ingested_at IS NULL THEN 1 END) as missing_reading_count,
        100 * missing_reading_count / readings as missing_reading_percent
        FROM bad_data
        GROUP BY processed_year, processed_month
        ORDER BY processed_year, processed_month
    """
    df = con.execute(query).df()
    df['date'] = pd.to_datetime(
    df['processed_year'].astype(str) + '-' + 
    df['processed_month'].astype(str) + '-01'
    )
    return df