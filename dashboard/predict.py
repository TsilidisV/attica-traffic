import os
import time

import mlflow
import requests
import streamlit as st
import yaml
from loguru import logger
from mlflow.artifacts import download_artifacts
from mlflow.tracking import MlflowClient
from requests.exceptions import RequestException, Timeout

# --- Constant ---
API_URL = "https://bluerrose-attica-traffic-api.hf.space/predict"

try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    MLFLOW_MONITOR_EXPERIMENT_NAME = config["drift"]["mlflow_monitor_experiment_name"]
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    raise

def call_hf_api(road_name, target_date):

    payload = {
        "road_name": road_name,
        "target_date": target_date.strftime("%Y-%m-%d"),
        "target_hour": target_date.hour
    }

    with st.status("Connecting to API...", expanded=False) as status:
        
        max_retries = 5
        wait_seconds = 5
        multiplier = 2
        success = False
        
        for attempt in range(1, max_retries + 1):
            try:
                st.write(f"Attempt {attempt} of {max_retries}...")
                
                # Make the request
                response = requests.post(
                    API_URL, 
                    json=payload, 
                    timeout=5 
                )
                
                if response.status_code == 200:
                    st.write("✅ Connection successful!")
                    status.update(label="API connection established", state="complete")
                    success = True
                    return response.json()
                
                elif response.status_code == 503:
                    st.write("😴 Server is asleep...")
                    status.update(label="Server was asleep and is now waking up. This will take a minute...")
                    # We don't break here, we let the loop continue to retry
                    
            except Timeout:
                st.write("⏰ Server is walking up from sleep...")
                
            except RequestException as e:
                st.write(f"❌ Connection error: {e}")
            
            # If we are here, it failed. Wait before next attempt.
            if attempt < max_retries:
                st.write(f"Waiting {wait_seconds * attempt * multiplier} seconds...")
                time.sleep(wait_seconds * attempt * multiplier)

        # This runs after the loop finishes
        if not success:
            status.update(
                label="Connection failed after multiple attempts.", 
                state="error"
            )
            st.error("Could not connect to the API. Please try again later.")

def get_drift_report():
    try:
        # 1. Setup MLflow
        #TODO: 
        track_uri = "https://dagshub.com/vtsilidis/mlflow-track-repo-test.mlflow"
        os.environ["MLFLOW_TRACKING_URI"] = track_uri
        mlflow.set_tracking_uri(track_uri)
        
        client = MlflowClient()
        
        # 2. Find the latest run in the 'traffic_monitoring' experiment
        #TODO: traffic_monitoring -> config
        experiment = client.get_experiment_by_name(MLFLOW_MONITOR_EXPERIMENT_NAME)
        
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
                return html_content
                
    except Exception as e:
        st.error(f"Failed to load drift report: {e}")