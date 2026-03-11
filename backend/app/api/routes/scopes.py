from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select

from app.api import deps
from app.models import Comment, Document, Favourite, Scope
from app.schemas.scope import (
    ScopeCreate,
    ScopeDetail,
    ScopeExportRequest,
    ScopeExportResponse,
    ScopeExtractRequest,
    ScopeExtractResponse,
    ScopeFeaturesResponse,
    ScopeListResponse,
    ScopeReorderRequest,
    ScopeSectionCreate,
    ScopeSectionPublic,
    ScopeSectionUpdate,
    ScopeStatusUpdate,
    ScopeSummary,
    ScopeUpdate,
    ScopeUploadResponse,
    ModuleItem,
    FeatureItem,
    SubFeature,
)
from app.services import scopes as scope_service

router = APIRouter()


def _map_scope_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, scope_service.ScopeNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, scope_service.ScopeAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, scope_service.ScopeSectionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to process scope request."
    )


@router.get("", response_model=ScopeListResponse)
async def list_scopes(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
    project_id: uuid.UUID | None = Query(None, alias="projectId"),
    client_id: uuid.UUID | None = Query(None, alias="clientId"),
    status: str | None = Query(None),
    search: str | None = Query(None),
    is_favourite: bool | None = Query(None, alias="isFavourite"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ScopeListResponse:
    """List scopes with filters and pagination."""
    try:
        # Rename parameter to avoid shadowing fastapi.status module
        scope_status_param = status if status in ["draft", "in_review", "approved", "rejected"] else None
        scope_list, total = await scope_service.list_scopes(
            session,
            current_user.id,
            workspace_id=workspace_id,
            project_id=project_id,
            client_id=client_id,
            status=scope_status_param,
            search=search,
            is_favourite=is_favourite,
            page=page,
            page_size=page_size,
        )

        # Get favourite status for each scope (if not already filtered)
        scope_ids = [s.id for s in scope_list]
        favourites = set()
        if scope_ids:
            fav_stmt = select(Favourite.scope_id).where(
                Favourite.scope_id.in_(scope_ids),
                Favourite.user_id == current_user.id,
            )
            fav_result = await session.execute(fav_stmt)
            favourites = {row[0] for row in fav_result.all()}

        summaries = []
        for scope in scope_list:
            # Get project and client info
            project_name = None
            client_id = None
            client_name = None
            
            if scope.project:
                project_name = scope.project.name
                if scope.project.client:
                    client_id = scope.project.client.id
                    client_name = scope.project.client.name
                elif scope.project.client_id:
                    # Client exists but not loaded, fetch it
                    from app.models import Client
                    client_stmt = select(Client).where(Client.id == scope.project.client_id)
                    client_result = await session.execute(client_stmt)
                    client = client_result.scalar_one_or_none()
                    if client:
                        client_id = client.id
                        client_name = client.name

            # Use model_validate with camelCase field names for Pydantic v2 compatibility
            summaries.append(
                ScopeSummary.model_validate({
                    "id": scope.id,
                    "workspaceId": scope.workspace_id,
                    "projectId": scope.project_id,
                    "title": scope.title,
                    "description": scope.description,
                    "status": scope.status,
                    "progress": scope.progress,
                    "confidenceScore": scope.confidence_score if scope.confidence_score is not None else 0,
                    "riskLevel": scope.risk_level if scope.risk_level is not None else "low",
                    "dueDate": scope.due_date,
                    "createdBy": scope.created_by,
                    "createdAt": scope.created_at,
                    "updatedAt": scope.updated_at,
                    "projectName": project_name,
                    "clientId": client_id,
                    "clientName": client_name,
                    "isFavourite": scope.id in favourites,
                })
            )

        # Use model_validate with camelCase field names for Pydantic v2 compatibility
        return ScopeListResponse.model_validate({
            "scopes": summaries,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasMore": (page * page_size) < total,
        })
    except Exception as exc:
        # Log the actual exception for debugging
        import traceback
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error in list_scopes: {exc}")
        logger.error(traceback.format_exc())
        raise _map_scope_exception(exc) from exc


@router.post("", response_model=ScopeDetail, status_code=status.HTTP_201_CREATED)
async def create_scope(
    request: Request,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    file: Optional[UploadFile] = File(None),
) -> ScopeDetail:
    """
    Create a new scope with optional input processing.
    
    Supports:
    - Template selection (templateId)
    - Multiple input sources (inputType: pdf, text, speech, ai_generate, google_docs, notion)
    - File uploads (for PDF or speech)
    - AI model selection (aiModel)
    - Hours estimation preferences (developerLevel, developerExperienceYears)
    """
    try:
        from app.services.scope_input_handler import create_scope_with_input
        from app.core.logging import get_logger
        
        logger = get_logger(__name__)
        
        # Parse payload from request body (handles both JSON and form data)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body_data = await request.json()
            # Clean up templateId - handle string identifiers or convert null/empty to None
            if "templateId" in body_data:
                template_id_value = body_data["templateId"]
                if template_id_value is None or template_id_value == "":
                    body_data["templateId"] = None
                elif isinstance(template_id_value, str):
                    # Check if it's a valid UUID format (36 chars with dashes)
                    is_uuid_format = len(template_id_value) == 36 and template_id_value.count("-") == 4
                    
                    if not is_uuid_format:
                        # If it's not a UUID format, try to find template by name/identifier
                        try:
                            from sqlalchemy import select
                            from app.models import Template
                            
                            # Try to find template by name (case-insensitive)
                            template_stmt = select(Template).where(
                                Template.name.ilike(template_id_value),
                                Template.type == "scope"
                            ).limit(1)
                            template_result = await session.execute(template_stmt)
                            template = template_result.scalar_one_or_none()
                            
                            if template:
                                body_data["templateId"] = str(template.id)
                            else:
                                # If not found, set to None (optional field)
                                logger.warning(f"Template not found by name '{template_id_value}', proceeding without template")
                                body_data["templateId"] = None
                        except Exception as e:
                            # If lookup fails, set to None
                            logger.warning(f"Failed to lookup template by name '{template_id_value}': {e}")
                            body_data["templateId"] = None
                    # If it's already a valid UUID format, keep it as is
            
            # Clean up projectId - convert null/empty string to None
            if "projectId" in body_data and (body_data["projectId"] is None or body_data["projectId"] == ""):
                body_data["projectId"] = None
            
            # Clean up inputData - ensure it's a string if provided
            if "inputData" in body_data:
                if body_data["inputData"] is None:
                    body_data["inputData"] = None
                elif not isinstance(body_data["inputData"], str):
                    # Convert to string if it's not already
                    body_data["inputData"] = str(body_data["inputData"])
            
            payload = ScopeCreate(**body_data)
        else:
            # Form data
            form_data = await request.form()
            payload_dict = dict(form_data)
            # Convert string values to appropriate types
            if "workspaceId" in payload_dict:
                payload_dict["workspaceId"] = uuid.UUID(payload_dict["workspaceId"])
            if "projectId" in payload_dict and payload_dict["projectId"]:
                payload_dict["projectId"] = uuid.UUID(payload_dict["projectId"])
            
            # Handle templateId - support both UUID and string identifiers
            if "templateId" in payload_dict:
                template_id_value = payload_dict["templateId"]
                if template_id_value is None or template_id_value == "":
                    payload_dict["templateId"] = None
                elif isinstance(template_id_value, str):
                    # Check if it's a valid UUID format (36 chars with dashes)
                    is_uuid_format = len(template_id_value) == 36 and template_id_value.count("-") == 4
                    
                    if not is_uuid_format:
                        # If it's not a UUID format, try to find template by name/identifier
                        try:
                            from sqlalchemy import select
                            from app.models import Template
                            
                            # Try to find template by name (case-insensitive)
                            template_stmt = select(Template).where(
                                Template.name.ilike(template_id_value),
                                Template.type == "scope"
                            ).limit(1)
                            template_result = await session.execute(template_stmt)
                            template = template_result.scalar_one_or_none()
                            
                            if template:
                                payload_dict["templateId"] = str(template.id)
                            else:
                                # If not found, set to None (optional field)
                                logger.warning(f"Template not found by name '{template_id_value}', proceeding without template")
                                payload_dict["templateId"] = None
                        except Exception as e:
                            # If lookup fails, set to None
                            logger.warning(f"Failed to lookup template by name '{template_id_value}': {e}")
                            payload_dict["templateId"] = None
                    else:
                        # It's a valid UUID format, convert it
                        payload_dict["templateId"] = uuid.UUID(template_id_value)
            
            if "developerExperienceYears" in payload_dict:
                payload_dict["developerExperienceYears"] = int(payload_dict["developerExperienceYears"])
            payload = ScopeCreate(**payload_dict)
        
        # If file is uploaded, read it
        file_content = None
        filename = None
        if file:
            file_content = await file.read()
            filename = file.filename
        
        # Use enhanced scope creation with input processing
        if payload.input_type and (payload.input_data or payload.input_url or file_content):
            result = await create_scope_with_input(
                session,
                current_user.id,
                payload,
                file_upload=file_content,
                filename=filename,
            )
            scope_id = result["scope_id"]
        else:
            # Standard scope creation without input processing
            scope = await scope_service.create_scope(session, current_user.id, payload)
            # Ensure scope is committed before fetching
            await session.commit()
            await session.refresh(scope)
            scope_id = scope.id
        
        # Fetch and return scope details
        scope = await scope_service.get_scope(session, scope_id, current_user.id, include_sections=True)
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error creating scope: {exc}", exc_info=True)
        raise _map_scope_exception(exc) from exc


@router.get("/{scope_id}", response_model=ScopeDetail)
async def get_scope(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Get scope details with sections."""
    try:
        scope = await scope_service.get_scope(session, scope_id, current_user.id, include_sections=True)
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.put("/{scope_id}", response_model=ScopeDetail)
async def update_scope(
    scope_id: uuid.UUID,
    request: Request,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Update a scope."""
    try:
        # Parse request body to handle status field conversion
        body_data = await request.json()

        # Convert camelCase status to snake_case if needed
        if "status" in body_data and body_data["status"]:
            status_value = body_data["status"]
            # Map camelCase to snake_case
            status_map = {
                "inReview": "in_review",
                "in_review": "in_review",
                "draft": "draft",
                "approved": "approved",
                "rejected": "rejected",
            }
            if status_value in status_map:
                body_data["status"] = status_map[status_value]
            elif status_value not in ["draft", "in_review", "approved", "rejected"]:
                # Invalid status value
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid status value: "
                        f"{status_value}. Valid values are: draft, in_review, approved, rejected"
                    ),
                )

        # Convert camelCase field names to snake_case for Pydantic
        if "dueDate" in body_data:
            body_data["due_date"] = body_data.pop("dueDate")

        # Create payload from cleaned data
        payload = ScopeUpdate(**body_data)

        scope = await scope_service.update_scope(session, scope_id, current_user.id, payload)

        # Reload scope with sections eagerly loaded to avoid MissingGreenlet error
        scope = await scope_service.get_scope(
            session,
            scope_id,
            current_user.id,
            include_sections=True,
        )

        return await _build_scope_detail(session, scope, current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        # Log the actual exception for debugging
        from app.core.logging import get_logger
        import traceback
        logger = get_logger(__name__)
        logger.error(f"Error updating scope {scope_id}: {exc}")
        logger.error(traceback.format_exc())
        raise _map_scope_exception(exc) from exc


@router.delete("/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a scope."""
    try:
        await scope_service.delete_scope(session, scope_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/duplicate", response_model=ScopeDetail, status_code=status.HTTP_201_CREATED)
async def duplicate_scope(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Duplicate a scope with all its sections."""
    try:
        scope = await scope_service.duplicate_scope(session, scope_id, current_user.id)
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.put("/{scope_id}/status", response_model=ScopeDetail)
async def update_scope_status(
    scope_id: uuid.UUID,
    payload: ScopeStatusUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Update scope status."""
    try:
        scope = await scope_service.update_scope_status(
            session, scope_id, current_user.id, payload.status
        )
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/favourite", status_code=status.HTTP_201_CREATED)
async def add_scope_favourite(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> dict[str, bool]:
    """Add scope to user's favourites."""
    try:
        await scope_service.add_scope_favourite(session, scope_id, current_user.id)
        return {"success": True}
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.delete("/{scope_id}/favourite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_scope_favourite(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Remove scope from user's favourites."""
    try:
        await scope_service.remove_scope_favourite(session, scope_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


# Scope Sections Endpoints


@router.get("/{scope_id}/sections", response_model=List[ScopeSectionPublic])
async def list_scope_sections(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> List[ScopeSectionPublic]:
    """List all sections for a scope."""
    try:
        sections = await scope_service.list_scope_sections(session, scope_id, current_user.id)
        return [
            ScopeSectionPublic(
                id=s.id,
                scope_id=s.scope_id,
                title=s.title,
                content=s.content,
                section_type=s.section_type,
                order_index=s.order_index,
                ai_generated=s.ai_generated,
                confidence_score=s.confidence_score,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sections
        ]
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/sections", response_model=ScopeSectionPublic, status_code=status.HTTP_201_CREATED)
async def create_scope_section(
    scope_id: uuid.UUID,
    payload: ScopeSectionCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeSectionPublic:
    """Create a new section for a scope."""
    try:
        section = await scope_service.create_scope_section(
            session,
            scope_id,
            current_user.id,
            title=payload.title,
            content=payload.content,
            section_type=payload.section_type,
            order_index=payload.order_index,
        )
        return ScopeSectionPublic(
            id=section.id,
            scope_id=section.scope_id,
            title=section.title,
            content=section.content,
            section_type=section.section_type,
            order_index=section.order_index,
            ai_generated=section.ai_generated,
            confidence_score=section.confidence_score,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.put("/{scope_id}/sections/{section_id}", response_model=ScopeSectionPublic)
async def update_scope_section(
    scope_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: ScopeSectionUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeSectionPublic:
    """Update a scope section."""
    try:
        section = await scope_service.update_scope_section(
            session,
            scope_id,
            section_id,
            current_user.id,
            title=payload.title,
            content=payload.content,
            order_index=payload.order_index,
        )
        return ScopeSectionPublic(
            id=section.id,
            scope_id=section.scope_id,
            title=section.title,
            content=section.content,
            section_type=section.section_type,
            order_index=section.order_index,
            ai_generated=section.ai_generated,
            confidence_score=section.confidence_score,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.delete("/{scope_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope_section(
    scope_id: uuid.UUID,
    section_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a scope section."""
    try:
        await scope_service.delete_scope_section(session, scope_id, section_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.put("/{scope_id}/sections/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_scope_sections(
    scope_id: uuid.UUID,
    payload: ScopeReorderRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Reorder scope sections."""
    try:
        await scope_service.reorder_scope_sections(
            session, scope_id, current_user.id, payload.section_ids
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/export", response_model=ScopeExportResponse, status_code=status.HTTP_200_OK)
async def export_scope(
    scope_id: uuid.UUID,
    payload: ScopeExportRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeExportResponse:
    """
    Export scope to PDF, DOCX, or print format.
    
    Formats:
    - pdf: Returns download URL for PDF file
    - docx: Returns download URL for Word document
    - print: Returns print-optimized JSON data
    """
    try:
        result = await scope_service.export_scope(
            session,
            scope_id,
            current_user.id,
            format=payload.format,
            include_sections=payload.include_sections,
            template=payload.template,
        )
        return ScopeExportResponse.model_validate({
            "downloadUrl": result.get("download_url"),
            "expiresAt": result.get("expires_at"),
            "printData": result.get("print_data"),
        })
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.get("/{scope_id}/exports/{filename}")
async def download_scope_export(
    scope_id: uuid.UUID,
    filename: str,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """
    Download an exported scope file (PDF or DOCX).
    """
    try:
        # Verify scope access
        await scope_service.get_scope(session, scope_id, current_user.id, include_sections=False)
        
        # Load file from storage
        from pathlib import Path
        from app.services.scope_export import EXPORT_STORAGE_DIR
        
        file_path = EXPORT_STORAGE_DIR / f"{scope_id}_{filename}"
        
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
        
        # Determine content type
        if filename.endswith(".pdf"):
            media_type = "application/pdf"
        elif filename.endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            media_type = "application/octet-stream"
        
        file_bytes = file_path.read_bytes()
        
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/upload", response_model=ScopeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_scope_document(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    file: UploadFile = File(...),
    current_user=Depends(deps.get_current_user),
) -> ScopeUploadResponse:
    """
    Upload a document for a scope.
    Supports PDF, DOCX, TXT, and image files.
    Note: File storage infrastructure needs to be configured.
    """
    try:
        # Validate file type
        allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg"}
        file_ext = None
        for ext in allowed_extensions:
            if file.filename and file.filename.lower().endswith(ext):
                file_ext = ext
                break

        if not file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}",
            )

        # Validate file size (50MB max)
        max_file_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum of {max_file_size // (1024 * 1024)}MB",
            )

        # TODO: Upload file to storage (S3, local filesystem, etc.)
        # For now, create a placeholder file URL
        # In production, this should:
        # 1. Generate unique filename
        # 2. Upload to storage service
        # 3. Get file URL
        # 4. Store in Document model

        from pathlib import Path

        # Placeholder: Save to local storage (for development)
        # In production, use S3 or similar
        upload_dir = Path("uploads") / str(scope_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / unique_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        # Generate file URL (placeholder - in production this would be a storage URL)
        file_url = f"/uploads/{scope_id}/{unique_filename}"

        # Create document record
        document = await scope_service.upload_scope_document(
            session,
            scope_id,
            current_user.id,
            filename=file.filename or unique_filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            file_url=file_url,
        )

        return ScopeUploadResponse(
            upload_id=document.id,
            status="processing",
            message="Document uploaded, extraction in progress",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.post("/{scope_id}/extract", response_model=ScopeExtractResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_scope_from_document(
    scope_id: uuid.UUID,
    payload: ScopeExtractRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeExtractResponse:
    """
    Trigger AI extraction from uploaded document.
    Returns extraction job ID for status polling.
    Now supports template guidance and hours estimation.
    """
    try:
        result = await scope_service.extract_scope_from_document(
            session,
            scope_id,
            current_user.id,
            upload_id=payload.upload_id,
            extraction_type=payload.extraction_type,
            template_id=payload.template_id,
            ai_model=payload.ai_model,
            developer_level=payload.developer_level,
            developer_experience_years=payload.developer_experience_years,
        )
        return ScopeExtractResponse(
            extraction_id=result["extraction_id"],
            status=result["status"],
            estimated_time=result["estimated_time"],
        )
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.get("/{scope_id}/features", response_model=ScopeFeaturesResponse)
async def get_scope_features(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeFeaturesResponse:
    """
    Get modules and features for a scope (Features tab).
    Extracts modules and features from scope sections, excluding status and hours.
    """
    try:
        # Get scope with sections
        scope = await scope_service.get_scope(session, scope_id, current_user.id, include_sections=True)
        
        modules = []
        
        # Process sections to extract modules and features
        for section in sorted(scope.sections, key=lambda x: (x.order_index or 0, x.created_at or datetime.now(timezone.utc))):
            # Skip overview sections - only process deliverable sections
            if section.section_type == "overview":
                continue
            
            # Parse section content (stored as JSON string)
            if not section.content:
                continue
                
            try:
                content_data = json.loads(section.content) if isinstance(section.content, str) else section.content
            except (json.JSONDecodeError, TypeError):
                # If content is not valid JSON, skip this section
                continue
            
            # Check if this section has module structure (name, features, etc.)
            if isinstance(content_data, dict) and "name" in content_data:
                # This is a module section
                module_name = content_data.get("name") or section.title
                module_description = content_data.get("description") or content_data.get("summary") or ""
                module_summary = content_data.get("summary") or content_data.get("description") or ""
                
                # Extract features
                features = []
                features_data = content_data.get("features", [])
                
                for feature_data in features_data:
                    if isinstance(feature_data, dict):
                        feature_name = feature_data.get("name", "")
                        feature_description = feature_data.get("description", "")
                        
                        # Extract sub-features
                        sub_features = []
                        sub_features_data = feature_data.get("sub_features") or feature_data.get("subFeatures", [])
                        
                        for sub_feat in sub_features_data:
                            if isinstance(sub_feat, dict):
                                sub_features.append(SubFeature(
                                    name=sub_feat.get("name", ""),
                                    description=sub_feat.get("description"),
                                ))
                            elif isinstance(sub_feat, str):
                                sub_features.append(SubFeature(
                                    name=sub_feat,
                                    description=None,
                                ))
                        
                        if feature_name:  # Only add if feature has a name
                            features.append(FeatureItem(
                                name=feature_name,
                                description=feature_description if feature_description else None,
                                subFeatures=sub_features,
                            ))
                
                # Create module (even if no features, still include the module)
                modules.append(ModuleItem(
                    name=module_name,
                    description=module_description if module_description else None,
                    summary=module_summary if module_summary else None,
                    features=features,
                ))
        
        return ScopeFeaturesResponse(modules=modules)
        
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


@router.get("/{scope_id}/document")
async def get_scope_document(
    scope_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> dict:
    """
    Get the full scope document JSON for a scope.
    Returns the original scope document structure generated by the LLM.
    """
    try:
        import json
        
        scope = await scope_service.get_scope(session, scope_id, current_user.id, include_sections=False)
        
        if not scope.scope_document_json:
            raise HTTPException(
                status_code=404,
                detail="Scope document not found. This scope may not have been generated from a document yet."
            )
        
        # Parse and return the scope document JSON
        try:
            scope_document = json.loads(scope.scope_document_json)
            return {
                "scopeId": str(scope_id),
                "document": scope_document,
            }
        except json.JSONDecodeError as exc:
            from app.core.logging import get_logger

            logger = get_logger(__name__)
            logger.error("Failed to parse scope document JSON for scope %s: %s", scope_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Scope document is corrupted and cannot be parsed.",
            ) from exc
        
    except HTTPException:
        raise
    except Exception as exc:
        raise _map_scope_exception(exc) from exc


# Helper Functions


async def _build_scope_detail(session, scope: Scope, user_id: uuid.UUID) -> ScopeDetail:
    """Build ScopeDetail response with sections and counts."""
    from datetime import datetime, timezone
    
    # Get sections - ensure all fields are properly loaded and set
    sections = []
    now = datetime.now(timezone.utc)
    
    # Access sections (should be eagerly loaded via selectinload)
    # Convert to list to avoid lazy loading issues
    scope_sections = list(scope.sections) if scope.sections else []
    
    for s in sorted(scope_sections, key=lambda x: (getattr(x, 'order_index', None) or 0, getattr(x, 'created_at', None) or now)):
        # Explicitly get all fields with proper defaults
        section_id = s.id if hasattr(s, 'id') and s.id is not None else None
        section_scope_id = s.scope_id if hasattr(s, 'scope_id') and s.scope_id is not None else scope.id
        section_title = s.title if hasattr(s, 'title') and s.title is not None else ""
        section_content = s.content if hasattr(s, 'content') else None
        section_type = s.section_type if hasattr(s, 'section_type') else None
        section_order = s.order_index if hasattr(s, 'order_index') and s.order_index is not None else 0
        section_ai_generated = s.ai_generated if hasattr(s, 'ai_generated') and s.ai_generated is not None else False
        section_confidence = s.confidence_score if hasattr(s, 'confidence_score') and s.confidence_score is not None else 0
        section_created = s.created_at if hasattr(s, 'created_at') and s.created_at is not None else now
        section_updated = s.updated_at if hasattr(s, 'updated_at') and s.updated_at is not None else now
        
        # Build section_data dict using alias names (camelCase) for Pydantic v2 compatibility
        # Even though schema has allow_population_by_field_name=True, using aliases directly is safer
        section_data = {
            'id': section_id,
            'scopeId': section_scope_id,  # Use alias name directly
            'title': section_title,
            'content': section_content,
            'sectionType': section_type,  # Use alias name directly
            'orderIndex': section_order,  # Use alias name directly
            'aiGenerated': section_ai_generated,  # Use alias name directly
            'confidenceScore': section_confidence,  # Use alias name directly
            'createdAt': section_created,  # Use alias name directly
            'updatedAt': section_updated,  # Use alias name directly
        }
        # Use model_validate for Pydantic v2 compatibility
        sections.append(ScopeSectionPublic.model_validate(section_data))

    # Get document count
    doc_count_stmt = select(func.count()).select_from(Document).where(Document.scope_id == scope.id)
    doc_count_result = await session.execute(doc_count_stmt)
    documents_count = doc_count_result.scalar_one() or 0

    # Get comment count
    comment_count_stmt = select(func.count()).select_from(Comment).where(Comment.scope_id == scope.id)
    comment_count_result = await session.execute(comment_count_stmt)
    comments_count = comment_count_result.scalar_one() or 0

    # Check if favourited
    is_favourite = await scope_service.get_scope_favourite(session, scope.id, user_id) is not None

    # Build ScopeDetail with camelCase alias names for Pydantic v2 compatibility
    scope_detail_data = {
        'id': scope.id,
        'workspaceId': scope.workspace_id if scope.workspace_id is not None else None,
        'projectId': scope.project_id if scope.project_id is not None else None,
        'title': scope.title if scope.title is not None else "",
        'description': scope.description if scope.description is not None else None,
        'status': scope.status if scope.status is not None else "draft",
        'progress': scope.progress if scope.progress is not None else 0,
        'confidenceScore': scope.confidence_score if scope.confidence_score is not None else 0,
        'riskLevel': scope.risk_level if scope.risk_level is not None else "low",
        'dueDate': scope.due_date if scope.due_date is not None else None,
        'createdBy': scope.created_by if scope.created_by is not None else None,
        'createdAt': scope.created_at if scope.created_at is not None else now,
        'updatedAt': scope.updated_at if scope.updated_at is not None else now,
        'sections': sections,
        'documentsCount': documents_count,
        'commentsCount': comments_count,
        'isFavourite': is_favourite,
    }
    
    # Add project and client info - prefer eagerly loaded relationships, with a safe fallback
    project_name = None
    client_id = None
    client_name = None

    if scope.project_id:
        project = None
        try:
            project = scope.project
        except Exception:
            project = None

        if project and getattr(project, "name", None):
            project_name = project.name
            if getattr(project, "client", None):
                client_id = project.client.id
                client_name = project.client.name
            elif getattr(project, "client_id", None):
                from app.models import Client

                client_stmt = select(Client).where(Client.id == project.client_id)
                client_result = await session.execute(client_stmt)
                client = client_result.scalar_one_or_none()
                if client:
                    client_id = client.id
                    client_name = client.name
        else:
            from app.core.logging import get_logger
            from app.models import Client, Project

            logger = get_logger(__name__)
            logger.warning(
                "Project relationship not eagerly loaded for scope %s; fetching explicitly.",
                scope.id,
            )

            project_stmt = select(Project).where(Project.id == scope.project_id)
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            if project:
                project_name = project.name
                if project.client_id:
                    client_stmt = select(Client).where(Client.id == project.client_id)
                    client_result = await session.execute(client_stmt)
                    client = client_result.scalar_one_or_none()
                    if client:
                        client_id = client.id
                        client_name = client.name

    # Add project and client info to response
    scope_detail_data["projectName"] = project_name
    scope_detail_data["clientId"] = client_id
    scope_detail_data["clientName"] = client_name

    return ScopeDetail.model_validate(scope_detail_data)


