$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
$VenvDir = Join-Path $ProjectDir ".venv"
$RequirementsFile = Join-Path $ProjectDir "requirements.txt"
$MainScript = Join-Path $ProjectDir "lyra\main.py"

Write-Host "Checking virtual environment..." -ForegroundColor Cyan

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

# Activate venv
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    . $ActivateScript
} else {
    Write-Host "Failed to find activate script at $ActivateScript" -ForegroundColor Red
    exit 1
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r $RequirementsFile --quiet

Write-Host "Starting LYRA..." -ForegroundColor Green
python $MainScript
