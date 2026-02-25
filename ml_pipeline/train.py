import os
import sys
import warnings

import dagshub
import mlflow
import mlflow.sklearn
import yaml
from dotenv import load_dotenv
from feature_engineering import load_optimized_data, preprocess_features
from loguru import logger
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, TargetEncoder
from feature_engineering import TimeFeatureExtractor, load_optimized_data, preprocess_features

# --- SUPPRESS WARNINGS ---
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

load_dotenv()

# --- SETUP LOGGING ---
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
)

# --- 1. LOAD CONFIGURATION ---
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    logger.success("Loaded config.yaml successfully.")
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    sys.exit(1)

TEST_SIZE = config["data"]["test_size"]
SEED = config["data"]["random_state"]
MODEL_PARAMS = config["model"]
MODEL_PARAMS["random_state"] = SEED

# --- 2. DAGSHUB / MLFLOW INIT ---
logger.info("Initializing DagsHub and MLflow...")
try:
    dagshub.auth.add_app_token(os.getenv("DAGSHUB_TOKEN"))
    dagshub.init(
        repo_owner=os.getenv("DAGSHUB_USERNAME"),
        repo_name=os.getenv("DAGSHUB_REPO"),
        mlflow=True,
    )
except Exception as e:
    logger.exception("Failed to initialize DagsHub/MLflow")
    sys.exit(1)


def main():
    # 3. FETCH AND PREP DATA (Using your separated module)
    df = load_optimized_data()
    X, y = preprocess_features(df)

    logger.info(f"Splitting data ({1 - TEST_SIZE}/{TEST_SIZE})...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED
    )

    # --- 4. BUILD THE SCIKIT-LEARN PIPELINE ---
    logger.info("Constructing Encoders + Regressor Pipeline...")
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "device_target_enc",
                TargetEncoder(target_type="continuous", random_state=SEED),
                ["device_id"],
            ),
            (
                "road_ordinal_enc",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                ["road_name"],
            ),
        ],
        remainder="passthrough",
    )

    model_pipeline = Pipeline(
        steps=[
            ("feature_engineer", TimeFeatureExtractor(country='GR')), # <--- New!
            ("preprocessor", preprocessor),
            ("regressor", HistGradientBoostingRegressor(**MODEL_PARAMS)),
        ]
    )

    # --- 5. TRAIN AND LOG ---
    mlflow.set_experiment("Traffic_Speed_Forecasting_Production")

    with mlflow.start_run(run_name="pipeline_target_encoded"):
        logger.info("Training full pipeline (This will encode AND fit the model)...")
        model_pipeline.fit(X_train, y_train)

        logger.info("Evaluating Pipeline on Test Set...")
        predictions = model_pipeline.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        logger.success(f"FINAL METRICS -> MAE: {mae:.2f} km/h | R2: {r2:.4f}")

        # Log Hyperparameters & Config
        mlflow.log_dict(config, "config.yaml")
        mlflow.log_params(MODEL_PARAMS)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2_score", r2)

        # Log the unified Pipeline
        logger.info("Saving complete Pipeline to MLflow...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        feat_eng_path = os.path.join(current_dir, "feature_engineering.py")
        signature = infer_signature(X_train.head(), predictions[:5])
        mlflow.sklearn.log_model(
            sk_model=model_pipeline,
            artifact_path="traffic_pipeline",
            signature=signature,
            input_example=X_train.iloc[:5],
            code_paths=[feat_eng_path]
        )

        logger.info("Saving road_name and device_id mapping to MLflow...")
        mapping_df = X[['road_name', 'device_id']].drop_duplicates()
        road_to_devices = mapping_df.groupby("road_name")["device_id"].apply(list).to_dict()
        mlflow.log_dict(road_to_devices, "config/road_mapping.json")

        logger.success("✅ Run finished! Entire pipeline securely logged to the cloud.")


if __name__ == "__main__":
    main()
