import os
import dagshub
import mlflow
from dotenv import load_dotenv

load_dotenv()

# Authenticate using build arguments
username = os.getenv("DAGSHUB_USERNAME")
token = os.getenv("DAGSHUB_TOKEN")
repo = os.getenv("DAGSHUB_REPO")

print("Authenticating with DagsHub...")
dagshub.auth.add_app_token(token)
dagshub.init(repo_owner=username, repo_name=repo, mlflow=True)

# The exact URIs from your DagsHub storage
MODEL_URI = "mlflow-artifacts:/6a85dac4a83e49f19a98d44c75aa5b0e/models/m-db84c59f1c0048eeb772a68ab629be41/artifacts"
MAPPING_URI = "mlflow-artifacts:/6a85dac4a83e49f19a98d44c75aa5b0e/7c962eb8b0544ec3837f32e5e3211bfa/artifacts/config/road_mapping.json"

# 1. Download the Model folder
print("Downloading model...")
mlflow.artifacts.download_artifacts(
    artifact_uri=MODEL_URI, 
    dst_path="./model_cache/model"
)

# 2. Download the JSON mapping directly
print("Downloading road mapping...")
mlflow.artifacts.download_artifacts(
    artifact_uri=MAPPING_URI, 
    dst_path="./model_cache/config"
)

print("✅ All artifacts successfully cached for Docker build!")