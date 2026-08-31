@echo off
cd /d "%~dp0"
call "%~dp0_run_python.bat" SELFTEST_SCORE_AUDIT.py
pause
