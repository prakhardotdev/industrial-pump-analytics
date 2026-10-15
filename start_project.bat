
@echo off
setlocal
title Industrial Pump Analytics Launcher

cd /d "%~dp0"

echo ==========================================
echo     INDUSTRIAL PUMP ANALYTICS
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ERROR: Frontend package.json not found.
    pause
    exit /b 1
)

echo Starting data ingestion...
start "Pump Ingestion" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -u ingestion\mqtt_to_postgres.py"

timeout /t 2 /nobreak >nul

echo Starting pump simulator...
start "Pump Simulator" /D "%~dp0" cmd /k ".venv\Scripts\python.exe simulator\pump_simulator.py"

timeout /t 2 /nobreak >nul

echo Starting alert engine...
start "Pump Alert Engine" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -u analytics\alert_engine.py"

timeout /t 2 /nobreak >nul

echo Starting FastAPI backend...
start "Pump API" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --reload"

timeout /t 2 /nobreak >nul

echo Starting React dashboard...
start "Pump Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo All startup commands have been launched.
echo Check all five windows for errors.
echo PostgreSQL and Mosquitto must already be running.
echo.
pause
