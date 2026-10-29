$ErrorActionPreference = 'Stop'
Start-Process wscript.exe -ArgumentList ('"' + (Join-Path $PSScriptRoot 'StartHidden.vbs') + '"')
$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $Health = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
        if ($Health.ready) { $Ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (!$Ready) { throw 'The server did not start. Check %LOCALAPPDATA%\RNGDashboardNext\server-errors.log.' }
$Edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Edge) { Start-Process $Edge -ArgumentList '--app=http://127.0.0.1:8765 --window-size=1280,900' } else { Start-Process 'http://127.0.0.1:8765' }
