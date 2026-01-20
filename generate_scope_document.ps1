# Generate downloadable scope document from created scope

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Generating Scope Document" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$API_URL = "http://localhost:8001"
$TEST_EMAIL = "admin@orbit.dev"
$TEST_PASSWORD = "admin123"
$SCOPE_ID = "ff6729fe-650e-49fa-aea7-c3f5d147c495"  # Latest scope ID

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

# Get Scope Details
Write-Host "Step 2: Getting scope details..." -ForegroundColor Yellow
$scopeDetails = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID" -Method Get -Headers $headers
Write-Host "✅ Scope retrieved: $($scopeDetails.title)" -ForegroundColor Green
Write-Host ""

# Get Sections
Write-Host "Step 3: Getting sections..." -ForegroundColor Yellow
$sectionsResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID/sections" -Method Get -Headers $headers
Write-Host "✅ Found $($sectionsResponse.Count) sections" -ForegroundColor Green
Write-Host ""

# Read original file
$EXPRESS_TXT_PATH = "backend\ingestion\Input\express.txt"
$originalContent = if (Test-Path $EXPRESS_TXT_PATH) { Get-Content $EXPRESS_TXT_PATH -Raw } else { "Original file not found" }

# Generate Document
Write-Host "Step 4: Generating document..." -ForegroundColor Yellow
$outputFile = "Express_ECG_Scope_Document_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

$document = @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EXPRESS ECG MOBILE APP - SCOPE DOCUMENT                    ║
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

This could mean:
  1. Extraction is still processing (wait 30-60 seconds and check again)
  2. Extraction failed (check ingestion service logs)
  3. Ingestion service is not running or configured

To trigger extraction manually:
  POST http://localhost:8001/api/scopes/$SCOPE_ID/extract
  Body: {
    "uploadId": "document-id-from-database",
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

$originalContent

╔══════════════════════════════════════════════════════════════════════════════╗
║                         API ENDPOINTS FOR VERIFICATION                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Get Scope Details:
  GET http://localhost:8001/api/scopes/$SCOPE_ID
  Authorization: Bearer YOUR_TOKEN

Get Sections:
  GET http://localhost:8001/api/scopes/$SCOPE_ID/sections
  Authorization: Bearer YOUR_TOKEN

List All Scopes:
  GET http://localhost:8001/api/scopes?workspaceId=$($scopeDetails.workspaceId)
  Authorization: Bearer YOUR_TOKEN

Trigger Extraction:
  POST http://localhost:8001/api/scopes/$SCOPE_ID/extract
  Authorization: Bearer YOUR_TOKEN
  Content-Type: application/json
  Body: {
    "uploadId": "document-uuid",
    "extractionType": "full",
    "aiModel": "gpt-4o",
    "developerLevel": "mid",
    "developerExperienceYears": 3
  }

═══════════════════════════════════════════════════════════════════════════════
Document Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
═══════════════════════════════════════════════════════════════════════════════
"@

$document | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "✅ Document created: $outputFile" -ForegroundColor Green
Write-Host ""

# Also create a JSON version
$jsonFile = "Express_ECG_Scope_Document_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$jsonData = @{
    scopeId = $SCOPE_ID
    title = $scopeDetails.title
    description = $scopeDetails.description
    status = $scopeDetails.status
    progress = $scopeDetails.progress
    createdAt = $scopeDetails.createdAt
    updatedAt = $scopeDetails.updatedAt
    sections = $sectionsResponse
    originalInput = $originalContent
} | ConvertTo-Json -Depth 10

$jsonData | Out-File -FilePath $jsonFile -Encoding UTF8
Write-Host "✅ JSON document created: $jsonFile" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Documents Generated!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Scope ID: $SCOPE_ID" -ForegroundColor Cyan
Write-Host "Sections: $($sectionsResponse.Count)" -ForegroundColor Cyan
Write-Host "Text Document: $outputFile" -ForegroundColor Cyan
Write-Host "JSON Document: $jsonFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: If sections are empty, extraction may still be processing" -ForegroundColor Yellow
Write-Host "      or the ingestion service needs to be checked." -ForegroundColor Yellow
Write-Host ""
