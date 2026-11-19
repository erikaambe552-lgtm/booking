$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = Join-Path $root "backend\venv\Scripts\python.exe" }
if (-not (Test-Path $python)) {
    Write-Host "Backend virtual environment not found. Create backend\.venv or backend\venv first." -ForegroundColor Red
    exit 1
}

Write-Host "1/4 Starting PostgreSQL + Redis (Docker)..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Host "Docker failed. Open Docker Desktop first, then run this again." -ForegroundColor Red; exit 1 }

Write-Host "2/4 Starting Django backend with 1 worker (new window)..." -ForegroundColor Cyan
$backendCommand = "Set-Location '$root\backend'; & '$python' manage.py collectstatic --noinput; if (`$LASTEXITCODE -eq 0) { & '$python' run_server_windows.py --workers 1 }"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

Write-Host "3/4 Building and serving the frontend (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run build; npm run preview"

Write-Host "    Waiting 25 seconds for both to start..."
Start-Sleep -Seconds 25

Write-Host "4/4 Opening the public tunnel (new window)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cloudflared tunnel --url http://localhost:4173"

Write-Host ""
Write-Host "Done. In the cloudflared window, copy the https://....trycloudflare.com link and share it." -ForegroundColor Green
Write-Host "To stop: close the three new windows, then run: docker compose stop"
