import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import typer
from dotenv import load_dotenv
from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# --- Configuration ---
load_dotenv()

# Optimizations for Hugging Face Hub uploads
os.environ["HF_HUB_HTTP_TIMEOUT"] = "300"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

app = typer.Typer()
API_URL = "https://data.gov.gr/api/v1/query/road_traffic_attica"
HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = os.getenv("HF_REPO_ID")

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)
logger.add("logs/pipeline.log", rotation="10 MB")

# --- Helpers ---


class DataMissingError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError,
            DataMissingError,
        )
    ),
    before_sleep=lambda retry_state: logger.warning(
        f"⚠️ Attempt {retry_state.attempt_number} failed for {retry_state.args[0]}. Retrying..."
    ),
    reraise=True,
)
def fetch_traffic_data(date_str: str) -> List[Dict[str, Any]]:
    params = {"date_from": date_str, "date_to": date_str}

    try:
        response = requests.get(API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise DataMissingError(f"No data returned for {date_str}")
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise DataMissingError(f"Endpoint not found for {date_str}")
        raise e


def save_local_parquet(
    data: List[Dict[str, Any]], date_obj: datetime, base_dir: Path
) -> Path:
    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    date_str = date_obj.strftime("%Y-%m-%d")

    df = pd.DataFrame(data)
    df["ingested_at"] = datetime.now(timezone.utc)

    # Hive Partitioning
    file_dir = base_dir / f"year={year}" / f"month={month}"
    file_dir.mkdir(parents=True, exist_ok=True)

    file_path = file_dir / f"{date_str}.parquet"
    df.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
    return file_path


def consolidate_partition(partition_dir: Path) -> Optional[Path]:
    """
    Scans a folder (e.g., .../month=01/), merges all parquet files into one,
    and deletes the originals.
    """
    files = list(partition_dir.glob("*.parquet"))
    if not files:
        return None

    # Avoid re-compacting if it's already just 1 compacted file
    if len(files) == 1 and files[0].name.startswith("compact-"):
        return files[0]

    logger.info(f"🔨 Compacting {len(files)} files in {partition_dir.name}...")

    try:
        # Read all files
        dfs = [pd.read_parquet(f) for f in files]
        combined_df = pd.concat(dfs, ignore_index=True)

        # Sort helps compression and read performance
        if "ingested_at" in combined_df.columns:
            combined_df = combined_df.sort_values("ingested_at")

        # Determine output filename: compact-YYYY-MM.parquet
        # structure is usually: .../year=YYYY/month=MM
        try:
            year_part = partition_dir.parent.name.split("=")[1]
            month_part = partition_dir.name.split("=")[1]
            new_filename = f"compact-{year_part}-{month_part}.parquet"
        except IndexError:
            new_filename = "compacted_data.parquet"

        output_path = partition_dir / new_filename

        # Write combined file
        combined_df.to_parquet(
            output_path, index=False, engine="pyarrow", compression="snappy"
        )

        # Delete originals ONLY if write succeeded
        if output_path.exists() and output_path.stat().st_size > 0:
            for f in files:
                if f != output_path:
                    f.unlink()
            return output_path
        else:
            raise RuntimeError("Compacted file is empty or missing")

    except Exception as e:
        logger.error(f"❌ Compaction failed for {partition_dir}: {e}")
        # If it failed, we leave the original files alone
        return None


# --- Commands ---


@app.command()
def ingest_daily(
    date: str = typer.Option(
        None, help="Date to ingest in YYYY-MM-DD. Defaults to yesterday."
    ),
    repo_id: str = typer.Option(REPO_ID, help="HF Repo ID"),
):
    """Daily ingest. Does NOT compact (appends new daily file)."""
    if not repo_id:
        raise typer.Exit(code=1)

    target_date = (
        datetime.strptime(date, "%Y-%m-%d")
        if date
        else datetime.now() - timedelta(days=1)
    )
    date_str = target_date.strftime("%Y-%m-%d")

    logger.info(f"🚀 Starting daily ingest for {date_str}")
    temp_dir = Path("temp_daily")

    try:
        data = fetch_traffic_data(date_str)
        file_path = save_local_parquet(data, target_date, temp_dir / "data")

        api = HfApi(token=HF_TOKEN)
        path_in_repo = f"data/year={target_date.year}/month={target_date.month:02d}/{date_str}.parquet"

        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Daily ingest: {date_str}",
        )
        logger.success("✅ Daily ingest complete.")
    except Exception as e:
        logger.exception("❌ Failure")
        raise typer.Exit(code=1)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@app.command()
