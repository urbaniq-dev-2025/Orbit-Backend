# RAG Implementation Guide: Learning Module/Feature Division from Examples

## What is This Approach?

This is a **RAG (Retrieval Augmented Generation)** approach, not traditional machine learning. Here's the difference:

### RAG (What We're Doing)
- **Retrieval**: Find similar example documents from your Input/Output pairs
- **Augmentation**: Inject those examples into the LLM prompt as context
- **Generation**: LLM generates new scope documents using the examples as guidance

**Advantages:**
- ✅ No training required - works immediately
- ✅ Easy to update - just add/remove example files
- ✅ Transparent - you can see which examples influenced the output
- ✅ Domain-specific - learns your organization's patterns
- ✅ Fast to implement

### Traditional Machine Learning (What We're NOT Doing)
- Would require training a model on thousands of examples
- Needs labeled datasets, feature engineering
- Requires retraining when patterns change
- Less interpretable

## How It Works

```
1. User uploads new document
   ↓
2. System extracts text from document
   ↓
3. RAG Retrieval: Find 2-3 most similar example documents from Input/ folder
   (using embeddings/semantic search)
   ↓
4. Load corresponding structured outputs from Output/ folder
   ↓
5. Build enhanced prompt:
   - System prompt (existing)
   - Few-shot examples (from Output/ folder)
   - Current document text
   ↓
6. LLM generates scope using examples as reference
   ↓
7. Return structured scope document
```

## Implementation Steps

### Step 1: Set Up Vector Database for Retrieval

You'll need to:
1. Create embeddings for all Input documents
2. Store them in a vector database (e.g., ChromaDB, Pinecone, or simple in-memory)
3. When a new document comes in, find similar ones using cosine similarity

### Step 2: Modify LLM Service

Update `services/llm_scope.py` to:
1. Accept example documents as context
2. Format them as few-shot examples in the prompt
3. Include them before the current document

### Step 3: Create RAG Service

New service: `services/rag_examples.py`
- Loads Input/Output pairs
- Creates embeddings for Input documents
- Retrieves similar examples for new documents
- Formats examples for prompt injection

## Code Structure

```
backend/ingestion/
├── Input/                    # Example input documents
│   ├── project-1.pdf
│   └── project-2.docx
├── Output/                   # Corresponding structured outputs
│   ├── project-1.json
│   └── project-2.json
├── clarivo_ingestion/
│   └── services/
│       ├── rag_examples.py   # NEW: RAG retrieval service
│       └── llm_scope.py      # MODIFY: Add few-shot examples
```

## Example Prompt Structure

```python
SYSTEM_PROMPT = "You are an expert BA..."

FEW_SHOT_EXAMPLES = """
Here are examples of how similar documents were structured:

Example 1:
Input: [similar document text]
Output: {example_output_1_json}

Example 2:
Input: [similar document text]
Output: {example_output_2_json}
"""

USER_PROMPT = """
Current document:
{document_text}

Generate scope following the patterns shown in the examples above.
"""
```

## Benefits for Your Use Case

1. **Learns Your Patterns**: Instead of hardcoded `_CANONICAL_MODULES`, the model learns from your actual project examples
2. **Domain Adaptation**: Different industries (FinTech, Healthcare, E-commerce) can have different module structures
3. **Continuous Improvement**: Add more examples over time to improve quality
4. **Consistency**: Ensures new projects follow similar structure to past successful ones

## Will This Actually Work?

**Yes!** This is a proven RAG pattern used by:
- GitHub Copilot (code examples)
- ChatGPT (few-shot learning)
- Many enterprise AI systems

**Key Success Factors:**
- Quality examples (3-5 good examples > 20 mediocre ones)
- Similarity matching (good embeddings = better retrieval)
- Prompt engineering (clear instructions + examples)

## Next Steps

1. ✅ Folders created (Input/ and Output/)
2. Add 3-5 example Input/Output pairs
3. Implement embedding generation for Input documents
4. Implement similarity search
5. Modify `llm_scope.py` to inject examples
6. Test with new documents

## Technical Requirements

You'll need:
- Embedding model (e.g., `sentence-transformers`, OpenAI embeddings, or Groq embeddings)
- Vector storage (simple: in-memory dict, production: ChromaDB/Weaviate)
- Similarity search (cosine similarity is standard)

This is much simpler than training a model and will work well for your use case!

