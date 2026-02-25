import polars as pl
import pandas as pd
import pytest
from datetime import datetime, date
from ml_pipeline.feature_engineering import preprocess_features, TimeFeatureExtractor

def test_preprocess_features_base_extraction():
    """Tests that Polars correctly parses the raw data into our base columns."""
    # 1. ARRANGE: Create deterministic dummy data
    dummy_data = pl.DataFrame(
        {
            "device_id": ["MS261", "MS797", "MS001"],
            "road_name": ["Kifisias", "Attiki Odos", "Poseidonos"],
            "processed_month": [10, 3, 8],
            "processed_day": ["Saturday", "Monday", "Wednesday"],
            "processed_hour": ["08:00", "16:00", "12:00"],
            "processed_at": [
                datetime(2024, 10, 26, 8, 0, 0),
                datetime(2024, 3, 25, 16, 0, 0),
                datetime(2024, 8, 14, 12, 0, 0),
            ],
            "average_speed": [55.0, 40.0, 60.0],
        }
    )

    # 2. ACT
    X, y = preprocess_features(dummy_data)

    # 3. ASSERT
    assert len(X) == 3
    assert isinstance(X, pd.DataFrame), "Output X must be a Pandas DataFrame"
    
    # Check that it ONLY outputs the base columns
    expected_cols = ["device_id", "road_name", "date", "hour"]
    assert list(X.columns) == expected_cols
    
    # Check data type parsing
    assert X.iloc[0]["hour"] == 8
    assert X.iloc[1]["date"] == pd.Timestamp("2024-03-25")


def test_time_feature_extractor_logic():
    """Tests that the Scikit-Learn transformer calculates dates and math correctly."""
    # 1. ARRANGE: Create a mock Pandas DataFrame (exactly what FastAPI will pass to the model)
    dummy_base_df = pd.DataFrame({
        "device_id": ["MS261", "MS797", "MS001"],
        "road_name": ["Kifisias", "Attiki Odos", "Poseidonos"],
        "date": [date(2024, 10, 26), date(2024, 3, 25), date(2024, 8, 14)], # Sat, Mon (Holiday), Wed
        "hour": [8, 16, 12] # Morning rush, Evening rush, Non-rush
    })
    
    extractor = TimeFeatureExtractor(country='GR')
    
    # 2. ACT: Run the transformer
    X_transformed = extractor.transform(dummy_base_df)
    
    # 3. ASSERT: Verify the math and logic
    # Check Row 0 (Saturday 08:00)
    assert X_transformed.iloc[0]["is_weekend"] == 1
    assert X_transformed.iloc[0]["day_id"] == 5 # Saturday is index 5
    assert X_transformed.iloc[0]["is_rush_hour"] == 1 # 8:00 is morning rush
    
    # Check Row 1 (Monday 16:00 on March 25th)
    assert X_transformed.iloc[1]["is_weekend"] == 0
    assert X_transformed.iloc[1]["is_rush_hour"] == 1 # 16:00 is evening rush
    assert X_transformed.iloc[1]["is_holiday"] == 1 # March 25th in GR

    # Check Row 2 (Wednesday 12:00)
    assert X_transformed.iloc[2]["is_rush_hour"] == 0
    assert X_transformed.iloc[2]["is_holiday"] == 0
    
    # Check that columns were properly engineered and old ones were dropped
    expected_cols = [
        "device_id", "road_name", "processed_month", "day_id", 
        "is_weekend", "is_holiday", "is_rush_hour", "hour_sin", "hour_cos"
    ]
    assert all(col in X_transformed.columns for col in expected_cols)
    assert "date" not in X_transformed.columns, "Transformer should drop the raw date column"
    assert "hour" not in X_transformed.columns, "Transformer should drop the raw hour column"