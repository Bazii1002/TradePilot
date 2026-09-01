@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 66_TEST_TRADINGECONOMICS_ADAPTER_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
