import os

import duckdb
import holidays
import numpy as np
import polars as pl
import yaml
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Load Configuration for the Data Layer
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    DB_NAME = config["data"]["db_name"]
    SCHEMA_NAME = config["data"]["schema_name"]
    TABLE_NAME = config["data"]["table_name"]
    SAMPLE_SIZE = config["data"]["sample_size"]
except FileNotFoundError:
    logger.error("config.yaml not found in the root directory.")
    raise


def get_motherduck_conn():
    token = os.getenv("MOTHERDUCK_TOKEN")
    return duckdb.connect(f"md:{DB_NAME}?motherduck_token={token}")


def load_optimized_data() -> pl.DataFrame:
    """Loads data efficiently using MotherDuck and Polars."""
    logger.info(f"Connecting to MotherDuck database: {DB_NAME}...")
    con = get_motherduck_conn()

    sample_clause = f"USING SAMPLE {SAMPLE_SIZE}" if SAMPLE_SIZE else ""

    query = f"""
        SELECT 
            device_id,                
            road_name, 
            processed_month, 
            processed_day, 
            processed_hour, 
            average_speed,
            processed_at
        FROM {DB_NAME}.{SCHEMA_NAME}.{TABLE_NAME}
        {sample_clause}
        WHERE average_speed IS NOT NULL
          AND average_speed > 2
          AND average_speed < 130
    """

    logger.debug(f"Executing SQL Query:\n{query}")
    df = con.sql(query).pl()  # Zero-copy transfer to Polars
    logger.success(f"Data loaded successfully: {len(df):,} rows.")
    return df


def preprocess_features(df: pl.DataFrame):
    """Blazing fast feature engineering using pure Polars."""
    logger.info("Starting feature engineering with Polars...")
    initial_len = len(df)

    day_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    # Extract Date and build Holidays
    df = df.with_columns(
        pl.col("processed_at").cast(pl.Datetime).dt.date().alias("processed_date")
    )
    years = df.select(pl.col("processed_date").dt.year().unique()).to_series().to_list()
    gr_holidays = holidays.GR(years=years)
    holiday_dates = list(gr_holidays.keys())

    # Polars Vectorized Transformations
    df = df.with_columns(
        [
            # Convert hour from string to int (02:00 -> 2)
            pl.col("processed_hour")
            .cast(pl.Utf8)
            .str.split(":")
            .list.first()
            .cast(pl.Int32)
            .alias("processed_hour"),
            # Convert day from string to int (Monday -> 0)
            pl.col("processed_day")
            .replace_strict(day_map)
            .cast(pl.Int32)
            .alias("day_id"),
            # Add is_holiday feature
            pl.col("processed_date")
            .is_in(holiday_dates)
            .cast(pl.Int32)
            .alias("is_holiday"),
        ]
        # After converting days and hour to ints:
    ).with_columns(
        [
            # Add is_weekend feature
            (pl.col("day_id") >= 5).cast(pl.Int32).alias("is_weekend"),
            (
                pl.col("processed_hour").is_between(7, 9)
                | pl.col("processed_hour").is_between(15, 18)
            )
            .cast(pl.Int32)
            .alias("is_rush_hour"),
            # Add hour_sin and hour_cos feature
            # Time is now circular instead of just being a categorical feature
            (pl.col("processed_hour") * (2.0 * np.pi / 24)).sin().alias("hour_sin"),
            (pl.col("processed_hour") * (2.0 * np.pi / 24)).cos().alias("hour_cos"),
        ]
    )

    feature_cols = [
        "device_id",
        "road_name",
        "processed_month",
        "day_id",
        "hour_sin",
        "hour_cos",
        "is_weekend",
        "is_rush_hour",
        "is_holiday",
    ]
    target_col = "average_speed"

    df = df.drop_nulls(subset=feature_cols + [target_col])

    if len(df) < initial_len:
        logger.warning(f"Dropped {initial_len - len(df):,} rows containing NaN values.")

    logger.info(
        f"Preprocessing complete. Feature matrix shape: ( {len(df)}, {len(feature_cols)} )"
    )

    # Convert to Pandas before returning for Scikit-Learn
    X = df.select(feature_cols).to_pandas()
    y = df.select(target_col).to_pandas()[target_col]

    return X, y
