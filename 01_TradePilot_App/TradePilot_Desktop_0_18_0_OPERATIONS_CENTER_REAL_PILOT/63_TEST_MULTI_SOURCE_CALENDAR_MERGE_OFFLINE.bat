@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python 63_TEST_MULTI_SOURCE_CALENDAR_MERGE_OFFLINE.py
if errorlevel 1 pause & exit /b 1
pause
