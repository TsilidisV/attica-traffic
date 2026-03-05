import pytest
from fastapi.testclient import TestClient
import numpy as np

# Import the module itself so we can override its global variables
import api.main as api_module
from api.main import app


# --- 1. MOCK THE GLOBALS ---
class MockModel:
    def predict(self, df):
        # Return a fake speed prediction (45.0) for every device row passed in
        return np.array([45.0] * len(df))


# This fixture automatically runs before every test
@pytest.fixture(autouse=True)
def mock_api_assets():
    # Inject fake data into the API's memory
    api_module.ROAD_TO_DEVICES = {"ΚΗΦΙΣΙΑΣ": ["MS468", "MS311", "MS316"]}
    api_module.MODEL = MockModel()


# --- 2. SETUP TEST CLIENT ---
client = TestClient(app)


# --- 3. THE TESTS ---
def test_predict_speed_success():
    response = client.post(
        "/predict",
        json={"road_name": "ΚΗΦΙΣΙΑΣ", "target_date": "2026-02-26", "target_hour": 14},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["road_name"] == "ΚΗΦΙΣΙΑΣ"
    assert data["average_predicted_speed_kmh"] == 45.0  # Matches our MockModel
    assert data["active_devices_used"] == 3  # Matches our fake mapping


def test_predict_speed_invalid_road():
    response = client.post(
        "/predict",
        json={"road_name": "FAKE_ROAD", "target_date": "2026-02-26", "target_hour": 14},
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Road 'FAKE_ROAD' not found in the trained mapping."
    )
