$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Data = Join-Path $env:LOCALAPPDATA 'RNGDashboard'
if (!(Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw 'Install Python 3.12 for Windows from python.org, including the Python launcher, then run Setup again.'
}
& py.exe -3.12 -c 'import sys; assert sys.version_info[:2] == (3,12)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install it, then rerun Setup.' }
if (!(Test-Path (Join-Path $Root '.venv\Scripts\python.exe'))) {
    & py.exe -3.12 -m venv (Join-Path $Root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
$Python = Join-Path $Root '.venv\Scripts\python.exe'
& $Python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependencies could not be installed. Check internet access, then rerun Setup.' }
New-Item -ItemType Directory -Force -Path $Data | Out-Null
# Protect records, exported files and credential hashes under this Windows account.
$Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $Data '/inheritance:r' '/grant:r' ($Identity + ':(OI)(CI)F') 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not secure the data folder permissions.' }
if (!(Test-Path (Join-Path $Data 'secrets.toml'))) {
    & $Python (Join-Path $PSScriptRoot 'migrate.py') --data-dir $Data
    if ($LASTEXITCODE -ne 0) { throw 'Migration did not complete. Your cloud data remains unchanged.' }
}
& $Python (Join-Path $PSScriptRoot 'check_install.py') --data-dir $Data
if ($LASTEXITCODE -ne 0) { throw 'Local installation verification did not pass. Keep the database and backups intact.' }
$Shell = New-Object -ComObject WScript.Shell
$DesktopLink = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'RNG Dashboard.lnk'))
$DesktopLink.TargetPath = 'powershell.exe'
$DesktopLink.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'Open.ps1') + '"'
$DesktopLink.WorkingDirectory = $Root
$DesktopLink.Save()
$Startup = [Environment]::GetFolderPath('Startup')
$StartupLink = $Shell.CreateShortcut((Join-Path $Startup 'RNG Dashboard Server.lnk'))
$StartupLink.TargetPath = 'wscript.exe'
$StartupLink.Arguments = '"' + (Join-Path $PSScriptRoot 'StartHidden.vbs') + '"'
$StartupLink.WorkingDirectory = $Root
$StartupLink.Save()
try {
    $BackupArgs = '"' + (Join-Path $PSScriptRoot 'backup.py') + '" --data-dir "' + $Data + '"'
    $Action = New-ScheduledTaskAction -Execute $Python -Argument $BackupArgs -WorkingDirectory $Root
    $Trigger = New-ScheduledTaskTrigger -Daily -At '19:00'
    $Principal = New-ScheduledTaskPrincipal -UserId $Identity -LogonType Interactive -RunLevel Limited
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
    Register-ScheduledTask -TaskName 'RNG Dashboard Daily Backup' -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
    Write-Host 'Daily backup task installed (runs under your signed-in Windows account).'
} catch { Write-Warning 'Daily scheduling could not be installed. Use Backup.cmd manually until it is configured.' }
Write-Host 'Setup complete. Open RNG Dashboard from your desktop.'
Write-Host 'The server starts when this Windows account signs in. Keep the server awake.'
