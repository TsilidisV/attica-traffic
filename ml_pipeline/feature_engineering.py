import os

import duckdb
import holidays
import numpy as np
import polars as pl
import yaml
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
load_dotenv()

# Load Configuration for the Data Layer
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    DB_NAME = config["data"]["db_name"]
    SCHEMA_NAME = config["data"]["schema_name"]
    TABLE_NAME = config["data"]["table_name"]
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    raise



class TimeFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Custom Scikit-Learn Transformer to engineer time-based features.
    This gets saved inside the MLflow model!
    """
    def __init__(self, country='GR'):
        self.country = country

    def fit(self, X, y=None):
        # We don't need to "learn" anything from the training data for time features
        return self

    def transform(self, X):
        # Create a copy to avoid SettingWithCopy warnings
        X_out = X.copy()
        
        # 1. Ensure date is a pandas datetime object
        X_out['date'] = pd.to_datetime(X_out['date'])
        
        # 2. Extract standard time features (Forcing int64 to avoid MLflow schema errors later)
        X_out['processed_month'] = X_out['date'].dt.month.astype(np.int64)
        X_out['day_id'] = X_out['date'].dt.dayofweek.astype(np.int64) # Monday=0, Sunday=6
        X_out['is_weekend'] = (X_out['day_id'] >= 5).astype(np.int64)
        
        # 3. Calculate Holidays dynamically
        years = X_out['date'].dt.year.unique()
        gr_holidays = holidays.country_holidays(self.country, years=years)
        # Check if the date is in the holiday dictionary
        X_out['is_holiday'] = X_out['date'].dt.date.isin(gr_holidays).astype(np.int64)
        
        # 4. Process Hour (Ensure it's an int)
        X_out['hour'] = X_out['hour'].astype(np.int64)
        
        # Rush hour: 7-9 and 15-18
        is_morning_rush = X_out['hour'].between(7, 9)
        is_evening_rush = X_out['hour'].between(15, 18)
        X_out['is_rush_hour'] = (is_morning_rush | is_evening_rush).astype(np.int64)
        
        # Circular time features
        X_out['hour_sin'] = np.sin(X_out['hour'] * (2.0 * np.pi / 24))
        X_out['hour_cos'] = np.cos(X_out['hour'] * (2.0 * np.pi / 24))
        
        # 5. Drop the raw date and hour columns since the model doesn't use them directly
        X_out = X_out.drop(columns=['date', 'hour'])
        
        return X_out


def get_motherduck_conn():
    token = os.getenv("MOTHERDUCK_TOKEN")
    return duckdb.connect(f"md:{DB_NAME}?motherduck_token={token}")


def load_optimized_data() -> pl.DataFrame:
    """Loads data efficiently using MotherDuck and Polars."""
    logger.info(f"Connecting to MotherDuck database: {DB_NAME}...")
    con = get_motherduck_conn()

    # TODO: adding "AND processed_date >= CURRENT_DATE - INTERVAL 1 YEAR"
    # improves model performance and accuracy
    # another idea is to pass sample_weight to gradient boosting model.
    # TODO: lookback is a hparam -> config
    query = f"""
        SELECT 
            device_id,                
            road_name, 
            processed_month, 
            processed_day, 
            processed_hour, 
            average_speed,
            processed_at,
            processed_date,
        FROM {DB_NAME}.{SCHEMA_NAME}.{TABLE_NAME}
        WHERE average_speed IS NOT NULL
          AND average_speed > 2
          AND average_speed < 130
          AND processed_date >= CURRENT_DATE - INTERVAL 1 YEAR
    """

    logger.debug(f"Executing SQL Query:\n{query}")
    df = con.sql(query).pl()  # Zero-copy transfer to Polars
    logger.success(f"Data loaded successfully: {len(df):,} rows.")
    return df


def preprocess_features(df: pl.DataFrame):
    """Prepares the base columns required by the Scikit-Learn Pipeline."""
    logger.info("Extracting base features with Polars...")
    initial_len = len(df)

    # We only extract the pure date and the hour as an integer.
    # The Scikit-learn Pipeline will handle all the complex feature engineering.
    df = df.with_columns(
        [
            pl.col("processed_at").cast(pl.Datetime).dt.date().alias("date"),
            pl.col("processed_hour")
            .cast(pl.Utf8)
            .str.split(":")
            .list.first()
            .cast(pl.Int64)
            .alias("hour")
        ]
    )

    # These are the ONLY inputs our ML Pipeline will need
    base_cols = ["device_id", "road_name", "date", "hour"]
    target_col = "average_speed"

    df = df.drop_nulls(subset=base_cols + [target_col])

    if len(df) < initial_len:
        logger.warning(f"Dropped {initial_len - len(df):,} rows containing NaN values.")

    # Convert to Pandas (The Scikit-Learn transformer expects Pandas)
    X = df.select(base_cols).to_pandas()
    y = df.select(target_col).to_pandas()[target_col]

    return X, y