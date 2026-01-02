@echo off
:: ===============================================================================
:: PROJECT SENTINEL - GUI APPLICATION
:: ===============================================================================

title Project Sentinel - GUI

echo ============================================================
echo   PROJECT SENTINEL - GUI DASHBOARD
echo ============================================================
echo.

cd /d "%~dp0"

:: Check for venv
dir /b ".venv\Scripts\python.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo Starting GUI...
    .\.venv\Scripts\python.exe app.py
) else (
    echo ERROR: .venv not found. Run setup.bat first.
    pause
)
