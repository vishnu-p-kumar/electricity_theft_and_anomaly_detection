# Smart Grid Electricity Theft, Anomaly, and Wastage Detection System

This project simulates a Bengaluru smart-grid deployment, generates smart-meter data, trains multiple machine learning models, serves a FastAPI backend, and displays results through a browser dashboard.

The system is designed to demonstrate:

- electricity theft detection
- anomaly detection
- energy wastage detection
- demand forecasting
- consumer segmentation
- weather-impact analysis
- drift monitoring and reporting

## 1. Project Overview

The project has four main layers:

1. Data generation: synthetic smart-meter readings are created for multiple Bengaluru areas with weather, load behavior, theft patterns, and wastage behavior.
2. Model training: anomaly, theft, and forecasting models are trained and saved in the `models/` directory.
3. Runtime simulation API: the backend loads historical data, replays live ticks from the generated simulation dataset, scores each tick, and exposes JSON endpoints and a live websocket.
4. Frontend dashboard: the dashboard consumes API endpoints and shows KPIs, charts, tables, heatmaps, and downloadable artifacts.

## 2. End-to-End Workflow

The actual project flow in code is:

1. `run_project.py` generates the dataset using [`src/data_generator.py`](src/data_generator.py).
2. The generated sample dataset is preprocessed by [`src/preprocess.py`](src/preprocess.py).
3. Engineered features are prepared by `src/feature_engineering.py`.
4. Detection and forecasting models are trained in [`src/train_models.py`](src/train_models.py).
5. Model files and metadata are saved in `models/`.
6. The FastAPI app in [`api/main.py`](api/main.py) bootstraps the dataset and models.
7. The runtime advances through live timestamps, scores the current tick, computes risk and efficiency, updates forecasts, clustering, drift, reports, and heatmap outputs.
8. The dashboard in `dashboard/sections/` calls backend endpoints such as `/overview`, `/theft`, `/anomalies`, `/forecast`, `/efficiency`, and `/ws/live`.

## 3. Data Used In The Project

The main dataset file is:

- `dataset/smart_meter_data.csv`

Additional generated files include:

- `data/processed/smart_meter_sample.csv`: sampled training dataset
- `data/processed/live_simulation.csv`: live replay dataset for the API
- `data/processed/meter_catalog.csv`: meter registry with area and coordinates

Each row represents a smart-meter reading at a timestamp. The core columns used throughout the project are:

- `meter_id`: unique smart meter identifier
- `timestamp`: reading time
- `region`: city or region name, currently Bengaluru
- `area`: area within Bengaluru
- `latitude`, `longitude`: geospatial coordinates
- `voltage`
- `current`
- `power`
- `consumption_kwh`: reported consumption
- `power_factor`
- `temperature`
- `humidity`
- `rainfall`
- `wind_speed`
- `weather_condition`
- `expected_consumption_kwh`: expected demand before theft/wastage effects
- `wastage_score`: relative excess use or inefficiency signal
- `wastage_flag`: binary flag derived from `wastage_score` and `power_factor`
- `usage_profile`: consumer behavior pattern such as residential or industrial
- `is_theft`: seeded training label in the synthetic data
- `theft_type`: synthetic theft scenario such as `meter_bypass` or `illegal_connection`
- `seeded_theft_probability`: generation-time theft confidence used in the simulation logic

## 4. Parameters And Features Used

### 4.1 Raw input parameters

The models and dashboard are built from electrical, environmental, and contextual parameters:

- voltage
- current
- power
- consumption_kwh
- power_factor
- temperature
- humidity
- rainfall
- wind_speed
- expected_consumption_kwh
- region
- area
- weather_condition
- usage_profile
- timestamp-derived hour and day patterns

### 4.2 Engineered features

The feature pipeline uses the base columns above and derived indicators. The configured base feature list is defined in [`utils/helpers.py`](utils/helpers.py) and includes:

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

Other derived runtime indicators used in later stages include:

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

## 5. Models Used In The Project

This project uses different models because each task is different.

