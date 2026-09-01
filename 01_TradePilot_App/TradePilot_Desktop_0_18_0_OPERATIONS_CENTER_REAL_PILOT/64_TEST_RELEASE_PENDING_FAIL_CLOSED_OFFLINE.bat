@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 64_TEST_RELEASE_PENDING_FAIL_CLOSED_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
