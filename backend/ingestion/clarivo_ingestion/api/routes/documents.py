from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse

from clarivo_ingestion.core.config import get_settings
from clarivo_ingestion.schemas.documents import (
    ClarificationListResponse,
    ClarificationResponseRequest,
    DocumentCreateResponse,
    DocumentStatusResponse,
    ModuleListResponse,
    ScopeExtractForScopeRequest,
    ScopeExtractForScopeResponse,
    ScopeSectionData,
    TextDocumentCreateRequest,
)
from clarivo_ingestion.schemas.scope import ScopeDocument, OutputFormatScopeDocument, EnhancedScopeDocument
from clarivo_ingestion.services.documents import DocumentService
from clarivo_ingestion.services.llm_scope import LLMDocumentScopeGenerator
from clarivo_ingestion.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    settings = get_settings()
    # Determine Input/Output directories relative to the ingestion backend directory
    # Assuming this file is in: backend/ingestion/clarivo_ingestion/api/routes/
    # Input/Output are in: backend/ingestion/
    backend_dir = Path(__file__).parent.parent.parent.parent
    input_dir = backend_dir / "Input"
    output_dir = backend_dir / "Output"
    return DocumentService(settings=settings, input_dir=input_dir, output_dir=output_dir)


@router.post(
    "",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a document for ingestion",
)
async def create_document(
    request: Request,
    source_type: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    service: DocumentService = Depends(get_document_service),
) -> DocumentCreateResponse:
    """
    Create a new document from either multipart/form-data upload or JSON payload.

    This endpoint supports:
    - File uploads (`uploaded_file`) with accompanying metadata JSON.
    - JSON submissions for pasted text, email, or URL content.
    """
    content_type = request.headers.get("content-type", "")

    if file is not None:
        if not source_type:
            raise HTTPException(status_code=422, detail="source_type is required for file uploads")
        try:
            parsed_metadata = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata must be valid JSON") from exc

        payload = await service.handle_file_upload(
            source_type=source_type,
            upload=file,
            metadata=parsed_metadata,
        )
        return payload

    if content_type.startswith("application/json"):
        body = await request.json()
        try:
            request_body = TextDocumentCreateRequest.model_validate(body)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="Invalid request payload") from exc
        payload = await service.handle_text_submission(request_body)
        return payload

    raise HTTPException(status_code=415, detail="Unsupported media type or empty payload")


@router.get(
    "/{doc_id}/status",
    response_model=DocumentStatusResponse,
    summary="Retrieve document ingestion status",
)
async def get_document_status(
    doc_id: UUID, service: DocumentService = Depends(get_document_service)
) -> DocumentStatusResponse:
    """Return current status for the specified document."""
    document = await service.get_status(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get(
    "/{doc_id}/clarifications",
    response_model=ClarificationListResponse,
    summary="List outstanding clarifications for a document",
)
async def list_clarifications(
    doc_id: UUID, service: DocumentService = Depends(get_document_service)
) -> ClarificationListResponse:
    clarifications = await service.list_clarifications(doc_id)
    if clarifications is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return clarifications


@router.post(
    "/{doc_id}/clarifications/{clarification_id}/responses",
    status_code=status.HTTP_200_OK,
    summary="Submit a clarification response",
)
async def submit_clarification_response(
    doc_id: UUID,
    clarification_id: UUID,
    request: ClarificationResponseRequest,
    service: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    try:
        await service.answer_clarification(doc_id, clarification_id, request)
    except DocumentService.DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentService.ClarificationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "clarification_id": str(clarification_id),
            "status": "answered",
            "message": "Thanks! Processing will resume shortly.",
        },
    )


@router.post(
    "/{doc_id}:cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a document ingestion job",
)
async def cancel_document(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> JSONResponse:
    try:
        await service.cancel_document(doc_id)
    except DocumentService.DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "doc_id": str(doc_id),
            "status": "cancelled",
            "message": "Document cancelled by user.",
        },
    )


