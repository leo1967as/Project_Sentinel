@echo off
:: ===============================================================================
:: PROJECT SENTINEL - GUARDIAN LAUNCHER
:: ===============================================================================
:: Runs the main guardian with proper Python venv
:: ===============================================================================

title Project Sentinel - Risk Guardian

echo ============================================================
echo   PROJECT SENTINEL - RISK GUARDIAN
echo ============================================================
echo.

cd /d "%~dp0"

:: Check for venv - use dir command for reliable detection
dir /b ".venv\Scripts\activate.bat" >nul 2>&1
if %errorlevel% equ 0 (
    echo Activating virtual environment...
    call ".venv\Scripts\activate.bat"
) else (
    echo WARNING: No .venv found. Using system Python.
    echo Run setup.bat first to create venv.
    echo.
)

:: Run main guardian
echo Starting Guardian...
echo.
python main_guardian.py

:: Keep open on error
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   ERROR: Guardian stopped unexpectedly
    echo ============================================================
    pause
)
