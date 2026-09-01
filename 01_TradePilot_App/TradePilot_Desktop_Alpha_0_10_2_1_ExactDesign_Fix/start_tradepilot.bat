@echo off
cd /d "%~dp0"
echo Starte TradePilot 0.10.2.1...
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
) else (
  python main.py
)
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo ========================================
  echo TradePilot wurde mit Fehlercode %ERR% beendet.
  echo Bitte diese Fehlermeldung nicht schliessen.
  echo ========================================
  pause
)
