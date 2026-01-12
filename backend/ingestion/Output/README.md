# Output Folder

This folder contains **example structured scope documents** - the desired output format for each corresponding input document.

## Purpose
These documents show the AI model:
- How to structure modules and features
- What level of detail is expected
- How to organize requirements by domain/functionality
- Your preferred module naming conventions

## Format
Each output file should be a JSON file matching the `ScopeDocument` schema:
- `executive_summary`
- `personas`
- `modules` (with features)
- `features` (detailed)
- `functional_requirements`
- `technical_requirements`
- `non_functional_requirements`
- `open_questions`

## How to Use
1. For each document in `../Input/`, create a corresponding JSON file here with the same base filename
2. Example: `Input/project-ecommerce-app.pdf` → `Output/project-ecommerce-app.json`
3. The system will use these as few-shot examples in RAG retrieval

## Example Structure
```
Output/
  ├── project-ecommerce-app.json
  ├── project-healthcare-portal.json
  └── project-fintech-platform.json
```