@router.get(
    "/{doc_id}/modules",
    response_model=ModuleListResponse,
    summary="List modules and their features for a document",
)
async def get_document_modules(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> ModuleListResponse:
    modules = await service.get_modules(doc_id)
    if modules is None:
        raise HTTPException(status_code=404, detail="Modules not available for this document")
    return ModuleListResponse(doc_id=doc_id, modules=modules)


@router.get(
    "/{doc_id}/scope",
    response_model=OutputFormatScopeDocument | ScopeDocument,  # Support both formats
    summary="Retrieve the latest scope document for a given submission",
)
async def get_document_scope(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> OutputFormatScopeDocument | ScopeDocument:
    scope = await service.get_scope(doc_id)
    if scope is None:
        raise HTTPException(status_code=404, detail="Scope not available for this document")
    return scope


@router.get(
    "/{doc_id}/scope.xlsx",
    summary="Download scope as an Excel file",
)
async def download_document_scope_excel(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> StreamingResponse:
    try:
        excel_bytes = await service.get_scope_excel(doc_id)
    except DocumentService.DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentService.ScopeNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        content=iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="scope-{doc_id}.xlsx"'},
    )


@router.get(
    "/{doc_id}/scope.pdf",
    summary="Download scope as a PDF file",
)
async def download_document_scope_pdf(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> StreamingResponse:
    try:
        pdf_bytes = await service.get_scope_pdf(doc_id)
    except DocumentService.DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentService.ScopeNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        content=iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="scope-{doc_id}.pdf"'},
    )


@router.post(
    "/extract-for-scope",
    response_model=ScopeExtractForScopeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Extract scope from document with scope context and hours estimation",
)
async def extract_for_scope(
    request: ScopeExtractForScopeRequest,
    service: DocumentService = Depends(get_document_service),
) -> ScopeExtractForScopeResponse:
    """
    Extract scope from document with scope context.
    Returns structured scope sections (modules with features and subfeatures) that can be mapped to ScopeSection records.
    """
    # Get document from store (or fetch from main DB if needed)
    # For now, we'll use the document service to get the document
    # TODO: Integrate with main database to fetch document by document_id
    
    # This is a placeholder - in production, fetch document from main DB
    # For now, we'll create a temporary document record
    from clarivo_ingestion.services.store import store
    from clarivo_ingestion.schemas.documents import DocumentRecord, DocumentStatus, DocumentStage
    
    # Try to get document from store (ingestion service's document store)
    try:
        document = await store.get(request.document_id)
    except Exception as e:
        logger.error(f"Failed to get document from store: {e}")
        # Document not in store, might be in main DB
        # For now, return error - in production, fetch from main DB
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found in ingestion service. Please ensure document was created via ingestion service API first."
        )
    
    if not document.content:
        raise HTTPException(status_code=400, detail="Document has no content")
    
    # Generate scope using LLM with template guidance
    settings = get_settings()
    backend_dir = Path(__file__).parent.parent.parent.parent
    input_dir = backend_dir / "Input"
    output_dir = backend_dir / "Output"
    
    llm_generator = LLMDocumentScopeGenerator(
        settings=settings,
        input_dir=input_dir,
        output_dir=output_dir,
    )
    
    # Load template structure if provided in request
    template_structure = request.template_structure if request.template_structure else None
    if request.template_id and not template_structure:
        logger.info(f"Template ID provided: {request.template_id}, but template structure not passed. Using template ID only.")
        # Template structure should be passed from main backend
        # If not provided, LLM will generate without template guidance
    
    # Generate scope
    try:
        generated_scope = await llm_generator.generate(document.content, template_structure=template_structure)
        
        # Map to scope sections (modules with features and subfeatures)
        scope_sections_data = _map_scope_to_sections(
            generated_scope,
            template_id=request.template_id,
            template_structure=template_structure,
        )
        
        # Convert to ScopeSectionData objects
        scope_sections = [
            ScopeSectionData(**section_data) for section_data in scope_sections_data
        ]
        
        extraction_id = uuid4()
        
        return ScopeExtractForScopeResponse(
            extraction_id=extraction_id,
            status="completed",
            scope_sections=scope_sections,
            confidence_score=85,  # TODO: Calculate from LLM response
            risk_level="low",  # TODO: Calculate from scope complexity
            total_hours=0,  # No hours estimation
            estimated_time=30,
        )
    except LLMDocumentScopeGenerator.ParseError as exc:
        # JSON parsing failed - try to use heuristic parser as fallback
        error_msg = str(exc)
        logger.warning(f"LLM JSON parsing failed for document {request.document_id}: {error_msg}")
        logger.info("Attempting fallback to heuristic scope parser...")
        
        try:
            from clarivo_ingestion.services.scope import ScopeParser
            heuristic_parser = ScopeParser()
            generated_scope = heuristic_parser.parse(document.content)
            
            logger.info(f"Heuristic parser succeeded with {len(generated_scope.modules)} modules and {len(generated_scope.features)} features")
            
            # Map to scope sections
            scope_sections_data = _map_scope_to_sections(
                generated_scope,
                template_id=request.template_id,
                template_structure=template_structure,
            )
            
            scope_sections = [
                ScopeSectionData(**section_data) for section_data in scope_sections_data
            ]
            
            extraction_id = uuid4()
            
            return ScopeExtractForScopeResponse(
                extraction_id=extraction_id,
                status="completed",
                scope_sections=scope_sections,
                confidence_score=70,  # Lower confidence for heuristic parser
                risk_level="medium",  # Higher risk for heuristic parser
                total_hours=0,
                estimated_time=30,
            )
        except Exception as fallback_exc:
            logger.error(f"Heuristic parser fallback also failed: {fallback_exc}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate scope: LLM JSON parsing failed and heuristic parser fallback also failed. Original error: {error_msg}"
            )
    except LLMDocumentScopeGenerator.ProviderError as exc:
        # Handle timeout and API errors gracefully
        error_msg = str(exc)
        if "timed out" in error_msg.lower():
            logger.warning(f"Scope generation timed out for document {request.document_id}: {error_msg}")
            # Return a processing status instead of error - backend can retry or poll
            extraction_id = uuid4()
            return ScopeExtractForScopeResponse(
                extraction_id=extraction_id,
                status="processing",
                scope_sections=[],
                confidence_score=0,
                risk_level="medium",
                total_hours=0,
                estimated_time=600,  # 10 minutes estimate for large documents
            )
        else:
            logger.error(f"LLM provider error for document {request.document_id}: {error_msg}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"LLM provider error: {error_msg}"
            )
    except LLMDocumentScopeGenerator.ParseError as exc:
        # Handle JSON parsing errors - log more details
        error_msg = str(exc)
        logger.error(f"JSON parsing error for document {request.document_id}: {error_msg}", exc_info=True)
        # Try to return partial results if possible, or return error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM response as JSON. The response may be malformed. Error: {error_msg}"
        )
    except Exception as exc:
        logger.error(f"Failed to generate scope: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate scope: {str(exc)}"
        )


