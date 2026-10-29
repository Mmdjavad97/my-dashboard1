param([string]$DataDir = "")
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Data = if ($DataDir) { $DataDir } else { Join-Path $env:LOCALAPPDATA 'RNGDashboard' }
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Secrets = Join-Path $Data 'secrets.toml'
if (!(Test-Path $Secrets)) { throw 'Run Setup first.' }
# Hold a Windows file lock for the whole server lifetime; prevent duplicate launches.
try { $Lock = [System.IO.File]::Open((Join-Path $Data 'server.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
catch { exit 0 }
try {
    Set-Location $Root
    $Arguments = @('-m', 'streamlit', 'run', ('"' + (Join-Path $Root 'app.py') + '"'),
        '--server.address=127.0.0.1', '--server.port=8501', '--server.headless=true',
        '--server.fileWatcherType=none', '--browser.gatherUsageStats=false', ('--secrets.files="' + $Secrets + '"'))
    $Process = Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Data 'server.log') -RedirectStandardError (Join-Path $Data 'server-errors.log') -Wait -PassThru
    exit $Process.ExitCode
} finally { $Lock.Dispose() }
