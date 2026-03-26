# Project Run Guide

## 1. Open terminal in project folder

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
```

## 2. Set the Python interpreter

If `python` works on your machine, you can use it directly.
On this system, use:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
```

## 3. Create `.env` if needed

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

## 4. Install dependencies

Main dependencies:

```powershell
& $PYTHON -m pip install -r requirements.txt
```

Test dependencies:

```powershell
& $PYTHON -m pip install -r requirements-test.txt
```

Optional advanced dependencies:

```powershell
& $PYTHON -m pip install -r requirements-advanced.txt
```

## 5. Generate data and train models

Run this once on first setup, or again if you want to regenerate artifacts:

```powershell
& $PYTHON run_project.py
```

This command:

- Generates synthetic smart meter data
- Trains anomaly, theft, and forecasting models
- Generates the heatmap
- Exports sample outputs
- Generates the daily report

## 6. Start the backend

Run the FastAPI server:

```powershell
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

## 7. Start the frontend

Serve the dashboard as a static site from the `dashboard` folder:

```powershell
Set-Location dashboard
& $PYTHON -m http.server 8080
```

Frontend URL:

```text
http://127.0.0.1:8080/index.html
```

After opening the dashboard, keep the API base URL set to:

```text
http://127.0.0.1:8000
```

## 8. Run the complete project

Use two terminals.

Terminal 1: backend

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2: frontend

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
Set-Location dashboard
& $PYTHON -m http.server 8080
```

Then open:

```text
http://127.0.0.1:8080/index.html
```

## 9. Useful optional commands

Generate data only:

```powershell
& $PYTHON run_project.py --skip-training
```

Generate full-scale dataset:

```powershell
& $PYTHON run_project.py --full-scale
```

Run optimization before training:

```powershell
& $PYTHON run_project.py --optimize-models --optimization-trials 12
```

Generate artifacts and start only the API:

```powershell
& $PYTHON run_project.py --start-api
```

Run tests:

```powershell
& $PYTHON -m pytest
```

## Recommended execution order

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

In a second terminal:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection\dashboard"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python311\python.exe"
& $PYTHON -m http.server 8080
```
