import pandas as pd
import numpy as np
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import TargetEncoder, OrdinalEncoder
from sklearn.ensemble import HistGradientBoostingRegressor


def test_pipeline_fit_predict():
    # 1. ARRANGE: Create dummy X and y (Must be >= 5 rows for TargetEncoder CV!)
    X_dummy = pd.DataFrame(
        {
            "device_id": ["MS1", "MS2", "MS1", "MS3", "MS2", "MS4"],
            "road_name": ["A", "B", "A", "C", "B", "D"],
            "processed_month": [1, 2, 3, 4, 5, 6],
            "day_id": [0, 1, 2, 3, 4, 5],
            "hour_sin": [0.5, 0.8, -0.5, 0.0, 1.0, -1.0],
            "hour_cos": [0.5, 0.6, 0.5, 1.0, 0.0, 0.0],
            "is_weekend": [0, 0, 0, 1, 0, 1],
            "is_rush_hour": [1, 0, 1, 0, 1, 0],
            "is_holiday": [0, 0, 1, 0, 0, 0],
        }
    )
    y_dummy = pd.Series([20.0, 50.0, 15.0, 80.0, 45.0, 60.0])

    # 2. ACT: Build the pipeline exactly as it is in train.py
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "device_target_enc",
                TargetEncoder(target_type="continuous"),
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

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                HistGradientBoostingRegressor(max_iter=5),
            ),  # Tiny max_iter for speed
        ]
    )

    # 3. ASSERT: Ensure it can fit and predict without dimension/type errors
    try:
        pipeline.fit(X_dummy, y_dummy)
        predictions = pipeline.predict(X_dummy)
    except Exception as e:
        pytest.fail(f"Pipeline failed to fit or predict: {e}")

    assert len(predictions) == 6
    assert all(isinstance(p, (float, np.floating)) for p in predictions)
