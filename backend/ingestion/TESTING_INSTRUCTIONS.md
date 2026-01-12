# Testing RAG-Enabled Scope Generation

## Server Status

The server should be starting in the background. Here's how to test it:

## Option 1: Use the Test Script

```bash
cd /home/aubergine/Aubergine-clarivo/Aubergine-Clarivo/backend/ingestion
./test_rag.sh
```

## Option 2: Manual Testing

### 1. Check Server Health
```bash
curl http://localhost:8000/health
```

### 2. Submit a Test Document

**Using a text file:**
```bash
curl -X POST http://localhost:8000/v1/documents \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "client_brief",
    "content": "We need a mobile app for food delivery. Users should be able to browse restaurants, add items to cart, place orders, and track deliveries. Restaurants need an admin panel to manage menus and orders. Payment integration with Stripe is required."
  }'
```

**Using a file upload:**
```bash
curl -X POST http://localhost:8000/v1/documents \
  -F source_type="client_brief" \
  -F metadata='{"project":"test"}' \
  -F file=@Input/investMates.txt
```

### 3. Check Document Status

Replace `<doc_id>` with the ID from step 2:
```bash
curl http://localhost:8000/v1/documents/<doc_id>/status
```

### 4. Get Generated Scope

```bash
curl http://localhost:8000/v1/documents/<doc_id>/scope
```

### 5. Download as Excel

```bash
curl http://localhost:8000/v1/documents/<doc_id>/scope.xlsx -o scope.xlsx
```

## What to Look For

### In Server Logs:
- ✅ "RAG example retriever initialized with Input: ..."
- ✅ "Loaded X example document pairs"
- ✅ "Including 3 RAG examples in prompt"
- ✅ "Retrieved example 'xxx' with similarity 0.XX"

### In Generated Scope:
- Modules should follow patterns from your example documents
- Feature organization should match your examples
- Structure should be consistent with your Output JSON files

## Troubleshooting

### Server Not Running?
```bash
cd /home/aubergine/Aubergine-clarivo/Aubergine-Clarivo/backend/ingestion
source .venv/bin/activate
uvicorn clarivo_ingestion.main:app --host 0.0.0.0 --port 8000 --reload
```

### Check Logs
Watch the terminal where the server is running for RAG-related messages.

### API Documentation
Visit http://localhost:8000/docs for interactive API documentation.

## Your Example Documents

The RAG system will use these 6 example pairs:
- `excavate.pdf` → `excavate.json`
- `express.txt` → `express.json`
- `investMates.txt` → `investMates.json`
- `mez.pdf` → `mez.json`
- `scatterplot.pdf` → `scatterplot.json`
- `shooting.pdf` → `shooting.json`

The system automatically finds the 3 most similar examples for each new document!