def backfill(
    start_date: str,
    end_date: str,
    repo_id: str = typer.Option(REPO_ID, help="HF Repo ID"),
):
    """Backfills data and compacts it locally before upload."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    api = HfApi(token=HF_TOKEN)

    logger.info(f"📦 Starting Optimized Backfill {start_date} -> {end_date}")

    while current <= end:
        month_str = current.strftime("%Y-%m")
        logger.info(f"Processing month: {month_str}")

        month_temp_dir = Path(f"temp_backfill_{month_str}")
        repo_base = month_temp_dir / "data"

        next_month = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        month_end = min(end, next_month - timedelta(days=1))

        # 1. Download all days in the month
        files_collected = 0
        iter_date = current
        while iter_date <= month_end:
            date_str = iter_date.strftime("%Y-%m-%d")
            try:
                data = fetch_traffic_data(date_str)
                save_local_parquet(data, iter_date, repo_base)
                files_collected += 1
            except DataMissingError:
                pass  # Already logged in retry
            except Exception as e:
                logger.error(f"Error {date_str}: {e}")
            iter_date += timedelta(days=1)

        # 2. Compact the downloaded month locally
        if files_collected > 0:
            # Find the specific month folder we just created
            # Structure: temp/data/year=YYYY/month=MM
            year_dir = list(repo_base.glob("year=*"))[
                0
            ]  # Should be only one year per batch
            month_dir = list(year_dir.glob("month=*"))[0]

            consolidate_partition(month_dir)

            logger.info(f"⬆️ Uploading compacted batch for {month_str}...")
            api.upload_folder(
                folder_path=month_temp_dir,
                repo_id=repo_id,
                repo_type="dataset",
                path_in_repo=".",
                commit_message=f"Backfill batch: {month_str} (Compacted)",
            )
            logger.success(f"✅ Batch {month_str} done.")
        else:
            logger.warning(f"No data for {month_str}")

        if month_temp_dir.exists():
            shutil.rmtree(month_temp_dir)
        current = next_month


@app.command()
def maintenance(
    year: int,
    month: int,
    repo_id: str = typer.Option(REPO_ID, help="HF Repo ID"),
):
    """
    CRON JOB: Downloads a specific month from HF, compacts it,
    and commits the change (Delete old files + Add new file).
    """
    if not repo_id:
        logger.error("HF_REPO_ID is missing.")
        raise typer.Exit(code=1)

    month_str = f"{year}-{month:02d}"
    logger.info(f"🧹 Starting maintenance for {month_str}...")

    api = HfApi(token=HF_TOKEN)
    temp_dir = Path(f"maintenance_{month_str}")

    repo_folder = f"data/year={year}/month={month:02d}"

    try:
        logger.info("Downloading existing files...")
        local_path = api.snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            allow_patterns=f"{repo_folder}/*.parquet",
            local_dir=temp_dir,
        )

        # We explicitly cast to str because Pylance thinks it might be a list (dry_run)
        target_dir = Path(str(local_path)) / repo_folder

        if not target_dir.exists():
            logger.warning("Folder not found in repo.")
            return

        old_files = [f.name for f in target_dir.glob("*.parquet")]
        if not old_files:
            logger.warning("No parquet files found to compact.")
            return

        compacted_path = consolidate_partition(target_dir)

        if not compacted_path:
            logger.info("No compaction needed (or failed).")
            return

        operations = []
        operations.append(
            CommitOperationAdd(
                path_in_repo=f"{repo_folder}/{compacted_path.name}",
                path_or_fileobj=compacted_path,
            )
        )

        for old_file in old_files:
            if old_file != compacted_path.name:
                operations.append(
                    CommitOperationDelete(path_in_repo=f"{repo_folder}/{old_file}")
                )

        logger.info(f"Committing changes: +1 file, -{len(operations) - 1} files...")
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            operations=operations,
            commit_message=f"Maintenance: Compacted {month_str}",
        )
        logger.success(f"✅ Maintenance complete for {month_str}")

    except Exception as e:
        logger.exception("❌ Maintenance failed")
        raise typer.Exit(code=1)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    app()
