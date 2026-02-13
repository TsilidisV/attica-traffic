# pages/1_Data.py
import streamlit as st


import altair as alt
import plotly.express as px
from utils import get_volatility_data


with st.spinner("Fetching data from MotherDuck..."):
    df = get_volatility_data()

chart = (
    alt.Chart(df.head(20))
    .mark_bar()
    .encode(
        # X-axis: The length of the bar (std_average_speed)
        x=alt.X(
            "std_average_speed",
            title="Standard deviation of the weighted average speed",
        ),
        # Y-axis: The categorical labels.
        # sort='-x' ensures the longest bars appear at the top.
        y=alt.Y("road_name", sort="-x", title="Road name"),
        # Color: The continuous scale based on weighted_avg_speed
        color=alt.Color(
            "weighted_avg_speed",
            scale=alt.Scale(scheme="redyellowgreen"),
            title="Speed",
        ),
        # Tooltip: Add hover info similar to Plotly
        tooltip=["road_name", "std_average_speed", "weighted_avg_speed"],
    )
)


chart_tail = (
    alt.Chart(df.tail(20))
    .mark_bar()
    .encode(
        # X-axis: The length of the bar (std_average_speed)
        x=alt.X(
            "std_average_speed",
            title="Standard deviation of the weighted average speed",
        ),
        # Y-axis: The categorical labels.
        # sort='-x' ensures the longest bars appear at the top.
        y=alt.Y("road_name", sort="-x", title="Road name"),
        # Color: The continuous scale based on weighted_avg_speed
        color=alt.Color(
            "weighted_avg_speed",
            scale=alt.Scale(scheme="redyellowgreen"),
            title="Speed",
        ),
        # Tooltip: Add hover info similar to Plotly
        tooltip=["road_name", "std_average_speed", "weighted_avg_speed"],
    )
)


"""
# 🚗 Road Reliability Ranking

The standard deviation of the weighted average speed is calculated.

## Top 20 High-Volatility Roads
Roads where travel time is unpredictable (sometimes fast, sometimes gridlocked).
"""

# Render interactive chart
st.altair_chart(chart, use_container_width=True)

"""
## Top 20 Low-Volatility Roads
Roads that are consistently slow or consistently fast.
"""

st.altair_chart(chart_tail, use_container_width=True)