### 5.1 Isolation Forest for anomaly detection

Defined in [`src/train_models.py`](src/train_models.py) and reused in [`src/detect_anomaly.py`](src/detect_anomaly.py).

- Purpose: detect unusual meter behavior without relying only on labeled theft examples
- Training logic: trained mainly on normal training records
- Output:
  - `anomaly_score`
  - `is_anomaly`
- Why it fits: anomaly detection in utility data is usually sparse and unsupervised methods work well for rare abnormal patterns

### 5.2 Random Forest for theft classification

Defined in [`src/train_models.py`](src/train_models.py).

- Purpose: classify whether a meter event is suspicious for electricity theft
- Output: theft probability from a tree-ensemble classifier
- Why it fits: robust on tabular data, nonlinear relationships, and mixed operational features

### 5.3 XGBoost or HistGradientBoosting fallback

Defined in [`src/train_models.py`](src/train_models.py).

- Purpose: boosted theft classifier used with the Random Forest ensemble
- Output: second theft probability estimate
- Runtime note: if `xgboost` is unavailable, the project falls back to `HistGradientBoostingClassifier`
- Why it fits: boosting captures more complex fraud decision boundaries than a single baseline model

### 5.4 Theft ensemble logic

Defined in [`src/theft_detector.py`](src/theft_detector.py).

- Final blend:
  - `0.45 * random_forest_probability`
  - `0.55 * xgboost_probability`
- Final field:
  - `theft_probability`
- Status logic marks events as `Electricity Theft`, `Anomaly`, or `Normal`

### 5.5 LSTM forecaster

Defined in [`src/demand_forecasting.py`](src/demand_forecasting.py).

- Purpose: short and medium horizon electricity demand forecasting
- Main outputs:
  - `next_hour`
  - `next_day`
  - `next_week`
  - future demand `series`
- Why it fits: LSTM is well suited for sequential demand patterns
- Runtime fallback: if TensorFlow/Keras model loading fails, the module falls back to a baseline forecaster so the API still works

### 5.6 Transformer forecaster

Defined in [`src/transformer_forecasting.py`](src/transformer_forecasting.py).

- Purpose: second forecasting path for comparison against LSTM
- Outputs: same horizon values and forecast series
- Why it fits: transformer-based sequence models can capture longer temporal structure
- Runtime fallback: if PyTorch or saved-model loading is not available, the module falls back to a baseline forecast

### 5.7 KMeans and DBSCAN for consumer segmentation

Defined in [`src/consumer_segmentation.py`](src/consumer_segmentation.py).

- Purpose: group meters by usage pattern and isolate suspicious clusters
- KMeans: creates broad behavioral segments
- DBSCAN: helps surface dense suspicious groups and outlier behavior

### 5.8 Risk scoring model

Defined in [`src/risk_scoring.py`](src/risk_scoring.py).

This is not a separate ML model but an important decision layer. It combines anomaly, theft, and operational stress indicators into:

- `risk_score`
- `risk_level`
- `risk_summary`

The risk score is built from weighted components such as:

- anomaly behavior
- theft probability
- wastage/efficiency pressure
- power quality indicators

### 5.9 Explainability

Defined in [`src/explainable_ai.py`](src/explainable_ai.py).

- Primary method: SHAP when available
- Fallback: feature-importance based explanation
- Output: human-readable reasons behind suspicious predictions

### 5.10 Drift monitoring

Defined in [`src/data_drift_monitor.py`](src/data_drift_monitor.py).

- Primary method: Evidently when available
- Fallback: statistical drift checks
- Output:
  - feature drift summary
  - concept drift indicators
  - data quality issues

### 5.11 Hyperparameter optimization

Defined in [`src/model_optimizer.py`](src/model_optimizer.py).

- Tool: Optuna
- Used for tuning:
  - Isolation Forest contamination
  - Random Forest depth
  - XGBoost learning rate

## 6. Model Training Configuration

The main training entry point is [`src/train_models.py`](src/train_models.py).

Important training parameters currently used:

