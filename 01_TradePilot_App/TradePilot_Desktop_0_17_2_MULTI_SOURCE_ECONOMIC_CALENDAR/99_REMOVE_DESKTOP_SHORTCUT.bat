@echo off
powershell -NoProfile -Command "$p=Join-Path ([Environment]::GetFolderPath('Desktop')) 'TradePilot.lnk'; if(Test-Path $p){Remove-Item -Force $p; Write-Host 'TradePilot Desktop-Verknuepfung entfernt.'} else {Write-Host 'Keine TradePilot-Verknuepfung gefunden.'}"
pause
