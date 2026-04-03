# UV Setup Script for Phoenix Assistant
# Run this to set up your environment with uv (faster than pip!)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phoenix Assistant - UV Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if uv is installed
Write-Host "`n[1/4] Checking for uv..." -ForegroundColor Yellow
$uvInstalled = Get-Command uv -ErrorAction SilentlyContinue

if (-not $uvInstalled) {
    Write-Host "UV not found. Installing uv..." -ForegroundColor Yellow
    Write-Host "Run this command first:" -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy ByPass -c 'irm https://astral.sh/uv/install.ps1 | iex'" -ForegroundColor Green
    Write-Host "`nAfter installing, restart PowerShell and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ UV is installed" -ForegroundColor Green
uv --version

# Check Python version
Write-Host "`n[2/4] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "✓ $pythonVersion" -ForegroundColor Green

# Sync dependencies
Write-Host "`n[3/4] Syncing dependencies with uv..." -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  - Create/update virtual environment" -ForegroundColor Cyan
Write-Host "  - Install all dependencies from pyproject.toml" -ForegroundColor Cyan
Write-Host "  - Be much faster than pip install -r requirements.txt" -ForegroundColor Cyan

uv sync

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies synced successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Error syncing dependencies" -ForegroundColor Red
    exit 1
}

# Verify installation
Write-Host "`n[4/4] Verifying installation..." -ForegroundColor Yellow
Write-Host "Activating virtual environment and checking key packages..." -ForegroundColor Cyan

# Activate venv and test imports
& .\.venv\Scripts\python.exe -c @"
import sys
print(f'Python: {sys.version}')

packages_to_check = [
    'pyttsx3',
    'speech_recognition',
    'requests',
    'PIL',
    'pyautogui',
    'keyboard',
]

print('\nChecking key packages:')
for pkg in packages_to_check:
    try:
        __import__(pkg)
        print(f'  ✓ {pkg}')
    except ImportError:
        print(f'  ✗ {pkg} - MISSING')
"@

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nTo activate the environment:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green

Write-Host "`nTo run Phoenix:" -ForegroundColor Yellow
Write-Host "  python MainPHNX.py" -ForegroundColor Green

Write-Host "`nTo update dependencies in the future:" -ForegroundColor Yellow
Write-Host "  uv sync" -ForegroundColor Green

Write-Host "`n✨ Your Phoenix Assistant is ready!" -ForegroundColor Cyan