def _map_scope_to_sections(
    scope: ScopeDocument | OutputFormatScopeDocument,
    template_id: UUID | None = None,
    template_structure: dict | None = None,
) -> list[dict]:
    """
    Map generated scope document to scope sections.
    
    Returns list of section dictionaries ready for ScopeSection creation.
    Structure: Modules with features and subfeatures, each with descriptions.
    """
    import json
    
    sections = []
    order_index = 0
    
    # Handle both ScopeDocument and OutputFormatScopeDocument formats
    modules = []
    if isinstance(scope, OutputFormatScopeDocument):
        modules = scope.modules or scope.featureModules or []
    elif isinstance(scope, ScopeDocument):
        # Convert ScopeDocument format to sections
        # Create Project Overview section
        if scope.executive_summary:
            sections.append({
                "title": "Project Overview",
                "content": json.dumps({
                    "overview": scope.executive_summary.overview,
                    "key_points": scope.executive_summary.key_points,
                }, indent=2),
                "section_type": "overview",
                "order_index": order_index,
                "confidence_score": 85,
                "hours_breakdown": None,
            })
            order_index += 1
        
        # Process modules from ScopeDocument
        if scope.modules:
            # Track which features have been assigned to modules
            assigned_features = set()
            
            # Convert ScopeDocument modules to sections with features and subfeatures
            for module in scope.modules:
                # Create a module structure with summary/description
                module_content = {
                    "name": module.name,
                    "summary": module.description or "",  # Module summary/description
                    "description": module.description or "",
                    "features": [],
                }
                
                # Normalize module feature names for matching (case-insensitive, strip whitespace)
                module_feature_names = {name.strip().lower() for name in (module.features or [])}
                
                # Process features from the scope's features list that match this module
                for feature in (scope.features or []):
                    # Normalize feature name for matching
                    feature_name_normalized = feature.name.strip().lower()
                    
                    # Check if feature matches this module (exact match)
                    if feature_name_normalized in module_feature_names:
                        # Extract subfeatures from acceptance_criteria or create from dependencies
                        sub_features = []
                        if feature.acceptance_criteria:
                            # Use acceptance criteria as subfeatures
                            sub_features = [
                                {
                                    "name": criterion,
                                    "description": criterion,
                                }
                                for criterion in feature.acceptance_criteria
                            ]
                        elif feature.dependencies:
                            # Use dependencies as subfeatures if no acceptance criteria
                            sub_features = [
                                {
                                    "name": dep,
                                    "description": f"Dependency: {dep}",
                                }
                                for dep in feature.dependencies
                            ]
                        
                        feature_data = {
                            "name": feature.name,
                            "description": feature.summary or "",
                            "sub_features": sub_features,
                        }
                        
                        module_content["features"].append(feature_data)
                        assigned_features.add(feature.name)
                
                # Create section for module (even if no features matched, still create the module)
                sections.append({
                    "title": module.name,
                    "content": json.dumps(module_content, indent=2),
                    "section_type": "deliverable",
                    "order_index": order_index,
                    "confidence_score": 85,
                    "hours_breakdown": None,  # No hours estimation
                })
                order_index += 1
            
            # Distribute unassigned features evenly across modules
            unassigned_features = [f for f in (scope.features or []) if f.name not in assigned_features]
            if unassigned_features and scope.modules:
                # Distribute features across modules
                modules_with_sections = [s for s in sections if s.get("section_type") == "deliverable"]
                if modules_with_sections:
                    for idx, feature in enumerate(unassigned_features):
                        # Round-robin distribution
                        target_module_idx = idx % len(modules_with_sections)
                        target_section = modules_with_sections[target_module_idx]
                        
                        # Parse existing content
                        module_content = json.loads(target_section["content"])
                        
                        # Extract subfeatures from acceptance_criteria
                        sub_features = []
                        if feature.acceptance_criteria:
                            sub_features = [
                                {
                                    "name": criterion,
                                    "description": criterion,
                                }
                                for criterion in feature.acceptance_criteria
                            ]
                        elif feature.dependencies:
                            sub_features = [
                                {
                                    "name": dep,
                                    "description": f"Dependency: {dep}",
                                }
                                for dep in feature.dependencies
                            ]
                        
                        feature_data = {
                            "name": feature.name,
                            "description": feature.summary or "",
                            "sub_features": sub_features,
                        }
                        
                        module_content["features"].append(feature_data)
                        
                        # Update section content
                        target_section["content"] = json.dumps(module_content, indent=2)
        
        # If no modules but there are features, create sections from features directly
        elif scope.features:
            for feature in scope.features:
                # Extract subfeatures from acceptance_criteria
                sub_features = []
                if feature.acceptance_criteria:
                    sub_features = [
                        {
                            "name": criterion,
                            "description": criterion,
                        }
                        for criterion in feature.acceptance_criteria
                    ]
                
                sections.append({
                    "title": feature.name,
                    "content": json.dumps({
                        "name": feature.name,
                        "summary": feature.summary or "",
                        "description": feature.summary or "",
                        "priority": feature.priority,
                        "acceptance_criteria": feature.acceptance_criteria,
                        "sub_features": sub_features,
                    }, indent=2),
                    "section_type": "feature",
                    "order_index": order_index,
                    "confidence_score": 85,
                    "hours_breakdown": None,  # No hours estimation
                })
                order_index += 1
    
    # Process modules from OutputFormatScopeDocument (no hours estimation)
    for module in modules:
        # Create module structure with summary/description
        module_content = {
            "name": module.name,
            "summary": module.description or "",  # Module summary/description
            "description": module.description or "",
            "features": [],
        }
        
        # Process features with subfeatures
        for feature in module.features:
            # Extract subfeatures - handle both string list and object list
            sub_features = []
            if feature.subfeatures:
                for sub_feat in feature.subfeatures:
                    if isinstance(sub_feat, str):
                        sub_features.append({
                            "name": sub_feat,
                            "description": sub_feat,
                        })
                    else:
                        # If it's already an object/dict
                        sub_features.append({
                            "name": sub_feat.get("name", str(sub_feat)),
                            "description": sub_feat.get("description", sub_feat.get("name", str(sub_feat))),
                        })
            
            feature_data = {
                "name": feature.name,
                "description": feature.description or "",
                "sub_features": sub_features,
            }
            
            module_content["features"].append(feature_data)
        
        # Create section for module
        sections.append({
            "title": module.name,
            "content": json.dumps(module_content, indent=2),
            "section_type": "deliverable",
            "order_index": order_index,
            "confidence_score": 85,
            "hours_breakdown": None,  # No hours estimation
        })
        order_index += 1
    
    return sections

