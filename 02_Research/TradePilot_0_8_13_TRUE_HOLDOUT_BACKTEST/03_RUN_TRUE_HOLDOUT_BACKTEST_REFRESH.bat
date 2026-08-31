@echo off
cd /d "%~dp0"
python TradePilot_Prepare_TRUE_HOLDOUT_0_8_13.py
if errorlevel 1 goto :error
python TradePilot_TRUE_HOLDOUT_Core_0_8_13.py --universe holdout --workers 8 --batch-size 25 --refresh-cache --cache-dir C:\TradePilot\03_Research_Data\holdout_cache_0_8_13
if errorlevel 1 goto :error
python TradePilot_Evaluate_TRUE_HOLDOUT_0_8_13.py
if errorlevel 1 goto :error
pause
exit /b 0
:error
pause
exit /b 1
