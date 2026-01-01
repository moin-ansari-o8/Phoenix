# UV Sync for Phoenix - SIMPLE VERSION
Write-Host "Phoenix - UV Sync" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

# Check UV
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "UV not found! Install: powershell -c 'irm https://astral.sh/uv/install.ps1 | iex'" -ForegroundColor Red
    exit 1
}

# Check if venv is active
if ($env:VIRTUAL_ENV) {
    Write-Host "Deactivating current environment..." -ForegroundColor Yellow
    deactivate
    Start-Sleep -Seconds 1
}

Write-Host "Running uv sync..." -ForegroundColor Green
uv sync

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDone! Now run:" -ForegroundColor Green
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "  python MainPHNX.py" -ForegroundColor Cyan
} else {
    Write-Host "`nFailed! Try:" -ForegroundColor Red
    Write-Host "  1. Close this terminal" -ForegroundColor Yellow
    Write-Host "  2. Open new terminal" -ForegroundColor Yellow
    Write-Host "  3. Run: uv sync" -ForegroundColor Yellow
}
