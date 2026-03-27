<h1 align="center">🚗 Attica Mobility! 🚦</h1>
<h2 align="center"> From Ingestion to Prediction: An End-to-End Data & ML Pipeline </h2>

<p align="center">
  <b>
    A serverless, portable MDS Lakehouse,<br>
    utilizing a resilient Medallion-style ELT pipeline,<br>
    designed to capture, archive, analyze and predict traffic data from Attica, Greece,<br>
    by answering the following business intelligence questions:
  </b>
</p>

<p align="center">
  <i>• What's traffic going to be like in a particular road and time?</i><br> 
  <i>• Which is the busiest time slot?</i><br> 
  <i>• Does total vehicle volume correlate with average network speed?</i><br>
  <i>• Which are the most and least volatile roads?</i><br>
  <i>• Do the measuring devices need maintenance?</i>
</p>

<p align="center">
  <a href="https://www.python.org/"><img height="42" src="https://cdn.simpleicons.org/python/3776AB" /></a>
  <a href="https://pytest.org/"><img height="42" src="https://cdn.simpleicons.org/pytest/0A9EDC" /></a>
  <a href="https://docs.github.com/en/actions/"><img height="42" src="https://cdn.simpleicons.org/githubactions/2088FF" /></a>
  <a href="https://huggingface.co/docs/datasets/index"><img height="42" src="https://cdn.simpleicons.org/huggingface/FFD21E" /></a>
  <a href="https://www.getdbt.com/"><img height="42" src="https://raw.githubusercontent.com/TsilidisV/TsilidisV/refs/heads/main/pictures/dbt.svg" /></a>
  <a href="https://motherduck.com/"><img height="42" src="https://cdn.simpleicons.org/duckdb/FFF000" /></a>
  <a href="https://scikit-learn.org/"><img height="42" src="https://cdn.simpleicons.org/scikitlearn/F7931E" /></a>
  <a href="https://mlflow.org/"><img height="42" src="https://cdn.simpleicons.org/mlflow/0194E2" /></a>
  <a href="https://docker.com/"><img height="42" src="https://cdn.simpleicons.org/docker/2496ED" /></a>
  <a href="https://fastapi.tiangolo.com/"><img height="42" src="https://cdn.simpleicons.org/fastapi/009688" /></a>
  <a href="https://streamlit.io/"><img height="42" src="https://cdn.simpleicons.org/streamlit/FF4B4B" /></a>
  
  
</p>

<p align="center">
  <a href="#-architecture">Architecture</a> |
  <a href="#-key-technical-features">Key Features</a> |
  <a href="#-project-structure">Project Structure</a> |
  <a href="#-getting-started">Getting Started</a> | 
  <a href="#-roadmap">Roadmap</a>
</p>


## 🏗 Architecture

The system is designed as a modern Lakehouse architecture, leveraging Hugging Face as a cost-effective Data Lake and MotherDuck as a serverless Data Warehouse.

- Ingestion: Python scripts extract data from the data.gov.gr API, adding metadata and handling schema enforcement.
- Storage: Raw data are stored in Parquet format on Hugging Face (Data Lake). A custom compaction logic merges daily files into monthly files to optimize storage and query performance.
- Transformation: dbt (Data Build Tool) handles the T in ELT, modeling data in MotherDuck, via a medallion architecture:
  - *Bronze*: Through **Python** and *orchestrated* by **Github Actions**, API responses are timestamped with metadata, converted to *Parquet*, and merged into monthly files to create a stable, immutable foundation for all downstream processing, while avoiding the *Small File Problem* and API rate limits of the project's *Data Lake*, i.e., **HuggingFace**.
  - *Silver*: Using **dbt** (also orchestrated by GitHub Actions), the raw data is typecasted, renamed for clarity, and deduplicated based on business logic. This layer creates a clean, consistent, and high-performance foundation inside our Data Warehouse, i.e, **MotherDuck**.
  - *Gold*: Cleaned silver models are joined and aggregated into final mart tables that are optimized specifically for reporting and high-level analytics, which are then served directly to the end-user via a **Streamlit** dashboard.
- Machine Learning: An `HistGradientBoostingRegressor` model predicts road speeds, with experiments tracked via MLflow and data drift monitoring handled by Evidently AI. If drift is detected, a discord notification is sent.
- Deployment: A FastAPI service containerized with Docker serves predictions, while a Streamlit dashboard provides business intelligence.
- Orchestration: GitHub Actions manages the entire lifecycle, from daily ingestion to CI/CD triggers.


