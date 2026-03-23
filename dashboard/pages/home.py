from datetime import datetime, timedelta

import figures
import pytz
import streamlit as st
import streamlit.components.v1 as components
from data import (
    get_daily_cache_key,
    get_health,
    get_heatmap_last_30,
    get_homepage_kpi,
    get_volatility_data_last_30,
)
from predict import call_hf_api, get_drift_report, get_model_data

DAGSHUB_USERNAME = st.secrets["DAGSHUB_USERNAME"]
DAGSHUB_REPO = st.secrets["DAGSHUB_REPO"]
model_experiment_link = f"https://dagshub.com/{DAGSHUB_USERNAME}/{DAGSHUB_REPO}.mlflow/#/experiments/0/runs?searchFilter=&orderByKey=attributes.start_time&orderByAsc=false&startTime=ALL&lifecycleFilter=Active&modelVersionFilter=All+Runs&datasetsFilter=W10%3D"
monitor_link = f"https://dagshub.com/{DAGSHUB_USERNAME}/{DAGSHUB_REPO}.mlflow/#/experiments/1/runs?searchFilter=&orderByKey=attributes.start_time&orderByAsc=false&startTime=ALL&lifecycleFilter=Active&modelVersionFilter=All+Runs&datasetsFilter=W10%3D&compareRunsMode=TABLE"

# Data loading
current_cache_key = get_daily_cache_key()

with st.spinner("Fetching data from MotherDuck..."):
    data = get_homepage_kpi(current_cache_key)

with st.spinner("Fetching data from MotherDuck..."):
    df_heat = get_heatmap_last_30(current_cache_key)

with st.spinner("Fetching data from MotherDuck..."):
    df_vol = get_volatility_data_last_30(current_cache_key)

with st.spinner("Fetching data from MotherDuck..."):
    df_health = get_health(current_cache_key)


# --- PAGE CONFIG ---
st.set_page_config(page_title="Attica Traffic Analytics", page_icon="🚗", layout="wide")


"""
# Attica Traffic Analytics 🚦🚗🚕🚐🚌🚚🚑🚙

In-depth analytics for Attica's road network, using the official data provided by [data.gov.gr](https://data.gov.gr/datasets/road_traffic_attica)

For a quick overview of the last 30 days, check out bellow. For analytics concerning the whole data period, spanning from late 2020, check out the tabs in the **sidebar**.

## Speed Predictor 

"""

container = st.container(border=True)

# Initialize session state variables if they don't exist
if "model_data" not in st.session_state:
    st.session_state.model_data = None


with container:
    tab1, tab2, tab3 = st.tabs(
        ["🔮 Live predictions", "🧐 Model evaluation", "🖥️ Data drift monitoring"]
    )

    with tab1:
        col1, col2, col3 = st.columns(3)

        with col1:
            # Input for Road Name (Pre-filled with the example value)
            road_name = st.selectbox(
                "Select a road",
                options=sorted(df_vol["road_name"].unique()),
                index=33,  # default to "ΚΗΦΙΣΙΑΣ"
            )

        with col2:
            # Input for Date time
            # We set the current datetime and replace mins with 0 and add 1 hour
            default_date = datetime.now(pytz.timezone("Europe/Athens")).replace(
                minute=0, second=0, microsecond=0
            ) + timedelta(hours=1)
            target_date = st.datetime_input(
                "Target date",
                value=default_date,
                step=60 * 60,  # 1 hour
            )

        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer
            submitted = st.button(
                "Get prediction", type="primary", use_container_width=True
            )

        if submitted:
            prediction = call_hf_api(road_name, target_date)

            predicted_speed = prediction.get("average_predicted_speed_kmh", "N/A")
            active_devices = prediction.get("active_devices_used", "N/A")

            st.metric(
                label=f"Predicted speed for {road_name} at {target_date.strftime('%Y-%m-%d %H:%M')}",
                value=f"{predicted_speed} Km/h",
            )

            with st.expander("See full json object"):
                st.json(prediction)

    with tab2:
        f"""
        ### Model evaluation report
        Automatically fetched from
        [DagsHub MLflow Artifacts]({model_experiment_link}).
        """

        # When button is clicked, fetch data and SAVE it to session state
        if st.button("Fetch model metrics", type="primary"):
            st.session_state.model_data = get_model_data()

        # Check if data exists in session state (instead of checking the button)
        # This block will now persist even when you click the radio button
        if st.session_state.model_data is not None:
            model_data = st.session_state.model_data  # Retrieve from state

            col1m, col2m = st.columns(2)

            with col1m:
                st.metric(
                    label="Mean absolute error",
                    value=f"{model_data['metrics']['mae']:.4f} Km/h",
                )

            with col2m:
                st.metric(
                    label="$$R^2$$ score",
                    value=f"{model_data['metrics']['r2_score']:.4f}",
                )

            st.divider()

            genre = st.radio(
                "Scale of the density of the data points",
                ["linear", "log"],
                captions=["True data density", "Favours outliers"],
                horizontal=True,
                help="ulo",
            )

            if genre == "linear":
                st.image(model_data["images"]["scatter_linear"], caption="Linear scale")
            elif genre == "log":
                st.image(model_data["images"]["scatter_log"], caption="Log scale")

            st.divider()

            st.image(model_data["images"]["residuals"])

    with tab3:
        f"""
        ### Data drift report
        Automatically fetched from
        [DagsHub MLflow Artifacts]({monitor_link}).
        """
        if st.button("Fetch latest drift report", type="primary"):
            with st.spinner("Connecting to DagsHub and downloading latest report..."):
                html_content = get_drift_report()
                components.html(html_content, height=1000, scrolling=True)

"""
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
    chart = figures.get_heatmap(df_heat)
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


"""
## Summary of Device Health

The dataset contains two primary sources of bad data:
1. Dead Readings: Some devices return zero counted cars and zero average speed at all times
2. Missing Readings: Time slots that data.gov.gr hosts no data

There's a clear increase in Dead Readings, indicating the necessity for device maintenance.

"""


with st.container(border=True):
    chart = figures.get_stacked_bars(df_health)
    st.altair_chart(chart, width="stretch")
