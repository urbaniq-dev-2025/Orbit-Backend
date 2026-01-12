## Scope Generation Fixtures

Use this directory to store paired outputs for evaluating heuristic versus LLM scope generation.

### Folder Structure

```
test-fixtures/
  scope/
    sample-001/
      document.pdf        # or .docx/.txt – original discovery notes
      heuristic.json      # output from SCOPE_GENERATION_STRATEGY=heuristic
      llm.json            # output from SCOPE_GENERATION_STRATEGY=hybrid or llm
      notes.md            # optional observations, expectations, manual verdict
```

### Sample Tracking

| Sample ID   | Source Document            | Notes                                             |
|-------------|----------------------------|---------------------------------------------------|
| sample-001  | `document.pdf`             | First regression pair highlighting module issues. |

Update the table as you capture more fixtures (`sample-002`, etc.).


