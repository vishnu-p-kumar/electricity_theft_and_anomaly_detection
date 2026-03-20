# Smart Grid Electricity Theft, Anomaly, and Energy Wastage Detection System

An end-to-end Bengaluru smart-grid analytics platform. The project simulates smart-meter readings, injects theft and wastage scenarios, detects suspicious behavior with machine learning, forecasts demand, exposes a FastAPI backend, streams realtime updates over WebSockets, renders a dashboard, writes SQLite snapshots, generates a Folium theft heatmap, and now adds advanced analytics for grid topology, risk scoring, segmentation, efficiency, drift monitoring, transformer forecasting, model optimization, reporting, and alerting.

## What This Project Does

- Simulates hourly electricity usage for Bengaluru smart meters inside valid Bengaluru latitude and longitude bounds.
- Seeds electricity theft scenarios such as meter bypass, abnormal spikes, constant low reporting, illegal connection, and tampered meters.
- Detects anomalies in smart-meter behavior.
- Classifies likely theft using supervised models.
- Scores operational risk from multiple signals instead of relying on a single threshold.
- Measures energy efficiency and highlights wasteful meters.
- Clusters consumers into behavioral segments.
- Models the distribution network as substation, feeder, node, and meter relationships.
- Forecasts demand with both LSTM and Transformer-style sequence models.
- Monitors incoming data drift and data quality changes.
- Exposes all analytics through REST endpoints and a live websocket feed.
- Displays the results on a modern HTML dashboard and Bengaluru theft heatmap.
- Exports PDF-style daily reports and supports alert delivery hooks.

## Core Model Stack

This project intentionally uses multiple model families because smart-grid monitoring is not one modeling problem.

### 1. Isolation Forest

Used for: anomaly detection

Why it is used:

- Electricity theft and equipment abnormalities are rare compared with normal meter readings.
- Isolation Forest works well when unusual behavior must be isolated without requiring a perfect label for every abnormal record.
- It is strong on tabular telemetry after feature engineering.

What it contributes:

- Produces `anomaly_score`
- Flags suspicious behavior even before a theft classifier is confident
- Supports early investigation workflows

### 2. Random Forest

Used for: supervised theft classification

Why it is used:

- Theft detection is a structured-data classification problem with nonlinear interactions.
- Random Forest is stable, robust, and usually a strong baseline for smart-meter tabular data.
- It provides a second probability signal that reduces dependence on a single classifier.

What it contributes:

- Produces `random_forest_probability`
- Learns from seeded theft scenarios in the synthetic training data
- Supports ensemble theft scoring and fallback explainability

### 3. XGBoost

Used for: primary theft probability scoring

Why it is used:

- Gradient boosting is often stronger than bagging models on tabular fraud and risk problems.
- It captures thresholds and interactions sharply.
- Theft ranking is often more useful operationally than only a hard class label.

What it contributes:

- Produces `xgboost_probability`
- Feeds the blended `theft_probability`
- Improves prioritization of the most suspicious meters

Fallback behavior:

- If `xgboost` is unavailable, the code falls back to `HistGradientBoostingClassifier`

### 4. LSTM

Used for: baseline deep learning demand forecasting

Why it is used:

- Demand forecasting is sequential and depends on recent temporal context.
- LSTM is a practical recurrent baseline for hourly load data with daily and weekly seasonality.

What it contributes:

- Forecasts next hour, next day, and next week
- Powers the backward-compatible forecast keys already used by the original dashboard and API

Fallback behavior:

- If TensorFlow is unavailable or the sample is too small, the code falls back to a baseline seasonal forecaster

### 5. Transformer Forecasting

Used for: advanced sequence forecasting

Why it is used:

- Transformer encoders can model longer-range temporal dependencies more flexibly than recurrent models.
- It provides a second forecasting path so the dashboard can compare recurrent and attention-style predictions.

What it contributes:

- Produces a second forecast stream beside LSTM
- Feeds the dashboard comparison plot and ensemble summary

Fallback behavior:

- If PyTorch is unavailable, the module falls back to a deterministic baseline forecaster

### 6. SHAP

Used for: explainable AI

Why it is used:

- Grid operators need reasons, not only risk scores.
- SHAP gives local feature contributions for tree-based classifiers.
- It converts suspicious predictions into human-readable operational reasons.

What it contributes:

- Alert explanations such as high night usage, voltage irregularity, or abnormal wastage
- Better trust and triage support for the dashboard and API

Fallback behavior:

- If `shap` is unavailable, the project falls back to feature-importance-weighted heuristics

## Advanced Smart Grid Analytics

The upgraded platform adds a second layer of research-style analytics on top of the original detector and dashboard.

### Grid Network Modeling

Module: `src/grid_network_model.py`

- Uses NetworkX when available
- Represents `Substation -> Feeder -> Distribution Node -> Smart Meter`
- Computes feeder loading
- Detects suspicious clusters of risky meters on the same feeder
- Exports graph payloads for the D3 network view

### Risk Scoring System

Module: `src/risk_scoring.py`

