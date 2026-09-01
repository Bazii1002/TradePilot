@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 "%~dp061_TEST_POST_RELEASE_ACTUAL_REFRESH_OFFLINE.py") || python "%~dp061_TEST_POST_RELEASE_ACTUAL_REFRESH_OFFLINE.py"
pause
