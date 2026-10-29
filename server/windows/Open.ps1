$ErrorActionPreference = 'Stop'
Start-Process 'wscript.exe' -ArgumentList ('"' + (Join-Path $PSScriptRoot 'StartHidden.vbs') + '"')
$Ready = $false
for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
    try {
        $Response = Invoke-WebRequest 'http://127.0.0.1:8501/_stcore/health' -UseBasicParsing -TimeoutSec 2
        if ($Response.StatusCode -eq 200) { $Ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (!$Ready) { throw 'The dashboard did not start. Check %LOCALAPPDATA%\RNGDashboard\server.log.' }
$Edge = Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'
if (!(Test-Path $Edge)) { $Edge = Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe' }
if (Test-Path $Edge) { Start-Process $Edge -ArgumentList '--app=http://localhost:8501', '--window-size=1280,900' }
else { Start-Process 'http://localhost:8501' }
