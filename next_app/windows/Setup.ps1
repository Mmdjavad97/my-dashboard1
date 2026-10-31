$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Data = Join-Path $env:LOCALAPPDATA 'RNGDashboardNext'
if (!(Get-Command py.exe -ErrorAction SilentlyContinue)) { throw 'Install Python 3.12 (64-bit) including the Python launcher, then retry.' }
& py.exe -3.12 -c 'import sys; assert sys.version_info[:2] == (3,12)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. It can be installed alongside other versions.' }
$Venv = Join-Path $Root 'next_app\.venv'
if (!(Test-Path (Join-Path $Venv 'Scripts\python.exe'))) {
    & py.exe -3.12 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
$Python = Join-Path $Venv 'Scripts\python.exe'
& $Python -m pip install --no-index --require-hashes --find-links (Join-Path $PSScriptRoot 'wheels') -r (Join-Path $PSScriptRoot 'requirements-offline.txt')
if ($LASTEXITCODE -ne 0) { throw 'Offline dependencies could not be installed. Verify Python 3.12 (64-bit), the complete ZIP, and the error above.' }
if (!(Test-Path (Join-Path $Root 'next_app\frontend\dist\index.html'))) { throw 'The built interface is missing. Use the complete release ZIP.' }
New-Item -ItemType Directory -Force -Path $Data | Out-Null
$Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $Data '/inheritance:r' '/grant:r' ($Identity + ':(OI)(CI)F') 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not protect the private data folder.' }
& $Python (Join-Path $Root 'next_app\backend\configure.py') --data-dir $Data
if ($LASTEXITCODE -ne 0) { throw 'Migration did not finish. Preserve any database/export and keep using the original cloud app.' }
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'RNG Dashboard Next.lnk'))
$Shortcut.TargetPath = 'powershell.exe'
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'Open.ps1') + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.IconLocation = Join-Path $Root 'next_app\frontend\dist\app-icons\rng.ico'
$Shortcut.Save()
$Startup = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'RNG Dashboard Next Server.lnk'))
$Startup.TargetPath = 'wscript.exe'
$Startup.Arguments = '"' + (Join-Path $PSScriptRoot 'StartHidden.vbs') + '"'
$Startup.WorkingDirectory = $Root
$Startup.Save()
try {
    $ArgsText = '"' + (Join-Path $Root 'server\windows\backup.py') + '" --data-dir "' + $Data + '"'
    $Action = New-ScheduledTaskAction -Execute $Python -Argument $ArgsText -WorkingDirectory $Root
    $Trigger = New-ScheduledTaskTrigger -Daily -At '19:00'
    $Principal = New-ScheduledTaskPrincipal -UserId $Identity -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName 'RNG Dashboard Next Daily Backup' -Action $Action -Trigger $Trigger -Principal $Principal -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable) -Force | Out-Null
} catch { Write-Warning 'Daily backup scheduling failed. Use Backup.cmd manually until configured.' }
Write-Host 'Setup complete. Open RNG Dashboard Next from your desktop.'
Write-Host 'The server starts at Windows sign-in. Keep this account signed in and the server awake.'
