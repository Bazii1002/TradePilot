@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 69_TEST_AUDIT_AND_REAL_LOCK_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
