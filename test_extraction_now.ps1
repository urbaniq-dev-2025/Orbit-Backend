# Test extraction with the fixed API key configuration

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Testing Scope Extraction" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$API_URL = "http://localhost:8001"
$TEST_EMAIL = "admin@orbit.dev"
$TEST_PASSWORD = "admin123"
$SCOPE_ID = "ff6729fe-650e-49fa-aea7-c3f5d147c495"
$DOCUMENT_ID = "2905c739-c5d2-426a-8c39-e5e4d35ba93c"

# Login
Write-Host "Step 1: Logging in..." -ForegroundColor Yellow
$loginBody = @{
    email = $TEST_EMAIL
    password = $TEST_PASSWORD
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "$API_URL/api/auth/signin" `
    -Method Post `
    -ContentType "application/json" `
    -Body $loginBody

$TOKEN = $loginResponse.access_token
$headers = @{"Authorization" = "Bearer $TOKEN"}
Write-Host "✅ Login successful" -ForegroundColor Green
Write-Host ""

# Trigger Extraction
Write-Host "Step 2: Triggering AI extraction..." -ForegroundColor Yellow
try {
    $extractBody = @{
        uploadId = $DOCUMENT_ID
        extractionType = "full"
        aiModel = "gpt-4o"
        developerLevel = "mid"
        developerExperienceYears = 3
    } | ConvertTo-Json

    $extractResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID/extract" `
        -Method Post `
        -ContentType "application/json" `
        -Headers $headers `
        -Body $extractBody
    
    Write-Host "✅ Extraction triggered!" -ForegroundColor Green
    Write-Host "Extraction ID: $($extractResponse.extractionId)" -ForegroundColor Cyan
    Write-Host "Status: $($extractResponse.status)" -ForegroundColor Gray
    Write-Host "Estimated Time: $($extractResponse.estimatedTime) seconds" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "⏳ Waiting 60 seconds for extraction to complete..." -ForegroundColor Yellow
    Start-Sleep -Seconds 60
} catch {
    Write-Host "❌ Extraction error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Get Sections
Write-Host "Step 3: Getting generated sections..." -ForegroundColor Yellow
try {
    $sectionsResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID/sections" -Method Get -Headers $headers
    Write-Host "✅ Found $($sectionsResponse.Count) sections" -ForegroundColor Green
    
    if ($sectionsResponse.Count -gt 0) {
        Write-Host ""
        Write-Host "Generated Sections:" -ForegroundColor Cyan
        foreach ($section in $sectionsResponse | Sort-Object { $_.orderIndex }) {
            Write-Host "  [$($section.orderIndex + 1)] $($section.title)" -ForegroundColor Green
            if ($section.content) {
                $preview = $section.content.Substring(0, [Math]::Min(150, $section.content.Length))
                Write-Host "      $preview..." -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "⚠️  No sections generated yet. Extraction might still be processing." -ForegroundColor Yellow
    }
    Write-Host ""
} catch {
    Write-Host "❌ Error getting sections: $_" -ForegroundColor Red
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Test Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
