@echo off
cd /d "%~dp0"
python TradePilot_Prepare_THIRD_HOLDOUT_0_8_19.py
if errorlevel 1 goto :error
python TradePilot_THIRD_HOLDOUT_Core_0_8_19.py --universe third_holdout --workers 8 --batch-size 25 --cache-dir C:\TradePilot\03_Research_Data\holdout_cache_0_8_19 --clear-cache
if errorlevel 1 goto :error
python TradePilot_Evaluate_THIRD_HOLDOUT_0_8_19.py
if errorlevel 1 goto :error
pause
exit /b 0
:error
pause
exit /b 1
