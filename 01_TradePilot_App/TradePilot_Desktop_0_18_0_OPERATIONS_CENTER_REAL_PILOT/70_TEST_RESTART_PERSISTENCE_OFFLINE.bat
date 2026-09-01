@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 70_TEST_RESTART_PERSISTENCE_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
