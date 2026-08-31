@echo off
cd /d "%~dp0"
call "%~dp0_run_python.bat" TradePilot_Backtest_0_8_5_SCORE_AUDIT.py --universe sp500-350
pause
