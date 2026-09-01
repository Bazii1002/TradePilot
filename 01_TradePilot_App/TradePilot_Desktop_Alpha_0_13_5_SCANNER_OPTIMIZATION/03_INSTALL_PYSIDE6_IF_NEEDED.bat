@echo off
cd /d "%~dp0"
echo ======================================================================================
echo TRADEPILOT 0.13.0 - ABHAENGIGKEITEN INSTALLIEREN / AKTUALISIEREN
echo ======================================================================================
python -m pip install --upgrade -r requirements.txt
pause
