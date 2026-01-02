@echo off
:: ===============================================================================
:: PROJECT SENTINEL - DATA COLLECTOR LAUNCHER
:: ===============================================================================

title Project Sentinel - Data Collector

echo ============================================================
echo   PROJECT SENTINEL - DATA COLLECTOR
echo ============================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python data_collector.py

if errorlevel 1 (
    echo.
    echo ERROR: Data Collector stopped unexpectedly
    pause
)
