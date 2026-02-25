import polars as pl
import pandas as pd
import pytest
from datetime import datetime
from ml_pipeline.feature_engineering import preprocess_features


def test_preprocess_features_logic():
    # 1. ARRANGE: Create deterministic dummy data
    dummy_data = pl.DataFrame(
        {
            "device_id": ["MS261", "MS797", "MS001"],
            "road_name": ["Kifisias", "Attiki Odos", "Poseidonos"],
            "processed_month": [10, 3, 8],
            "processed_day": ["Saturday", "Monday", "Wednesday"],
            "processed_hour": ["08:00", "16:00", "12:00"],
            # Row 2 is exactly March 25th (A Greek Holiday!)
            "processed_at": [
                datetime(2024, 10, 26, 8, 0, 0),
                datetime(2024, 3, 25, 16, 0, 0),
                datetime(2024, 8, 14, 12, 0, 0),
            ],
            "average_speed": [55.0, 40.0, 60.0],
        }
    )

    # 2. ACT: Run the function
    X, y = preprocess_features(dummy_data)

    # 3. ASSERT: Verify the math and logic
    assert len(X) == 3
    assert isinstance(X, pd.DataFrame), (
        "Output X must be a Pandas DataFrame for scikit-learn"
    )

    # Check Row 0 (Saturday 08:00)
    assert X.iloc[0]["is_weekend"] == 1
    assert X.iloc[0]["day_id"] == 5

    # Check Row 1 (Monday 16:00 on March 25th)
    assert X.iloc[1]["is_weekend"] == 0
    assert X.iloc[1]["is_rush_hour"] == 1
    assert X.iloc[1]["is_holiday"] == 1

    # Check Columns exist
    expected_cols = [
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
    assert all(col in X.columns for col in expected_cols)
