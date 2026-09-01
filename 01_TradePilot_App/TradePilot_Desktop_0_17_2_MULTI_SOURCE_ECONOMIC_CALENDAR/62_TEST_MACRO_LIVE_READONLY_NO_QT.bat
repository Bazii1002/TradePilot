@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 "%~dp062_TEST_MACRO_LIVE_READONLY_NO_QT.py") || python "%~dp062_TEST_MACRO_LIVE_READONLY_NO_QT.py"
pause