## 🛠 Tech Stack

| Category | Tools |
| --- | --- |
| **Data Engineering** | dbt, MotherDuck |
| **MLOps** | Scikit-learn, MLflow, Dagshub, Evidently AI, Discord Webhooks |
| **DevOps / CI/CD** | GitHub Actions, Docker, Pytest |
| **Serving / UI** | FastAPI, Hugging Face Spaces, Streamlit |


## 🌟 Key Technical Features


### 1. Resilience Ingestion

* **Exponential Backoff:** Built-in exponential retry logic using `tenacity` to handle API instability.
* **Atomic Transactions:** Ingests data to a local staging area before performing a bulk upload to Hugging Face, ensuring no partial or corrupted files land in the lake.
* **CI/CD Awareness:** The `daily` command triggers a **Red 🔴 Alert** (Exit Code 1) on missing data, while the `backfill` command is fault-tolerant for historical recovery.

### 2. Robust Data Engineering

* **Small File Problem Mitigation:** Implemented a monthly compaction job that merges daily Parquet files, reducing metadata overhead and improving read speeds.
* **Data Modeling:** Followed a modular dbt structure:
  * **Staging:** Typecasting and deduplication.
  * **Intermediate:** Fact/Dimension modeling with standardized road naming   conventions.
  * **Marts:** Business-ready tables focusing on KPIs, hourly trends, and   sensor health.
  
* **Data Quality:** Built-in flagging system in the transformation layer to   identify dead sensors, ghost readings, and missing values.

### 3. MLOps & Monitoring

* **Feature Engineering:** Custom pipeline within the ML module to process temporal and spatial features for the Gradient Boosting model.
* **Experiment Tracking:** Integrated MLflow (hosted on Dagshub) to log hyperparameters and model versions.
* **Drift Detection:** Weekly **Evidently AI** jobs analyze data drift. If the feature distribution shifts significantly, an automated alert is fired to **Discord** via webhooks.


### 4. Automation & CI/CD

* **Automated Deployment:** GitHub Actions automatically syncs changes to Hugging Face Spaces. If dependencies change, `requirements.txt` for the streamlit dashboard is dynamically updated.
* **Quality Gates:** CI pipeline runs `pytest` on every push to ensure code stability.
* **Scheduled Orchestration:**
  * **Daily:** Ingestion & dbt transformations.
  * **Weekly:** Drift monitoring.
  * **Monthly:** File compaction/maintenance.


### 5. The Compaction Strategy

Hugging Face (and many data lakes) struggles with thousands of tiny files. To solve this, we run a two-phase process:

- **Daily**: A small file is uploaded for yesterday's data (e.g., `2025-02-11.parquet`).
- **Maintenance (Monthly)**: A CRON job downloads all daily files for a previous month, merges them into a single file (e.g., `compact-2025-02.parquet`), and deletes the small originals.


### 6. Observability

This project uses `loguru` for professional-grade logging:

* **Formatted Console Logs:** Color-coded status updates for real-time monitoring.
* **File Rotation:** Logs are rotated every **10 MB** to manage disk space.
* **GitHub Actions Integration:** Full traceback capture allows for rapid debugging of pipeline failures directly from the Actions UI.


## 📂 Project Structure

```text
attica-mobility/
├── .github/workflows/
    ├── ci.yaml                 # Testing, pushing to HF spaces, etc.
    ├── daily_pipeline.yaml     # Daily ingestion and transformation
    ├── drift_monitor.yaml      # Weekly data drift monitoring
│   └── monthly_maintenance.yml # Monthly data lake compacting
├── api/                        # FastAPI
├── dashboard/                  # Streamlit dashboard
├── ingestion/
│   └── ingestion.py            # The EL script
├── transform/                  # dbt loading, transformations and tests
    └── models                  # Models following a medallion architecture
        ├── staging
        ├── intermediate
        └── marts
            └── reporting
├── ml_pipeline/
    ├── feature_engineering.py  # Data loading and feature engineering
    ├── train.py                # Trains a HistGradientBoostingRegressor model
    └── monitor.py              # Data drift monitoring
├── tests/                      # pytest tests
├── logs/                       # Structured, rotated logs
├── .env.example                # Secret template for tokens and usernames
├── config.yaml                 # Hyperparameters, data split rations, etc.
├── pyproject.toml              # Centralized 'uv' dependencies
├── uv.lock                     # Deterministic environment
├── config.yaml                 # Centralized configuration
└── README.md
```

## 🚀 Getting Started

