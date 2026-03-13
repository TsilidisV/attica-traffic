import os
import json
import duckdb
import pandas as pd
import mlflow
import yaml
from mlflow.tracking import MlflowClient
from mlflow.artifacts import download_artifacts
from dotenv import load_dotenv
from loguru import logger

from evidently import Report
from evidently.presets import DataDriftPreset

load_dotenv()

try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    DB_NAME = config["data"]["db_name"]
    SCHEMA_NAME = config["data"]["schema_name"]
    TABLE_NAME = config["data"]["table_name"]
    MLFLOW_MONITOR_EXPERIMENT_NAME = config["drift"]["mlflow_monitor_experiment_name"]
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    raise

def main():
    logger.info("Starting Daily Data Drift Monitoring...")
    
    # 1. SETUP MLFLOW AUTHENTICATION
    # TODO: use env variables for track_uri
    track_uri = "https://dagshub.com/vtsilidis/mlflow-track-repo-test.mlflow"
    os.environ["MLFLOW_TRACKING_URI"] = track_uri
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("DAGSHUB_USERNAME")
    os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("DAGSHUB_TOKEN")
    mlflow.set_tracking_uri(track_uri)
    
    # 2. FETCH REFERENCE DATA FROM LATEST MODEL
    client = MlflowClient()
    # TODO: config
    model_name = "Attica_Traffic_Model"
    
    logger.info(f"Looking up latest registered version of '{model_name}'...")
    try:
        # The modern way to search models without deprecated "stages"
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            logger.error("No registered model found.")
            return
            
        # Sort to find the highest version number safely
        latest_version = max(versions, key=lambda v: int(v.version))
        run_id = latest_version.run_id
        
        ref_uri = f"runs:/{run_id}/data/reference_data.parquet"
        local_ref_path = download_artifacts(artifact_uri=ref_uri)
        reference_df = pd.read_parquet(local_ref_path)
        logger.success(f"Loaded Reference Data: {reference_df.shape[0]} rows.")
        
    except Exception as e:
        logger.error(f"Failed to load reference data: {e}")
        return

    # 3. FETCH CURRENT DATA FROM MOTHERDUCK (RAW!)
    logger.info("Fetching recent raw traffic data from MotherDuck...")
    try:
        token = os.getenv("MOTHERDUCK_TOKEN")
        con = duckdb.connect(f"md:attica_traffic?motherduck_token={token}")
        
        # TODO: lookback as a hyperparameter
        query = f"""
            SELECT device_id, road_name, average_speed
            FROM {DB_NAME}.{SCHEMA_NAME}.{TABLE_NAME} 
            WHERE processed_date >= CURRENT_DATE - INTERVAL 14 DAY
        """
        current_df = con.sql(query).df()
        
        if current_df.empty:
            logger.warning("No recent data found. Exiting monitor.")
            return
            
        # Ensure column order matches reference exactly (dropping extra DB columns if any)
        columns_to_keep = reference_df.columns.tolist()
        # Drop the target variable if it accidentally got pulled from the DB for the current data
        # (Since we are monitoring input features, we don't strictly need the target in the live data for this specific report)
        current_df = current_df[[col for col in columns_to_keep if col in current_df.columns]]
        
        logger.success(f"Loaded Raw Current Data: {current_df.shape[0]} rows.")
        
    except Exception as e:
        logger.error(f"Failed to fetch current data: {e}")
        return

    # 4. RUN EVIDENTLY AI DRIFT REPORT
    logger.info("Calculating Data Drift metrics on raw features...")
    report_blueprint = Report(metrics=[DataDriftPreset()])
    evaluation_result = report_blueprint.run(reference_data=reference_df, current_data=current_df)
    
    html_path = "drift_report.html"
    json_path = "drift_report.json"
    evaluation_result.save_html(html_path)
    evaluation_result.save_json(json_path)
    
    dataset_drifted = evaluation_result.dict()["metrics"][0]["value"]["count"]
    drift_share = evaluation_result.dict()["metrics"][0]["value"]["share"]
    
    logger.info(f"Drift Detection Status: {dataset_drifted} (Share: {drift_share:.2f})")

    # 5. LOG TO MLFLOW
    mlflow.set_experiment(MLFLOW_MONITOR_EXPERIMENT_NAME)
    
    with mlflow.start_run(run_name="daily_drift_check"):
        mlflow.log_metric("dataset_drift_detected", int(dataset_drifted))
        mlflow.log_metric("drift_share", drift_share)
        mlflow.log_artifact(html_path, "reports")
        mlflow.log_artifact(json_path, "reports")
        
    os.remove(html_path)
    os.remove(json_path)
    
    # github actions integration
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            is_drifting = "true" if dataset_drifted else "false"
            f.write(f"drift_detected={is_drifting}\n")
            f.write(f"drift_share={drift_share:.2f}\n")

    logger.success("Monitoring complete! Reports saved to MLflow.")

if __name__ == "__main__":
    main()