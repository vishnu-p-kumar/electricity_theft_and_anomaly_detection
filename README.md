# Smart Grid Electricity Theft, Anomaly, and Wastage Detection System

This project simulates a Bengaluru smart-grid deployment, generates synthetic smart-meter data, trains multiple machine learning models, serves a FastAPI backend, and presents the results through a live browser dashboard.

It is built as a complete end-to-end demonstration system rather than a single model script. The codebase covers:

- synthetic electricity-consumption data generation
- electricity theft detection
- anomaly detection
- energy wastage and efficiency analysis
- short-horizon demand forecasting
- consumer segmentation
- weather-impact analysis
- drift monitoring
- report and artifact generation
- live API streaming for a dashboard

## Table of Contents

- [1. What This Project Does](#1-what-this-project-does)
- [2. System Architecture](#2-system-architecture)
- [3. Repository Structure](#3-repository-structure)
- [4. End-to-End Workflow](#4-end-to-end-workflow)
- [5. Data Generation](#5-data-generation)
- [6. Dataset Columns and Features](#6-dataset-columns-and-features)
- [7. Models and Analytics Modules](#7-models-and-analytics-modules)
- [8. Backend Runtime and API](#8-backend-runtime-and-api)
- [9. Frontend Dashboard](#9-frontend-dashboard)
- [10. Generated Outputs and Artifacts](#10-generated-outputs-and-artifacts)
- [11. Installation and Setup](#11-installation-and-setup)
- [12. How to Run the Project](#12-how-to-run-the-project)
- [13. Command-Line Options](#13-command-line-options)
- [14. Environment Variables](#14-environment-variables)
- [15. Testing](#15-testing)
- [16. Recent Runtime Behavior Notes](#16-recent-runtime-behavior-notes)
- [17. Troubleshooting](#17-troubleshooting)
- [18. Presentation Summary](#18-presentation-summary)

## 1. What This Project Does

At a high level, the system creates synthetic smart-meter readings for multiple Bengaluru areas, learns patterns from those readings, and then replays the generated data as if it were a live feed.

The project is meant to answer questions such as:

- which meters currently look suspicious for electricity theft
- which readings are statistically anomalous even if theft is uncertain
- where energy wastage is likely happening
- how demand is expected to evolve over the next hour, day, and week
- which areas and usage groups appear riskier than others
- whether the incoming live data distribution is drifting away from the training baseline

The project is especially useful for:

- academic demonstrations
- machine learning project presentations
- smart-grid monitoring prototypes
- end-to-end MLOps-style coursework
- dashboard-based analytics demos

## 2. System Architecture

The repository has four main layers:

1. Data generation  
   Synthetic meter data is created with geography, weather, usage profiles, theft scenarios, and power-quality variations.

2. Model training and analytics preparation  
   The project trains anomaly, theft, and forecasting models and writes metadata and model artifacts into `models/`.

3. FastAPI runtime simulation  
   The API loads historical data, replays a generated live dataset one timestamp at a time, computes predictions and metrics, and exposes them through REST endpoints and a WebSocket.

4. Dashboard visualization  
   A static frontend consumes the API and renders KPIs, charts, tables, heatmaps, alerts, and downloadable artifacts.

## 3. Repository Structure

Top-level folders and files:

- `api/`  
  FastAPI application and live runtime simulation.

- `src/`  
  Core business logic for generation, preprocessing, training, scoring, forecasting, reporting, drift checks, and explainability.

- `dashboard/`  
  Static frontend with HTML sections, JavaScript components, and CSS.

- `dataset/`  
  Main generated dataset output.

- `data/processed/`  
  Processed training sample, live simulation slice, meter catalog, and generation summary.

- `models/`  
  Trained models and metadata files.

- `database/`  
  SQLite database used by the runtime for current snapshots and derived tables.

- `reports/`  
  PDF and JSON analytics artifacts.

- `maps/`  
  Generated heatmap output.

- `sample_outputs/`  
  Example API request and response payloads for reference.

- `tests/`  
  Pytest coverage for API behavior, data pipeline, forecasting fallbacks, analytics, and theft-probability logic.

- `run_project.py`  
  Main CLI entry point that generates data, trains models, and optionally starts the API.

- `run.md`  
  Practical PowerShell run guide for this project.

## 4. End-to-End Workflow

The real code flow is:

1. `run_project.py` loads generation settings from `utils/helpers.py`.
2. `src/data_generator.py` creates:
   - `dataset/smart_meter_data.csv`
   - `data/processed/smart_meter_sample.csv`
   - `data/processed/live_simulation.csv`
   - `data/processed/meter_catalog.csv`
3. `src/preprocess.py` and `src/feature_engineering.py` prepare model-ready data.
4. `src/train_models.py` trains:
   - Isolation Forest
   - Random Forest
   - XGBoost or HistGradientBoosting fallback
   - LSTM forecaster
   - Transformer forecaster
5. `api/main.py` bootstraps the project state on startup.
6. The runtime replays one timestamp from the live simulation dataset at each interval.
7. Each tick is scored for theft, anomaly, risk, efficiency, drift, segmentation, and forecast context.
8. The API exposes the current state through endpoints like `/overview`, `/theft`, and `/forecast`.
9. The frontend dashboard displays the current results and listens to `/ws/live` for live updates.

## 5. Data Generation

The synthetic data pipeline is implemented in `src/data_generator.py`.

### 5.1 Geographic coverage

Meters are distributed across Bengaluru areas defined in `utils/helpers.py`, including:

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

Coordinates are jittered slightly around area centers so the map does not collapse multiple meters into a single point.

### 5.2 Usage profiles

Each meter is assigned a usage profile such as:

- `residential`
- `night_usage`
- `industrial`
- `ac_heavy`
- `commercial`

These profiles affect base load curves, hourly demand patterns, and weather sensitivity.

### 5.3 Weather integration

`src/weather_api.py` provides weather inputs used during generation and runtime:

- temperature
- humidity
- rainfall
- wind speed
- weather condition

The system primarily uses synthetic hourly weather, but the weather service is structured so live weather support can be extended.

### 5.4 Theft scenarios

The project simulates multiple electricity theft patterns:

- `meter_bypass`
- `abnormal_spikes`
- `constant_low_consumption`
- `illegal_connection`
- `tampered_meter`

These scenarios affect:

- reported consumption
- actual load
- voltage behavior
- power factor
- anomaly characteristics

### 5.5 Generation settings

Generation defaults come from `generation_config()` in `utils/helpers.py`.

Default mode:

- `num_meters = 180`
- `days = 60`
- `chunk_size = 45`
- `sample_rows = 45000`
- `simulation_days = 10`
- `simulation_meter_limit = 120`
- `seed = 42`

Full-scale mode:

- `num_meters = 1000`
- `days = 365`
- `chunk_size = 100`
- `sample_rows = 120000`
- `simulation_days = 14`
- `simulation_meter_limit = 80`
- `seed = 42`

## 6. Dataset Columns and Features

The generated data is centered around timestamped smart-meter readings.

### 6.1 Important raw columns

Main columns that appear across the pipeline:

- `meter_id`
- `timestamp`
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
- `expected_consumption_kwh`
- `wastage_score`
- `usage_profile`
- `is_theft`
- `theft_type`
- `seeded_theft_probability`

### 6.2 Engineered features

The base feature set configured in `utils/helpers.py` includes:

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

Categorical columns encoded into the feature matrix:

- `region`
- `area`
- `weather_condition`
- `usage_profile`

### 6.3 Runtime-derived columns

Later stages of the runtime add higher-level outputs such as:

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

## 7. Models and Analytics Modules

This project uses several specialized modules because theft detection is only one part of the overall monitoring workflow.

### 7.1 Anomaly detection

Files:

- `src/train_models.py`
- `src/detect_anomaly.py`

Model:

- Isolation Forest

Purpose:

- identify unusual electrical behavior without needing only labeled theft examples

Outputs:

- `anomaly_score`
- `is_anomaly`

### 7.2 Theft classification

Files:

- `src/train_models.py`
- `src/theft_detector.py`

Models:

- Random Forest
- XGBoost, with `HistGradientBoostingClassifier` fallback when needed

Purpose:

- estimate the probability that a meter event is suspicious for electricity theft

Runtime behavior:

- the model blend is calibrated into `theft_probability`
- theft alerts are now intentionally pushed into the `0.9+` range for clearer live interpretation

Outputs:

- `random_forest_probability`
- `xgboost_probability`
- `theft_probability`
- `status`

### 7.3 Risk scoring

File:

- `src/risk_scoring.py`

This is not a separate ML model, but it is a key decision layer. It blends:

- anomaly intensity
- theft probability
- voltage irregularity
- night usage behavior

Outputs:

- `risk_score`
- `risk_level`
- `risk_summary`

### 7.4 Energy efficiency analytics

File:

- `src/energy_efficiency.py`

Purpose:

- estimate low-efficiency behavior and losses

Outputs:

- `efficiency_score`
- `estimated_losses_kwh`
- `wastage_flag`

### 7.5 Demand forecasting

Files:

- `src/demand_forecasting.py`
- `src/transformer_forecasting.py`

Models:

- LSTM forecaster
- Transformer forecaster

Purpose:

- forecast short and medium horizon electricity demand

Outputs:

- `next_hour`
- `next_day`
- `next_week`
- future demand `series`

Fallback behavior:

- if TensorFlow or PyTorch forecasting artifacts are unavailable, baseline forecast logic is used so the API can still run

### 7.6 Consumer segmentation

File:

- `src/consumer_segmentation.py`

Methods:

- KMeans
- DBSCAN

Purpose:

- group consumers by usage pattern
- isolate suspicious or outlier clusters

### 7.7 Explainability

File:

- `src/explainable_ai.py`

Purpose:

- explain suspicious predictions for theft and alert views

Primary path:

- SHAP when available

Fallback path:

- model feature-importance style explanation

### 7.8 Drift monitoring

File:

- `src/data_drift_monitor.py`

Purpose:

- monitor whether recent live data differs from the baseline training distribution

Primary path:

- Evidently-based report generation

Fallback path:

- simple numeric and rate-shift checks

### 7.9 Hyperparameter optimization

File:

- `src/model_optimizer.py`

Tool:

- Optuna

Purpose:

- improve Isolation Forest, Random Forest, and boosting hyperparameters before training

## 8. Backend Runtime and API

The backend is implemented in `api/main.py`.

### 8.1 Startup behavior

When the API starts, it:

1. ensures project folders exist
2. generates datasets if they are missing
3. trains models if artifacts are missing
4. loads historical and live simulation frames
5. creates a forecast cache
6. advances one initial tick so the dashboard has data immediately

### 8.2 Live simulation loop

The runtime advances through the generated live dataset using a timestamp cursor.

At each tick, the backend:

1. selects the current timestamp slice from `live_simulation.csv`
2. classifies meter events for anomaly and theft
3. ensures at least one visible theft candidate for demo visibility when needed
4. keeps the first detected theft meter sticky so the main theft location stays consistent across live refreshes
5. computes risk and efficiency metrics
6. updates recent buffers for overview and drift logic
7. refreshes forecasting, segmentation, heatmap, report, and SQLite snapshots
8. broadcasts a combined live message over `/ws/live`

### 8.3 API endpoints

Main JSON endpoints:

- `/`
- `/health`
- `/overview`
- `/meters`
- `/anomalies`
- `/theft`
- `/weather-impact`
- `/forecast`
- `/risk-scores`
- `/consumer-segments`
- `/efficiency`
- `/drift-report`
- `/predict`

Artifact endpoints:

- `/artifacts/daily-report`
- `/artifacts/drift-report`
- `/artifacts/sample-overview`
- `/artifacts/heatmap`

Live endpoint:

- `/ws/live`

### 8.4 Predict endpoint input

`/predict` accepts one or more meter readings with fields such as:

- `meter_id`
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

And it returns:

- theft status
- theft probability
- anomaly score
- risk score
- risk level
- efficiency score
- explanation reason

## 9. Frontend Dashboard

The dashboard is a static frontend under `dashboard/`.

Main entry files:

- `dashboard/index.html`
- `dashboard/main.js`
- `dashboard/style.css`

The app is section-based. Each page under `dashboard/sections/` focuses on one analytics area.

### 9.1 Overview

File:

- `dashboard/sections/overview.html`

Shows:

- total meters
- active meters
- theft alerts
- anomalies
- wastage alerts
- current demand
- recent live demand pulse
- area-wise consumption
- risk distribution
- operator insights

### 9.2 Live Monitoring

File:

- `dashboard/sections/live_monitoring.html`

Shows:

- current load
- 24-hour peak load
- average voltage
- peak-demand region
- live charts and meter tables

### 9.3 Theft Detection

File:

- `dashboard/sections/theft_detection.html`

Shows:

- theft alert count
- average risk score
- average theft probability
- critical areas
- theft probability plots
- current theft investigation table

### 9.4 Anomaly Detection

File:

- `dashboard/sections/anomaly_detection.html`

Shows:

- anomaly count
- mean anomaly score
- max anomaly score
- impacted areas
- anomaly distributions and suspicious cases

### 9.5 Demand Forecast

File:

- `dashboard/sections/demand_forecast.html`

Shows:

- next-hour forecast
- next-day forecast
- next-week forecast
- LSTM vs Transformer comparison
- future series output

### 9.6 Energy Efficiency

File:

- `dashboard/sections/energy_efficiency.html`

Shows:

- low-efficiency meter count
- average efficiency
- estimated losses
- power-factor loss signals

### 9.7 Consumer Segmentation

File:

- `dashboard/sections/consumer_segmentation.html`

Shows:

- cluster mix
- suspicious segments
- average consumption by segment
- cluster member details

### 9.8 Heatmap

File:

- `dashboard/sections/heatmap.html`

Shows:

- current theft incidents
- anomaly hotspots
- mapped meters
- area hotspot summaries
- link to `dashboard/theft_heatmap.html`

### 9.9 Weather Impact

File:

- `dashboard/sections/weather_impact.html`

Shows:

- weather band analytics
- temperature vs consumption scatter
- area weather effects
- live weather snapshot

### 9.10 Alerts

File:

- `dashboard/sections/alerts.html`

Shows:

- consolidated alert severities
- theft alerts
- anomaly alerts
- wastage alerts
- drift events

### 9.11 Reports

File:

- `dashboard/sections/reports.html`

Shows:

- report KPIs
- downloadable artifacts
- sample outputs
- report summaries

## 10. Generated Outputs and Artifacts

The project can create all of the following:

- `dataset/smart_meter_data.csv`
- `data/processed/smart_meter_sample.csv`
- `data/processed/live_simulation.csv`
- `data/processed/meter_catalog.csv`
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

## 11. Installation and Setup

This project is currently set up for Windows PowerShell, and the commands in `run.md` match that environment.

### 11.1 Python

Use Python 3.11 if possible. Your current local run guide already points to:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
```

### 11.2 Create `.env`

If the file does not exist:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

### 11.3 Install dependencies

Main dependencies:

- FastAPI
- Uvicorn
- pandas
- NumPy
- scikit-learn
- XGBoost
- TensorFlow
- matplotlib
- Plotly
- folium
- SHAP
- requests
- websockets

Install with:

```powershell
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
```

## 12. How to Run the Project

The most practical run instructions are already collected in `run.md`.

### 12.1 Complete workflow

Typical order:

1. install dependencies
2. generate data and train models
3. start the backend
4. start the dashboard static server
5. open the dashboard in a browser

### 12.2 Bootstrap data and models

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
& $PYTHON run_project.py
```

### 12.3 Start the backend

```powershell
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Backend URL:

- `http://127.0.0.1:8000`

### 12.4 Start the frontend

From the `dashboard/` folder:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection\dashboard"
& $PYTHON -m http.server 8080
```

Frontend URL:

- `http://127.0.0.1:8080/index.html`

### 12.5 Run tests

```powershell
& $PYTHON -m pytest
```

## 13. Command-Line Options

`run_project.py` supports:

- `--full-scale`  
  Generate a 1000-meter, one-year dataset.

- `--num-meters`  
  Override the default number of meters.

- `--days`  
  Override the number of simulated days.

- `--skip-training`  
  Generate data only.

- `--forecast-epochs`  
  Set LSTM training epochs.

- `--skip-sample-export`  
  Skip sample API payload generation.

- `--skip-report`  
  Skip PDF report generation.

- `--start-api`  
  Start FastAPI immediately after bootstrapping.

- `--optimize-models`  
  Run Optuna-based tuning before training.

- `--optimization-trials`  
  Number of optimization trials to run.

## 14. Environment Variables

Main runtime environment variables used by the project:

- `SMARTGRID_FULL_SCALE`  
  `1` enables full-scale dataset generation settings.

- `SMARTGRID_UPDATE_INTERVAL`  
  Controls the simulation refresh interval in seconds.

- `SMARTGRID_DEMO_MODE`  
  Simplifies some reporting behavior for demo runs.

- `SMARTGRID_ENABLE_PERIODIC_REPORTS`  
  Enables periodic report generation in the runtime loop.

- `SMARTGRID_ENABLE_ALERTS`  
  Enables alert dispatch integrations.

Optional notification-related variables used by `src/alert_engine.py`:

- `SMARTGRID_SMTP_HOST`
- `SMARTGRID_SMTP_PORT`
- `SMARTGRID_SMTP_USER`
- `SMARTGRID_SMTP_PASSWORD`
- `SMARTGRID_ALERT_EMAIL_FROM`
- `SMARTGRID_ALERT_EMAIL_TO`
- `SMARTGRID_SLACK_WEBHOOK`
- `SMARTGRID_TELEGRAM_BOT_TOKEN`
- `SMARTGRID_TELEGRAM_CHAT_ID`

## 15. Testing

The project includes coverage for the major layers.

Current test modules include:

- `tests/test_api.py`
- `tests/test_data_pipeline.py`
- `tests/test_forecasting_and_exports.py`
- `tests/test_advanced_analytics.py`
- `tests/test_theft_detector.py`

The tests cover areas such as:

- API payload behavior
- overview and theft counts
- sticky theft behavior across live ticks
- WebSocket client disconnect handling
- feature engineering
- forecasting fallbacks
- export generation
- consumer segmentation
- efficiency metrics
- theft-probability calibration

## 16. Recent Runtime Behavior Notes

The current codebase includes a few important runtime behaviors that are worth knowing when you demo or explain the system.

### 16.1 Sticky live theft detection

The runtime keeps the first detected theft meter sticky during live replay so the main theft location does not keep jumping every few seconds. This makes the dashboard easier to follow during presentations.

### 16.2 Theft probabilities above 0.9

The theft classifier now calibrates strong theft cases into the `0.9+` range, which makes the theft panel and alert views clearer and more decisive during live monitoring.

### 16.3 Safe WebSocket disconnect handling

If a dashboard tab or client disconnects immediately after opening the live stream, the backend now treats that as a normal disconnect instead of surfacing a long ASGI traceback.

## 17. Troubleshooting

### 17.1 TensorFlow warnings on Windows

You may see logs about:

- oneDNN custom operations
- CPU instruction optimization
- GPU not being available on native Windows

These are usually informational and do not mean the project failed.

### 17.2 WebSocket clients connect and close quickly

This is expected when dashboard tabs reload or reconnect. The runtime now handles these disconnects cleanly.

### 17.3 Some models or advanced libraries are unavailable

The project contains fallback behavior for several components:

- theft boosting falls back if XGBoost is unavailable
- forecasting falls back when deep-learning models cannot be loaded
- drift reporting falls back when Evidently is unavailable
- explainability falls back when SHAP is unavailable

### 17.4 The dashboard shows no new data

Check:

- the backend is running on `127.0.0.1:8000`
- the frontend static server is running on port `8080`
- the API base inside the dashboard matches the backend address
- datasets and models have already been generated

## 18. Presentation Summary

If you need a short explanation during a viva, demo, or presentation, use this:

This project simulates a Bengaluru smart-grid monitoring system. It generates synthetic smart-meter readings with weather, theft, anomaly, and wastage patterns; trains anomaly, theft, and forecasting models; replays the data as a live stream through a FastAPI backend; and visualizes everything in a dashboard. The system can identify suspicious theft cases, unusual meter behavior, low-efficiency operations, demand forecasts, risk by area, weather effects, and drift in incoming data.
