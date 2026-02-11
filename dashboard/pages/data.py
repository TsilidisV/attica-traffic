# pages/1_Data.py
import streamlit as st


import plotly.express as px
from utils import get_traffic_data




with st.spinner("Fetching data from MotherDuck..."):
    df = get_traffic_data()


st.title("🚗 Attica Traffic Intelligence")
st.markdown("Real-time traffic patterns from the **Attica Region** data lake.")


st.sidebar.header("Filters")
selected_roads = st.sidebar.multiselect(
    "Select Roads",
    options=df["road_name"].unique(),
    default=["ΜΕΣΟΓΕΙΩΝ", "ΚΗΦΙΣΙΑΣ"] # Pick two popular ones as default
)

if selected_roads:
    filtered_df = df[df["road_name"].isin(selected_roads)]
else:
    filtered_df = df

fig_speed = px.line(
        filtered_df, 
        x="processed_hour", 
        y="avg_average_speed", 
        color="road_name",
    )

fig_speed.update_layout(
    xaxis = dict(
        tickmode = 'linear',
        tick0 = 0.0,
        dtick = 2
    )
)

st.plotly_chart(fig_speed, use_container_width=True)