- Produces a `risk_score` between `0` and `100`
- Combines anomaly score, blended theft probability, voltage irregularity, and night usage ratio
- Maps each meter to `Low`, `Medium`, `High`, or `Critical`

### Consumer Segmentation

Module: `src/consumer_segmentation.py`

- Uses KMeans for broad consumer behavior grouping
- Uses DBSCAN to highlight unusual dense or isolated behavioral groups
- Segments consumers into Residential, Commercial, Industrial, and Suspicious cluster

### Energy Efficiency Analysis

Module: `src/energy_efficiency.py`

- Computes `efficiency_score`
- Estimates losses from useful energy vs total energy and power factor degradation
- Flags low-efficiency or wasteful meters

### Data Drift Monitoring

Module: `src/data_drift_monitor.py`

- Uses Evidently when installed
- Falls back to deterministic distribution-shift checks otherwise
- Tracks feature drift, concept drift, and data quality issues

### Model Optimization

Module: `src/model_optimizer.py`

- Uses Optuna when installed
- Optimizes Isolation Forest contamination
- Optimizes Random Forest max depth
- Optimizes XGBoost learning rate
- Saves best hyperparameters to `models/optimizer_best_params.json`

### Grid Simulation

Module: `src/grid_simulator.py`

- Uses pandapower when installed
- Falls back to feeder-load heuristics otherwise
- Estimates voltage stability, line losses, and overload conditions

### Automated Reporting

Module: `src/report_generator.py`

- Generates `reports/daily_energy_report.pdf`
- Includes usage summary, theft incidents, weather impact, and regional consumption

### Alert Notification System

Module: `src/alert_engine.py`

- Supports email, Slack, and Telegram
- Remains disabled unless credentials and `SMARTGRID_ENABLE_ALERTS=1` are configured

## End-to-End Architecture

```text
Synthetic Smart Meter Data
  -> Preprocessing
  -> Feature Engineering
  -> Isolation Forest anomaly scoring
  -> Random Forest + XGBoost theft scoring
  -> Risk scoring + efficiency scoring
  -> LSTM + Transformer forecasting
  -> SHAP / feature-importance explanation
  -> Grid graph + feeder analysis + drift monitor
  -> FastAPI + WebSocket + SQLite
  -> Dashboard + Folium heatmap + PDF report + alert hooks
```

## Core Engineered Features

Important engineered features include:

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

These features matter because theft and inefficiency usually appear as patterns across time, weather, and electrical quality rather than one raw measurement.

## Project Structure

```text
electricity_theft_detection/
|-- .github/workflows/ci.yml
|-- api/
|-- dashboard/
|-- data/
|-- database/
|-- dataset/
|-- maps/
|-- models/
|-- reports/
|-- sample_outputs/
|-- src/
|   |-- alert_engine.py
|   |-- consumer_segmentation.py
|   |-- data_drift_monitor.py
|   |-- demand_forecasting.py
|   |-- energy_efficiency.py
|   |-- explainable_ai.py
|   |-- grid_network_model.py
|   |-- grid_simulator.py
|   |-- model_optimizer.py
|   |-- report_generator.py
|   |-- risk_scoring.py
|   |-- transformer_forecasting.py
|   `-- ...
|-- tests/
|-- utils/
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- docker-compose.yml
|-- pytest.ini
|-- requirements.txt
|-- requirements-test.txt
|-- requirements-advanced.txt
`-- run_project.py
```

## Installation

### Prerequisites

- Python 3.10 or newer
- `pip`
- Optional: Docker Desktop
- Optional: OpenWeather API key

### Base Install

Install the standard runnable stack:

```bash
pip install -r requirements.txt
```

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

### Advanced Optional Install

Install this only if you want the Optuna, Evidently, pandapower, and PyTorch paths enabled:

```bash
pip install -r requirements-advanced.txt
```

## Environment Variables

Copy the sample file if needed:

```powershell
Copy-Item .env.example .env
```

Important variables:

- `OPENWEATHER_API_KEY`: enables live OpenWeather snapshots
- `SMARTGRID_UPDATE_INTERVAL`: websocket/API tick interval in seconds
- `SMARTGRID_FULL_SCALE`: set to `1` for the full 1000-meter, 365-day generation path
- `SMARTGRID_ENABLE_ALERTS`: set to `1` to enable outbound alert delivery
- `SMARTGRID_SLACK_WEBHOOK`: Slack webhook for alert messages
- `SMARTGRID_TELEGRAM_BOT_TOKEN`: Telegram bot token
- `SMARTGRID_TELEGRAM_CHAT_ID`: Telegram target chat
- `SMARTGRID_SMTP_HOST`, `SMARTGRID_SMTP_PORT`, `SMARTGRID_SMTP_USER`, `SMARTGRID_SMTP_PASSWORD`: SMTP settings
- `SMARTGRID_ALERT_EMAIL_FROM`, `SMARTGRID_ALERT_EMAIL_TO`: email sender and recipient

## How To Run The Project

### Option 1: Quickstart

Recommended for the first run:

```bash
python run_project.py
```

What it does:

