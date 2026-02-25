import pytest
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

# Import the functions and exceptions from your ingestion script
# (Assuming your script is named ingestion.py)
from ingestion.ingestion import (
    fetch_traffic_data,
    save_local_parquet,
    consolidate_partition,
    DataMissingError
)

# --- 1. Testing the API Fetch Logic ---


def test_fetch_traffic_data_success(mocker):
    """Test that valid API responses are returned correctly."""
    # ARRANGE: Create a fake network response
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{"device_id": "MS1", "speed": 50}]
    mock_response.raise_for_status.return_value = None

    # Intercept requests.get so it never hits the real internet
    mocker.patch("requests.get", return_value=mock_response)

    # ACT
    data = fetch_traffic_data("2024-02-23")

    # ASSERT
    assert len(data) == 1
    assert data[0]["device_id"] == "MS1"


def test_fetch_traffic_data_empty_raises_error(mocker):
    """Test that an empty list from the API raises our custom error."""
    # We must patch Tenacity's sleep so the test doesn't wait 4+ seconds during retries!
    mocker.patch("ingestion.ingestion.fetch_traffic_data.retry.sleep")

    mock_response = mocker.Mock()
    mock_response.json.return_value = []  # Empty data!
    mocker.patch("requests.get", return_value=mock_response)

    # ASSERT it raises the specific error
    with pytest.raises(DataMissingError, match="No data returned"):
        fetch_traffic_data("2024-02-23")


# --- 2. Testing the File System & Parquet Logic ---


def test_save_local_parquet(tmp_path: Path):
    """Test that data is saved to the correct Hive-partitioned path."""
    # ARRANGE: dummy data and a fake date
    dummy_data = [{"device_id": "MS1", "speed": 50}]
    test_date = datetime(2024, 2, 23)

    # ACT: Run the function using Pytest's temporary folder (tmp_path)
    file_path = save_local_parquet(dummy_data, test_date, tmp_path)

    # ASSERT
    # 1. File exists
    assert file_path.exists()

    # 2. Hive partitioning is correct (year=2024/month=02)
    assert "year=2024" in file_path.parts
    assert "month=02" in file_path.parts
    assert file_path.name == "2024-02-23.parquet"

    # 3. Read it back and check the injected timestamp
    df = pd.read_parquet(file_path)
    assert len(df) == 1
    assert "ingested_at" in df.columns
    assert df["device_id"].iloc[0] == "MS1"


def test_consolidate_partition(tmp_path: Path):
    """Test that multiple files are merged and originals are deleted."""
    # ARRANGE: Create a fake Hive partition folder
    partition_dir = tmp_path / "year=2024" / "month=02"
    partition_dir.mkdir(parents=True)

    # Create 3 small dummy parquet files
    for i in range(3):
        df = pd.DataFrame(
            [{"id": i, "val": "test", "ingested_at": datetime.now(timezone.utc)}]
        )
        df.to_parquet(partition_dir / f"day_{i}.parquet")

    # ACT: Run the consolidation
    compacted_file = consolidate_partition(partition_dir)

    # ASSERT
    assert compacted_file is not None
    assert compacted_file.exists()
    assert compacted_file.name == "compact-2024-02.parquet"

    # Read the compacted file to ensure all 3 rows survived
    combined_df = pd.read_parquet(compacted_file)
    assert len(combined_df) == 3

    # Ensure the original files were deleted!
    remaining_files = list(partition_dir.glob("*.parquet"))
    assert len(remaining_files) == 1
    assert remaining_files[0] == compacted_file
