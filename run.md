# Project Run Guide

## 1. Open terminal in project folder

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_detection - Copy"
```

## 2. Create `.env` file

```powershell
Copy-Item .env.example .env
```

## 3. Install main dependencies

```powershell
python -m pip install -r requirements.txt
```

## 4. Install test dependencies

```powershell
python -m pip install -r requirements-test.txt
```

## 5. Optional: install advanced dependencies

Install this only if you want optional features like Optuna, PyTorch, Evidently, and pandapower.

```powershell
python -m pip install -r requirements-advanced.txt
```

## 6. Generate data and train models

This is the main command for first run.

```powershell
python run_project.py
```

This command:

- Generates smart meter data
- Trains anomaly detection model
- Trains theft detection models
- Trains forecasting models
- Creates heatmap
- Generates sample outputs
- Generates report

## 7. Run tests

```powershell
python -m pytest
```

## 8. Start the API server

After models and dataset are created, run:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

API will run at:

```text
http://127.0.0.1:8000
```

## 9. Open the dashboard

Open this file in browser:

```powershell
Start-Process .\dashboard\index.html
```

## 10. Check API health

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

## Important optional commands

### Run only data generation

```powershell
python run_project.py --skip-training
```

### Run full-scale dataset generation

```powershell
python run_project.py --full-scale
```

### Run optimization before training

```powershell
python run_project.py --optimize-models --optimization-trials 12
```

### Generate data, train models, and start API together

```powershell
python run_project.py --start-api
```

## Recommended execution order

```powershell
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m pip install -r requirements-test.txt
python run_project.py
python -m pytest
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
Start-Process .\dashboard\index.html
```
