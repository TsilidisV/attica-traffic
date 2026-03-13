import os
import requests
import streamlit as st
import streamlit.components.v1 as components
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.artifacts import download_artifacts
from dotenv import load_dotenv

# Load environment variables (DagsHub credentials)
load_dotenv()

st.set_page_config(page_title="Attica Traffic AI", page_icon="🚦", layout="wide")

st.title("🚦 Attica Traffic Prediction & MLOps System")
st.markdown("A decoupled, cloud-native machine learning system with automated data drift monitoring.")

# Create tabs for different views
tab1, tab2 = st.tabs(["🔮 Live Predictions", "📊 Data Drift Monitoring"])

# ==========================================
# TAB 1: LIVE PREDICTIONS (Calling HF API)
# ==========================================
with tab1:
    st.header("Predict Average Speed")
    st.markdown("Query the live FastAPI backend deployed on Hugging Face Spaces.")
    
    # --- UPDATE THIS WITH YOUR ACTUAL FASTAPI URL ---
    API_URL = "https://your-username-your-space-name.hf.space/predict" 
    
    with st.form("prediction_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            device_id = st.text_input("Device ID (e.g., MS261)", value="MS261")
        with col2:
            target_datetime = st.text_input("Target Datetime", value="2026-03-15T08:30:00")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            submitted = st.form_submit_button("Get Prediction", use_container_width=True)
            
    if submitted:
        with st.spinner("Calling Hugging Face API..."):
            try:
                payload = {
                    "device_id": device_id,
                    "target_datetime": target_datetime
                }
                response = requests.post(API_URL, json=payload)
                response.raise_for_status()
                
                result = response.json()
                predicted_speed = result.get("predicted_average_speed", 0)
                
                st.success("API Request Successful!")
                st.metric(label=f"Predicted Speed for {device_id}", value=f"{predicted_speed:.2f} km/h")
                
            except Exception as e:
                st.error(f"Failed to connect to API: {e}")

# ==========================================
# TAB 2: DATA DRIFT MONITORING (Evidently + MLflow)
# ==========================================
with tab2:
    st.header("Continuous Training: Data Drift Report")
    st.markdown("Automatically fetched from DagsHub MLflow Artifacts.")
    
    # We use a button so we don't download the heavy HTML file on every single page refresh
    if st.button("Fetch Latest Drift Report", type="primary"):
        with st.spinner("Connecting to DagsHub and downloading latest report..."):
            try:
                # 1. Setup MLflow
                track_uri = "https://dagshub.com/vtsilidis/mlflow-track-repo-test.mlflow"
                os.environ["MLFLOW_TRACKING_URI"] = track_uri
                mlflow.set_tracking_uri(track_uri)
                
                client = MlflowClient()
                
                # 2. Find the latest run in the 'traffic_monitoring' experiment
                experiment = client.get_experiment_by_name("traffic_monitoring")
                
                if experiment is None:
                    st.error("Could not find 'traffic_monitoring' experiment in MLflow.")
                else:
                    runs = client.search_runs(
                        experiment_ids=[experiment.experiment_id],
                        order_by=["start_time DESC"],
                        max_results=1
                    )
                    
                    if not runs:
                        st.error("No drift monitoring runs found.")
                    else:
                        latest_run_id = runs[0].info.run_id
                        
                        # 3. Download the HTML artifact
                        html_uri = f"runs:/{latest_run_id}/reports/drift_report.html"
                        local_html_path = download_artifacts(artifact_uri=html_uri)
                        
                        # 4. Read and render the HTML inside Streamlit
                        with open(local_html_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                            
                        st.success(f"Successfully loaded report from Run ID: {latest_run_id}")
                        
                        # Render the HTML using Streamlit components!
                        # Scrolling is enabled, height is set to 1000px so it feels like a native dashboard
                        components.html(html_content, height=1000, scrolling=True)
                        
            except Exception as e:
                st.error(f"Failed to load drift report: {e}")