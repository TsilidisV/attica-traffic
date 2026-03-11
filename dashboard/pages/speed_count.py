import streamlit as st
from data import get_daily_cache_key, get_speed_count
from figures import get_twin_multiple

current_cache_key = get_daily_cache_key()

with st.spinner("Fetching data from MotherDuck..."):
    df = get_speed_count(current_cache_key)

st.title("Traffic Flow Theory (Speed vs. Volume Correlation) 🚕")
st.markdown(
    "As expected, speed and volume are highly correlated for all roads."
    "       The higher the vehicle count, the lower the speed gets."
)


selected_roads = st.multiselect(
    "Select roads:", options=df["road_name"].unique(), default=["ΜΕΣΟΓΕΙΩΝ", "ΚΗΦΙΣΙΑΣ"]
)

filtered_df = df[df["road_name"].isin(selected_roads)] if selected_roads else df

chart = get_twin_multiple(filtered_df)
st.altair_chart(chart, width="stretch")