- `max_rows=60000`
- `forecast_epochs=5`
- `seed=42`
- test split: `20%`
- Isolation Forest:
  - `n_estimators=220`
  - contamination loaded from optimizer output or derived from theft rate
- Random Forest:
  - `n_estimators=240`
  - `max_depth` from optimizer output, default `16`
  - `min_samples_leaf=2`
  - `class_weight="balanced_subsample"`
- XGBoost:
  - `n_estimators=220`
  - `max_depth=6`
  - `learning_rate` from optimizer output, default `0.08`
  - `subsample=0.85`
  - `colsample_bytree=0.9`

The saved model artifacts include:

- `models/isolation_forest.pkl`
- `models/random_forest.pkl`
- `models/xgboost_model.pkl`
- `models/lstm_model.h5`
- `models/transformer_forecaster.pt`
- `models/model_metadata.json`
- `models/demand_metadata.json`
- `models/transformer_metadata.json`

## 7. Synthetic Data Generation Logic

The dataset is produced by [`src/data_generator.py`](src/data_generator.py).

### 7.1 Meter and geography setup

- meters are distributed across named Bengaluru areas
- coordinates are jittered around area centers
- each meter gets a usage profile such as:
  - `residential`
  - `night_usage`
  - `industrial`
  - `ac_heavy`
  - `commercial`

### 7.2 Theft scenarios

Synthetic theft types include:

- `meter_bypass`
- `abnormal_spikes`
- `constant_low_consumption`
- `illegal_connection`
- `tampered_meter`

These modify reported consumption, actual load, voltage, and power factor to create realistic suspicious behavior.

### 7.3 Default generation settings

Defined in [`utils/helpers.py`](utils/helpers.py):

Default mode:

- `num_meters=180`
- `days=60`
- `chunk_size=45`
- `sample_rows=45000`
- `simulation_days=10`
- `simulation_meter_limit=60`
- `seed=42`

Full-scale mode:

- `num_meters=1000`
- `days=365`
- `chunk_size=100`
- `sample_rows=120000`
- `simulation_days=14`
- `simulation_meter_limit=80`
- `seed=42`

## 8. Runtime And API Workflow

The backend is implemented in [`api/main.py`](api/main.py).

When the API starts:

1. It ensures the dataset and processed files exist.
2. It trains models if artifacts are missing.
3. It loads the historical training frame and live simulation frame.
4. It builds the first live forecast.
5. It starts a simulation loop that advances one timestamp at a fixed interval.

For each live tick, the backend:

1. takes the current meter slice from `live_simulation.csv`
2. classifies theft and anomaly behavior
3. ensures at least one visible theft candidate for presentation/demo purposes if the current tick has zero theft alerts
4. computes risk score and efficiency metrics
5. updates recent-history buffers
6. refreshes forecast, segmentation, drift, alert payloads, SQLite tables, heatmap, and reports
7. sends the combined snapshot over `/ws/live`

Main API endpoints:

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
- `/ws/live`

## 9. Frontend Dashboard: What Each Section Means

The frontend is organized into HTML sections under `dashboard/sections/`. Each section displays data from the current API state.

### 9.1 Overview

File: `dashboard/sections/overview.html`

This is the executive summary page.

Main KPIs:

- `Total Smart Meters`: unique meters in the historical dataset
- `Active Meters`: meters present in the latest live tick
- `Electricity Theft Alerts`: current-tick meters whose status is `Electricity Theft`
- `Anomalies Detected`: current-tick anomaly count
- `Power Wastage Alerts`: current-tick low-efficiency or wastage-flagged meters
- `Current Electricity Demand`: latest aggregate `consumption_kwh`

Main visuals:

- `Live Demand Pulse`: recent total demand with anomaly and theft overlays
- `Region-Wise Consumption`: current area-wise total consumption
- `Risk Distribution Panel`: average area risk and critical meter count
- `Operator Insights`: textual summary built from forecast, risk, efficiency, alerts, and drift

### 9.2 Live Monitoring

File: `dashboard/sections/live_monitoring.html`

