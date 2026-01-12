#!/bin/bash
# Test script for RAG-enabled scope generation

echo "=== Testing RAG-Enabled Scope Generation ==="
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server is not running. Please start it first:"
    echo "   cd /home/aubergine/Aubergine-clarivo/Aubergine-Clarivo/backend/ingestion"
    echo "   source .venv/bin/activate"
    echo "   uvicorn clarivo_ingestion.main:app --reload"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Test 1: Submit a text document
echo "📄 Test 1: Submitting a text document..."
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "client_brief",
    "content": "We need a mobile app for food delivery. Users should be able to browse restaurants, add items to cart, place orders, and track deliveries. Restaurants need an admin panel to manage menus and orders. Payment integration with Stripe is required."
  }')

DOC_ID=$(echo $RESPONSE | grep -o '"doc_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$DOC_ID" ]; then
    echo "❌ Failed to create document"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Document created with ID: $DOC_ID"
echo ""

# Wait for processing
echo "⏳ Waiting for scope generation (this may take 30-60 seconds)..."
sleep 5

# Check status
echo "📊 Checking document status..."
STATUS=$(curl -s http://localhost:8000/v1/documents/$DOC_ID/status)
echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"
echo ""

# Get scope
echo "📋 Retrieving generated scope..."
SCOPE=$(curl -s http://localhost:8000/v1/documents/$DOC_ID/scope)
echo "$SCOPE" | python3 -m json.tool 2>/dev/null || echo "$SCOPE"
echo ""

echo "=== Test Complete ==="
echo ""
echo "💡 Check the server logs to see RAG examples being retrieved!"
echo "   Look for messages like: 'Including 3 RAG examples in prompt'"



