@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 65_SHOW_CALENDAR_PROVIDER_STATUS.py
if errorlevel 1 pause & exit /b 1
pause