This section shows current operational state.

Main KPIs:

- `Current Load`
- `24h Peak Load`
- `Average Voltage`
- `Peak Region`

Main visuals:

- electricity consumption time series
- area-wise usage chart
- peak load analysis
- live smart-meter monitoring table

### 9.3 Electricity Theft Detection

File: `dashboard/sections/theft_detection.html`

This section focuses only on current theft alerts.

Main KPIs:

- `Theft Alerts`: full current-tick theft count
- `Average Risk Score`: mean `risk_score` of current theft alerts
- `Average Theft Probability`: mean `theft_probability` of current theft alerts
- `Critical Areas`: number of distinct areas with theft alerts whose `risk_score >= 80`

Main visuals:

- `Risk Distribution by Region`
- `Theft Probability Surface`
- `Electricity Theft Panel`

The theft panel records usually show:

- meter id
- area
- status
- risk score
- theft probability
- anomaly score
- explanation or reason

### 9.4 Anomaly Detection

File: `dashboard/sections/anomaly_detection.html`

This section focuses on Isolation Forest outputs.

Main KPIs:

- `Anomaly Count`: full current-tick anomaly count
- `Average Score`: mean `anomaly_score`
- `Highest Score`: maximum `anomaly_score`
- `Impacted Areas`: number of areas with anomalous readings

Main visuals:

- anomaly score distribution
- suspicious meter scatter
- anomaly investigation queue

### 9.5 Demand Forecasting

File: `dashboard/sections/demand_forecast.html`

This section compares the forecasting models.

Main KPIs:

- `Next Hour Forecast`
- `Next Day Forecast`
- `Next Week Forecast`
- `Current Demand`

Main visuals:

- `LSTM vs Transformer`
- `Forecast Horizon Comparison`
- `Model Summary`
- `First 12 Forecast Steps`

The backend also exposes an ensemble forecast that averages the LSTM and transformer horizon values.

### 9.6 Energy Efficiency Analytics

File: `dashboard/sections/energy_efficiency.html`

This section shows wastage and operational inefficiency.

Main KPIs:

- `Low-Efficiency Meters`: meters flagged with low efficiency or wastage
- `Average Efficiency`: mean `efficiency_score`
- `Estimated Losses`: estimated energy losses in kWh
- `Average PF Loss`: average power-factor loss indicator

Main visuals:

- efficiency histogram
- region efficiency comparison
- power wastage detection panel

Important logic:

- `wastage_flag` is set when wastage score is high or power factor is poor
- this flag is used consistently across overview and efficiency sections

### 9.7 Consumer Segmentation

File: `dashboard/sections/consumer_segmentation.html`

This section clusters customers by behavior.

Main KPIs:

- `Clustered Meters`
- `Suspicious Cluster`
- `Dominant Segment`
- `Highest Avg Consumption`

Main visuals:

- consumer cluster scatter
- segment share
- average demand by segment
- suspicious cluster members

### 9.8 Bengaluru Heatmap

File: `dashboard/sections/heatmap.html`

This section shows geospatial distribution.

Main KPIs:

- `Mapped Meters`
- `Theft Incidents`
- `Anomaly Hotspots`
- `Active Areas`

Main visuals:

- interactive Bengaluru map with:
  - current meter markers
  - theft rings
  - anomaly heat overlays
- hotspot summary table by area
- link to the generated Folium heatmap `dashboard/theft_heatmap.html`

### 9.9 Weather Impact Analytics

File: `dashboard/sections/weather_impact.html`

This section links weather to demand and wastage.

Main KPIs:

- `Average Temperature`
- `Average Humidity`
- `Rain-Affected Areas`
- `Weather-Sensitive Area`

Main visuals:

- temperature vs consumption scatter
- weather band demand
- area weather vs demand
- live weather summary

### 9.10 Alert Center

File: `dashboard/sections/alerts.html`

This page combines multiple alert categories.

Main KPIs:

- `Critical Alerts`
- `High Alerts`
- `Medium Alerts`
- `Drift Status`

