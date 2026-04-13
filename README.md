# Smart Grid Electricity Theft, Anomaly, and Wastage Detection System

This repository is an end-to-end smart-grid analytics demo built around synthetic Bengaluru smart-meter data. It generates realistic meter readings, trains multiple machine learning models, replays a live simulation through a FastAPI backend, and visualizes the system state in a browser dashboard.

The project is designed for:

- academic projects and demonstrations
- electricity theft detection prototypes
- anomaly and wastage monitoring demos
- dashboard-driven analytics presentations
- end-to-end ML systems coursework

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Core Features](#2-core-features)
- [3. Repository Layout](#3-repository-layout)
- [4. End-to-End Flow](#4-end-to-end-flow)
- [5. Data Generation](#5-data-generation)
- [6. Datasets and Key Columns](#6-datasets-and-key-columns)
- [7. Modeling and Analytics Modules](#7-modeling-and-analytics-modules)
- [8. FastAPI Runtime](#8-fastapi-runtime)
- [9. Dashboard](#9-dashboard)
- [10. Generated Files and Artifacts](#10-generated-files-and-artifacts)
- [11. Installation](#11-installation)
- [12. How to Run](#12-how-to-run)
- [13. Docker Support](#13-docker-support)
- [14. API Endpoints](#14-api-endpoints)
- [15. Configuration](#15-configuration)
- [16. Testing](#16-testing)
- [17. Recent Runtime Notes](#17-recent-runtime-notes)
- [18. Troubleshooting](#18-troubleshooting)
- [19. Short Presentation Summary](#19-short-presentation-summary)

## 1. Project Overview

At a high level, the system simulates hourly smart-meter readings across multiple Bengaluru areas, trains anomaly/theft/forecasting models from that data, then replays a generated live stream so the backend and dashboard behave like a running monitoring platform.

The project answers questions like:

- Which meters currently look suspicious for electricity theft?
- Which readings are unusual even if theft is not certain?
- Which meters appear inefficient or wasteful?
- How is demand expected to change in the next hour, day, and week?
- Which areas are carrying higher operational risk?
- Is recent data drifting away from the historical baseline?

## 2. Core Features

- Synthetic smart-meter generation with geographic, weather, and usage-profile context
- Electricity theft simulation using multiple theft patterns
- Unsupervised anomaly detection
- Supervised theft classification with blended probabilities
- Risk scoring and risk-level summaries
- Energy efficiency and wastage estimation
- Pole-level electricity tamper detection and illegal connection monitoring
- LSTM and Transformer-based demand forecasting
- Consumer segmentation for usage-pattern analysis
- Drift monitoring between historical and recent windows
- Explainable predictions for suspicious meters
- Optional alert delivery via email, Slack, and Telegram
- FastAPI REST API plus live WebSocket feed
- Multi-section dashboard with charts, tables, and downloadable artifacts

## 3. Repository Layout

Important folders and files:

- `api/`
  FastAPI application and live runtime simulation.

- `src/`
  Core logic for generation, preprocessing, model training, scoring, reporting, forecasting, and analytics.

- `dashboard/`
  Static frontend with reusable components, section pages, CSS, and the generated heatmap view.

- `data/raw/`
  Placeholder for raw inputs if you later want to extend the project beyond synthetic generation.

- `data/processed/`
  Generated processed artifacts including:
  - `smart_meter_sample.csv`
  - `live_simulation.csv`
  - `meter_catalog.csv`
  - `generation_summary.json`

- `dataset/`
  Main synthetic dataset output:
  - `smart_meter_data.csv`

- `models/`
  Trained model artifacts and metadata.

- `database/`
  SQLite snapshots produced by the runtime.

- `reports/`
  PDF and JSON report artifacts.

- `maps/`
  Generated Folium heatmap output.

- `sample_outputs/`
  Reference request/response payloads exported from the pipeline.

- `tests/`
  Pytest coverage for APIs, data generation, analytics, forecasting, and theft logic.

- `run_project.py`
  Main command-line bootstrap script.

- `run.md`
  Practical PowerShell run guide for this repository.

- `docker-compose.yml`
  Two-service setup for the API and static dashboard.

## 4. End-to-End Flow

The real code path is:

1. `run_project.py` reads generation settings from `utils/helpers.py`.
2. `src/data_generator.py` creates the full dataset, the processed sample, the meter catalog, and the live replay dataset.
3. `src/train_models.py` trains anomaly, theft, and forecasting artifacts.
4. `api/main.py` bootstraps runtime state, loads datasets and models, and begins a timestamp-by-timestamp simulation loop.
5. Each live tick is classified for anomaly/theft, enriched with risk and efficiency metrics, written into SQLite tables, and exposed through REST and WebSocket endpoints.
6. The dashboard polls the REST endpoints every few seconds and can also consume the live WebSocket snapshot payload.

## 5. Data Generation

The synthetic data pipeline is implemented in [src/data_generator.py](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/src/data_generator.py).

### 5.1 Geographic Coverage

Meters are distributed across Bengaluru areas defined in `utils/helpers.py`:

- Whitefield
- Electronic City
- Indiranagar
- Koramangala
- Marathahalli
- Yelahanka
- BTM Layout
- Jayanagar
- Malleshwaram
- Rajajinagar
- Hebbal
- Bellandur
- HSR Layout
- Banashankari
- Peenya Industrial Area

Coordinates are jittered around each area center so meters from the same area still appear at slightly different positions on the map.

### 5.2 Usage Profiles

Every meter is assigned a usage profile:

- `residential`
- `night_usage`
- `industrial`
- `ac_heavy`
- `commercial`

These profiles drive the base load curve, daily behavior, and weather sensitivity.

### 5.3 Weather Generation

Weather is handled in [src/weather_api.py](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/src/weather_api.py).

The service can:

- fetch live weather from OpenWeather when `OPENWEATHER_API_KEY` is configured
- fall back to synthetic Bengaluru hourly weather when no live API key is available

Generated weather includes:

- temperature
- humidity
- rainfall
- wind speed
- weather condition

### 5.4 Theft Scenarios

The project simulates several theft patterns:

- `meter_bypass`
- `abnormal_spikes`
- `constant_low_consumption`
- `illegal_connection`
- `tampered_meter`

These affect reported consumption, actual power draw, voltage, power factor, and downstream anomaly/theft behavior.

### 5.5 Generation Defaults

Defaults come from `generation_config()` in [utils/helpers.py](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/utils/helpers.py).

Default mode:

- `num_meters = 500`
- `days = 60`
- `chunk_size = 45`
- `sample_rows = 45000`
- `simulation_days = 10`
- `simulation_meter_limit = 425`
- `seed = 42`

Full-scale mode:

- `num_meters = 1000`
- `days = 365`
- `chunk_size = 100`
- `sample_rows = 120000`
- `simulation_days = 14`
- `simulation_meter_limit = 80`
- `seed = 42`

### 5.6 Stable Live Theft Generation

The live replay dataset is intentionally different from the main training dataset.

For the generated live stream:

- a deterministic subset of live meters is selected as theft candidates
- those theft meters keep the same `meter_id`, `area`, and location through the replay window
- non-selected live meters are prevented from randomly becoming theft during that replay

This makes the dashboard easier to follow during demos because the theft location does not jump to a different place every few seconds.

## 6. Datasets and Key Columns

### 6.1 Main Generated Files

The data pipeline produces:

- `dataset/smart_meter_data.csv`
  Full generated dataset.

- `data/processed/smart_meter_sample.csv`
  Downsampled training-oriented sample.

- `data/processed/live_simulation.csv`
  Dataset used by the FastAPI runtime for live replay.

- `data/processed/meter_catalog.csv`
  Static meter metadata including meter ID, area, latitude, longitude, and usage profile.

- `data/processed/pole_catalog.csv`
  Pole and transformer hierarchy linking each pole to its connected meters.

- `data/processed/generation_summary.json`
  Summary of generation configuration and live theft meter IDs.

### 6.2 Important Raw Columns

The core generated schema includes:

- `meter_id`
- `timestamp`
- `region`
- `area`
- `transformer_id`
- `pole_id`
- `connected_meters`
- `latitude`
- `longitude`
- `voltage`
- `current`
- `power`
- `consumption_kwh`
- `power_factor`
- `temperature`
- `humidity`
- `rainfall`
- `wind_speed`
- `weather_condition`
- `is_theft`
- `expected_consumption_kwh`
- `wastage_score`
- `usage_profile`
- `theft_type`
- `seeded_theft_probability`

### 6.3 Feature Engineering

Feature engineering is handled in `src/feature_engineering.py`.

Base numeric features configured in `utils/helpers.py` include:

- `voltage`
- `current`
- `power`
- `consumption_kwh`
- `power_factor`
- `temperature`
- `humidity`
- `rainfall`
- `wind_speed`
- `expected_consumption_kwh`
- `hour_of_day`
- `day_of_week`
- `rolling_average_consumption`
- `consumption_variance`
- `peak_usage_ratio`
- `night_usage_ratio`
- `weather_consumption_ratio`
- `power_factor_loss`
- `voltage_irregularity`
- `current_power_gap`
- `wastage_score`

Categorical columns:

- `region`
- `area`
- `weather_condition`
- `usage_profile`

### 6.4 Runtime-Derived Columns

After detection and scoring, the runtime adds fields such as:

- `anomaly_score`
- `is_anomaly`
- `random_forest_probability`
- `xgboost_probability`
- `theft_probability`
- `status`
- `risk_score`
- `risk_level`
- `risk_summary`
- `efficiency_score`
- `estimated_losses_kwh`
- `wastage_flag`

## 7. Modeling and Analytics Modules

### 7.1 Anomaly Detection

Files:

- `src/detect_anomaly.py`
- `src/train_models.py`

Model:

- Isolation Forest

Outputs:

- `anomaly_score`
- `is_anomaly`

### 7.2 Theft Detection

Files:

- `src/theft_detector.py`
- `src/train_models.py`

Models:

- Random Forest
- XGBoost, with `HistGradientBoostingClassifier` fallback when needed

Theft probability is calibrated using:

- model probabilities
- seeded theft probability from generation
- anomaly score
- wastage score

Outputs:

- `random_forest_probability`
- `xgboost_probability`
- `theft_probability`
- `status`

### 7.3 Risk Scoring

File:

- `src/risk_scoring.py`

Purpose:

- blend model outputs and electrical heuristics into a single score
- group meters into `Low`, `Medium`, `High`, and `Critical`

### 7.4 Energy Efficiency

File:

- `src/energy_efficiency.py`

Purpose:

- estimate low-efficiency behavior
- flag wastage-sensitive meters
- estimate losses in kWh

### 7.4 Pole Monitoring and Tamper Detection

Files:

- `src/pole_monitoring.py`
- `src/pole_tamper_detector.py`

Purpose:

- simulate pole-level supply from meter-side load, technical losses, and hidden unmetered load
- compare supplied energy against the sum of connected meter usage
- detect pole imbalance, abnormal load spikes, and possible direct tapping from the pole
- produce pole-level tamper probabilities and alertable events

### 7.5 Demand Forecasting

Files:

- `src/demand_forecasting.py`
- `src/transformer_forecasting.py`

Models:

- LSTM forecaster
- Transformer forecaster

Outputs:

- `next_hour`
- `next_day`
- `next_week`
- forecast `series`

Fallback logic exists so the API can still operate when deep-learning forecasting artifacts are unavailable.

### 7.6 Consumer Segmentation

File:

- `src/consumer_segmentation.py`

Methods used:

- KMeans
- DBSCAN

This module groups meters into behavior-driven segments for dashboard views and suspicious-cluster summaries.

### 7.7 Explainability

File:

- `src/explainable_ai.py`

Purpose:

- generate readable reasons for suspicious theft predictions
- support theft investigation tables and API responses

### 7.8 Data Drift Monitoring

File:

- `src/data_drift_monitor.py`

Purpose:

- compare recent live predictions with the historical baseline
- detect missing-value changes, concept drift, and theft-rate shifts

### 7.9 Reporting and Exports

Files:

- `src/report_generator.py`
- `src/sample_outputs.py`
- `src/spatial_analysis.py`

Artifacts include:

- PDF daily report
- JSON drift report
- Folium theft heatmap
- sample request/response payloads

### 7.10 Hyperparameter Optimization

File:

- `src/model_optimizer.py`

Tool:

- Optuna

Used to tune model settings before training when explicitly enabled from the CLI.

## 8. FastAPI Runtime

The backend lives in [api/main.py](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/api/main.py).

### 8.1 Startup Behavior

On startup the runtime:

1. ensures project directories exist
2. regenerates datasets if required artifacts are missing or outdated
3. retrains models if model files are missing
4. loads historical and live data
5. prepares forecast, drift, and segmentation caches
6. advances one tick immediately so the dashboard has data on first load

### 8.2 Live Tick Processing

On each tick the runtime:

1. selects the current timestamp slice from `live_simulation.csv`
2. classifies anomaly and theft behavior
3. ensures a visible theft candidate exists when needed for demo visibility
4. maintains sticky theft behavior for the first theft meter in the live view
5. limits theft alert volume for readability
6. computes risk and efficiency outputs
7. updates recent buffers and SQLite tables
8. refreshes forecast, clustering, drift, report, and heatmap artifacts
9. broadcasts a combined payload to WebSocket clients

### 8.3 SQLite Runtime Tables

The backend writes snapshots into `database/meter_data.db`, including tables such as:

- `meter_readings`
- `live_predictions`
- `recent_predictions`
- `risk_scores`
- `consumer_segments`
- `efficiency_metrics`
- `drift_reports`
- `forecast_snapshots`
- `pole_energy_data`
- `pole_tamper_events`

### 8.4 Alert Integrations

Alert delivery logic is implemented in [src/alert_engine.py](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/src/alert_engine.py).

Supported outbound providers:

- SMTP email
- Slack webhook
- Telegram bot API

Alerts are only dispatched when `SMARTGRID_ENABLE_ALERTS=1`.

Pole tamper alerts are also generated when a pole shows a sustained energy mismatch or suspected illegal connection.

## 9. Dashboard

The frontend is a static dashboard under `dashboard/`.

Primary files:

- `dashboard/index.html`
- `dashboard/main.js`
- `dashboard/style.css`

Reusable JS helpers and feature components:

- `dashboard/components/core.js`
- `dashboard/components/charts.js`
- `dashboard/components/alerts.js`
- `dashboard/components/forecast.js`
- `dashboard/components/heatmap.js`
- `dashboard/components/segmentation.js`

### 9.1 Sections

Each HTML file under `dashboard/sections/` renders one analytics surface:

- `overview.html`
  High-level KPIs, recent live demand, area consumption, and operator insights.

- `live_monitoring.html`
  Realtime load, recent demand traces, top meters, and latest reading table.

- `theft_detection.html`
  Theft KPIs, scatter/risk views, and sortable investigation queue.

- `anomaly_detection.html`
  Current anomalies, scores, and suspicious-case charts.

- `demand_forecast.html`
  LSTM vs Transformer forecasting outputs and comparison charts.

- `energy_efficiency.html`
  Low-efficiency metrics, estimated losses, and wastage-focused analytics.

- `consumer_segmentation.html`
  Segment mix, cluster summaries, and cluster member views.

- `pole_monitoring.html`
  Pole supply vs meter balance, suspicious poles, mismatch charts, and pole tamper alerts.

- `heatmap.html`
  Theft hotspot map integration and area-based map summaries.

- `weather_impact.html`
  Weather-band analytics and consumption-vs-weather visuals.

- `alerts.html`
  Consolidated alert panels and severity-oriented summaries.

- `reports.html`
  Download links, report KPIs, and sample output references.

### 9.2 Refresh Pattern

Most dashboard sections refresh every 3 seconds by calling the API and can also react to the `/ws/live` snapshot payload. The frontend and backend refresh intervals are intentionally short so the project feels live during demos.

## 10. Generated Files and Artifacts

Common generated outputs:

- `dataset/smart_meter_data.csv`
- `data/processed/smart_meter_sample.csv`
- `data/processed/live_simulation.csv`
- `data/processed/meter_catalog.csv`
- `data/processed/pole_catalog.csv`
- `data/processed/generation_summary.json`
- `models/isolation_forest.pkl`
- `models/random_forest.pkl`
- `models/xgboost_model.pkl`
- `models/lstm_model.h5`
- `models/transformer_forecaster.pt`
- `models/model_metadata.json`
- `models/demand_metadata.json`
- `models/transformer_metadata.json`
- `models/optimizer_best_params.json`
- `database/meter_data.db`
- `reports/daily_energy_report.pdf`
- `reports/drift_report.json`
- `maps/theft_heatmap.html`
- `dashboard/theft_heatmap.html`
- `sample_outputs/predict_request.json`
- `sample_outputs/predict_response.json`
- `sample_outputs/theft_response.json`
- `sample_outputs/overview_response.json`
- `sample_outputs/manifest.json`

## 11. Installation

This repository is currently set up primarily for Windows PowerShell usage, and [run.md](/c:/Users/vishn/Desktop/College/SEMISTER/CSE%206th%20SEM/Data%20Science/Project%201/electricity_theft_and_anomaly_detection/run.md) reflects that environment.

### 11.1 Python

Use Python 3.11 when possible.

Example interpreter path used in this project:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
```

### 11.2 Create `.env`

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

### 11.3 Install Dependencies

Main dependencies include:

- FastAPI
- Uvicorn
- pandas
- NumPy
- scikit-learn
- XGBoost
- TensorFlow
- matplotlib
- seaborn
- Plotly
- folium
- geopandas
- SHAP
- requests
- websockets
- pydantic

Install:

```powershell
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
```

Optional advanced dependencies:

```powershell
& $PYTHON -m pip install -r requirements-advanced.txt
```

## 12. How to Run

### 12.1 Quick Start

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
& $PYTHON run_project.py
& $PYTHON -m pytest
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Then in a second terminal:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection\dashboard"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
& $PYTHON -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080/index.html
```

### 12.2 Bootstrap Data and Models

```powershell
& $PYTHON run_project.py
```

This command:

- generates synthetic smart-meter data
- writes the live replay dataset
- trains anomaly, theft, and forecasting models
- exports sample outputs
- generates the heatmap
- generates the PDF report

### 12.3 Generate Data Only

```powershell
& $PYTHON run_project.py --skip-training
```

### 12.4 Start the API

```powershell
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### 12.5 Demo Mode

To reduce periodic report generation during a presentation:

```powershell
$env:SMARTGRID_DEMO_MODE = "1"
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 12.6 Frontend

```powershell
Set-Location dashboard
& $PYTHON -m http.server 8080
```

### 12.7 Useful CLI Options

`run_project.py` supports:

- `--full-scale`
  Generate a 1000-meter, one-year dataset.

- `--num-meters`
  Override meter count.

- `--days`
  Override simulated days.

- `--skip-training`
  Generate data only.

- `--forecast-epochs`
  Set LSTM training epochs.

- `--skip-sample-export`
  Skip reference payload export.

- `--skip-report`
  Skip PDF report generation.

- `--start-api`
  Start FastAPI immediately after bootstrapping.

- `--optimize-models`
  Run Optuna optimization before training.

- `--optimization-trials`
  Set Optuna trial count.

## 13. Docker Support

This repository includes both a `Dockerfile` and `docker-compose.yml`.

### 13.1 Dockerfile

The API container:

- uses `python:3.11`
- installs `requirements.txt`
- exposes port `8000`
- starts `uvicorn api.main:app --host 0.0.0.0 --port 8000`

### 13.2 Docker Compose

The compose setup defines:

- `api`
  FastAPI backend with persisted volumes for datasets, models, reports, maps, and samples.

- `dashboard`
  Nginx static server exposing the dashboard on port `8080`.

Ports:

- API: `8000`
- Dashboard: `8080`

## 14. API Endpoints

### 14.1 Main JSON Endpoints

- `GET /`
- `GET /health`
- `GET /overview`
- `GET /meters`
- `GET /anomalies`
- `GET /theft`
- `GET /weather-impact`
- `GET /forecast`
- `GET /risk-scores`
- `GET /consumer-segments`
- `GET /efficiency`
- `GET /api/pole-status`
- `GET /api/pole-tamper-alerts`
- `GET /api/pole-energy-balance`
- `GET /drift-report`
- `POST /predict`

### 14.2 Artifact Endpoints

- `GET /artifacts/daily-report`
- `GET /artifacts/drift-report`
- `GET /artifacts/sample-overview`
- `GET /artifacts/heatmap`

### 14.3 WebSocket Endpoint

- `WS /ws/live`

### 14.4 `/predict` Input Shape

The prediction endpoint accepts one reading or a list of readings with fields like:

- `meter_id`
- `timestamp` optional
- `region`
- `area`
- `latitude`
- `longitude`
- `voltage`
- `current`
- `power`
- `consumption_kwh`
- `power_factor`
- `temperature`
- `humidity`
- `rainfall`
- `wind_speed`
- `weather_condition`
- `expected_consumption_kwh` optional
- `wastage_score` optional
- `usage_profile`

The response includes:

- `status`
- `theft_probability`
- `anomaly_score`
- `risk_score`
- `risk_level`
- `efficiency_score`
- explanation details

## 15. Configuration

### 15.1 Main Runtime Variables

- `SMARTGRID_FULL_SCALE`
  Use full generation settings when set to `1`.

- `SMARTGRID_UPDATE_INTERVAL`
  Tick interval in seconds for the live runtime.

- `SMARTGRID_DEMO_MODE`
  Demo-friendly runtime mode with reduced periodic reporting.

- `SMARTGRID_ENABLE_PERIODIC_REPORTS`
  Enable report generation during the runtime loop.

- `SMARTGRID_ENABLE_ALERTS`
  Enable outbound alert dispatch.

- `OPENWEATHER_API_KEY`
  Optional API key for live weather instead of synthetic fallback weather.

### 15.2 Alert Variables

- `SMARTGRID_SMTP_HOST`
- `SMARTGRID_SMTP_PORT`
- `SMARTGRID_SMTP_USER`
- `SMARTGRID_SMTP_PASSWORD`
- `SMARTGRID_ALERT_EMAIL_FROM`
- `SMARTGRID_ALERT_EMAIL_TO`
- `SMARTGRID_SLACK_WEBHOOK`
- `SMARTGRID_TELEGRAM_BOT_TOKEN`
- `SMARTGRID_TELEGRAM_CHAT_ID`

## 16. Testing

Pytest coverage is included for the major layers of the system.

Current test modules:

- `tests/test_api.py`
- `tests/test_data_pipeline.py`
- `tests/test_forecasting_and_exports.py`
- `tests/test_advanced_analytics.py`
- `tests/test_theft_detector.py`

Covered behavior includes:

- health and payload responses
- theft and anomaly counts
- sticky theft behavior in the runtime
- stable live theft generation behavior
- feature engineering outputs
- pole hierarchy generation and pole tamper payloads
- risk scoring and efficiency metrics
- consumer clustering
- forecast fallbacks and Transformer pipeline behavior
- sample export generation
- theft-probability calibration
- WebSocket disconnect handling

Run all tests:

```powershell
& $PYTHON -m pytest
```

## 17. Recent Runtime Notes

### 17.1 Stable Live Theft Simulation

The generated live stream now keeps theft attached to a deterministic set of meters so the theft place shown in the dashboard stays consistent during replay.

### 17.2 Sticky Theft Presentation Behavior

The runtime still preserves the first visible theft meter in the current live view so the theft table and related panels remain stable and readable during demos.

### 17.3 Strong Theft Probability Calibration

Strong theft cases are intentionally pushed into clearer high-confidence ranges for better live interpretation in the dashboard and alerts.

### 17.4 Safe WebSocket Disconnect Handling

Fast reconnects and tab closes are handled cleanly so reloading the dashboard does not create noisy server tracebacks.

## 18. Troubleshooting

### 18.1 TensorFlow or PyTorch Warnings

Warnings about CPU instructions, oneDNN, or missing GPU support are usually informational. They do not necessarily mean the project failed.

### 18.2 Missing Advanced Libraries

Several components include fallback behavior:

- boosting fallback when XGBoost is unavailable
- forecast fallback when deep-learning artifacts cannot be loaded
- drift fallback when Evidently is unavailable
- explainability fallback when SHAP is unavailable
- synthetic weather fallback when OpenWeather is not configured

### 18.3 Dashboard Shows No Data

Check:

- the API is running on `127.0.0.1:8000`
- the frontend static server is running on `8080`
- the dashboard API base is pointing to the backend
- datasets and models were generated with `run_project.py`

### 18.4 Theft Location Still Looks Old

If you changed generator logic and the dashboard still shows old behavior, regenerate artifacts:

```powershell
& $PYTHON run_project.py
```

The runtime also checks `generation_summary.json` so older live datasets are automatically refreshed when needed.

### 18.5 Alert Delivery Not Working

Make sure:

- `SMARTGRID_ENABLE_ALERTS=1`
- provider-specific environment variables are set
- the machine has outbound network access for Slack/Telegram or SMTP

## 19. Short Presentation Summary

This project simulates a Bengaluru smart-grid monitoring platform. It generates synthetic smart-meter data with weather, theft, anomaly, and wastage behavior; trains anomaly, theft, and forecasting models; replays the data as a live FastAPI stream; and visualizes the results in a dashboard. The system highlights suspected electricity theft, anomalies, energy inefficiency, demand forecasts, risk by area, weather impact, segmentation patterns, and drift in recent data.

## Pole Monitoring Architecture

The pole extension adds a hierarchy of `transformer -> pole -> meter` without replacing the existing meter-centric flow. During generation, each meter is assigned a `transformer_id`, a `pole_id`, and a `connected_meters` mapping. During live runtime, the backend aggregates current meter readings into pole-level supply snapshots, estimates technical losses, and injects simulated hidden load for direct pole tapping and abnormal pole spikes.

Pole tampering is identified from the energy balance formula:

`Energy supplied to pole - (sum of meter consumption + technical losses)`

When that mismatch grows beyond the configured threshold, or when the gap and load pattern diverge from the pole's historical behavior, the pole is marked suspicious. The detector blends rule-based imbalance checks with an optional Isolation Forest score so the system can flag missing meter load, abnormal pole load growth, and likely illegal pole connections while keeping the original meter detection pipeline intact.
