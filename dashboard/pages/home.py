import streamlit as st
from utils import get_homepage_data
import altair as alt

with st.spinner("Fetching data from MotherDuck..."):
    data = get_homepage_data()


# --- PAGE CONFIG ---
st.set_page_config(page_title="Attica Traffic Analytics", page_icon="🚗", layout="wide")


"""
# 🚗 Attica Traffic Analytics

In-depth analysis for Attica's road network, using the official data provided by [data.gov.gr](https://data.gov.gr/datasets/road_traffic_attica)

For a quick overview of the last 30 days, check out bellow. For analysis concerning the whole data period, spanning from late 2020, check out the tabs in the sidebar.

##  Last 30 Days Summary



"""


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


base = alt.Chart(data["daily_speed_count"]).encode(
    x=alt.X(
        "processed_date:T", axis=alt.Axis(title="Date")
    )  # 'T' for encoding time data value
)

# 3. Create the First Line (Revenue - Left Axis)
# We give it a specific color and title.
line1 = base.mark_line(color="#57A44C").encode(
    y=alt.Y(
        "weighted_avg_speed",
        axis=alt.Axis(title="Weighted average speed (Km/h)", titleColor="#57A44C"),
        scale=alt.Scale(zero=False),  # Optional: allows axis to scale to data
    )
)

# 4. Create the Second Line (Growth Rate - Right Axis)
# We use transform_calculus or simply distinct encoding to separate it.
# The key is resolve_scale(y='independent') later.
line2 = base.mark_line(color="#AC3E31", strokeDash=[5, 5]).encode(  # Dashed line style
    y=alt.Y(
        "total_counted_cars",
        axis=alt.Axis(title="Total vehicles counted", titleColor="#AC3E31"),
        scale=alt.Scale(zero=False),
    )
)

# 5. Layer them together
# This is the magic step: resolve_scale(y='independent')
chart = (
    alt.layer(line1, line2)
    .resolve_scale(y="independent")
    .properties(title={"text": "Traffic Trends: Speed vs. Volume"})
    .interactive()
)

# 6. Display in Streamlit
st.altair_chart(chart, use_container_width=True)
