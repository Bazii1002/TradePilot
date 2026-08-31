@echo off
setlocal
where python >nul 2>nul
if %errorlevel%==0 (
  python %*
  exit /b %errorlevel%
)
where py >nul 2>nul
if %errorlevel%==0 (
  py %*
  exit /b %errorlevel%
)
echo FEHLER: Python wurde nicht gefunden.
echo Bitte Python installieren und beim Setup "Add Python to PATH" aktivieren.
exit /b 1
