$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js and npm first."
}

$LogDir = Join-Path $Root ".dev-logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$PreviousChaosEnabled = $env:CHAOS_ENABLED
$env:CHAOS_ENABLED = "true"
$Processes = @()
try {
    Write-Host "Starting loopback demo services on ports 5001-5003..."
    $Processes += Start-Process -FilePath $Python -ArgumentList @("-m", "backend.demo_services.launcher") `
        -WorkingDirectory $Root -RedirectStandardOutput (Join-Path $LogDir "demo-services.log") `
        -RedirectStandardError (Join-Path $LogDir "demo-services-error.log") -PassThru

    Write-Host "Starting backend on http://127.0.0.1:5000 (CHAOS_ENABLED=true, local dev only)..."
    $Processes += Start-Process -FilePath $Python -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "5000", "--reload") `
        -WorkingDirectory $Root -RedirectStandardOutput (Join-Path $LogDir "backend.log") `
        -RedirectStandardError (Join-Path $LogDir "backend-error.log") -PassThru

    Write-Host "Starting frontend on http://localhost:3000..."
    $Processes += Start-Process -FilePath $env:ComSpec -ArgumentList @("/c", "npm run dev -- --host 127.0.0.1") `
        -WorkingDirectory $Root -RedirectStandardOutput (Join-Path $LogDir "frontend.log") `
        -RedirectStandardError (Join-Path $LogDir "frontend-error.log") -PassThru

    Write-Host "OpsPilot is starting. Logs are in .dev-logs. Press Ctrl-C to stop."
    while ($Processes | Where-Object { -not $_.HasExited }) {
        Start-Sleep -Seconds 1
    }
    throw "A development process exited unexpectedly."
}
finally {
    foreach ($Process in $Processes) {
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force
        }
    }
    if ($null -eq $PreviousChaosEnabled) {
        Remove-Item Env:CHAOS_ENABLED -ErrorAction SilentlyContinue
    } else {
        $env:CHAOS_ENABLED = $PreviousChaosEnabled
    }
}
