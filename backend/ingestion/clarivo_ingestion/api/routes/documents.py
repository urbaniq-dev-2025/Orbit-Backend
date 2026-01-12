from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

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
    TextDocumentCreateRequest,
)
from clarivo_ingestion.schemas.scope import ScopeDocument, OutputFormatScopeDocument
from clarivo_ingestion.services.documents import DocumentService

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

