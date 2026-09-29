# Start all services for AI Digital Twin for Software Intelligence
$rootDir = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting AI Digital Twin Services (Phase 7 - AI Assistant)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Ollama (if not running)
$ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaProc) {
    $ollamaExe = "C:\Users\Sandesh\AppData\Local\Programs\Ollama\ollama.exe"
    if (Test-Path $ollamaExe) {
        Write-Host "[1/3] Starting Ollama server daemon..." -ForegroundColor Yellow
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } else {
        Write-Host "[1/3] Ollama executable not found at $ollamaExe" -ForegroundColor Red
    }
} else {
    Write-Host "[1/3] Ollama server is already running." -ForegroundColor Green
}

# 2. Start Backend FastAPI
$backendPortConn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $backendPortConn) {
    Write-Host "[2/3] Starting FastAPI backend on http://localhost:8000..." -ForegroundColor Yellow
    $backendDir = Join-Path $rootDir "backend"
    $pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
    Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory $backendDir -WindowStyle Hidden
    Start-Sleep -Seconds 4
} else {
    Write-Host "[2/3] Backend is already running on port 8000." -ForegroundColor Green
}

# 3. Start Frontend Vite Dev Server
$frontendPortConn = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if (-not $frontendPortConn) {
    Write-Host "[3/3] Starting Frontend Vite dev server on http://localhost:5173..." -ForegroundColor Yellow
    $frontendDir = Join-Path $rootDir "frontend"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $frontendDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[3/3] Frontend is already running on port 5173." -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Service URLs:" -ForegroundColor Green
Write-Host "  Frontend (Vite UI):       http://localhost:5173" -ForegroundColor White
Write-Host "  Backend API (FastAPI):   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs (Swagger UI):   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Ollama Local Service:    http://localhost:11434" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
