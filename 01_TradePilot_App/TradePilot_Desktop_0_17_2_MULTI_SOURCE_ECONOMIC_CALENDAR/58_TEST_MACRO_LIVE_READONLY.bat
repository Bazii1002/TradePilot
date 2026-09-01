@echo off
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
%PY% "58_TEST_MACRO_LIVE_READONLY.py"
pause
