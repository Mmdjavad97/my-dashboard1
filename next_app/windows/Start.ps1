$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Data = Join-Path $env:LOCALAPPDATA 'RNGDashboardNext'
if (!(Test-Path (Join-Path $Data 'dashboard.sqlite3'))) { throw 'Run next_app\windows\Setup.cmd first.' }
try { $Lock = [System.IO.File]::Open((Join-Path $Data 'server.lock'), 'OpenOrCreate', 'ReadWrite', 'None') } catch { exit 0 }
try {
    $env:RNG_DATA_DIR = $Data
    $ArgsText = '-m uvicorn next_app.backend.main:app --host 127.0.0.1 --port 8765 --proxy-headers --forwarded-allow-ips 127.0.0.1'
    $Process = Start-Process -FilePath (Join-Path $Root 'next_app\.venv\Scripts\python.exe') -ArgumentList $ArgsText -WorkingDirectory $Root -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput (Join-Path $Data 'server.log') -RedirectStandardError (Join-Path $Data 'server-errors.log')
    $Result = $Process.ExitCode
} finally { $Lock.Dispose() }
exit $Result
