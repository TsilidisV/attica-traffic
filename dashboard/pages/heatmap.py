# pages/1_Data.py
import altair as alt

# import plotly.express as px
import streamlit as st
from utils import get_hourly_daily_data

with st.spinner("Fetching data from MotherDuck..."):
    df = get_hourly_daily_data()


st.title("🚗 Spatio-Temporal Heatmap")
st.markdown(
    "Commuter roads, like Κηφισίας, peak at 08:00 and 18:00 on weekdays."
    "Nightlife/Entertainment roads, like Αχίλλεως , might peak later in the evening on Fridays/Saturdays"
)


# --- 2. User Selection ---
selected_region = st.selectbox("Select a road:", options=df["road_name"].unique())

# --- 3. Filter Data ---
subset_df = df[df["road_name"] == selected_region]

# Make days appear in the correct order
day_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

## --- 4. Prepare Data (Pivot) ---
## We pivot to create the grid matrix (X vs Y)
# heatmap_data = subset_df.pivot_table(
#    index="processed_hour",  # Y-axis
#    columns="processed_day",  # X-axis
#    values="weighted_avg_speed",  # Color intensity
#    aggfunc="mean",  # Handle duplicates
# )
#
#
# heatmap_data = heatmap_data.reindex(columns=day_order)
#
#
## --- 5. Plotting with Plotly Express ---
#
#
# fig = px.imshow(
#    heatmap_data,
#    labels=dict(x="Month", y="Hour", color="Average speed"),  # Custom labels for hover
#    x=heatmap_data.columns,
#    y=heatmap_data.index,
#    text_auto=".2f",  # Displays the values inside the squares (like annot=True)
#    aspect="auto",  # Allows the heatmap to stretch to fit the container
#    color_continuous_scale="RdYlGn",  # Plotly color scale
#    origin="lower",  # Make hours appear in the reverse order
#    height=600,
# )
#
## Update layout for a cleaner look
# fig.update_layout(title_text=f"Sales Heatmap - {selected_region}")
#
#
## Render interactive chart
# st.plotly_chart(fig, width='stretch')
#
#
# day_order = [
#    "Monday",
#    "Tuesday",
#    "Wednesday",
#    "Thursday",
#    "Friday",
#    "Saturday",
#    "Sunday",
# ]

# --- Plotting with Altair ---

# 1. Define the Base Chart
# We group by Day (x) and Hour (y).
base = alt.Chart(subset_df).encode(
    x=alt.X(
        "processed_day",
        sort=day_order,
        title="Day",
        # Rotate labels by -45 degrees
        axis=alt.Axis(labelAngle=-45, labelOverlap=False),
    ),
    y=alt.Y("processed_hour", title="Hour", sort="descending"),
)

# 2. Create the Heatmap (Rectangles)
# We aggregate the mean speed automatically here.
heatmap = base.mark_rect().encode(
    color=alt.Color(
        "weighted_avg_speed",
        aggregate="mean",
        scale=alt.Scale(scheme="redyellowgreen"),
        title="Average Speed",
    ),
    tooltip=[
        "processed_day",
        "processed_hour",
        alt.Tooltip("weighted_avg_speed", aggregate="mean", format=".2f"),
    ],
)

# 3. Create the Text Labels (equivalent to text_auto=True)
text = base.mark_text().encode(
    text=alt.Text("weighted_avg_speed", aggregate="mean", format=".1f"),
    # Optional: Adjust text color based on background for readability
    # color=alt.value('black')
)

# 4. Combine and Display
chart = (heatmap + text).properties(title=f"Speed heatmap for {selected_region}")

st.altair_chart(chart, width='stretch')
