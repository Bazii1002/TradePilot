@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 67_TEST_OPERATIONS_CENTER_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
