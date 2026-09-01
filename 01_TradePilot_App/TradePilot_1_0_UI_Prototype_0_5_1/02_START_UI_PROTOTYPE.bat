@echo off
cd /d "%~dp0"
set QT_QUICK_CONTROLS_STYLE=Basic
python main.py
if errorlevel 1 pause
