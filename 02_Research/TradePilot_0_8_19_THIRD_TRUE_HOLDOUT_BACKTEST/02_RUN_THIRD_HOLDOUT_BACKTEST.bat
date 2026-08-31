@echo off
cd /d "%~dp0"
python TradePilot_Prepare_THIRD_HOLDOUT_0_8_19.py
if errorlevel 1 goto :error
python TradePilot_THIRD_HOLDOUT_Core_0_8_19.py --universe third_holdout --workers 8 --batch-size 25 --cache-dir C:\TradePilot\03_Research_Data\holdout_cache_0_8_19
if errorlevel 1 goto :error
python TradePilot_Evaluate_THIRD_HOLDOUT_0_8_19.py
if errorlevel 1 goto :error
echo.
echo THIRD TRUE HOLDOUT 0.8.19 abgeschlossen.
pause
exit /b 0
:error
echo.
echo FEHLER - Lauf abgebrochen. Siehe Meldung oben.
pause
exit /b 1
