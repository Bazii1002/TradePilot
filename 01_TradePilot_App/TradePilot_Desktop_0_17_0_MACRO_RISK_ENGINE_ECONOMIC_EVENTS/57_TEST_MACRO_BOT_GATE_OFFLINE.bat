@echo off
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
%PY% "57_TEST_MACRO_BOT_GATE_OFFLINE.py"
pause
