@echo off
:: ===============================================================================
:: PROJECT SENTINEL - INITIAL SETUP
:: ===============================================================================
:: Creates Python venv and installs dependencies
:: ===============================================================================

title Project Sentinel - Setup

echo ============================================================
echo   PROJECT SENTINEL - INITIAL SETUP
echo ============================================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

:: Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo Installing uv package manager...
    pip install uv
)

:: Create venv
echo.
echo Creating virtual environment...
uv venv .venv

:: Activate venv
call .venv\Scripts\activate.bat

:: Install dependencies
echo.
echo Installing dependencies...
uv pip install -r requirements.txt

:: Run config wizard
echo.
echo ============================================================
echo   CONFIGURATION WIZARD
echo ============================================================
echo.

python config_setup.py

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo   To start the guardian:
echo     run_guardian.bat
echo.
echo   To start data collector:
echo     run_collector.bat
echo.
pause
