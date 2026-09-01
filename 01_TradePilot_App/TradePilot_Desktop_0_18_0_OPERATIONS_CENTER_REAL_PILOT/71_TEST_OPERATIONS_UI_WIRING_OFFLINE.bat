@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 71_TEST_OPERATIONS_UI_WIRING_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
