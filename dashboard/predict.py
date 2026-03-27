import os
import time
import datetime
from typing import Dict, Any, Optional

import mlflow
import requests
import streamlit as st
import yaml
from loguru import logger
from mlflow.artifacts import download_artifacts
from mlflow.tracking import MlflowClient
from requests.exceptions import RequestException, Timeout

# --- Constants & Configuration ---
API_URL = "https://bluerrose-attica-traffic-api.hf.space/predict"

# Streamlit secrets
DAGSHUB_USERNAME = st.secrets["DAGSHUB_USERNAME"]
DAGSHUB_REPO = st.secrets["DAGSHUB_REPO"]
DAGSHUB_TOKEN = st.secrets["DAGSHUB_TOKEN"]

# Load Configuration
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    MLFLOW_MONITOR_EXPERIMENT_NAME = config["drift"]["mlflow_monitor_experiment_name"]
    MLFLOW_MODEL_NAME = config["mlflow"]["model_name"]
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    raise

# --- Helper Functions ---

def _setup_mlflow() -> MlflowClient:
    """
    Centralized helper to configure MLflow tracking URI and authentication for DagsHub.
    
    Returns:
        MlflowClient: An initialized MLflow client ready for queries.
    """
    track_uri = f"https://dagshub.com/{DAGSHUB_USERNAME}/{DAGSHUB_REPO}.mlflow"
    os.environ["MLFLOW_TRACKING_URI"] = track_uri
    os.environ["MLFLOW_TRACKING_USERNAME"] = DAGSHUB_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = DAGSHUB_TOKEN
    mlflow.set_tracking_uri(track_uri)
    
    return MlflowClient()

# --- Main Functions ---

def call_hf_api(road_name: str, target_date: datetime.datetime) -> Optional[Dict[str, Any]]:
    """
    Calls the Hugging Face model API with built-in retry logic to handle cold starts (503).
    
    Args:
        road_name (str): The name of the road to predict traffic for.
        target_date (datetime): The target date and time for the prediction.
        
    Returns:
        dict: The JSON response from the API if successful.
        None: If the connection fails after all retries.
    """
    payload = {
        "road_name": road_name,
        "target_date": target_date.strftime("%Y-%m-%d"),
        "target_hour": target_date.hour
    }

    with st.status("Connecting to API...", expanded=False) as status:
        max_retries = 5
        wait_seconds = 5
        multiplier = 2
        
        for attempt in range(1, max_retries + 1):
            try:
                st.write(f"Attempt {attempt} of {max_retries}...")
                response = requests.post(API_URL, json=payload, timeout=5)
                
                if response.status_code == 200:
                    st.write("✅ Connection successful!")
                    status.update(label="API connection established", state="complete")
                    return response.json()
                
                elif response.status_code == 503:
                    st.write("😴 Server is asleep...")
                    status.update(label="Server was asleep and is waking up. This takes a minute...", state='running')
                    # Do not break; allow the loop to wait and retry
                    
            except Timeout:
                st.write("⏰ Server is waking up from sleep (Timeout)...")
                status.update(label="Server is waking up. This will take a bit...", state='running')
            except RequestException as e:
                st.write(f"❌ Connection error: {e}")
            
            # Backoff logic if the attempt failed
            if attempt < max_retries:
                sleep_time = wait_seconds * attempt * multiplier
                st.write(f"Waiting {sleep_time} seconds before next attempt...")
                time.sleep(sleep_time)

        # Triggers only if the loop exhausts all retries without returning
        status.update(label="Connection failed after multiple attempts.", state="error")
        st.error("Could not connect to the API. Please try again later.")
        return None


def get_drift_report() -> Optional[str]:
    """
    Fetches the latest Evidently data drift HTML report from MLflow.
    
    Returns:
        str: The raw HTML content of the drift report if successful.
        None: If the report cannot be found or downloaded.
    """
    try:
        client = _setup_mlflow()
        experiment = client.get_experiment_by_name(MLFLOW_MONITOR_EXPERIMENT_NAME)
        
        if not experiment:
            st.error(f"Could not find '{MLFLOW_MONITOR_EXPERIMENT_NAME}' experiment in MLflow.")
            return None
            
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if not runs:
            st.error("No drift monitoring runs found.")
            return None
            
        latest_run_id = runs[0].info.run_id
        html_uri = f"runs:/{latest_run_id}/reports/drift_report.html"
        local_html_path = download_artifacts(artifact_uri=html_uri)
        
        with open(local_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        st.success(f"Successfully loaded report from Run ID: {latest_run_id}")
        return html_content
            
    except Exception as e:
        logger.error(f"Failed to load drift report: {e}")
        st.error(f"Failed to load drift report: {e}")
        return None


def get_model_data() -> Optional[Dict[str, Any]]:
    """
    Fetches the latest registered model's metrics and evaluation plots from MLflow.
    
    Returns:
        dict: A dictionary containing the 'run_id', 'metrics' (dict), and 'images' (dict of local paths).
        None: If fetching the model data fails entirely.
    """
    client = _setup_mlflow()

    try:
        # Get the latest model version based on the integer version number
        model_versions = client.search_model_versions(f"name='{MLFLOW_MODEL_NAME}'")
        if not model_versions:
            st.error(f"No model versions found for '{MLFLOW_MODEL_NAME}'.")
            return None
            
        latest_version_info = max(model_versions, key=lambda v: int(v.version))
        run_id = latest_version_info.run_id
    except Exception as e:
        logger.error(f"Failed to fetch model versions: {e}")
        st.error(f"Failed to fetch model versions: {e}")
        return None

    data_payload = {
        "run_id": run_id,
        "metrics": {},
        "images": {}
    }

    with st.status("Connecting to DagsHub...", expanded=False) as status:
        # 1. Fetch Metrics
        try:
            run = client.get_run(run_id)
            data_payload["metrics"] = run.data.metrics 
            st.write("✅ Metrics downloaded")
        except Exception as e:
            logger.error(f"Failed to fetch metrics for run {run_id}: {e}")
            st.warning("Could not download metrics.")

        # 2. Fetch Evaluation Plots
        target_images = {
            "residuals": f"runs:/{run_id}/plots/residuals_histogram.png",
            "scatter_log": f"runs:/{run_id}/plots/actual_vs_predicted_bins=log.png",
            "scatter_linear": f"runs:/{run_id}/plots/actual_vs_predicted_bins=none.png"
        }

        for key, uri in target_images.items():
            try:
                status.update(label=f"Downloading image '{key}'...", state='running')
                local_path = download_artifacts(artifact_uri=uri)
                data_payload["images"][key] = local_path
                st.write(f"✅ Image '{key}' downloaded")
            except Exception as e:
                logger.error(f"Failed to download {key} at {uri}: {e}")
                data_payload["images"][key] = None 
        
        status.update(label="Model data successfully downloaded", state='complete')
        return data_payload