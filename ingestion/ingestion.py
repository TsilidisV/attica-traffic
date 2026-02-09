import os
import sys
import time
import json
from loguru import logger
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Third-party imports
import typer
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from huggingface_hub import HfApi

# --- CONFIGURATION & ENVIRONMENT ---
load_dotenv()

# Critical optimizations for Hugging Face Hub uploads
# 1. Increase HTTP timeout to 5 minutes to prevent WriteTimeout on slow connections
os.environ["HF_HUB_HTTP_TIMEOUT"] = "300"
# 2. Enable the high-performance Rust-based transfer agent (if installed)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Constants
API_URL = "https://data.gov.gr/api/v1/query/road_traffic_attica"
HF_REPO_ID = "bluerRose/attica-traffic-datalake"  
HF_TOKEN = os.environ.get("HF_TOKEN")
REPO_TYPE = "dataset"

# --- LOGGING SETUP ---
# 1. Console: Nice colors, strict format
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
)

# 2. File: Save detailed logs (JSON or text) for debugging later
logger.add(
    "logs/ingestion_{time}.log", rotation="10 MB", retention="10 days", level="DEBUG"
)

# CLI Initialization
app = typer.Typer(help="Attica Traffic Data Pipeline CLI")
api = HfApi(token=HF_TOKEN)


# --- HELPER FUNCTIONS ---


