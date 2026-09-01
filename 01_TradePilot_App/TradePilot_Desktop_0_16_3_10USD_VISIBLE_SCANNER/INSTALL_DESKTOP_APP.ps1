$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'TradePilot.lnk'
$launcher = Join-Path $appDir 'TradePilot_Launcher.vbs'
$icon = Join-Path $appDir 'assets\ui\TradePilot.ico'

# Verify Python + PySide6 before creating shortcut
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python wurde nicht gefunden. TradePilot benoetigt die bestehende Python-Installation.' }
& python -c "import PySide6; import yfinance; print('Python/PySide6/yfinance: OK')"
if ($LASTEXITCODE -ne 0) { throw 'Python-Abhaengigkeiten fehlen. Fuehre zuerst 03_INSTALL_PYSIDE6_IF_NEEDED.bat aus.' }

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = "$env:WINDIR\System32\wscript.exe"
$sc.Arguments = '"' + $launcher + '"'
$sc.WorkingDirectory = $appDir
$sc.IconLocation = $icon
$sc.Description = 'TradePilot Production REAL Core 0.16.0'
$sc.Save()

Write-Host ''
Write-Host 'TRADEPILOT DESKTOP APP INSTALLIERT' -ForegroundColor Green
Write-Host ('Verknuepfung: ' + $shortcutPath)
Write-Host ('App-Ordner:   ' + $appDir)
Write-Host ''
Write-Host 'Ab jetzt TradePilot ueber das Desktop-Icon starten.' -ForegroundColor Cyan
