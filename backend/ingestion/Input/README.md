# Input Folder

This folder contains **example input documents** - raw, unstructured client requirement documents, meeting notes, RFPs, or discovery documents.

## Purpose
These documents serve as training/reference examples to help the AI model understand:
- What kinds of input documents to expect
- Common patterns in requirement documents
- Different domains and industries

## How to Use
1. Add your example input documents here (PDF, DOCX, TXT, or MD files)
2. For each input document, create a corresponding structured output in the `../Output/` folder with the same filename
3. The system will use these pairs to learn module/feature division patterns

## Example Structure
```
Input/
  ├── project-ecommerce-app.pdf
  ├── project-healthcare-portal.docx
  └── project-fintech-platform.txt
```