def get_retry_session(
    retries: int = 5,
    backoff_factor: float = 1.0,
    status_forcelist: list = [429, 500, 502, 503, 504],
) -> requests.Session:
    """
    Creates a requests Session with built-in exponential backoff.
    This ensures that transient network issues or API rate limits
    don't immediately crash the pipeline.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_data(date_str: str) -> list:
    """
    Fetches traffic data from the API for a specific date using a robust session.
    """
    params = {"date_from": date_str, "date_to": date_str}
    session = get_retry_session()

    try:
        response = session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RetryError:
        logger.error(f"❌ Max retries exceeded for {date_str}. Site might be down.")
        return []
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP Error for {date_str}: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected Error for {date_str}: {e}")
        return []
    finally:
        session.close()


def get_bronze_path(date_obj: datetime) -> str:
    """Returns the Hive-partitioned path for the Raw JSON (Bronze Layer)."""
    return (
        f"data/bronze/traffic/"
        f"year={date_obj.year}/month={date_obj.month:02d}/day={date_obj.day:02d}/"
        f"traffic_{date_obj.strftime('%Y-%m-%d')}.json"
    )


def get_silver_path(date_obj: datetime) -> str:
    """Returns the Hive-partitioned path for the Processed Parquet (Silver Layer)."""
    return f"data/silver/traffic/year={date_obj.year}/month={date_obj.month:02d}/data.parquet"


def process_and_upload_chunk(
    start_date: datetime, end_date: datetime, is_daily: bool = False
) -> bool:
    """
    Core pipeline logic:
    1. Iterates over a date range, fetching data day-by-day.
    2. Saves raw API responses as JSON (Bronze).
    3. Merges data into a Pandas DataFrame, enforces schema, and saves as Parquet (Silver).
    4. Uploads the resulting local directory to Hugging Face.

    Returns: bool indicating if data was found and uploaded.
    """
    chunk_label = (
        start_date.strftime("%Y-%m-%d")
        if is_daily
        else f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    )
    logger.info(f"🔄 Processing {chunk_label}...")

    local_root = Path("temp_ingest")
    if local_root.exists():
        shutil.rmtree(local_root)
    local_root.mkdir(parents=True)

    chunk_records = []
    current_day = start_date

    # --- 1. DOWNLOAD & BRONZE PHASE ---
    while current_day <= end_date:
        date_str = current_day.strftime("%Y-%m-%d")
        data = fetch_data(date_str)

        if data:
            # Inject reference date in case API data is missing it
            for row in data:
                row["ref_date"] = date_str

            # Save Bronze JSON locally
            bronze_file = local_root / get_bronze_path(current_day)
            bronze_file.parent.mkdir(parents=True, exist_ok=True)
            with open(bronze_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            chunk_records.extend(data)

        current_day += timedelta(days=1)

    # --- 2. TRANSFORMATION & SILVER PHASE ---
    if chunk_records:
        df = pd.DataFrame(chunk_records)

        # A. Add Metadata
        # Use timezone-naive UTC timestamp so DuckDB reads it natively as a TIMESTAMP type
        df["ingested_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)

        # Drop the helper injected column
        df = df.drop(columns=["ref_date"], errors="ignore")

        # B. Save Parquet Locally
        # Note: If a chunk spans two months, it saves to the start_date's month folder.
        # MotherDuck's * glob pattern handles this seamlessly on read.
        parquet_file = local_root / get_silver_path(start_date)
        parquet_file.parent.mkdir(parents=True, exist_ok=True)

        # Deduplicate before saving
        dedupe_subset = [c for c in df.columns if c != "ingested_at"]
        df = df.drop_duplicates(subset=dedupe_subset, keep="last")

        df.to_parquet(parquet_file, index=False, engine="pyarrow", compression="snappy")

        # --- 3. UPLOAD PHASE ---
        max_retries = 3
        upload_success = False

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🚀 Uploading to Hugging Face... (Attempt {attempt + 1}/{max_retries})"
                )
                api.upload_folder(
                    folder_path=str(local_root),
                    repo_id=HF_REPO_ID,
                    repo_type=REPO_TYPE,
                    commit_message=f"Ingest: {chunk_label}",
                )
                logger.info("✅ Upload successful.")
                upload_success = True
                break
            except Exception as e:
                logger.error(f"❌ Upload failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    logger.error(
                        "❌ Max upload retries reached. Data for this chunk may be missing on remote."
                    )

        # Cleanup temp directory
        if local_root.exists():
            shutil.rmtree(local_root)
        return upload_success

    else:
        logger.warning(f"⚠️ No data found for {chunk_label}. Skipping upload.")
        if local_root.exists():
            shutil.rmtree(local_root)
        return False


# --- CLI COMMANDS ---


@app.command()
@logger.catch
def daily(
    date_override: Optional[str] = typer.Option(
        None, help="Target date in YYYY-MM-DD. Defaults to yesterday."
    ),
):
    """
    Runs ingestion for a single day.
    Designed for CI/CD (GitHub Actions): It will FAIL (exit code 1) if no data is found,
    triggering an alert that the pipeline is broken.
    """
    if date_override is None:
        target_date = datetime.now() - timedelta(days=1)
    else:
        target_date = datetime.strptime(date_override, "%Y-%m-%d")

    date_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"▶️ Starting DAILY ingestion for {date_str}")

    # 1. Quick fetch to verify data exists before doing heavy processing
    test_data = fetch_data(date_str)

    if not test_data:
        logger.error(f"🔴 CRITICAL: No data found for {date_str}. API might be down.")
        logger.error("Failing the script to trigger GitHub Actions alert.")
        sys.exit(1)  # Crash the script deliberately

    # 2. Proceed with standard processing and upload
    success = process_and_upload_chunk(target_date, target_date, is_daily=True)

    if not success:
        logger.error("🔴 CRITICAL: Upload failed. Failing the script.")
        sys.exit(1)

    logger.info("✅ Daily ingestion finished successfully.")


@app.command()
@logger.catch
def backfill(
    start_date: str,
    end_date: str,
    chunk_days: int = typer.Option(
        7, help="Number of days to process in one upload chunk."
    ),
):
    """
    Bulk backfill for historical data.
    Processes data in chunks (default 7 days) to prevent memory issues and API timeouts.
    Tolerates missing days without crashing the entire backfill process.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    logger.info(
        f"▶️ Starting BACKFILL: {start_date} -> {end_date} (Chunks: {chunk_days} days)"
    )

    current_start = start
    while current_start <= end:
        current_end = min(current_start + timedelta(days=chunk_days - 1), end)

        # Process chunk. (Errors are logged, but we don't sys.exit() on backfills)
        process_and_upload_chunk(current_start, current_end, is_daily=False)

        current_start = current_end + timedelta(days=1)

    logger.info("✅ Backfill process completed.")


if __name__ == "__main__":
    app()
