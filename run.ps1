Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "   Starting DoorKnock (敲門) Server...   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "Web UI & API running at: http://localhost:8000" -ForegroundColor Green
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
