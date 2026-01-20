# Complete script to create scope, trigger extraction, and generate downloadable document

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Complete Scope Creation & Extraction Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$API_URL = "http://localhost:8001"
$TEST_EMAIL = "admin@orbit.dev"
$TEST_PASSWORD = "admin123"
$EXPRESS_TXT_PATH = "backend\ingestion\Input\express.txt"

# Step 1: Login
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

# Step 2: Get Workspace
Write-Host "Step 2: Getting workspace..." -ForegroundColor Yellow
$workspacesResponse = Invoke-RestMethod -Uri "$API_URL/api/workspaces" -Method Get -Headers $headers
$WORKSPACE_ID = if ($workspacesResponse -is [Array]) { $workspacesResponse[0].id } else { $workspacesResponse.workspaces[0].id }
Write-Host "✅ Workspace ID: $WORKSPACE_ID" -ForegroundColor Green
Write-Host ""

# Step 3: Read express.txt
Write-Host "Step 3: Reading express.txt..." -ForegroundColor Yellow
$fileContent = Get-Content $EXPRESS_TXT_PATH -Raw
Write-Host "✅ File read ($($fileContent.Length) chars)" -ForegroundColor Green
Write-Host ""

# Step 4: Create Scope
Write-Host "Step 4: Creating scope..." -ForegroundColor Yellow
$scopeBody = @{
    workspaceId = $WORKSPACE_ID
    title = "Express ECG Mobile App - Scope"
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
Write-Host "✅ Scope created: $SCOPE_ID" -ForegroundColor Green
Write-Host ""

# Step 5: Wait and get scope details
Write-Host "Step 5: Getting scope details..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
$scopeDetails = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID" -Method Get -Headers $headers
Write-Host "✅ Scope retrieved" -ForegroundColor Green
Write-Host ""

# Step 6: Get documents from database (via direct query)
Write-Host "Step 6: Checking for documents..." -ForegroundColor Yellow
$docQuery = "SELECT id, filename, processing_status FROM documents WHERE scope_id = '$SCOPE_ID' LIMIT 1;"
$docResult = docker-compose exec -T postgres psql -U postgres -d orbit -c $docQuery 2>&1
if ($docResult -match "text_input\.txt") {
    $docIdMatch = [regex]::Match($docResult, "([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
    if ($docIdMatch.Success) {
        $DOCUMENT_ID = $docIdMatch.Groups[1].Value
        Write-Host "✅ Document found: $DOCUMENT_ID" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Could not extract document ID" -ForegroundColor Yellow
        $DOCUMENT_ID = $null
    }
} else {
    Write-Host "⚠️  No document found in database" -ForegroundColor Yellow
    $DOCUMENT_ID = $null
}
Write-Host ""

# Step 7: Trigger Extraction (if document exists)
if ($DOCUMENT_ID) {
    Write-Host "Step 7: Triggering AI extraction..." -ForegroundColor Yellow
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
        Write-Host "Status: $($extractResponse.status)" -ForegroundColor Gray
        Write-Host "Estimated Time: $($extractResponse.estimatedTime) seconds" -ForegroundColor Gray
        Write-Host ""
        
        Write-Host "⏳ Waiting 45 seconds for extraction..." -ForegroundColor Yellow
        Start-Sleep -Seconds 45
    } catch {
        Write-Host "⚠️  Extraction error: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Skipping extraction - no document ID" -ForegroundColor Yellow
    Write-Host ""
}

# Step 8: Get Sections
Write-Host "Step 8: Getting generated sections..." -ForegroundColor Yellow
$sectionsResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID/sections" -Method Get -Headers $headers
Write-Host "✅ Found $($sectionsResponse.Count) sections" -ForegroundColor Green
Write-Host ""

# Step 9: Generate Downloadable Document
Write-Host "Step 9: Generating downloadable document..." -ForegroundColor Yellow
$outputFile = "Express_ECG_Scope_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

$document = @"
==========================================
EXPRESS ECG MOBILE APP - SCOPE DOCUMENT
==========================================

Scope ID: $SCOPE_ID
Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Title: $($scopeDetails.title)
Description: $($scopeDetails.description)
Status: $($scopeDetails.status)
Progress: $($scopeDetails.progress)%

==========================================
SCOPE SECTIONS
==========================================

"@

if ($sectionsResponse -and $sectionsResponse.Count -gt 0) {
    foreach ($section in $sectionsResponse | Sort-Object { $_.orderIndex }) {
        $document += @"

──────────────────────────────────────────
Section $($section.orderIndex + 1): $($section.title)
──────────────────────────────────────────
Type: $($section.sectionType)
AI Generated: $($section.aiGenerated)
Confidence Score: $($section.confidenceScore)%

$($section.content)

"@
    }
} else {
    $document += @"

No sections have been generated yet.

This could mean:
1. Extraction is still processing (wait 30-60 seconds and check again)
2. Extraction failed (check logs: docker-compose logs backend-api)
3. Extraction was not triggered (manually trigger via POST /api/scopes/$SCOPE_ID/extract)

To check sections again:
GET http://localhost:8001/api/scopes/$SCOPE_ID/sections

"@
}

$document += @"

==========================================
ORIGINAL INPUT TEXT
==========================================

$fileContent

==========================================
API ENDPOINTS FOR VERIFICATION
==========================================

Get Scope:
GET http://localhost:8001/api/scopes/$SCOPE_ID

Get Sections:
GET http://localhost:8001/api/scopes/$SCOPE_ID/sections

Trigger Extraction:
POST http://localhost:8001/api/scopes/$SCOPE_ID/extract
Body: {
  "uploadId": "$DOCUMENT_ID",
  "extractionType": "full",
  "aiModel": "gpt-4o"
}

==========================================
"@

$document | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "✅ Document created: $outputFile" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scope ID: $SCOPE_ID" -ForegroundColor Cyan
Write-Host "Sections: $($sectionsResponse.Count)" -ForegroundColor Cyan
Write-Host "Document: $outputFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Check sections: GET /api/scopes/$SCOPE_ID/sections" -ForegroundColor Gray
Write-Host "2. If no sections, trigger extraction manually" -ForegroundColor Gray
Write-Host "3. Review the generated document: $outputFile" -ForegroundColor Gray
Write-Host ""
