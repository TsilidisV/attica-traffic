import streamlit as st
import altair as alt
from utils import get_traffic_data

with st.spinner("Fetching data from MotherDuck..."):
    df = get_traffic_data()

st.title("🚗 Traffic Flow Theory (Speed vs. Volume Correlation)")
st.markdown(
    "As expected, speed and volume are highly correlated for all roads."
    "       The higher the vehicle count, the lower the speed gets."
)

st.header("Filters")
selected_roads = st.multiselect(
    "Select Roads", options=df["road_name"].unique(), default=["ΜΕΣΟΓΕΙΩΝ", "ΚΗΦΙΣΙΑΣ"]
)

filtered_df = df[df["road_name"].isin(selected_roads)] if selected_roads else df

# --- ALTAIR IMPLEMENTATION ---

# 1. Create a selection for interactivity (Legacy Syntax)
# In Altair 4, use 'selection_multi' instead of 'selection_point'
highlight = alt.selection_multi(fields=["road_name"], bind="legend")

# 2. Shared Base
base = alt.Chart(filtered_df).encode(
    x=alt.X("processed_hour", axis=alt.Axis(title="Hour of Day", labelAngle=-45)),
    tooltip=[
        alt.Tooltip("road_name", title="Road"),
        alt.Tooltip("processed_hour", title="Hour"),
        alt.Tooltip("weighted_avg_speed", title="Speed (km/h)", format=".1f"),
        alt.Tooltip("avg_counted_cars", title="Volume (Count)", format=","),
    ],
)

# 3. Speed Line (Left Axis, Solid)
# In Altair 4, use '.add_selection' instead of '.add_params'
line_speed = (
    base.mark_line(strokeWidth=3)
    .encode(
        y=alt.Y(
            "weighted_avg_speed:Q",
            axis=alt.Axis(title="Weighted average speed (Km/h)"),
            scale=alt.Scale(zero=False),
        ),
        color=alt.Color(
            "road_name:N", legend=alt.Legend(title="Click to Isolate Road")
        ),
        opacity=alt.condition(highlight, alt.value(1), alt.value(0.1)),
    )
    .add_selection(highlight)
)

# 4. Volume Line (Right Axis, Dashed)
line_volume = base.mark_line(strokeDash=[4, 4], strokeWidth=3).encode(
    y=alt.Y(
        "avg_counted_cars:Q",
        axis=alt.Axis(title="Average vehicle volume"),
        scale=alt.Scale(zero=False),
    ),
    color=alt.Color("road_name:N", legend=None),
    opacity=alt.condition(highlight, alt.value(1), alt.value(0.1)),
)

# 5. Layer and Final Polish
chart = (
    alt.layer(line_speed, line_volume)
    .resolve_scale(y="independent")
    .properties(
        title={
            "text": "Solid Line = Speed (Left) | Dashed Line = Volume (Right)",
            "color": "gray",
        },
        height=400,
    )
)

# Fix for Streamlit Deprecation Warning
# Use width="stretch" instead of use_container_width=True
st.altair_chart(chart, width="stretch")
