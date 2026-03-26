# Models Used In This Project

This project uses different models because electricity theft detection is not a single problem. It includes anomaly detection, theft classification, demand forecasting, clustering, explainability, and drift monitoring.

## 1. `src/train_models.py`

### Isolation Forest

- Used for: anomaly detection
- Saved as: `models/isolation_forest.pkl`
- Why selected: electricity theft and abnormal meter behavior are rare, so an unsupervised anomaly model works well for separating unusual records from normal usage
- Use of model: generates anomaly scores and helps identify suspicious readings even before theft classification

### Random Forest Classifier

- Used for: theft classification
- Saved as: `models/random_forest.pkl`
- Why selected: it is stable, handles nonlinear tabular data well, and gives a strong baseline for smart meter features
- Use of model: predicts theft probability from engineered meter features

### XGBoost Classifier

- Used for: primary boosted theft classification
- Saved as: `models/xgboost_model.pkl`
- Why selected: boosting usually performs very well on structured fraud and risk data and captures complex decision boundaries better than a single simple model
- Use of model: produces an additional theft probability which is blended with Random Forest output for final theft scoring

### Fallback for XGBoost

- File: `src/train_models.py`
- Fallback model: `HistGradientBoostingClassifier`
- Why used: if `xgboost` library is not installed, the project still needs a boosting-based classifier
- Use of model: replaces XGBoost while keeping the training pipeline working

## 2. `src/detect_anomaly.py`

### Isolation Forest

- Used for: scoring new incoming records
- Why selected: the trained anomaly model is reused on live or processed data
- Use of model: creates `anomaly_score` and `is_anomaly`

## 3. `src/theft_detector.py`

### Random Forest + XGBoost Ensemble

- Used for: final theft prediction
- Why selected: combining two strong classifiers is more robust than depending on only one model
- Use of model: calculates `random_forest_probability`, `xgboost_probability`, and blended `theft_probability`

## 4. `src/demand_forecasting.py`

### LSTM

- Used for: demand forecasting
- Saved as: `models/lstm_model.h5`
- Why selected: electricity consumption is time-series data, and LSTM is good at learning sequential patterns such as hourly and daily usage behavior
- Use of model: predicts next hour, next day, and next week demand

### Baseline Seasonal Forecaster

- Used for: fallback forecasting
- Why selected: if TensorFlow is unavailable or training data is too small, the system still needs forecasts
- Use of model: creates simple future demand estimates from recent history

## 5. `src/transformer_forecasting.py`

### Transformer Regressor

- Used for: advanced demand forecasting
- Saved as: `models/transformer_forecaster.pt`
- Why selected: transformer models can learn longer temporal relationships and provide a second forecasting path for comparison with LSTM
- Use of model: produces transformer-based forecast values for dashboard comparison and forecast summary

### Baseline Forecaster

- Used for: fallback when PyTorch is unavailable
- Why selected: keeps the forecasting module functional even without deep learning support
- Use of model: provides deterministic forecast output from recent demand history

## 6. `src/consumer_segmentation.py`

### KMeans

- Used for: consumer segmentation
- Why selected: KMeans is simple and effective for grouping consumers with similar electricity usage patterns
- Use of model: creates broad clusters such as Residential, Commercial, and Industrial based on consumption behavior

### DBSCAN

- Used for: suspicious behavior grouping
- Why selected: DBSCAN is useful for finding outliers and dense groups without forcing every point into a cluster
- Use of model: helps mark unusual consumers as suspicious clusters

## 7. `src/explainable_ai.py`

### SHAP

- Used for: explainable AI
- Why selected: users need to know why a meter is predicted as suspicious, not only the final score
- Use of model: explains important features behind model predictions, such as night usage, voltage irregularity, or wastage

### Fallback Feature Importance Method

- Used for: explanation when SHAP is not installed
- Why selected: keeps explanation support available even without the SHAP package
- Use of model: estimates top contributing features using model feature importance and input values

## 8. `src/data_drift_monitor.py`

### Evidently

- Used for: drift monitoring
- Why selected: it is designed for checking changes between reference data and current data
- Use of model: detects feature drift, concept drift, and data quality issues

### Fallback Statistical Drift Check

- Used for: drift detection without Evidently
- Why selected: the system should still monitor drift even if optional libraries are missing
- Use of model: compares feature means and relative shift between old and new data

## 9. `src/model_optimizer.py`

### Optuna

- Used for: hyperparameter optimization
- Why selected: it can efficiently search better parameters for the main detection models
- Use of model: tunes Isolation Forest contamination, Random Forest depth, and XGBoost learning rate

## 10. Summary

### Main detection and forecasting files

- `src/train_models.py`: Isolation Forest, Random Forest, XGBoost, LSTM, Transformer
- `src/detect_anomaly.py`: Isolation Forest
- `src/theft_detector.py`: Random Forest and XGBoost ensemble
- `src/demand_forecasting.py`: LSTM
- `src/transformer_forecasting.py`: Transformer
- `src/consumer_segmentation.py`: KMeans and DBSCAN
- `src/explainable_ai.py`: SHAP
- `src/data_drift_monitor.py`: Evidently or fallback statistical drift
- `src/model_optimizer.py`: Optuna

### Why these models were selected overall

- Isolation Forest is good for rare abnormal patterns
- Random Forest is reliable for tabular classification
- XGBoost improves theft scoring on structured data
- LSTM and Transformer are suitable for time-series forecasting
- KMeans and DBSCAN help group consumers and identify unusual clusters
- SHAP improves trust by explaining predictions
- Evidently helps monitor production data quality and drift
- Optuna improves model settings automatically
