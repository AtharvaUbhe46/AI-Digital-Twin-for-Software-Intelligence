try {
    $o = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "Ollama: ONLINE, models: $($o.models.name -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "Ollama: OFFLINE ($($_.Exception.Message))" -ForegroundColor Red
}

try {
    $b = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/assistant/status" -TimeoutSec 3
    Write-Host "Backend: ONLINE, connected=$($b.connected), model=$($b.model), model_available=$($b.model_available)" -ForegroundColor Green
} catch {
    Write-Host "Backend: OFFLINE ($($_.Exception.Message))" -ForegroundColor Red
}

try {
    $f = Invoke-WebRequest -Uri "http://localhost:5173/" -TimeoutSec 3
    Write-Host "Frontend: ONLINE (HTTP $($f.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "Frontend: OFFLINE ($($_.Exception.Message))" -ForegroundColor Red
}
