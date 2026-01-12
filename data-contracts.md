## Data Contracts & Schemas v0

### 1. Document Metadata
Represents each uploaded artifact and its processing state.
```json
{
  "doc_id": "uuid",
  "source_type": "uploaded_file | pasted_text | url | email",
  "file_name": "string",
  "content_type": "application/pdf",
  "owner_user_id": "string",
  "engagement_id": "string",
  "status": "submitted | processing | completed | failed",
  "domain": {
    "label": "fintech",
    "confidence": 0.82
  },
  "version_token": "string",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "metadata": {
    "page_count": 12,
    "language": "en",
    "notes": "string"
  }
}
```

### 2. Cleaned Text Snapshot
Stores normalized text and chunk references.
```json
{
  "doc_id": "uuid",
  "snapshot_id": "uuid",
  "text": "string",
  "tokens": 12345,
  "chunk_ids": ["uuid", "uuid"],
  "created_at": "ISO8601"
}
```

### 3. Chunk Schema
Used for embedding and retrieval.
```json
{
  "chunk_id": "uuid",
  "doc_id": "uuid",
  "sequence": 12,
  "text": "string",
  "embedding_vector": "[float]",
  "tags": ["requirement-rich", "persona:admin"],
  "source_location": {
    "page": 4,
    "paragraph": 2
  },
  "created_at": "ISO8601"
}
```

### 4. Requirement Graph
Captures structured understanding for downstream generation.
```json
{
  "graph_id": "uuid",
  "doc_id": "uuid",
  "version": 3,
  "personas": [
    {
      "persona_id": "uuid",
      "name": "Sales Rep",
      "description": "string",
      "goals": ["string"],
      "pain_points": ["string"],
      "source_chunks": ["chunk_id"]
    }
  ],
  "features": [
    {
      "feature_id": "uuid",
      "name": "Lead Scoring Dashboard",
      "summary": "string",
      "priority": "P1 | P2 | P3",
      "dependencies": ["feature_id"],
      "acceptance_criteria": ["Given ..."],
      "personas": ["persona_id"],
      "modules": ["module_id"],
      "interactions": ["interaction_id"],
      "notes": ["string"],
      "source_chunks": ["chunk_id"]
    }
  ],
  "modules": [
    {
      "module_id": "uuid",
      "name": "Analytics",
      "description": "string",
      "features": ["feature_id"]
    }
  ],
  "interactions": [
    {
      "interaction_id": "uuid",
      "statement": "Persona logs in to view dashboard",
      "type": "user_action | system_action",
      "linked_feature": "feature_id"
    }
  ],
  "functional_requirements": [
    {
      "req_id": "uuid",
      "description": "string",
      "category": "functional",
      "source_chunks": ["chunk_id"]
    }
  ],
  "technical_requirements": [
    {
      "req_id": "uuid",
      "description": "string",
      "category": "technical",
      "source_chunks": ["chunk_id"]
    }
  ],
  "non_functional_requirements": [
    {
      "req_id": "uuid",
      "description": "NFR description",
      "metric": "string",
      "source_chunks": ["chunk_id"]
    }
  ],
  "questions": [
    {
      "question_id": "uuid",
      "text": "string",
      "status": "open | answered",
      "answer": "string",
      "source_chunks": ["chunk_id"]
    }
  ],
  "confidence_score": 0.78,
  "validation": {
    "status": "pass | warn | fail",
    "issues": [
      {
        "issue_id": "uuid",
        "type": "persona_coverage | contradiction | duplicate",
        "severity": "high | medium | low",
        "summary": "string",
        "related_entities": ["feature_id"],
        "recommendation": "string"
      }
    ]
  },
  "created_at": "ISO8601",
  "created_by": "service_name"
}
```

### 5. Export Artifact Record
```json
{
  "artifact_id": "uuid",
  "doc_id": "uuid",
  "graph_id": "uuid",
  "type": "markdown | confluence | notion | pdf | excel | json",
  "location": "s3://bucket/path",
  "checksum": "string",
  "size_bytes": 123456,
  "created_at": "ISO8601",
  "created_by": "service_name",
  "download_count": 3,
  "last_downloaded_at": "ISO8601"
}
```

### 6. Event Contracts
- `document.submitted`: `{ "doc_id": "...", "owner_user_id": "...", "source_type": "...", "timestamp": "..." }`
- `processing.completed`: `{ "doc_id": "...", "graph_id": "...", "status": "success", "duration_ms": 12345 }`
- `validation.failed`: `{ "doc_id": "...", "issue_ids": ["..."], "severity": "high" }`
- `export.ready`: `{ "doc_id": "...", "artifact_id": "...", "type": "excel" }`

### 7. Versioning & Governance
- Each graph and artifact increment `version` when regenerated; maintain parent-child linkage.  
- Schemas managed via Schema Registry (e.g., Glue Schema Registry) with semantic versioning.  
- Backward compatibility policy: additive changes allowed; breaking changes require migration plan and consumer notice.

### 8. Open Decisions
- Whether to store embeddings inline (vector DB) or reference by key only.  
- Naming conventions for IDs (UUID vs. ULID).  
- Need for additional audit fields (e.g., approver, manual edits).  
- JSON schema validation enforcement at API layer vs. downstream.