- Generates a practical-size seeded dataset
- Trains anomaly, theft, and forecasting models
- Generates the Bengaluru theft heatmap
- Writes sample outputs
- Generates the daily PDF report

### Option 2: Full Research-Scale Generation

```bash
python run_project.py --full-scale
```

This uses the requested larger simulation path and is heavier on CPU, RAM, and disk.

### Option 3: Hyperparameter Optimization + Training

```bash
python run_project.py --optimize-models --optimization-trials 12
```

This runs the Optuna optimization module first when Optuna is installed, saves best parameters, and then trains using those parameters.

### Option 4: Data Only

```bash
python run_project.py --skip-training
```

### Option 5: Train and Start the API

```bash
python run_project.py --start-api
```

### Option 6: Run the API Directly

After datasets and models exist:

```bash
uvicorn api.main:app --reload
```

### Option 7: Open the Dashboard

1. Start the API on `http://127.0.0.1:8000`
2. Open `dashboard/index.html`
3. Keep the dashboard API base URL set to `http://127.0.0.1:8000`

The dashboard uses both REST polling and `ws://127.0.0.1:8000/ws/live`.

## Docker Run

### Build and Start

```bash
docker compose up --build
```

Services:

- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:8080`

### Stop

```bash
docker compose down
```

Notes:

- The API container installs `requirements.txt`
- The advanced optional stack is not required for the standard Docker path
- Reports, models, datasets, database, and maps are written to mounted local folders

## API Endpoints

Core endpoints:

- `GET /`
- `GET /health`
- `GET /overview`
- `GET /meters`
- `GET /anomalies`
- `GET /theft`
- `GET /weather-impact`
- `GET /forecast`
- `POST /predict`
- `GET /ws/live`

Advanced endpoints:

- `GET /risk-scores`
- `GET /consumer-segments`
- `GET /efficiency`
- `GET /grid-status`
- `GET /drift-report`

## Dashboard Panels

The upgraded dashboard now includes:

- Overview cards
- Live consumption chart
- Weather vs usage chart
- Area-wise consumption chart
- Theft detection panel
- Wastage and efficiency panel
- Grid network view
- Risk distribution panel
- Consumer segmentation panel
- Efficiency monitor
- Grid status panel
- Data drift panel
- Demand forecast comparison panel
- Smart meter monitoring table

## Reports and Generated Artifacts

The main generated artifacts include:

- `dataset/smart_meter_data.csv`
- `data/processed/smart_meter_sample.csv`
- `data/processed/live_simulation.csv`
- `data/processed/meter_catalog.csv`
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
- `maps/theft_heatmap.html`
- `reports/daily_energy_report.pdf`
- `reports/drift_report.json`

## Testing

Run the test suite with:

```bash
pytest
```

The tests cover:

- Bengaluru meter bounds
- Preprocessing behavior
- Feature engineering
- LSTM forecast fallback behavior
- Transformer forecast pipeline behavior
- Risk scoring
- Consumer clustering
- Energy efficiency scoring
- Grid network graph and feeder load generation
- API health endpoint
- Sample output export

## Practical Notes

- The project is designed to run in reduced mode when optional heavy libraries are not installed.
- `networkx` is part of the standard stack because the grid-graph path is lightweight.
- PyTorch, Evidently, Optuna, and pandapower are optional and are activated by `requirements-advanced.txt`.
- If those advanced packages are absent, the project still runs end to end using deterministic fallbacks.
- OpenWeather is optional. Synthetic Bengaluru weather is used when no API key is configured.

## Recommended First Run

Use this exact order:

1. `pip install -r requirements.txt`
2. `pip install -r requirements-test.txt`
3. `python run_project.py`
4. `pytest`
5. `uvicorn api.main:app --reload`
6. Open `dashboard/index.html`

If you want the container path:

1. `docker compose up --build`
2. Open `http://127.0.0.1:8080`

## Summary

The platform now combines:

- Isolation Forest for anomaly detection
- Random Forest and XGBoost for theft scoring
- Risk scoring for operational prioritization
- KMeans and DBSCAN for consumer segmentation
- Efficiency scoring for wastage analysis
- LSTM and Transformer forecasting for demand prediction
- NetworkX and feeder analytics for grid modeling
- Evidently-style drift checks for distribution monitoring
- Optuna-based optimization for model tuning
- pandapower-compatible simulation for grid-state estimation
- SHAP for explainable AI

That mix is intentional. Smart-grid monitoring requires anomaly detection, supervised theft scoring, temporal forecasting, grid analysis, and explainability at the same time.

## Verified Windows PowerShell Command Order

These commands were verified on March 13, 2026 in PowerShell.

If `python` is already available on your PATH, replace `& $PYTHON` with `python`.
If `python` is not available on your PATH, use the full interpreter path:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
```

Run the project in this order:

```powershell
Copy-Item .env.example .env
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
& $PYTHON run_project.py
& $PYTHON -m pytest
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Optional checks after the API starts:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

Then open the dashboard file in your browser:

```powershell
Start-Process .\dashboard\index.html
```
