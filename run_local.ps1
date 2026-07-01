# run_local.ps1 — start the full stack locally (Windows PowerShell)
# Run from the job-search-app directory: .\run_local.ps1

Write-Host "=== Job Search Pipeline — Local Dev ===" -ForegroundColor Cyan

if (-not (Test-Path "requirements.txt")) {
    Write-Host "ERROR: run this from the job-search-app directory" -ForegroundColor Red
    exit 1
}

# IMPORTANT: no --reload. The pipeline writes to data\jobs.db, and uvicorn's
# reload watcher restarts the server mid-request, causing "Cannot reach backend".
Write-Host "Starting FastAPI backend on :8000 (no reload)..." -ForegroundColor Green
$backend = Start-Process -PassThru -NoNewWindow uvicorn `
    -ArgumentList "backend.main:app","--host","0.0.0.0","--port","8000"

Start-Sleep -Seconds 2

Write-Host "Starting Streamlit on :8501..." -ForegroundColor Green
streamlit run frontend/app.py --server.port 8501 --browser.gatherUsageStats false

Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
