import streamlit as st
from data import get_spatiotemporal
from figures import get_heatmap

with st.spinner("Fetching data from MotherDuck..."):
    df = get_spatiotemporal()


st.title("Spatio-Temporal Heatmap 🚗")
st.markdown(
    "Commuter roads, like Κηφισίας, peak at 08:00 and 18:00 on weekdays. "
    "Nightlife/Entertainment roads, like Ιερά Οδός, might peak later in the evening on Fridays/Saturdays"
)


# --- 2. User Selection ---
selected_region = st.selectbox("Select a road:", options=df["road_name"].unique())

# --- 3. Filter Data ---
subset_df = df[df["road_name"] == selected_region]


chart = get_heatmap(subset_df, selected_region)
st.altair_chart(chart, width="stretch")


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
