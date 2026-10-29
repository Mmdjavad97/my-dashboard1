param([string]$DataDir = '', [string]$Account = '')
$ErrorActionPreference = 'Stop'
if (!$DataDir) { $DataDir = Join-Path $env:LOCALAPPDATA 'RNGDashboard' }
if (!$Account) { $Account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name }
$Admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$Admin) {
    $Arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'),
        '-DataDir', ('"' + $DataDir + '"'), '-Account', ('"' + $Account + '"'))
    Start-Process powershell.exe -Verb RunAs -ArgumentList $Arguments -Wait
    exit
}
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (!(Test-Path (Join-Path $DataDir 'secrets.toml'))) { throw 'Run Setup first under the Windows account that owns the dashboard.' }
# The running application uses the original user's LIMITED account, never SYSTEM.
# S4U allows local-file operation before sign-in without storing that user's password.
$Principal = New-ScheduledTaskPrincipal -UserId $Account -LogonType S4U -RunLevel Limited
$Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'Start.ps1') + '" -DataDir "' + $DataDir + '"'
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $Arguments -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'RNG Dashboard Server' -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
$BackupArgs = '"' + (Join-Path $PSScriptRoot 'backup.py') + '" --data-dir "' + $DataDir + '"'
$BackupAction = New-ScheduledTaskAction -Execute (Join-Path $Root '.venv\Scripts\python.exe') -Argument $BackupArgs -WorkingDirectory $Root
$BackupTrigger = New-ScheduledTaskTrigger -Daily -At '19:00'
$BackupSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName 'RNG Dashboard Daily Backup' -Action $BackupAction -Trigger $BackupTrigger -Principal $Principal -Settings $BackupSettings -Force | Out-Null
Write-Host 'Unattended startup and backups configured for your limited Windows account.'
Write-Host 'The current server keeps running. After your next restart, test access before signing in.'
Write-Host 'Keep the program and database on a local disk; S4U cannot use authenticated network shares.'
