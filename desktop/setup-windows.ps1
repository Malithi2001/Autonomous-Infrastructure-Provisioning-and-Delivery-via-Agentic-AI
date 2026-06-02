param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "Missing required command: $Name" -ForegroundColor Red
        Write-Host $InstallHint
        exit 1
    }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Desktop = Join-Path $Root "desktop"
$BackendVenvPython = Join-Path $Backend "venv\Scripts\python.exe"

Write-Host "Smart DevOps Assistant - Windows desktop setup" -ForegroundColor Green
Write-Host "This installs local dependencies, builds the desktop frontend, packages the backend, and optionally creates the installer."

Require-Command "python" "Install Python 3.11 or newer from https://www.python.org/downloads/ and enable Add Python to PATH."
Require-Command "node" "Install Node.js LTS from https://nodejs.org/."
Require-Command "npm" "npm is included with Node.js LTS."

Write-Step "Creating backend virtual environment"
if (-not (Test-Path $BackendVenvPython)) {
    Push-Location $Backend
    python -m venv venv
    Pop-Location
}

Write-Step "Installing backend dependencies"
& $BackendVenvPython -m pip install --upgrade pip
& $BackendVenvPython -m pip install -r (Join-Path $Backend "requirements.txt")

Write-Step "Installing frontend dependencies"
Push-Location $Frontend
if (Test-Path "package-lock.json") {
    npm ci
} else {
    npm install
}
Pop-Location

Write-Step "Installing desktop packaging dependencies"
Push-Location $Desktop
if (Test-Path "package-lock.json") {
    npm ci
} else {
    npm install
}
Pop-Location

Write-Step "Building desktop frontend"
Push-Location $Frontend
$env:VITE_DESKTOP_MODE = "true"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run build
Pop-Location

Write-Step "Building backend executable"
Push-Location $Backend
$env:DESKTOP_MODE = "true"
$env:DISABLE_AUTH = "true"
& $BackendVenvPython -m PyInstaller pyinstaller.spec
Pop-Location

if (-not $SkipInstaller) {
    Write-Step "Building Windows installer"
    Push-Location $Desktop
    npm run build:win
    Pop-Location

    Write-Host ""
    Write-Host "Installer created in: $Desktop\dist" -ForegroundColor Green
    Get-ChildItem (Join-Path $Desktop "dist") -Filter "*.exe" | ForEach-Object {
        Write-Host " - $($_.FullName)" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "Skipped installer build. You can run the app from source with:" -ForegroundColor Yellow
    Write-Host "  .\desktop\run-desktop.ps1"
}

Write-Host ""
Write-Host "Done. Desktop mode opens without login as Desktop User." -ForegroundColor Green
