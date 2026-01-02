@echo off
:: Run GUI Tests
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m pytest tests/test_gui.py -v
pause
