# Test Full Scope Generation Flow
$baseUrl = "http://localhost:8001/api"
$ingestionUrl = "http://localhost:8000/v1"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Testing Full Scope Generation Flow" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Test Backend API Health
Write-Host "1. Testing Backend API Health..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "$baseUrl/health/live" -UseBasicParsing
    Write-Host "   ✅ Backend API is healthy" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Backend API health check failed" -ForegroundColor Red
    exit 1
}

# Step 2: Test Ingestion Service Health
Write-Host "2. Testing Ingestion Service Health..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "$ingestionUrl/../healthz" -UseBasicParsing
    Write-Host "   ✅ Ingestion Service is healthy" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Ingestion Service health check failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "All services are healthy!" -ForegroundColor Green
