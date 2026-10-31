$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Windows.Forms
    $Picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $Picker.Description = 'Select your INSTALLED dashboard folder: the folder containing next_app. Do not select this update folder.'
    $Picker.ShowNewFolderButton = $false
    if ($Picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $Root = $Picker.SelectedPath
    $Picker.Dispose()
    $Python = Join-Path $Root 'next_app\.venv\Scripts\python.exe'
    $Open = Join-Path $Root 'next_app\windows\Open.ps1'
    if (!(Test-Path $Python) -or !(Test-Path $Open)) { throw 'This is not the installed dashboard folder. Choose the folder containing next_app and its existing .venv.' }
    $Manifest = Get-Content (Join-Path $PSScriptRoot 'logo-update.json') -Raw | ConvertFrom-Json
    # Check the package and existing program BEFORE stopping or changing anything.
    foreach ($File in $Manifest.files) {
        $Relative = $File.path.Replace('/', '\')
        if ([System.IO.Path]::IsPathRooted($Relative) -or $Relative.Split('\') -contains '..') { throw 'Invalid update path.' }
        $Source = Join-Path (Join-Path $PSScriptRoot 'payload') $Relative
        if (!(Test-Path $Source) -or (Get-FileHash $Source -Algorithm SHA256).Hash.ToLower() -ne $File.sha256) { throw 'The update package is incomplete or damaged. Extract the entire ZIP again.' }
        $Target = Join-Path $Root $Relative
        if (Test-Path $Target) {
            $Current = (Get-FileHash $Target -Algorithm SHA256).Hash.ToLower()
            if ($Current -ne $File.sha256 -and $Current -ne $File.previous) { throw ('Your program version differs at ' + $File.path + '. Nothing was changed. Keep this installation and request an update for its version.') }
        } elseif ($File.previous) { throw ('An existing program file is missing: ' + $File.path) }
    }
    $Data = Join-Path $env:LOCALAPPDATA 'RNGDashboardNext'
    $Backup = Join-Path $Data ('program-updates\rng-logo-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    # Back up PROGRAM files only. Database, exports, passwords and uploads are never touched.
    foreach ($File in $Manifest.files) {
        $Relative = $File.path.Replace('/', '\')
        $Target = Join-Path $Root $Relative
        if (Test-Path $Target) {
            $Copy = Join-Path $Backup $Relative
            New-Item -ItemType Directory -Force -Path (Split-Path $Copy) | Out-Null
            Copy-Item -LiteralPath $Target -Destination $Copy
        }
    }
    $Processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $Python -and $_.CommandLine -match 'uvicorn\s+next_app\.backend\.main:app' })
    foreach ($Process in $Processes) { Stop-Process -Id $Process.ProcessId -ErrorAction Stop }
    # Start.ps1 releases its server lock when the old child exits.
    for ($Try = 0; $Try -lt 30; $Try++) {
        try {
            $Lock = [System.IO.File]::Open((Join-Path $Data 'server.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (!$Lock) { throw 'The old server is still stopping. No program files were replaced. Retry shortly.' }
    $Written = @()
    try {
        foreach ($File in $Manifest.files) {
            $Relative = $File.path.Replace('/', '\')
            $Target = Join-Path $Root $Relative
            New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
            $Written += $Relative
            Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'payload') $Relative) -Destination $Target -Force
        }
    } catch {
        foreach ($Relative in $Written) {
            $Old = Join-Path $Backup $Relative
            $Target = Join-Path $Root $Relative
            if (Test-Path $Old) { Copy-Item -LiteralPath $Old -Destination $Target -Force }
            else { Remove-Item -LiteralPath $Target -Force -ErrorAction SilentlyContinue }
        }
        throw
    } finally { $Lock.Dispose() }
    $ShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'RNG Dashboard Next.lnk'
    if (Test-Path $ShortcutPath) {
        try {
            $Shell = New-Object -ComObject WScript.Shell
            $Shortcut = $Shell.CreateShortcut($ShortcutPath)
            $Shortcut.IconLocation = Join-Path $Root 'next_app\frontend\dist\app-icons\rng.ico'
            $Shortcut.Save()
        } catch { Write-Warning 'The app icons were updated, but the existing desktop shortcut icon could not be refreshed.' }
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Open
    if ($LASTEXITCODE -ne 0) { throw 'Files were updated, but the server did not reopen. Use the existing desktop shortcut and check server-errors.log if necessary.' }
    Write-Host 'RNG Logo update installed. Your database and uploaded files were not changed.'
    Write-Host 'On phone and other PCs, close the app, refresh its HTTPS page, then reinstall the app shortcut if its icon is still old.'
} catch {
    Write-Host ('Update stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
