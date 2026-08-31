@echo off
cd /d "%~dp0"
python TradePilot_Prepare_SECOND_HOLDOUT_0_8_15.py
if errorlevel 1 goto :error
python TradePilot_SECOND_HOLDOUT_Core_0_8_15.py --universe second_holdout --workers 8 --batch-size 25 --cache-dir C:\TradePilot\03_Research_Data\holdout_cache_0_8_15 --refresh-cache
if errorlevel 1 goto :error
python TradePilot_Evaluate_SECOND_HOLDOUT_0_8_15.py
if errorlevel 1 goto :error
pause
exit /b 0
:error
echo FEHLER - Lauf abgebrochen.
pause
exit /b 1
