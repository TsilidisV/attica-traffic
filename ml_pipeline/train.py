import os
import sys
import warnings

import dagshub
import mlflow
import mlflow.sklearn
import yaml
from dotenv import load_dotenv
from loguru import logger
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, TargetEncoder
from ml_pipeline.feature_engineering import TimeFeatureExtractor, load_optimized_data, preprocess_features
from ml_pipeline.train_utils import plot_residuals_histogram, plot_actual_vs_predicted_hexbin

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
SAMPLE_SIZE = config["drift"]["sample_size"]
MODEL_NAME = config["mlflow"]["model_name"]
EXPERIMENT_NAME = config["mlflow"]["experiment_name"]

def build_pipeline(model_params=None):
    """Factory function to build the ML pipeline."""
    if model_params is None:
        model_params = {}
        
    preprocessor = ColumnTransformer(
        transformers=[
            ("device_target_enc", TargetEncoder(target_type="continuous"), ["device_id"]),
            ("road_ordinal_enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), ["road_name"]),
        ],
        remainder="passthrough",
    )

    return Pipeline(
        steps=[
            ("feature_engineer", TimeFeatureExtractor(country='GR')), 
            ("preprocessor", preprocessor),
            ("regressor", HistGradientBoostingRegressor(**model_params)),
        ]
    )

def main():
    # --- 1. DAGSHUB / MLFLOW INIT ---
    # Moved INSIDE main() so it only runs during actual training
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

    # 3. FETCH AND PREP DATA (Using your separated module)
    df = load_optimized_data()
    X, y = preprocess_features(df)

    logger.info(f"Splitting data ({1 - TEST_SIZE}/{TEST_SIZE})...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED
    )

    # --- 4. BUILD THE SCIKIT-LEARN PIPELINE ---
    logger.info("Constructing Encoders + Regressor Pipeline...")
    model_pipeline = build_pipeline(MODEL_PARAMS)

    # --- 5. TRAIN AND LOG ---
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="pipeline_target_encoded"):
        # Logging training dataset metadata for data lineage
        logger.info("Logging full training dataset metadata to MLflow...")
        full_train_df = X_train.copy(deep=False)
        full_train_df['average_speed'] = y_train
        
        mlflow_dataset = mlflow.data.from_pandas(
            full_train_df,
            targets="average_speed",
            name="dataset"
        )
        mlflow.log_input(mlflow_dataset, context="training")

        logger.info("Training full pipeline (This will encode AND fit the model)...")
        model_pipeline.fit(X_train, y_train)

        logger.info("Evaluating Pipeline on Test Set...")
        predictions = model_pipeline.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        logger.success(f"FINAL METRICS -> MAE: {mae:.2f} Km/h | R2: {r2:.4f}")

        # Log Hyperparameters & Config
        mlflow.log_dict(config, "config.yaml")
        mlflow.log_params(MODEL_PARAMS)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2_score", r2)

        # Save reference data for evidently AI
        logger.info("Saving Reference Dataset for Data Drift Monitoring...")
        # Combine features and target
        reference_df = X_train.copy()
        reference_df['average_speed'] = y_train 
        # Sample the data (Statistically, 50,000 rows is more than enough for drift detection)
        # This keeps MLflow storage costs low and CI/CD downloads fast.
        if len(reference_df) > SAMPLE_SIZE:
            reference_df = reference_df.sample(n=SAMPLE_SIZE, random_state=SEED)
        # Save locally as Parquet (optimized), log it, and delete the local copy
        reference_file = "reference_data.parquet"
        reference_df.to_parquet(reference_file, index=False)
        mlflow.log_artifact(reference_file, "data")
        os.remove(reference_file) 
        logger.success("Reference dataset successfully logged to MLflow.")

        # Log the unified Pipeline
        logger.info("Saving complete Pipeline to MLflow...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        signature = infer_signature(X_train.head(), predictions[:5])
        mlflow.sklearn.log_model(
            sk_model=model_pipeline,
            name="traffic_pipeline",
            signature=signature,
            input_example=X_train.iloc[:5],
            code_paths=[current_dir],
            registered_model_name=MODEL_NAME
        )

        # Log plots
        logger.info("Generating Residuals vs Predicted plot...")
        actual_vs_predicted_fig = plot_actual_vs_predicted_hexbin(y_test, predictions, bins=None)
        mlflow.log_figure(actual_vs_predicted_fig, "plots/actual_vs_predicted_bins=none.png")

        actual_vs_predicted_fig_log = plot_actual_vs_predicted_hexbin(y_test, predictions, bins='log')
        mlflow.log_figure(actual_vs_predicted_fig_log, "plots/actual_vs_predicted_bins=log.png")

        logger.info("Generating Residuals Histogram...")
        hist_fig = plot_residuals_histogram(y_test, predictions)
        mlflow.log_figure(hist_fig, "plots/residuals_histogram.png")

        # log road name artifacts
        logger.info("Saving road_name and device_id mapping to MLflow...")
        mapping_df = X[['road_name', 'device_id']].drop_duplicates()
        road_to_devices = mapping_df.groupby("road_name")["device_id"].apply(list).to_dict()
        mlflow.log_dict(road_to_devices, "config/road_mapping.json")

        logger.success("✅ Run finished! Entire pipeline securely logged to the cloud.")


if __name__ == "__main__":
    main()
