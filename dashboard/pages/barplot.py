# pages/1_Data.py
import streamlit as st


from data import get_volatility_data
from figures import get_bar_chart

with st.spinner("Fetching data from MotherDuck..."):
    df = get_volatility_data()




"""
# Road Reliability Ranking 🚐

The standard deviation of the weighted average speed is calculated.

Roads with a high standard deviation are unpredictable (sometimes fast, sometimes gridlocked).
On the other hand, roads with a low standard deviation are consistently slow or consistently fast.
"""

selected_roads = st.multiselect(
    "Select roads:", options=df["road_name"].unique()
)

filtered_df = df[df["road_name"].isin(selected_roads)] if selected_roads else df
chart = get_bar_chart(filtered_df)

st.altair_chart(chart, width='stretch')

