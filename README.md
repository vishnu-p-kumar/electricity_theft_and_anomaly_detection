# Smart Grid Electricity Theft, Anomaly, and Wastage Detection System

An end-to-end smart-grid analytics project built on synthetic Bengaluru smart-meter data. The system generates realistic meter readings, trains multiple machine learning models, replays a live monitoring stream through FastAPI, stores runtime state in SQLite, and serves a browser dashboard for operators.

This repository is useful for:

- data science and machine learning coursework
- electricity theft detection demos and prototypes
- anomaly detection and energy wastage monitoring
- smart-grid dashboard presentations
- full-stack ML system demonstrations

## Table of Contents

- [1. Project Summary](#1-project-summary)
- [2. Key Capabilities](#2-key-capabilities)
- [3. System Architecture](#3-system-architecture)
- [4. Repository Structure](#4-repository-structure)
- [5. Data Generation Pipeline](#5-data-generation-pipeline)
- [6. Dataset Schema](#6-dataset-schema)
- [7. Modeling and Analytics](#7-modeling-and-analytics)
- [8. Runtime and API Behavior](#8-runtime-and-api-behavior)
- [9. Dashboard](#9-dashboard)
- [10. Generated Artifacts](#10-generated-artifacts)
- [11. Installation](#11-installation)
- [12. How to Run](#12-how-to-run)
- [13. Configuration](#13-configuration)
- [14. Docker Support](#14-docker-support)
- [15. API Reference](#15-api-reference)
- [16. Testing](#16-testing)
- [17. Project Workflow Summary](#17-project-workflow-summary)
- [18. Troubleshooting](#18-troubleshooting)
- [19. Presentation Summary](#19-presentation-summary)

## 1. Project Summary

At a high level, the project does five things:

1. Generates hourly synthetic smart-meter data for Bengaluru areas.
2. Simulates electricity theft, anomalies, energy wastage, weather effects, and pole-level tampering.
3. Trains anomaly detection, theft detection, and demand forecasting models.
4. Replays a live simulation through a FastAPI backend that updates every few seconds.
5. Visualizes current and historical analytics in a static dashboard.

The repository is meter-centric but also includes a pole-monitoring layer. Each meter is mapped into a `transformer -> pole -> meter` hierarchy, allowing the system to detect direct pole tapping, supply mismatch, and hidden unmetered consumption in addition to meter-level suspicious behavior.

## 2. Key Capabilities

- Synthetic smart-meter generation across multiple Bengaluru areas
- Weather-aware electricity consumption simulation
- Multiple theft scenarios such as bypass, tampering, illegal connections, and abnormal spikes
- Isolation Forest based anomaly detection
- Random Forest plus boosted-model theft classification
- Theft probability calibration using anomaly, wastage, and seeded theft context
- Meter-level risk scoring and risk categories
- Energy efficiency and wastage analytics
- Pole energy balance monitoring and pole tamper detection
- LSTM and Transformer-based demand forecasting with fallback behavior
- Data drift monitoring between historical and recent windows
- Explainable predictions for suspicious meters
- Optional alert dispatch to email, Slack, and Telegram
- FastAPI REST API plus WebSocket live stream
- Multi-section static dashboard for realtime monitoring and artifact downloads

## 3. System Architecture

The current implementation follows this flow:

1. `run_project.py` loads generation defaults from `utils/helpers.py`.
2. `src/data_generator.py` creates:
   - the main dataset
   - a sampled training dataset
   - a live simulation dataset
   - meter and pole catalogs
   - generation summary metadata
3. `src/train_models.py` trains:
   - Isolation Forest for anomaly detection
   - Random Forest for theft detection
   - XGBoost or a fallback boosted model for theft detection
   - LSTM demand forecaster
   - Transformer demand forecaster
4. `api/main.py` boots the runtime, regenerates missing artifacts when needed, loads models and datasets, and starts a simulation loop.
5. Each live tick is enriched with anomaly scores, theft probabilities, risk levels, efficiency metrics, pole energy balance, drift state, clustering output, and forecast output.
6. Runtime snapshots are written into SQLite tables in `database/meter_data.db`.
7. The dashboard reads API endpoints every few seconds and can also consume the `/ws/live` WebSocket payload.

## 4. Repository Structure

Important folders and files:

- `api/`
  FastAPI backend and live runtime simulation.

- `src/`
  Core Python modules for generation, preprocessing, training, forecasting, scoring, explainability, drift detection, pole monitoring, reporting, and exports.

- `dashboard/`
  Static frontend with HTML sections, shared JavaScript components, and styling.

- `data/raw/`
  Placeholder location for raw source data if the project is extended beyond synthetic generation.

- `data/processed/`
  Processed intermediate outputs such as the sample training set, live simulation data, meter catalog, pole catalog, and generation summary.

- `dataset/`
  Main generated synthetic dataset.

- `models/`
  Trained model artifacts and metadata files.

- `database/`
  SQLite runtime database generated by the API.

- `reports/`
  Generated PDF and JSON reporting artifacts.

- `maps/`
  Generated HTML heatmaps.

- `sample_outputs/`
  Example API request/response payloads.

- `tests/`
  Pytest-based tests for data generation, analytics modules, forecasting, API payloads, and runtime behavior.

- `run_project.py`
  Main bootstrap script for generation, training, exports, reports, and optional API startup.

- `run.md`
  PowerShell-oriented run guide.

- `model.md`
  High-level explanation of the models used in the project.

- `docker-compose.yml`
  Two-service stack for API and dashboard.

## 5. Data Generation Pipeline

The synthetic data generator is implemented in `src/data_generator.py`.

### 5.1 Geographic Coverage

Meters are distributed across Bengaluru locations defined in `utils/helpers.py`:

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

Coordinates are jittered around each area center so meters appear spatially distinct on the map while still staying inside Bengaluru bounds.

### 5.2 Usage Profiles

Every meter is assigned a usage profile that drives base load behavior:

- `residential`
- `night_usage`
- `industrial`
- `ac_heavy`
- `commercial`

These profiles influence load shape, temperature sensitivity, weekday/weekend patterns, and expected consumption.

### 5.3 Weather Generation

Weather is handled by `src/weather_api.py`.

Behavior:

- If `OPENWEATHER_API_KEY` is configured, the weather service can fetch current live weather from OpenWeather.
- For historical generation and fallback scenarios, the project simulates Bengaluru hourly weather.

Generated weather fields include:

- `temperature`
- `humidity`
- `rainfall`
- `wind_speed`
- `weather_condition`

### 5.4 Theft Scenarios

The dataset simulates these theft patterns:

- `meter_bypass`
- `abnormal_spikes`
- `constant_low_consumption`
- `illegal_connection`
- `tampered_meter`

These patterns modify reported consumption, actual load, voltage, current behavior, and downstream risk signals.

### 5.5 Pole Hierarchy

The project extends the meter dataset with:

- `transformer_id`
- `pole_id`
- `connected_meters`

The pole hierarchy is generated automatically and stored in `data/processed/pole_catalog.csv`. This enables pole-level supply simulation and tamper detection during runtime.

### 5.6 Default Generation Settings

`utils/helpers.py` defines two standard configurations.

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

### 5.7 Live Simulation Stability

The live replay dataset intentionally behaves differently from the broader historical training data:

- a deterministic subset of live meters is selected as theft candidates
- the selected live theft meters remain stable during the live replay window
- non-selected live meters can have random theft disabled during replay

This keeps the dashboard easier to follow during presentations because the suspicious meters do not jump randomly every few seconds.

## 6. Dataset Schema

### 6.1 Main Generated Files

The generator writes these key outputs:

- `dataset/smart_meter_data.csv`
  Full synthetic dataset.

- `data/processed/smart_meter_sample.csv`
  Sampled training-friendly dataset.

- `data/processed/live_simulation.csv`
  Dataset used by the FastAPI live runtime.

- `data/processed/meter_catalog.csv`
  Meter metadata.

- `data/processed/pole_catalog.csv`
  Pole and transformer hierarchy.

- `data/processed/generation_summary.json`
  Generation metadata and live theft meter list.

### 6.2 Core Meter Columns

Important source columns include:

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

### 6.3 Preprocessing and Engineered Fields

`src/preprocess.py` and `src/feature_engineering.py` add additional runtime and model features such as:

- `wastage_flag`
- `power_gap`
- `temperature_band`
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

Categorical feature groups include:

- `region`
- `area`
- `weather_condition`
- `usage_profile`

### 6.4 Runtime-Derived Fields

After live scoring, the runtime adds fields like:

- `anomaly_score`
- `is_anomaly`
- `random_forest_probability`
- `xgboost_probability`
- `theft_probability`
- `status`
- `risk_score`
- `risk_level`
- `efficiency_score`
- `estimated_losses_kwh`
- `tamper_probability`
- `tamper_flag`
- `energy_gap`

## 7. Modeling and Analytics

### 7.1 Anomaly Detection

Files:

- `src/detect_anomaly.py`
- `src/train_models.py`

Model:

- Isolation Forest

Purpose:

- detect unusual readings even when theft is not explicitly confirmed
- produce `anomaly_score` and `is_anomaly`

### 7.2 Theft Detection

Files:

- `src/theft_detector.py`
- `src/train_models.py`

Models:

- Random Forest
- XGBoost when available
- `HistGradientBoostingClassifier` fallback if XGBoost is unavailable

Final theft probability is calibrated using:

- model probabilities
- anomaly score
- seeded theft probability
- wastage score

Outputs include:

- `random_forest_probability`
- `xgboost_probability`
- `theft_probability`
- `status`

### 7.3 Risk Scoring

File:

- `src/risk_scoring.py`

Purpose:

- combine model outputs and electrical heuristics into a single risk score
- assign `Low`, `Medium`, `High`, and `Critical` risk levels

### 7.4 Energy Efficiency and Wastage

File:

- `src/energy_efficiency.py`

Purpose:

- compute efficiency metrics
- estimate losses in kWh
- surface low-efficiency and wastage-sensitive meters

### 7.5 Pole Monitoring and Pole Tamper Detection

Files:

- `src/pole_monitoring.py`
- `src/pole_tamper_detector.py`

Purpose:

- aggregate meter load into pole-level supply behavior
- estimate technical losses and hidden load
- compute energy mismatch between supplied and metered energy
- detect suspicious poles and likely illegal connections

Core idea:

`supplied_energy - (meter_energy_sum + loss_estimate) = energy_gap`

Large or abnormal energy gaps can trigger pole tamper alerts.

### 7.6 Demand Forecasting

Files:

- `src/demand_forecasting.py`
- `src/transformer_forecasting.py`

Models:

- LSTM forecaster
- Transformer forecaster
- seasonal/baseline fallback logic when deep learning dependencies or artifacts are unavailable

Forecast outputs include:

- `next_hour`
- `next_day`
- `next_week`
- forecast `series`
- comparison between LSTM and Transformer outputs

### 7.7 Explainability

File:

- `src/explainable_ai.py`

Methods:

- SHAP when available
- fallback feature-importance style explanations when SHAP is unavailable

Purpose:

- explain suspicious predictions in human-readable form
- support theft investigation tables and API responses

### 7.8 Data Drift Monitoring

File:

- `src/data_drift_monitor.py`

Methods:

- Evidently when available
- fallback statistical drift checks otherwise

Purpose:

- compare recent live data to historical reference data
- identify feature drift, data-quality issues, and theft-rate shifts

### 7.9 Hyperparameter Optimization

File:

- `src/model_optimizer.py`

Method:

- Optuna

Purpose:

- tune anomaly and theft model parameters before training when explicitly requested from the CLI

### 7.10 Reporting and Export Utilities

Files:

- `src/report_generator.py`
- `src/spatial_analysis.py`
- `src/sample_outputs.py`

Outputs include:

- PDF report
- drift JSON report
- HTML heatmap
- example prediction and overview API payloads

## 8. Runtime and API Behavior

The backend lives in `api/main.py`.

### 8.1 Startup Behavior

On startup the runtime:

1. ensures project directories exist
2. regenerates data artifacts if key files are missing or outdated
3. retrains models if required model artifacts are missing
4. loads historical and live datasets
5. initializes forecast, drift, and pole-monitoring state
6. advances one simulation tick immediately so the dashboard has data at first load

### 8.2 Live Tick Processing

Every update cycle:

1. the runtime selects one timestamp slice from `live_simulation.csv`
2. meter readings are classified for anomaly and theft
3. a visible theft candidate may be injected if none is present
4. the first detected theft meter can be kept sticky for demo stability
5. theft alerts are capped for readability
6. risk and efficiency metrics are computed
7. pole energy is simulated and checked for tampering
8. recent windows are updated for drift monitoring
9. forecast data is rebuilt
10. SQLite tables are refreshed
11. the latest snapshot is broadcast to WebSocket clients
12. periodic reports and heatmap outputs are regenerated on schedule

### 8.3 SQLite Tables

The backend writes runtime data into `database/meter_data.db` using tables such as:

- `meter_readings`
- `live_predictions`
- `recent_predictions`
- `risk_scores`
- `efficiency_metrics`
- `drift_reports`
- `forecast_snapshots`
- `pole_energy_data`
- `pole_tamper_events`

### 8.4 Alert Integrations

`src/alert_engine.py` supports optional outbound alert delivery through:

- SMTP email
- Slack webhook
- Telegram bot API

Alerts are sent only when `SMARTGRID_ENABLE_ALERTS=1`.

## 9. Dashboard

The frontend is a static dashboard in `dashboard/`.

Main files:

- `dashboard/index.html`
- `dashboard/main.js`
- `dashboard/style.css`

Shared components:

- `dashboard/components/core.js`
- `dashboard/components/charts.js`
- `dashboard/components/alerts.js`
- `dashboard/components/forecast.js`
- `dashboard/components/heatmap.js`

The dashboard defaults to the API base URL `http://127.0.0.1:8000` and stores UI state such as selected section and theme in local storage.

### 9.1 Dashboard Sections

Each file in `dashboard/sections/` represents one analytics view:

- `overview.html`
  High-level KPIs, live demand, and system health.

- `live_monitoring.html`
  Realtime usage and meter-level monitoring.

- `theft_detection.html`
  Theft counts, suspicious meters, and investigation priorities.

- `anomaly_detection.html`
  Anomaly metrics and suspicious outlier summaries.

- `demand_forecast.html`
  LSTM and Transformer forecast comparisons.

- `energy_efficiency.html`
  Wastage and efficiency views.

- `pole_monitoring.html`
  Pole energy balance, suspicious poles, and illegal connection signals.

- `heatmap.html`
  Interactive theft hotspot map.

- `weather_impact.html`
  Demand behavior against weather conditions.

- `alerts.html`
  Consolidated alerts and operational notifications.

- `reports.html`
  Downloadable reports and sample output references.

### 9.2 Refresh Pattern

The dashboard polls the backend frequently and also supports the `/ws/live` WebSocket snapshot payload. The backend update interval defaults to 4 seconds and can be changed with `SMARTGRID_UPDATE_INTERVAL`.

## 10. Generated Artifacts

Common generated files include:

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
- `models/optimizer_best_params.json` when optimization is used
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

The repository is currently easiest to run in Windows PowerShell, and `run.md` is written with that workflow in mind.

### 11.1 Python Version

Use Python 3.11 if possible.

Example interpreter path used on this machine:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
```

If `python` is already configured in your PATH, you can use `python` instead of `$PYTHON`.

### 11.2 Create `.env`

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### 11.3 Install Dependencies

Core dependencies from `requirements.txt` include:

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
- joblib
- requests
- websockets
- SHAP
- pydantic

Install the main stack:

```powershell
& $PYTHON -m pip install -r requirements.txt
```

Install testing tools:

```powershell
& $PYTHON -m pip install -r requirements-test.txt
```

Optional advanced dependencies:

```powershell
& $PYTHON -m pip install -r requirements-advanced.txt
```

Advanced extras add packages such as:

- Optuna
- Evidently
- PyTorch

## 12. How to Run

### 12.1 Quick Start

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
& $PYTHON run_project.py
& $PYTHON -m pytest
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

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

- generates synthetic datasets
- writes meter and pole catalogs
- trains anomaly, theft, and forecasting models
- exports sample outputs
- builds the theft heatmap
- generates the PDF report

### 12.3 Generate Data Only

```powershell
& $PYTHON run_project.py --skip-training
```

### 12.4 Useful CLI Options

`run_project.py` currently supports:

- `--full-scale`
  Generate the 1000-meter, 365-day configuration.

- `--num-meters`
  Override the number of meters.

- `--days`
  Override the number of simulation days.

- `--skip-training`
  Generate data without model training.

- `--forecast-epochs`
  Set LSTM training epochs.

- `--skip-sample-export`
  Skip writing example API payloads.

- `--skip-report`
  Skip generating the PDF report.

- `--start-api`
  Start FastAPI immediately after bootstrapping.

- `--optimize-models`
  Run Optuna-based optimization before training.

- `--optimization-trials`
  Set the number of Optuna trials.

### 12.5 Start the API Manually

```powershell
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### 12.6 Demo Mode

To reduce periodic report generation during a demo:

```powershell
$env:SMARTGRID_DEMO_MODE = "1"
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 12.7 Start the Frontend

```powershell
Set-Location dashboard
& $PYTHON -m http.server 8080
```

### 12.8 Run Everything with a Single Bootstrap Command

```powershell
& $PYTHON run_project.py --start-api
```

This generates artifacts first and then launches the backend.

## 13. Configuration

### 13.1 Main Environment Variables

The `.env.example` file currently includes:

- `OPENWEATHER_API_KEY`
- `SMARTGRID_UPDATE_INTERVAL`
- `SMARTGRID_FULL_SCALE`
- `SMARTGRID_ENABLE_ALERTS`
- `SMARTGRID_SLACK_WEBHOOK`
- `SMARTGRID_TELEGRAM_BOT_TOKEN`
- `SMARTGRID_TELEGRAM_CHAT_ID`
- `SMARTGRID_SMTP_HOST`
- `SMARTGRID_SMTP_PORT`
- `SMARTGRID_SMTP_USER`
- `SMARTGRID_SMTP_PASSWORD`
- `SMARTGRID_ALERT_EMAIL_FROM`
- `SMARTGRID_ALERT_EMAIL_TO`

Additional runtime variables used in code:

- `SMARTGRID_DEMO_MODE`
  Disables periodic reporting by default for presentation-friendly runtime behavior.

- `SMARTGRID_ENABLE_PERIODIC_REPORTS`
  Explicitly controls periodic report generation in the runtime loop.

### 13.2 Common Configuration Notes

- Set `SMARTGRID_FULL_SCALE=1` to make the API bootstrap using the full generation profile.
- Set `SMARTGRID_ENABLE_ALERTS=1` only when email, Slack, or Telegram configuration is ready.
- Leave `OPENWEATHER_API_KEY` empty if synthetic weather is acceptable.
- Adjust `SMARTGRID_UPDATE_INTERVAL` if you want a faster or slower live replay loop.

## 14. Docker Support

The project includes both a `Dockerfile` and `docker-compose.yml`.

### 14.1 Dockerfile

The API image:

- uses Python 3.11
- installs `requirements.txt`
- exposes port `8000`
- starts `uvicorn api.main:app --host 0.0.0.0 --port 8000`

### 14.2 Docker Compose Services

The compose setup defines two services:

- `api`
  FastAPI backend with mounted volumes for data, models, reports, maps, database, and sample outputs.

- `dashboard`
  Nginx-based static dashboard server.

Exposed ports:

- API: `8000`
- Dashboard: `8080`

### 14.3 Run with Docker Compose

```powershell
docker compose up --build
```

Then open:

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:8080`

## 15. API Reference

### 15.1 Main Endpoints

- `GET /`
- `GET /health`
- `GET /overview`
- `GET /meters`
- `GET /anomalies`
- `GET /theft`
- `GET /weather-impact`
- `GET /forecast`
- `GET /risk-scores`
- `GET /efficiency`
- `GET /api/pole-status`
- `GET /api/pole-tamper-alerts`
- `GET /api/pole-energy-balance`
- `GET /drift-report`
- `POST /predict`

### 15.2 Artifact Endpoints

- `GET /artifacts/daily-report`
- `GET /artifacts/drift-report`
- `GET /artifacts/sample-overview`
- `GET /artifacts/heatmap`

### 15.3 WebSocket Endpoint

- `WS /ws/live`

### 15.4 `POST /predict` Input

The prediction endpoint accepts one meter reading or a list of readings. Important fields include:

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
- `theft_type`
- `seeded_theft_probability`

### 15.5 `POST /predict` Output

Each prediction response returns fields such as:

- `meter_id`
- `region`
- `area`
- `latitude`
- `longitude`
- `status`
- `theft_probability`
- `anomaly_score`
- `risk_score`
- `risk_level`
- `efficiency_score`
- `reason`

## 16. Testing

Pytest coverage exists for major system layers.

Current test modules:

- `tests/test_api.py`
- `tests/test_data_pipeline.py`
- `tests/test_forecasting_and_exports.py`
- `tests/test_advanced_analytics.py`
- `tests/test_theft_detector.py`

Covered areas include:

- API health and payload structure
- live theft candidate injection behavior
- sticky theft runtime behavior
- theft and anomaly payload counts
- pole endpoint responses and pole payload helpers
- meter catalog geographic bounds
- stable live theft generation rules
- preprocessing and feature engineering outputs
- pole hierarchy generation and energy-gap detection
- risk scoring and efficiency metrics
- forecasting fallback behavior
- export generation
- theft probability calibration
- WebSocket registration failure handling

Run tests with:

```powershell
& $PYTHON -m pytest
```

## 17. Project Workflow Summary

A typical workflow for this repository is:

1. Install dependencies.
2. Generate synthetic data and train models with `run_project.py`.
3. Start the FastAPI backend.
4. Start the static dashboard server.
5. Use `/health` to confirm the backend is ready.
6. Open the dashboard and point it to `http://127.0.0.1:8000`.
7. Monitor theft, anomalies, forecasts, pole alerts, and report artifacts.

## 18. Troubleshooting

### 18.1 Deep Learning Library Warnings

Warnings from TensorFlow or PyTorch about CPU optimizations, missing GPU support, or oneDNN are usually informational.

### 18.2 Optional Dependency Fallbacks

The codebase includes several fallbacks:

- boosted theft model fallback when XGBoost is unavailable
- forecast fallback when TensorFlow or PyTorch artifacts are unavailable
- drift fallback when Evidently is unavailable
- explainability fallback when SHAP is unavailable
- synthetic weather fallback when OpenWeather is not configured

### 18.3 Dashboard Shows No Data

Check that:

- the API is running on `127.0.0.1:8000`
- the frontend static server is running on `8080`
- the dashboard API base URL is correct
- `run_project.py` or API bootstrap has generated required artifacts

### 18.4 Missing Reports or Heatmaps

Regenerate artifacts with:

```powershell
& $PYTHON run_project.py
```

### 18.5 Alert Delivery Not Working

Check that:

- `SMARTGRID_ENABLE_ALERTS=1`
- SMTP, Slack, or Telegram variables are correctly configured
- the machine has outbound network access

### 18.6 Runtime Regenerates Data Unexpectedly

The API bootstrap intentionally regenerates artifacts when required files are missing or when the live dataset and metadata do not match the expected configuration.

## 19. Presentation Summary

This project simulates a Bengaluru smart-grid intelligence platform. It generates synthetic smart-meter data with weather, theft, anomaly, wastage, and pole-level tamper behavior; trains multiple ML models; replays the data as a live FastAPI stream; stores runtime snapshots in SQLite; and visualizes the full monitoring workflow in a multi-section dashboard. The result is a complete demonstration of electricity theft detection, anomaly monitoring, energy efficiency analysis, demand forecasting, weather impact analysis, drift detection, and pole tamper surveillance.
