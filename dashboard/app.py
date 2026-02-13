import streamlit as st

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
heatmap = st.Page("pages/heatmap.py", title="Spatiotemporal Heatmap", icon="🔥")
speed_count = st.Page("pages/speed_count.py", title="Speed vs Vehicle Count", icon="🏃")
barplot = st.Page("pages/barplot.py", title="Reliability Ranking", icon="📊")

# Create navigation structure (Grouped)
pg = st.navigation([home, heatmap, speed_count, barplot])

# Run the navigation
pg.run()
