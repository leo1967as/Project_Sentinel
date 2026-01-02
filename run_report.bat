@echo off
:: ===============================================================================
:: PROJECT SENTINEL - DAILY REPORT LAUNCHER
:: ===============================================================================
:: Run this manually or schedule via Task Scheduler for 05:00 AM
:: ===============================================================================

title Project Sentinel - Daily Report

echo ============================================================
echo   PROJECT SENTINEL - DAILY REPORT
echo ============================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python daily_report.py

echo.
echo Report generation complete.
timeout /t 5