### Prerequisites

* Python 3.12
* [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
* Hugging Face account with a Write Token for a dataset and a spaces repo
* MotherDuck account with a Access Token
* Dagshub account with a Token and a repo
* A discord webhook
### Installation & Setup

1. **Clone & Sync:**
```bash
git clone https://github.com/TsilidisV/attica-traffic.git
cd attica-traffic
uv sync
```


2. **Environment Variables:**
```bash
cp .env.example .env
# Add your tokens, usernames, repos and webhooks to the .env file
```


3. Running the Pipeline

```bash
# Ingest yesterday's data (Standard Daily Run)
uv run --package attica-ingestion python ingestion/ingestion.py ingest-daily

# Ingest a specific date
uv run --package attica-ingestion python ingestion/ingestion.py ingest-daily 2023-04-20

# Historical Backfill
uv run --package attica-ingestion python ingestion/ingestion.py backfill 2020-12-01 2021-12-01

# Run dbt and install packages
uv run --package attica-transform python -c "import dotenv; dotenv.load_dotenv(); import os; os.system('dbt deps --project-dir transform --profiles-dir transform ')"

# Run dbt and build models
uv run --package attica-transform python -c "import dotenv; dotenv.load_dotenv(); import os; os.system('dbt build --project-dir transform --profiles-dir transform --target prod')"

# Train model
uv run --package attica-ml python -m ml_pipeline.train  

# Monitor data drift
uv run --package attica-ml python -m ml_pipeline.monitor  

# Run API
uv run --package attica-api fastapi dev api/main.py
# or
docker build -t my-api-image-test -f api/Dockerfile .
docker run -p 8000:7860 --env-file ./.env my-api-image-test

# Run the streamlit dashboard
uv run --package attica-dashboard streamlit run dashboard/app.py
```

## Challenges & Solutions

- compact logic
- data drift monitoring: model used to train on the full data set, but limiting to the last year improved results. By looking at the evidently report, I realized that a left-shifted distribution meant slower traffic, and deduced that naive retraining wouldn't fix it because of historical data dilution.



## 🗺 Roadmap

* [x] **Phase 1:** Resilient EL Pipeline (Python + GitHub Actions)
* [x] **Phase 2:** Analytics Engineering (dbt + MotherDuck)
* [x] **Phase 3:** Interactive Visualizations (Streamlit)
* [x] **Phase 4:** ML model for speed predictions
* [x] **Phase 5:** Model deployment through an API (FastAPI)
* [x] **Phase 6:** ML model monitoring (Evidently AI)



## 📊 Caching Architecture: The Time-Shifted Key

Our Streamlit dashboard relies on heavy analytical queries from Motherduck. Because Motherduck is updated via a daily batch job (completing around `05:12 UTC`), standard time-to-live (TTL) caching is insufficient. 

Standard TTL expires relative to user traffic, meaning an early morning visitor could accidentally lock stale data into the cache for the next 24 hours.

### How we solve this
We utilize a **Time-Shifted Cache Key** combined with Streamlit's `max_entries=1` parameter.

1. **The Generator:** The `get_daily_cache_key()` function generates a dummy argument passed to all `@st.cache_data` functions.
2. **The Shift:** The function subtracts 6 hours from the current UTC time before extracting the calendar date. 
3. **The Rollover:** This mathematical shift forces the extracted date to change at exactly `06:00 UTC` every day.

### Execution Timeline Example

| Actual UTC Time | Shift Applied (-6h) | Resulting Cache Key | Dashboard State |
| :--- | :--- | :--- | :--- |
| **04:00** | 22:00 (Yesterday) | `2024-11-01` | Serving yesterday's cached data. |
| **05:12** | 23:12 (Yesterday) | `2024-11-01` | *Motherduck ingestion completes.* |
| **05:59** | 23:59 (Yesterday) | `2024-11-01` | Final minute of yesterday's cache. |
| **06:00** | 00:00 (Today) | `2024-11-02` | **Key changes! Cache Invalidated.** |
| **06:01** | 00:01 (Today) | `2024-11-02` | First visitor triggers Motherduck query. |
| **14:00** | 08:00 (Today) | `2024-11-02` | Dashboard serves today's cached data. |

### Memory Management
All data loading decorators are configured with `@st.cache_data(max_entries=1)`. The moment the cache key rolls over at `06:00 UTC`, Streamlit immediately drops the previous day's `pandas.DataFrame` from memory, preventing out-of-memory (OOM) crashes on Streamlit Cloud.


```mermaid
