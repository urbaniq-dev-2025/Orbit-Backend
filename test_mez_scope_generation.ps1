# Test script for full scope generation flow with mez.pdf
# This script tests the complete flow: login, create scope, upload document, extract, and verify sections

$ErrorActionPreference = "Stop"

# Configuration
$baseUrl = "http://localhost:8001"
# Try common default credentials
$email = "admin@orbit.dev"
$password = "admin123"
# If that fails, try test user
$tryTestUser = $false
$workspaceId = ""  # Will be fetched
$scopeId = ""
$documentId = ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Testing Full Scope Generation with mez.pdf" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login
Write-Host "Step 1: Logging in..." -ForegroundColor Yellow
$loginSuccess = $false
try {
    $loginBody = @{
        email = $email
        password = $password
    } | ConvertTo-Json

    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/signin" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody `
        -ErrorAction Stop

    $token = $loginResponse.access_token
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type" = "application/json"
    }
    Write-Host "✅ Login successful" -ForegroundColor Green
    $loginSuccess = $true
} catch {
    Write-Host "⚠️  Login with $email failed, trying test@orbit.dev..." -ForegroundColor Yellow
    try {
        $email = "test@orbit.dev"
        $password = "test123456"
        $loginBody = @{
            email = $email
            password = $password
        } | ConvertTo-Json

        $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/signin" `
            -Method POST `
            -ContentType "application/json" `
            -Body $loginBody `
            -ErrorAction Stop

        $token = $loginResponse.access_token
        $headers = @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"
        }
        Write-Host "✅ Login successful with test user" -ForegroundColor Green
        $loginSuccess = $true
    } catch {
        Write-Host "❌ Login failed with both credentials" -ForegroundColor Red
        Write-Host "   Error: $_" -ForegroundColor Red
        Write-Host "   Please check your credentials or create a test user" -ForegroundColor Yellow
        exit 1
    }
}

# Step 2: Get Workspace
Write-Host "`nStep 2: Fetching workspace..." -ForegroundColor Yellow
try {
    $workspacesResponse = Invoke-RestMethod -Uri "$baseUrl/api/workspaces" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop

    if ($workspacesResponse -and $workspacesResponse.Count -gt 0) {
        $workspaceId = $workspacesResponse[0].id
        Write-Host "✅ Workspace found: $workspaceId" -ForegroundColor Green
    } else {
        Write-Host "❌ No workspaces found" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Failed to fetch workspaces: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Read mez.pdf file
Write-Host "`nStep 3: Reading mez.pdf file..." -ForegroundColor Yellow
$pdfPath = "backend\ingestion\Input\mez.pdf"
if (-not (Test-Path $pdfPath)) {
    Write-Host "❌ File not found: $pdfPath" -ForegroundColor Red
    exit 1
}

$pdfBytes = [System.IO.File]::ReadAllBytes($pdfPath)
$pdfBase64 = [Convert]::ToBase64String($pdfBytes)
Write-Host "✅ File read: $($pdfBytes.Length) bytes" -ForegroundColor Green

# Step 4: Create Scope with PDF
Write-Host "`nStep 4: Creating scope with PDF upload..." -ForegroundColor Yellow
try {
    # Use PowerShell's built-in multipart form data support
    $formFields = @{
        workspaceId = $workspaceId
        title = "Mez App - Product Scope"
        templateId = "scope-web-app"
        inputType = "pdf"
        aiModel = "gpt-4-turbo"
        developerLevel = "mid"
        developerExperienceYears = "3"
        file = Get-Item -Path $pdfPath
    }
    
    # Use Invoke-RestMethod with -Form parameter (PowerShell 7+)
    # For PowerShell 5.1, we'll use a different approach
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $response = Invoke-RestMethod -Uri "$baseUrl/api/scopes" `
            -Method POST `
            -Headers @{ "Authorization" = "Bearer $token" } `
            -Form $formFields `
            -ErrorAction Stop
    } else {
        # PowerShell 5.1 fallback - use a simpler boundary format
        $boundary = "----WebKitFormBoundary" + [System.Guid]::NewGuid().ToString().Replace("-", "")
        $CRLF = "`r`n"
        
        $bodyParts = New-Object System.Collections.ArrayList
        
        # Add form fields
        foreach ($key in @('workspaceId', 'title', 'templateId', 'inputType', 'aiModel', 'developerLevel', 'developerExperienceYears')) {
            $value = $formFields[$key]
            [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("--$boundary$CRLF"))
            [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("Content-Disposition: form-data; name=`"$key`"$CRLF$CRLF"))
            [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("$value$CRLF"))
        }
        
        # Add file
        [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("--$boundary$CRLF"))
        [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("Content-Disposition: form-data; name=`"file`"; filename=`"mez.pdf`"$CRLF"))
        [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("Content-Type: application/pdf$CRLF$CRLF"))
        
        # Add file bytes
        [void]$bodyParts.Add($pdfBytes)
        
        # Add closing boundary
        [void]$bodyParts.Add([System.Text.Encoding]::UTF8.GetBytes("$CRLF--$boundary--$CRLF"))
        
        # Combine all parts
        $finalBody = $bodyParts | ForEach-Object { $_ } | ForEach-Object { $bytes = $_; $bytes } | ForEach-Object { $bytes = $_; $bytes }
        
        # Better approach: build as byte array
        $totalSize = ($bodyParts | Measure-Object -Property Length -Sum).Sum
        $finalBodyArray = New-Object byte[] $totalSize
        $offset = 0
        foreach ($part in $bodyParts) {
            [System.Buffer]::BlockCopy($part, 0, $finalBodyArray, $offset, $part.Length)
            $offset += $part.Length
        }
        
        $formHeaders = @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "multipart/form-data; boundary=$boundary"
        }
        
        $response = Invoke-WebRequest -Uri "$baseUrl/api/scopes" `
            -Method POST `
            -Headers $formHeaders `
            -Body $finalBodyArray `
            -ErrorAction Stop
        
        $response = $response.Content | ConvertFrom-Json
    }
    
    $scopeId = $response.id
    Write-Host "✅ Scope created: $scopeId" -ForegroundColor Green
    if ($response.extraction_id) {
        Write-Host "   Extraction ID: $($response.extraction_id)" -ForegroundColor Gray
    }
    if ($response.status) {
        Write-Host "   Status: $($response.status)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to create scope: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Error details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "   Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 5: Wait a bit for processing
Write-Host "`nStep 5: Waiting 10 seconds for initial processing..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Step 6: Check Scope Status
Write-Host "`nStep 6: Checking scope status..." -ForegroundColor Yellow
try {
    $scopeResponse = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    Write-Host "✅ Scope Status:" -ForegroundColor Green
    Write-Host "   Title: $($scopeResponse.title)" -ForegroundColor Gray
    Write-Host "   Status: $($scopeResponse.status)" -ForegroundColor Gray
    Write-Host "   Progress: $($scopeResponse.progress)%" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to get scope: $_" -ForegroundColor Red
}

# Step 7: Get Sections
Write-Host "`nStep 7: Fetching scope sections..." -ForegroundColor Yellow
try {
    $sectionsResponse = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId/sections" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    $sectionCount = $sectionsResponse.Count
    Write-Host "✅ Found $sectionCount sections" -ForegroundColor Green
    
    if ($sectionCount -gt 0) {
        Write-Host "`nSections:" -ForegroundColor Cyan
        foreach ($section in $sectionsResponse) {
            Write-Host "  - $($section.title) (Type: $($section.section_type), Order: $($section.order_index))" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  No sections found yet. Extraction may still be in progress." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed to get sections: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Error details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# Step 8: Check Documents
Write-Host "`nStep 8: Checking documents..." -ForegroundColor Yellow
try {
    $documentsResponse = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId/documents" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    Write-Host "✅ Found $($documentsResponse.Count) document(s)" -ForegroundColor Green
    foreach ($doc in $documentsResponse) {
        Write-Host "   - $($doc.filename) (Status: $($doc.processing_status))" -ForegroundColor Gray
        $documentId = $doc.id
    }
} catch {
    Write-Host "⚠️  Could not fetch documents (endpoint may not exist)" -ForegroundColor Yellow
}

# Step 9: Wait and check again (for long-running extractions)
Write-Host "`nStep 9: Waiting 30 seconds and checking sections again..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

try {
    $sectionsResponse2 = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId/sections" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    $sectionCount2 = $sectionsResponse2.Count
    Write-Host "✅ After wait: Found $sectionCount2 sections" -ForegroundColor Green
    
    if ($sectionCount2 -gt $sectionCount) {
        Write-Host "✅ New sections appeared! Extraction is working." -ForegroundColor Green
    } elseif ($sectionCount2 -eq 0) {
        Write-Host "⚠️  Still no sections. Check Docker logs for extraction status." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed to get sections on second check: $_" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Scope ID: $scopeId" -ForegroundColor Cyan
Write-Host "Check Docker logs if sections are missing:" -ForegroundColor Yellow
Write-Host "  docker-compose logs --tail=100 ingestion-service" -ForegroundColor Gray
Write-Host "  docker-compose logs --tail=100 backend-api" -ForegroundColor Gray
