@echo off
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\backend\configure.py" --data-dir "%LOCALAPPDATA%\RNGDashboardNext"
pause
