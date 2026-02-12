# PowerShell script to test scope creation via API
# This tests the complete flow with OpenAI API

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Testing Scope Creation with OpenAI API" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$API_URL = "http://localhost:8001"
$TEST_EMAIL = "test@orbit.dev"
$TEST_PASSWORD = "test123456"

Write-Host "Step 1: Authenticating user..." -ForegroundColor Yellow
Write-Host "Email: $TEST_EMAIL"
Write-Host ""

# Login to get token
$loginBody = @{
    email = $TEST_EMAIL
    password = $TEST_PASSWORD
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$API_URL/api/auth/signin" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody
    
    $TOKEN = $loginResponse.access_token
    
    if (-not $TOKEN) {
        Write-Host "❌ Login failed" -ForegroundColor Red
        Write-Host "Response: $($loginResponse | ConvertTo-Json)"
        exit 1
    }
    
    Write-Host "✅ Login successful" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Login error: $_" -ForegroundColor Red
    exit 1
}

# Get workspace ID
Write-Host "Step 2: Getting workspace..." -ForegroundColor Yellow

$headers = @{
    "Authorization" = "Bearer $TOKEN"
}

try {
    $workspacesResponse = Invoke-RestMethod -Uri "$API_URL/api/workspaces" `
        -Method Get `
        -Headers $headers
    
    # Response is a list/array of workspaces
    $WORKSPACE_ID = $null
    if ($workspacesResponse -is [array] -and $workspacesResponse.Count -gt 0) {
        $WORKSPACE_ID = $workspacesResponse[0].id
    } elseif ($workspacesResponse.id) {
        $WORKSPACE_ID = $workspacesResponse.id
    } elseif ($workspacesResponse.workspaces -and $workspacesResponse.workspaces.Count -gt 0) {
        $WORKSPACE_ID = $workspacesResponse.workspaces[0].id
    }
    
    if (-not $WORKSPACE_ID) {
        Write-Host "❌ Could not get workspace ID" -ForegroundColor Red
        Write-Host "Response type: $($workspacesResponse.GetType().Name)" -ForegroundColor Yellow
        Write-Host "Response: $($workspacesResponse | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Creating a default workspace..." -ForegroundColor Yellow
        
        # Try to create a workspace
        $createWorkspaceBody = @{
            name = "Test Workspace"
        } | ConvertTo-Json
        
        try {
            $newWorkspace = Invoke-RestMethod -Uri "$API_URL/api/workspaces" `
                -Method Post `
                -ContentType "application/json" `
                -Headers $headers `
                -Body $createWorkspaceBody
            $WORKSPACE_ID = $newWorkspace.id
            Write-Host "✅ Created workspace: $WORKSPACE_ID" -ForegroundColor Green
        } catch {
            Write-Host "❌ Could not create workspace: $_" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✅ Workspace ID: $WORKSPACE_ID" -ForegroundColor Green
    }
    Write-Host ""
} catch {
    Write-Host "❌ Error getting workspace: $_" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Yellow
    exit 1
}

# Get template ID (optional)
Write-Host "Step 3: Getting template (optional)..." -ForegroundColor Yellow

try {
    $templatesResponse = Invoke-RestMethod -Uri "$API_URL/api/templates?type=scope" `
        -Method Get `
        -Headers $headers
    
    $TEMPLATE_ID = $null
    if ($templatesResponse.templates -and $templatesResponse.templates.Count -gt 0) {
        $TEMPLATE_ID = $templatesResponse.templates[0].id
        Write-Host "✅ Template ID: $TEMPLATE_ID" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No template found, proceeding without template" -ForegroundColor Yellow
    }
    Write-Host ""
} catch {
    Write-Host "⚠️  Could not get templates, proceeding without template" -ForegroundColor Yellow
    Write-Host ""
}

# Test requirements text
$TEST_REQUIREMENTS = @"
We need a mobile food delivery application with the following features:

1. User Authentication
   - Email/Password login
   - Social login (Google, Facebook)
   - Password reset functionality

2. Restaurant Browsing
   - List of restaurants with filters (cuisine, rating, distance)
   - Restaurant detail page with menu
   - Search functionality

3. Order Management
   - Add items to cart
   - Modify cart items
   - Apply promo codes
   - Place order
   - Order tracking in real-time

4. Payment Integration
   - Stripe payment gateway
   - Multiple payment methods (card, wallet)
   - Payment history

5. Admin Panel
   - Restaurant management
   - Menu management
   - Order management
   - Analytics dashboard
"@

Write-Host "Step 4: Creating scope with text input..." -ForegroundColor Yellow
Write-Host "Input type: text"
Write-Host "Developer level: mid (3 years experience)"
Write-Host ""

# Create scope with text input
$createBody = @{
    workspaceId = $WORKSPACE_ID
    title = "Food Delivery App - Test Scope"
    description = "Test scope creation with hours estimation"
    inputType = "text"
    inputData = $TEST_REQUIREMENTS
    developerLevel = "mid"
    developerExperienceYears = 3
}

if ($TEMPLATE_ID) {
    $createBody.templateId = $TEMPLATE_ID
}

# Convert to JSON with proper encoding
$createBodyJson = $createBody | ConvertTo-Json -Depth 10 -Compress
$createBodyJson = $createBodyJson -replace '\\"', '"' -replace '"{', '{' -replace '}"', '}'

try {
    # Send as JSON - FastAPI should accept JSON when no file is provided
    $createResponse = Invoke-RestMethod -Uri "$API_URL/api/scopes" `
        -Method Post `
        -ContentType "application/json" `
        -Headers $headers `
        -Body $createBodyJson
    
    $SCOPE_ID = $createResponse.id
    
    if (-not $SCOPE_ID) {
        Write-Host "❌ Scope creation failed" -ForegroundColor Red
        Write-Host "Response: $($createResponse | ConvertTo-Json)"
        exit 1
    }
    
    Write-Host "✅ Scope created: $SCOPE_ID" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Scope creation error: $_" -ForegroundColor Red
    Write-Host "Response: $($_.ErrorDetails.Message)"
    exit 1
}

# Wait for processing
Write-Host "Step 5: Waiting for extraction to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host ""

# Get scope details
Write-Host "Step 6: Fetching scope details..." -ForegroundColor Yellow

try {
    $scopeDetails = Invoke-RestMethod -Uri "$API_URL/api/scopes/$SCOPE_ID" `
        -Method Get `
        -Headers $headers
    
    Write-Host "✅ Scope details retrieved" -ForegroundColor Green
    Write-Host ""
    
    # Display results
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Results" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Title: $($scopeDetails.title)"
    Write-Host "Status: $($scopeDetails.status)"
    Write-Host "Progress: $($scopeDetails.progress)%"
    Write-Host "Confidence Score: $($scopeDetails.confidenceScore)"
    Write-Host "Risk Level: $($scopeDetails.riskLevel)"
    Write-Host "Number of Sections: $($scopeDetails.sections.Count)"
    Write-Host ""
    
    if ($scopeDetails.sections -and $scopeDetails.sections.Count -gt 0) {
        Write-Host "Sections:" -ForegroundColor Cyan
        $sectionCount = [Math]::Min(5, $scopeDetails.sections.Count)
        for ($i = 0; $i -lt $sectionCount; $i++) {
            $section = $scopeDetails.sections[$i]
            Write-Host "  $($i + 1). $($section.title)" -ForegroundColor White
            Write-Host "     Type: $($section.sectionType)"
            Write-Host "     AI Generated: $($section.aiGenerated)"
            Write-Host "     Confidence: $($section.confidenceScore)%"
            
            # Try to extract hours from content
            if ($section.content) {
                try {
                    $contentData = $section.content | ConvertFrom-Json
                    if ($contentData.total_hours) {
                        Write-Host "     ⏱️  Hours: $($contentData.total_hours)" -ForegroundColor Green
                    }
                } catch {
                    # Content is not JSON, skip
                }
            }
            Write-Host ""
        }
    } else {
        Write-Host "⚠️  No sections found yet. Extraction may still be processing." -ForegroundColor Yellow
        Write-Host "   Try again in a few seconds."
    }
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "✅ Test completed!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Scope ID: $SCOPE_ID"
    Write-Host "View scope: GET $API_URL/api/scopes/$SCOPE_ID"
    Write-Host ""
    
} catch {
    Write-Host "❌ Error fetching scope details: $_" -ForegroundColor Red
    Write-Host "Response: $($_.ErrorDetails.Message)"
}
