@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 "%~dp059_TEST_CALENDAR_HARDENING_OFFLINE.py") || python "%~dp059_TEST_CALENDAR_HARDENING_OFFLINE.py"
pause
