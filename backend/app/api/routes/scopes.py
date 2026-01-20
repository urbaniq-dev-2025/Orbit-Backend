from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from typing import Optional
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
    ScopeListResponse,
    ScopeReorderRequest,
    ScopeSectionCreate,
    ScopeSectionPublic,
    ScopeSectionUpdate,
    ScopeStatusUpdate,
    ScopeSummary,
    ScopeUpdate,
    ScopeUploadResponse,
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
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    project_id: Optional[uuid.UUID] = Query(None, alias="projectId"),
    client_id: Optional[uuid.UUID] = Query(None, alias="clientId"),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_favourite: Optional[bool] = Query(None, alias="isFavourite"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ScopeListResponse:
    """List scopes with filters and pagination."""
    try:
        scope_status = status if status in ["draft", "in_review", "approved", "rejected"] else None
        scope_list, total = await scope_service.list_scopes(
            session,
            current_user.id,
            workspace_id=workspace_id,
            project_id=project_id,
            client_id=client_id,
            status=scope_status,
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

            summaries.append(
                ScopeSummary(
                    id=scope.id,
                    workspace_id=scope.workspace_id,
                    project_id=scope.project_id,
                    title=scope.title,
                    description=scope.description,
                    status=scope.status,
                    progress=scope.progress,
                    confidence_score=scope.confidence_score,
                    risk_level=scope.risk_level,
                    due_date=scope.due_date,
                    created_by=scope.created_by,
                    created_at=scope.created_at,
                    updated_at=scope.updated_at,
                    project_name=project_name,
                    client_id=client_id,
                    client_name=client_name,
                    is_favourite=scope.id in favourites,
                )
            )

        return ScopeListResponse(
            scopes=summaries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
    except Exception as exc:
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
    payload: ScopeUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Update a scope."""
    try:
        scope = await scope_service.update_scope(session, scope_id, current_user.id, payload)
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
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
    Export scope to PDF or DOCX format.
    Note: File storage infrastructure needs to be configured for production use.
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
        return ScopeExportResponse(
            download_url=result["download_url"],
            expires_at=result["expires_at"],
        )
    except Exception as exc:
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
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum of {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # TODO: Upload file to storage (S3, local filesystem, etc.)
        # For now, create a placeholder file URL
        # In production, this should:
        # 1. Generate unique filename
        # 2. Upload to storage service
        # 3. Get file URL
        # 4. Store in Document model

        import os
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


# Helper Functions


async def _build_scope_detail(session, scope: Scope, user_id: uuid.UUID) -> ScopeDetail:
    """Build ScopeDetail response with sections and counts."""
    # Get sections
    sections = [
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
        for s in sorted(scope.sections, key=lambda x: (x.order_index, x.created_at))
    ]

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

    return ScopeDetail(
        id=scope.id,
        workspace_id=scope.workspace_id,
        project_id=scope.project_id,
        title=scope.title,
        description=scope.description,
        status=scope.status,
        progress=scope.progress,
        confidence_score=scope.confidence_score,
        risk_level=scope.risk_level,
        due_date=scope.due_date,
        created_by=scope.created_by,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
        sections=sections,
        documents_count=documents_count,
        comments_count=comments_count,
        is_favourite=is_favourite,
    )


