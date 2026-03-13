import streamlit as st

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
heatmap = st.Page("pages/heatmap.py", title="Spatiotemporal Heatmap", icon="🔥")
speed_count = st.Page("pages/speed_count.py", title="Speed vs Vehicle Count", icon="🏃")
barplot = st.Page("pages/barplot.py", title="Reliability Ranking", icon="📊")
data_drift_monitor = st.Page("pages/data_drift_monitor.py", title="Data Drift Monitoring", icon="🖥️")

# Create navigation structure (Grouped)
pg = st.navigation([home, heatmap, speed_count, barplot, data_drift_monitor])

# Run the navigation
pg.run()
