# MEETME — Full Stack Runner
Write-Host "Starting MEETME — AI Meeting Intelligence & Autonomous Execution Platform..." -ForegroundColor Yellow

$env:PYTHONPATH="."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting MEETME FastAPI Backend on port 8000...' -ForegroundColor Cyan; `$env:PYTHONPATH='.'; .\venv\Scripts\Activate.ps1; python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting MEETME Next.js Frontend on port 3000...' -ForegroundColor Green; cd frontend; npm run dev"

Write-Host "MEETME servers launched!" -ForegroundColor Green
Write-Host "Backend API: http://127.0.0.1:8000/docs"
Write-Host "Frontend App: http://127.0.0.1:3000"
