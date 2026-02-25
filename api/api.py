import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import date
from typing import Dict

import mlflow.pyfunc
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from loguru import logger
from mlflow.artifacts import download_artifacts
from pydantic import BaseModel, Field

# Load environment variables (DAGSHUB_USERNAME, DAGSHUB_TOKEN)
load_dotenv()


# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events cleanly."""
    global MODEL, ROAD_TO_DEVICES
    logger.info("Initializing API Assets from MLflow...")

    try:
        os.environ["MLFLOW_TRACKING_URI"] = (
            "https://dagshub.com/vtsilidis/mlflow-track-repo-test.mlflow"
        )
        os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("DAGSHUB_USERNAME")
        os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("DAGSHUB_TOKEN")

        # ⚠️ Replace with your actual Run ID!
        # Once Evidently AI is set up, this will become: "models:/traffic_pipeline@production"
        run_id = "4712765c615e47afab2222187fddaba2"

        # 2. Load the Road -> Devices JSON mapping
        mapping_uri = f"runs:/{run_id}/config/road_mapping.json"
        local_path = download_artifacts(artifact_uri=mapping_uri)

        with open(local_path, "r") as f:
            ROAD_TO_DEVICES = json.load(f)

        logger.success(f"✅ {len(ROAD_TO_DEVICES)} road mappings loaded successfully!")

        # 1. Load the Model Pipeline
        model_uri = f"mlflow-artifacts:/6a85dac4a83e49f19a98d44c75aa5b0e/models/m-5ef68d4c71934ac7b72cdb79721e405d/artifacts/"
        MODEL = mlflow.pyfunc.load_model(model_uri)

        logger.success(f"✅ Pipeline loaded successfully!")

    except Exception as e:
        logger.error(f"Failed to load assets from MLflow: {e}")

    # Yield control back to FastAPI to start accepting requests
    yield

    # --- SHUTDOWN LOGIC ---
    logger.info("Shutting down API. Cleaning up resources...")


# --- INITIALIZE FASTAPI APP ---
app = FastAPI(title="Attica Traffic Forecasting API", version="1.0", lifespan=lifespan)


# --- PYDANTIC SCHEMAS ---
class TrafficRequest(BaseModel):
    road_name: str = Field(..., examples=["ΚΗΦΙΣΙΑΣ"], description="Road name")
    target_date: date = Field(..., description="Format: YYYY-MM-DD")
    target_hour: int = Field(..., ge=0, le=23, description="Hour of the day (0-23)")


class TrafficResponse(BaseModel):
    road_name: str
    target_datetime: str = Field(..., description="Format: YYYY-MM-DD HH:MM")
    average_predicted_speed_kmh: float = Field(
        ..., description="Average speed across all devices on the road"
    )
    active_devices_used: int = Field(
        ..., description="Number of sensor devices used for this prediction"
    )
    device_breakdown: Dict[str, float] = Field(
        ..., description="Granular speed prediction per device ID"
    )


# --- PREDICTION ENDPOINT ---
@app.post("/predict", response_model=TrafficResponse)
def predict_speed(request: TrafficRequest):
    road = request.road_name

    # Fetch all devices for the requested road
    if road not in ROAD_TO_DEVICES:
        raise HTTPException(
            status_code=404, detail=f"Road '{road}' not found in the trained mapping."
        )

    devices_on_road = ROAD_TO_DEVICES[road]
    num_devices = len(devices_on_road)

    # Construct the batch DataFrame for the Scikit-Learn Pipeline
    input_df = pd.DataFrame(
        {
            "device_id": devices_on_road,
            "road_name": [road] * num_devices,
            "date": [str(request.target_date)] * num_devices,
            "hour": [request.target_hour] * num_devices,
        }
    )

    # Run Inference
    try:
        predictions = MODEL.predict(input_df)
    except Exception as e:
        logger.error(f"Prediction failed during inference: {e}")
        raise HTTPException(status_code=500, detail="Error during model inference.")

    # Aggregate results and build the response
    average_road_speed = float(np.mean(predictions))
    device_breakdown = dict(zip(devices_on_road, np.round(predictions, 2).tolist()))

    # Return the Pydantic model directly
    return TrafficResponse(
        road_name=road,
        target_datetime=f"{request.target_date} {request.target_hour:02d}:00",
        average_predicted_speed_kmh=round(average_road_speed, 2),
        active_devices_used=num_devices,
        device_breakdown=device_breakdown,
    )
