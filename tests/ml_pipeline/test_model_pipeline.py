import pandas as pd
import numpy as np
import pytest
from datetime import date
from ml_pipeline.train import build_pipeline 

def test_pipeline_fit_predict():
    # 1. ARRANGE
    X_dummy = pd.DataFrame({
        "device_id": ["MS1", "MS2", "MS1", "MS3", "MS2", "MS4"],
        "road_name": ["A", "B", "A", "C", "B", "D"],
        "date": [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), 
                 date(2024, 4, 1), date(2024, 5, 1), date(2024, 6, 1)],
        "hour": [8, 14, 18, 2, 9, 17],
    })
    y_dummy = pd.Series([20.0, 50.0, 15.0, 80.0, 45.0, 60.0])

    # 2. ACT: Build the real pipeline, but with a tiny max_iter for testing speed
    pipeline = build_pipeline(model_params={"max_iter": 5})

    # 3. ASSERT
    try:
        pipeline.fit(X_dummy, y_dummy)
        predictions = pipeline.predict(X_dummy)
    except Exception as e:
        pytest.fail(f"Pipeline failed to fit or predict: {e}")

    assert len(predictions) == 6
    assert all(isinstance(p, (float, np.floating)) for p in predictions)