Alerts can be built from:

- theft risk
- anomaly events
- efficiency/wastage warnings
- data drift warnings

### 9.11 Reports & Insights

File: `dashboard/sections/reports.html`

This page summarizes generated artifacts and current operations.

Main KPIs:

- `Theft Incidents`
- `Efficiency Watch`
- `Drift Watch`
- `Next Day Demand`

Downloadable artifacts include:

- daily PDF report
- drift report JSON
- Bengaluru heatmap
- sample API output

## 10. Files And Modules

Important project files:

- [`run_project.py`](run_project.py): dataset generation and model training entry point
- [`api/main.py`](api/main.py): FastAPI app and runtime simulation
- [`src/data_generator.py`](src/data_generator.py): synthetic data generation
- [`src/preprocess.py`](src/preprocess.py): cleaning and snapshot helpers
- [`src/train_models.py`](src/train_models.py): training pipeline
- [`src/theft_detector.py`](src/theft_detector.py): theft scoring
- [`src/detect_anomaly.py`](src/detect_anomaly.py): anomaly scoring
- [`src/demand_forecasting.py`](src/demand_forecasting.py): LSTM forecasting
- [`src/transformer_forecasting.py`](src/transformer_forecasting.py): transformer forecasting
- [`src/risk_scoring.py`](src/risk_scoring.py): composite risk scoring
- [`src/energy_efficiency.py`](src/energy_efficiency.py): efficiency and loss metrics
- [`src/consumer_segmentation.py`](src/consumer_segmentation.py): segmentation
- [`src/data_drift_monitor.py`](src/data_drift_monitor.py): drift detection
- [`src/explainable_ai.py`](src/explainable_ai.py): explanation layer
- [`src/spatial_analysis.py`](src/spatial_analysis.py): heatmap generation
- [`src/report_generator.py`](src/report_generator.py): PDF reporting
- [`run.md`](run.md): current step-by-step run commands

## 11. CLI Parameters

The main command-line options in [`run_project.py`](run_project.py) are:

- `--full-scale`: generate a 1000-meter, 1-year dataset
- `--num-meters`: override meter count
- `--days`: override number of simulated days
- `--skip-training`: generate data only
- `--forecast-epochs`: set LSTM training epochs
- `--skip-sample-export`: skip sample API output generation
- `--skip-report`: skip PDF report generation
- `--start-api`: start FastAPI after bootstrapping
- `--optimize-models`: run Optuna-based optimization before training
- `--optimization-trials`: number of optimization trials

## 12. Runtime Environment Variables

Important environment variables used by the API:

- `SMARTGRID_FULL_SCALE`
  - `1` enables full-scale generation config
- `SMARTGRID_UPDATE_INTERVAL`
  - controls live simulation refresh interval in seconds
- `SMARTGRID_ENABLE_ALERTS`
  - `1` enables external alert dispatch simulation

## 13. How To Run

Use the commands in [`run.md`](run.md). The current project setup uses separate commands for backend and frontend.

Typical order:

1. install dependencies
2. generate data and train models with `run_project.py`
3. start backend with `uvicorn`
4. start frontend static server from `dashboard/`

## 14. Outputs Generated By The Project

The project can generate:

- trained model artifacts in `models/`
- generated datasets in `dataset/` and `data/processed/`
- SQLite runtime tables in `database/meter_data.db`
- `reports/daily_energy_report.pdf`
- `reports/drift_report.json`
- `dashboard/theft_heatmap.html`
- sample API responses in `sample_outputs/`

## 15. Presentation Summary

If you need a short explanation during presentation:

- the project creates synthetic Bengaluru smart-meter data with weather and theft scenarios
- Isolation Forest detects unusual meter behavior
- Random Forest and XGBoost estimate theft probability
- risk scoring combines theft, anomaly, and operational stress into one severity score
- LSTM and transformer models forecast electricity demand
- the FastAPI backend simulates live incoming ticks
- the frontend dashboard explains the current grid state through KPIs, charts, alerts, maps, and reports

