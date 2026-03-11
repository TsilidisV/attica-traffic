# utils.py
import duckdb
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

def get_daily_cache_key() -> datetime.date:
    """
    Generates a deterministic cache key to force a daily data refresh at exactly 06:00 UTC.

    ### The Problem:
    Standard Streamlit `@st.cache_data(ttl=...)` invalidates based on the time of the 
    *first user visit*. If the first user visits at 10:00 UTC, the cache lives until 
    10:00 UTC the next day. This ignores our daily Motherduck batch pipeline, which 
    completes at ~05:12 UTC, potentially serving stale data for hours.

    ### The Solution:
    Instead of `ttl`, we use this function to generate a static date string that 
    changes exactly once a day at 06:00 UTC. We pass this string as an argument to 
    our data-loading functions. When the string changes, Streamlit sees a "new" 
    function argument, invalidates the old cache (enforced by `max_entries=1`), 
    and fetches the fresh Motherduck data.

    ### Implementation Logic (Time-Shifting):
    To make the key roll over at 06:00 UTC instead of midnight, we take the current 
    UTC time and physically shift it backward by 6 hours before extracting the date.
    
    Examples of the shift on Nov 2nd:
    - At 05:12 UTC (pipeline runs) -> Shifted to Nov 1st 23:12 -> Key: "Nov 1" (Stale cache retained)
    - At 05:59 UTC                -> Shifted to Nov 1st 23:59 -> Key: "Nov 1" (Stale cache retained)
    - At 06:00 UTC (rollover)     -> Shifted to Nov 2nd 00:00 -> Key: "Nov 2" (CACHE INVALIDATED)
    - At 14:00 UTC                -> Shifted to Nov 2nd 08:00 -> Key: "Nov 2" (Fresh cache hit)

    Returns:
        datetime.date: The shifted UTC date used as the Streamlit cache key.
    """
    # Force UTC to ensure consistent behavior regardless of Streamlit server region
    now_utc = datetime.now(timezone.utc)
    
    # Shift time backward by 6 hours. 
    shifted_time = now_utc - timedelta(hours=6)
    
    return shifted_time.date()

# Shared Database Connection
@st.cache_resource
def get_connection():
    token = st.secrets["MOTHERDUCK_TOKEN"]
    # Connect explicitly to your database
    return duckdb.connect(f"md:attica_traffic?motherduck_token={token}")

@st.cache_data
def get_homepage_kpi(cache_key):
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


@st.cache_data
def get_heatmap_last_30(cache_key):
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


@st.cache_data
def get_spatiotemporal(cache_key):
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


@st.cache_data
def get_volatility_data_last_30(cache_key):
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


@st.cache_data
def get_volatility_data(cache_key):
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


@st.cache_data
def get_speed_count(cache_key):
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


@st.cache_data
def get_health(cache_key):
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