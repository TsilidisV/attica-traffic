import figures
import streamlit as st
from data import get_heatmap_last_30, get_homepage_kpi, get_volatility_data_last_30

with st.spinner("Fetching data from MotherDuck..."):
    data = get_homepage_kpi()

with st.spinner("Fetching data from MotherDuck..."):
    df_test = get_heatmap_last_30()

with st.spinner("Fetching data from MotherDuck..."):
    df_vol = get_volatility_data_last_30()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Attica Traffic Analytics", page_icon="🚗", layout="wide")


"""
# Attica Traffic Analytics 🚗🚕🚐🚌🚚🚑🚙

In-depth analytics for Attica's road network, using the official data provided by [data.gov.gr](https://data.gov.gr/datasets/road_traffic_attica)

For a quick overview of the last 30 days, check out bellow. For analytics concerning the whole data period, spanning from late 2020, check out the tabs in the **sidebar**.

##  Last 30 Days Summary



"""

with st.container(border=True):
    with st.container(horizontal=True, gap="medium"):
        cols = st.columns(4, gap="medium")

        with cols[0]:
            st.metric(
                "Weighted average speed",
                f"{data['last_kpi']['weighted_avg_speed'][0]:0.2f}Km/h",
                delta=f"{data['last_kpi']['weighted_avg_speed'][0] - data['previous_kpi']['weighted_avg_speed'][0]:0.2f}Km/h",
                width="content",
            )

        with cols[1]:
            st.metric(
                "Total vehicles counted",
                f"{int(data['last_kpi']['sum_counted_cars'][0]):,}",
                delta=f"{int(data['last_kpi']['sum_counted_cars'][0]) - int(data['previous_kpi']['sum_counted_cars'][0]):,}",
                delta_color="inverse",
                width="content",
            )

        with cols[2]:
            st.metric(
                "Total roads accounted",
                f"{data['last_kpi']['distinct_roads_count'][0]:}",
                delta=f"{data['last_kpi']['distinct_roads_count'][0] - data['previous_kpi']['distinct_roads_count'][0]:,}",
                width="content",
            )

        with cols[3]:
            st.metric(
                "Total measurement devices",
                f"{data['last_kpi']['distinct_devices_count'][0]:,}",
                delta=f"{data['last_kpi']['distinct_devices_count'][0] - data['previous_kpi']['distinct_devices_count'][0]:,}",
                width="content",
            )

    with st.container(horizontal=True, gap="medium"):
        cols = st.columns(3, gap="medium")

        with cols[0]:
            st.metric(
                "Busiest time slot",
                f"{data['busiest_times']['processed_day'][0]} {data['busiest_times']['processed_hour'][0]}",
                width="content",
            )

        with cols[1]:
            st.metric(
                "Lightest time slot",
                f"{data['busiest_times']['processed_day'][1]} {data['busiest_times']['processed_hour'][1]}",
                width="content",
            )

        with cols[2]:
            st.metric(
                "Last updated",
                f"{data['last_kpi']['latest_timestamp'][0]}",
                width="content",
            )


with st.container(border=True):
    twin_chart = figures.get_twin_plot(data["daily_speed_count"])
    st.altair_chart(twin_chart, width="stretch")

with st.container(border=True):
    chart = figures.get_heatmap(df_test)
    st.altair_chart(chart, width="stretch")

with st.container(horizontal=True, gap="medium", border=True):
    cols = st.columns(2, gap="medium")

    with cols[0]:
        """
        Top 20 High-Volatility Roads
        """
        chart_vol_head = figures.get_bar_chart(df_vol.head(20))
        st.altair_chart(chart_vol_head, width="stretch")

    with cols[1]:
        """
        Top 20 Low-Volatility Roads
        """
        chart_vol_head = figures.get_bar_chart(df_vol.tail(20))
        st.altair_chart(chart_vol_head, width="stretch")
