@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 68_TEST_POSITION_MONITORING_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
