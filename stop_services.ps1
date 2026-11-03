# Stop all services for AI Digital Twin
Write-Host "Stopping AI Digital Twin Services..." -ForegroundColor Yellow

# Stop Frontend (node on port 5173)
$conn = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Frontend process on port 5173." -ForegroundColor Green
}

# Stop Backend (python on port 8000)
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Backend process on port 8000." -ForegroundColor Green
}

# Stop Ollama
$ollama = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollama) {
    Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Ollama process." -ForegroundColor Green
}

Write-Host "All services stopped." -ForegroundColor Cyan
