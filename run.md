# Complete Project Run Guide

## Project folder

Open PowerShell and go to the project directory:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
```

## Python interpreter

Use this Python interpreter:

```powershell
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
```

Check that it works:

```powershell
& $PYTHON --version
```

## First-time setup

Create the environment file if needed:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Install project dependencies:

```powershell
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
```

## Generate data and train models

Run this once before starting the full project:

```powershell
& $PYTHON run_project.py
```

Optional: run tests

```powershell
& $PYTHON -m pytest
```

## Run the complete project

Use two PowerShell terminals.

### Terminal 1: Backend

If port `8000` is already in use, stop the old backend first:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*uvicorn api.main:app*8000*' } | Select-Object ProcessId, CommandLine
Stop-Process -Id <PID> -Force
```

Run these commands in this order:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

If `8000` is busy and you do not want to stop the old process, use:

```powershell
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### Terminal 2: Frontend

Run these commands in this order:

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
Set-Location dashboard
& $PYTHON -m http.server 8080
```

Frontend URL:

```text
http://127.0.0.1:8080
```

## Login page

Open this link in the browser if using port `8000`:

```text
http://127.0.0.1:8000/login
```

Or this link if using port `8001`:

```text
http://127.0.0.1:8001/login
```

You can also open:

```text
http://127.0.0.1:8000
```

It now redirects to the login page first.

## Exact command order

If you want the full command order from start to finish, use this:

### Terminal 1

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
& $PYTHON --version
& $PYTHON -m pip install -r requirements.txt
& $PYTHON -m pip install -r requirements-test.txt
& $PYTHON run_project.py
& $PYTHON -m pytest
& $PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2

```powershell
cd "c:\Users\vishn\Desktop\College\SEMISTER\CSE 6th SEM\Data Science\Project 1\electricity_theft_and_anomaly_detection"
$PYTHON = "C:\Users\vishn\AppData\Local\Programs\Python\Python310\python.exe"
Set-Location dashboard
& $PYTHON -m http.server 8080
```

## Final URLs

- Login page on `8000`: `http://127.0.0.1:8000/login`
- Login page on `8001`: `http://127.0.0.1:8001/login`
- Backend API on `8000`: `http://127.0.0.1:8000`
- Backend API on `8001`: `http://127.0.0.1:8001`
- Frontend static server: `http://127.0.0.1:8080`
