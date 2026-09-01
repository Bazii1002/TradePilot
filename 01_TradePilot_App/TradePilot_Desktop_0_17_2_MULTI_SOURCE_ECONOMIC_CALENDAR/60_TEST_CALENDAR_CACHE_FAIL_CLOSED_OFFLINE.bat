@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 "%~dp060_TEST_CALENDAR_CACHE_FAIL_CLOSED_OFFLINE.py") || python "%~dp060_TEST_CALENDAR_CACHE_FAIL_CLOSED_OFFLINE.py"
pause
