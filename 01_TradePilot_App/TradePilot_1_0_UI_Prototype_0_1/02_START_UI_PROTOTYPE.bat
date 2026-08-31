@echo off
cd /d "%~dp0"
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo PySide6 fehlt. Installiere es einmalig mit:
  echo python -m pip install PySide6
  echo.
  pause
  exit /b 1
)
python main.py
if errorlevel 1 pause
