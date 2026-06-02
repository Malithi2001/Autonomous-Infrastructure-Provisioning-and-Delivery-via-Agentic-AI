$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Desktop = Join-Path $Root "desktop"
$BackendVenvPython = Join-Path $Backend "venv\Scripts\python.exe"
$FrontendIndex = Join-Path $Frontend "dist\index.html"

if (-not (Test-Path $BackendVenvPython)) {
    Write-Host "Backend virtual environment is missing. Run .\desktop\setup-windows.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FrontendIndex)) {
    Write-Host "Frontend build is missing. Run .\desktop\setup-windows.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $Desktop "node_modules"))) {
    Write-Host "Desktop dependencies are missing. Run .\desktop\setup-windows.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Smart DevOps Assistant in desktop mode..." -ForegroundColor Green

$env:DESKTOP_MODE = "true"
$env:DISABLE_AUTH = "true"
$env:HOST = "127.0.0.1"
$env:PORT = "8000"
$env:SMART_DEVOPS_SKIP_BACKEND = "true"

$backendProcess = Start-Process `
    -FilePath $BackendVenvPython `
    -ArgumentList "run_backend.py" `
    -WorkingDirectory $Backend `
    -PassThru `
    -WindowStyle Minimized

try {
    Start-Sleep -Seconds 3
    Push-Location $Desktop
    npm start
    Pop-Location
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
}
