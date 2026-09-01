@echo off
cd /d "%~dp0"
echo ========================================
echo TradePilot Desktop Alpha 0.10.0 Setup
echo ========================================

if not exist ".env" if exist "C:\etoro-bot\.env" (
  echo Kopiere bestehende eToro/OpenAI Konfiguration...
  copy /Y "C:\etoro-bot\.env" ".env" >nul
)
if not exist "stock_universe.json" if exist "C:\etoro-bot\stock_universe.json" (
  echo Kopiere Aktienuniversum...
  copy /Y "C:\etoro-bot\stock_universe.json" "stock_universe.json" >nul
)
if not exist "instrument_ids.json" if exist "C:\etoro-bot\instrument_ids.json" (
  echo Kopiere Instrument-Cache...
  copy /Y "C:\etoro-bot\instrument_ids.json" "instrument_ids.json" >nul
)

if not exist ".venv\Scripts\python.exe" (
  echo Erstelle Python-Umgebung...
  python -m venv .venv
)

echo Installiere/aktualisiere Abhaengigkeiten...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation fehlgeschlagen.
  pause
  exit /b 1
)

echo Starte TradePilot...
.venv\Scripts\python.exe main.py
