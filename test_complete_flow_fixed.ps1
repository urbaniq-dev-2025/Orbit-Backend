# Complete Scope Generation Test - Fixed Version
# Tests: Create Scope → Upload Document → Extract → Get Sections → Generate Document

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Complete Scope Generation Test (Fixed)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$API_URL = "http://localhost:8001"
$TEST_EMAIL = "admin@orbit.dev"
$TEST_PASSWORD = "admin123"
$EXPRESS_TXT_PATH = "backend\ingestion\Input\express.txt"

# Step 1: Login
Write-Host "Step 1: Logging in..." -ForegroundColor Yellow
try {
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
} catch {
    Write-Host "❌ Login error: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Get Workspace
Write-Host "Step 2: Getting workspace..." -ForegroundColor Yellow
try {
    $workspacesResponse = Invoke-RestMethod -Uri "$API_URL/api/workspaces" -Method Get -Headers $headers
    $WORKSPACE_ID = if ($workspacesResponse -is [Array]) { $workspacesResponse[0].id } else { $workspacesResponse.workspaces[0].id }
    Write-Host "✅ Workspace ID: $WORKSPACE_ID" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Error getting workspaces: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Read express.txt
Write-Host "Step 3: Reading express.txt file..." -ForegroundColor Yellow
if (-not (Test-Path $EXPRESS_TXT_PATH)) {
    Write-Host "❌ File not found: $EXPRESS_TXT_PATH" -ForegroundColor Red
    exit 1
}

$fileContent = Get-Content $EXPRESS_TXT_PATH -Raw
Write-Host "✅ File read successfully ($($fileContent.Length) characters)" -ForegroundColor Green
Write-Host ""

# Step 4: Create Scope with Text Input
Write-Host "Step 4: Creating scope with text input..." -ForegroundColor Yellow
try {
    $scopeBody = @{
        workspaceId = $WORKSPACE_ID
        title = "Express ECG Mobile App - Final Test $(Get-Date -Format 'HH:mm:ss')"
        description = "Cross-platform mobile application for Express ECG cardiac care services"
        inputType = "text"
        inputData = $fileContent
        templateId = "scope-web-app"
        aiModel = "gpt-4o"
        developerLevel = "mid"
        developerExperienceYears = 3
    } | ConvertTo-Json

    $createResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes" `
        -Method Post `
        -ContentType "application/json" `
        -Headers $headers `
        -Body $scopeBody
    
    $SCOPE_ID = $createResponse.id
    Write-Host "✅ Scope created successfully!" -ForegroundColor Green
    Write-Host "Scope ID: $SCOPE_ID" -ForegroundColor Cyan
    Write-Host "Title: $($createResponse.title)" -ForegroundColor Gray
    Write-Host "Status: $($createResponse.status)" -ForegroundColor Gray
    Write-Host ""
    
    # Wait for document processing
    Write-Host "⏳ Waiting 5 seconds for document processing..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
} catch {
    Write-Host "❌ Error creating scope: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    exit 1
}

# Step 5: Get Document ID from Database (Fixed query)
Write-Host "Step 5: Getting document ID..." -ForegroundColor Yellow
try {
    $docResult = docker-compose exec -T postgres psql -U postgres -d orbit -c "SELECT id FROM documents WHERE scope_id = '$SCOPE_ID' LIMIT 1;" 2>&1
    $docIdMatch = [regex]::Match($docResult, "([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
    if ($docIdMatch.Success) {
        $DOCUMENT_ID = $docIdMatch.Groups[1].Value
        Write-Host "✅ Document found: $DOCUMENT_ID" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Could not extract document ID from database" -ForegroundColor Yellow
        Write-Host "Database output: $docResult" -ForegroundColor Gray
        $DOCUMENT_ID = $null
    }
    Write-Host ""
} catch {
    Write-Host "⚠️  Error querying database: $_" -ForegroundColor Yellow
    $DOCUMENT_ID = $null
}

# Step 6: Trigger Extraction (if document exists)
if ($DOCUMENT_ID) {
    Write-Host "Step 6: Triggering AI extraction..." -ForegroundColor Yellow
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
        
        Write-Host "⏳ Waiting 90 seconds for extraction to complete..." -ForegroundColor Yellow
        Start-Sleep -Seconds 90
    } catch {
        Write-Host "❌ Extraction error: $_" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response: $responseBody" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "⚠️  Continuing to check sections anyway..." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Skipping extraction - no document ID found" -ForegroundColor Yellow
    Write-Host ""
}

# Step 7: Get Scope Details
Write-Host "Step 7: Getting scope details..." -ForegroundColor Yellow
try {
    $scopeDetails = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID" -Method Get -Headers $headers
    Write-Host "✅ Scope details retrieved" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Error getting scope details: $_" -ForegroundColor Red
    exit 1
}

# Step 8: Get Sections (Check multiple times)
Write-Host "Step 8: Getting generated sections..." -ForegroundColor Yellow
$maxRetries = 3
$sectionsResponse = @()
for ($i = 1; $i -le $maxRetries; $i++) {
    try {
        $sectionsResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID/sections" -Method Get -Headers $headers
        Write-Host "✅ Found $($sectionsResponse.Count) sections (attempt $i)" -ForegroundColor Green
        
        if ($sectionsResponse.Count -gt 0) {
            break
        } elseif ($i -lt $maxRetries) {
            Write-Host "⏳ Waiting 10 seconds before retry..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    } catch {
        Write-Host "❌ Error getting sections (attempt $i): $_" -ForegroundColor Red
    }
}

if ($sectionsResponse.Count -gt 0) {
    Write-Host ""
    Write-Host "Generated Sections:" -ForegroundColor Cyan
    foreach ($section in $sectionsResponse | Sort-Object { $_.orderIndex }) {
        Write-Host "  [$($section.orderIndex + 1)] $($section.title)" -ForegroundColor Green
        if ($section.content) {
            $preview = $section.content.Substring(0, [Math]::Min(100, $section.content.Length))
            Write-Host "      $preview..." -ForegroundColor Gray
        }
    }
} else {
    Write-Host "⚠️  No sections generated yet." -ForegroundColor Yellow
}
Write-Host ""

# Step 9: Generate Downloadable Document
Write-Host "Step 9: Generating downloadable document..." -ForegroundColor Yellow
$outputFile = "Express_ECG_Scope_Final_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

$document = @"
╔══════════════════════════════════════════════════════════════════════════════╗
║              EXPRESS ECG MOBILE APP - COMPLETE SCOPE DOCUMENT                ║
╚══════════════════════════════════════════════════════════════════════════════╝

SCOPE INFORMATION
────────────────────────────────────────────────────────────────────────────────
Scope ID:          $SCOPE_ID
Title:             $($scopeDetails.title)
Description:       $($scopeDetails.description)
Status:            $($scopeDetails.status)
Progress:          $($scopeDetails.progress)%
Created:           $($scopeDetails.createdAt)
Updated:           $($scopeDetails.updatedAt)
Workspace ID:      $($scopeDetails.workspaceId)
Document ID:       $DOCUMENT_ID

"@

if ($sectionsResponse -and $sectionsResponse.Count -gt 0) {
    $document += @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                           GENERATED SCOPE SECTIONS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

"@
    
    foreach ($section in $sectionsResponse | Sort-Object { $_.orderIndex }) {
        $document += @"
────────────────────────────────────────────────────────────────────────────────
SECTION $($section.orderIndex + 1): $($section.title)
────────────────────────────────────────────────────────────────────────────────
Type:              $($section.sectionType)
AI Generated:      $($section.aiGenerated)
Confidence Score:  $($section.confidenceScore)%
Created:           $($section.createdAt)

$($section.content)

"@
    }
} else {
    $document += @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                              SCOPE SECTIONS                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

⚠️  No sections have been generated yet.

Possible reasons:
  1. Extraction is still processing (wait longer and check again)
  2. Extraction failed (check ingestion service logs)
  3. API key is invalid or expired

To check extraction status:
  GET http://localhost:8001/api/scopes/$SCOPE_ID/sections

To trigger extraction manually:
  POST http://localhost:8001/api/scopes/$SCOPE_ID/extract
  Body: {
    "uploadId": "$DOCUMENT_ID",
    "extractionType": "full",
    "aiModel": "gpt-4o",
    "developerLevel": "mid",
    "developerExperienceYears": 3
  }

"@
}

$document += @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                         ORIGINAL INPUT TEXT                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

$fileContent

═══════════════════════════════════════════════════════════════════════════════
Document Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
═══════════════════════════════════════════════════════════════════════════════
"@

$document | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "✅ Document created: $outputFile" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Test Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scope ID: $SCOPE_ID" -ForegroundColor Cyan
Write-Host "Document ID: $DOCUMENT_ID" -ForegroundColor Cyan
Write-Host "Sections Generated: $($sectionsResponse.Count)" -ForegroundColor Cyan
Write-Host "Output File: $outputFile" -ForegroundColor Cyan
Write-Host ""

if ($sectionsResponse.Count -gt 0) {
    Write-Host "🎉 SUCCESS! Scope generation is working!" -ForegroundColor Green
    Write-Host "   Review the generated document: $outputFile" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Sections not generated yet." -ForegroundColor Yellow
    Write-Host "   Check ingestion service logs for details." -ForegroundColor Gray
}
Write-Host ""
