# Simplified test for mez.pdf scope generation
# Uses text input instead of PDF upload to avoid multipart issues

$ErrorActionPreference = "Stop"

$baseUrl = "http://localhost:8001"
$email = "admin@orbit.dev"
$password = "admin123"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Testing Mez Scope Generation (Text Input)" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Login
Write-Host "Step 1: Logging in..." -ForegroundColor Yellow
$loginBody = @{
    email = $email
    password = $password
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/signin" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody `
        -ErrorAction Stop
    $token = $loginResponse.access_token
    $headers = @{"Authorization" = "Bearer $token"}
    Write-Host "✅ Login successful" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Trying test user..." -ForegroundColor Yellow
    $email = "test@orbit.dev"
    $password = "test123456"
    $loginBody = @{email = $email; password = $password} | ConvertTo-Json
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/signin" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody
    $token = $loginResponse.access_token
    $headers = @{"Authorization" = "Bearer $token"}
    Write-Host "✅ Login successful" -ForegroundColor Green
}

# Get Workspace
Write-Host "`nStep 2: Getting workspace..." -ForegroundColor Yellow
$workspaces = Invoke-RestMethod -Uri "$baseUrl/api/workspaces" -Headers $headers
$workspaceId = $workspaces[0].id
Write-Host "✅ Workspace: $workspaceId" -ForegroundColor Green

# Read mez.pdf text content (simplified - just use the summary from the web search)
# Clean up special characters that might cause encoding issues
$mezContentRaw = @"
Mez App - Product Document

1. Customer Profile
- Login/Signup via email, phone, Google, or Apple.
- Profile info: name, contact, preferred store, dietary preferences.
Account management: edit profile, change password, delete account.

2. Social Media Integration
- Links to Facebook, Instagram, TikTok pages → "Follow Us" buttons inside the app linked to customer profiles.

3. Location & Stores
- Detect location to suggest nearest cafe.
- Manual store selection if location disabled.
- Show store info: hours, open/closed status, contact details.

4. Menu & Ordering
- Browse the menu by categories with pictures, prices, and item descriptions.
- Modifiers & add-ons (e.g., size, milk type, flavors).
- Cart with real-time pricing, notes, and tip options.
- Order types: Pickup or Dine-in.
- QR code scanning: auto-opens app with store + dine-in table context.
- Order tracking: show order status (queued, preparing, ready).

5. Payment
- Apple Pay / Google Pay + saved cards.
- Secure checkout with digital receipts.

6. Offers & Promotions
- Generic offers (happy hour, seasonal).
- Targeted offers for new users, lapsed users, or based on past orders.
- Promo codes and auto-applied discounts.

7. Rewards & Loyalty
- Points system: earn points on spend, redeem for free drinks or merchandise.
- Milestone reward: every 10th order in a month is free.
- Wallet view: track points, rewards, and redemption history.
- Subscription passes (e.g., monthly coffee pass).
- Merch store with loyalty redemption.

8. Notifications
- Order updates (order placed).
- Promotional notifications for offers, new menu items, or loyalty reminders.
- Geofencing: Notification when near a store.

9. Support & Help
- Order history & receipts.
- Help center & contact form (Whatsapp Chat).

10. Admin Features (Back Office)
- Menu management: update items, prices, availability.
- Offer management: create/edit targeted or generic offers.
- Rewards setup: configure point rules and free-order milestones.
- Order board: view incoming orders in real time.
- Integrate with each store's POS software for order placement / whatsapp chat for queries on orders.
"@

# Clean up special Unicode characters that might cause encoding issues
# Replace special quotes and dashes with ASCII equivalents
$mezContent = $mezContentRaw
$mezContent = $mezContent -replace [char]0x2013, '-'  # en dash
$mezContent = $mezContent -replace [char]0x2014, '-'  # em dash
$mezContent = $mezContent -replace [char]0x2018, "'"  # left single quote
$mezContent = $mezContent -replace [char]0x2019, "'"  # right single quote
$mezContent = $mezContent -replace [char]0x201C, '"'  # left double quote
$mezContent = $mezContent -replace [char]0x201D, '"'  # right double quote

# Create Scope with Text Input
Write-Host "`nStep 3: Creating scope with text input..." -ForegroundColor Yellow
# Ensure proper UTF-8 encoding
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$mezContentBytes = $utf8NoBom.GetBytes($mezContent)
$mezContentEncoded = [System.Text.Encoding]::UTF8.GetString($mezContentBytes)

$scopeBody = @{
    workspaceId = $workspaceId
    title = "Mez App - Product Scope"
    templateId = "scope-web-app"
    inputType = "text"
    inputData = $mezContentEncoded
    aiModel = "gpt-4o-mini"
    developerLevel = "mid"
    developerExperienceYears = 3
} | ConvertTo-Json -Depth 10 -Compress

try {
    $createResponse = Invoke-RestMethod -Uri "$baseUrl/api/scopes" `
        -Method POST `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $scopeBody `
        -ErrorAction Stop
    
    $scopeId = $createResponse.scope_id
    Write-Host "✅ Scope created: $scopeId" -ForegroundColor Green
    Write-Host "   Extraction ID: $($createResponse.extraction_id)" -ForegroundColor Gray
    Write-Host "   Status: $($createResponse.status)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to create scope: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    exit 1
}

# Wait for processing
Write-Host "`nStep 4: Waiting 15 seconds for extraction..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check Sections
Write-Host "`nStep 5: Checking sections..." -ForegroundColor Yellow
try {
    $sections = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId/sections" -Headers $headers
    Write-Host "✅ Found $($sections.Count) sections" -ForegroundColor Green
    
    if ($sections.Count -gt 0) {
        Write-Host "`nSections:" -ForegroundColor Cyan
        foreach ($section in $sections) {
            Write-Host "  - $($section.title) (Type: $($section.section_type), Order: $($section.order_index))" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  No sections yet. Waiting 30 more seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
        $sections = Invoke-RestMethod -Uri "$baseUrl/api/scopes/$scopeId/sections" -Headers $headers
        Write-Host "✅ After wait: Found $($sections.Count) sections" -ForegroundColor Green
        if ($sections.Count -gt 0) {
            foreach ($section in $sections) {
                Write-Host "  - $($section.title)" -ForegroundColor Gray
            }
        }
    }
} catch {
    Write-Host "❌ Failed to get sections: $_" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host "Scope ID: $scopeId" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
