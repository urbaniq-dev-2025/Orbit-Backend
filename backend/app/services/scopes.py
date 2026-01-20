from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Document, Favourite, Scope, ScopeSection, Workspace, WorkspaceMember, Project, Client
from app.schemas.scope import ScopeCreate, ScopeStatus, ScopeUpdate

logger = get_logger(__name__)


class ScopeNotFoundError(Exception):
    """Raised when a requested scope does not exist."""


class ScopeAccessError(Exception):
    """Raised when a user attempts to access a scope they do not have permission for."""


async def _check_workspace_access(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if user has access to workspace."""
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_scopes(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    status: Optional[ScopeStatus] = None,
    search: Optional[str] = None,
    is_favourite: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Scope], int]:
    """List scopes with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return [], 0

    # Build query with joins for project and client info
    stmt: Select[Scope] = (
        select(Scope)
        .outerjoin(Project, Scope.project_id == Project.id)
        .outerjoin(Client, Project.client_id == Client.id)
        .where(Scope.workspace_id.in_(accessible_workspace_ids))
    )

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return [], 0
        stmt = stmt.where(Scope.workspace_id == workspace_id)

    if project_id:
        stmt = stmt.where(Scope.project_id == project_id)
    
    # Filter by client_id (via project relationship)
    if client_id:
        # Verify client belongs to accessible workspace
        from app.models import Client
        client_stmt = select(Client.id).where(
            Client.id == client_id,
            Client.workspace_id.in_(accessible_workspace_ids),
        )
        client_result = await session.execute(client_stmt)
        if client_result.scalar_one_or_none() is None:
            # Client not found or not accessible
            return [], 0
        
        # Filter scopes by projects that belong to this client
        project_ids_stmt = select(Project.id).where(Project.client_id == client_id)
        project_ids_result = await session.execute(project_ids_stmt)
        project_ids = [row[0] for row in project_ids_result.all()]
        
        if project_ids:
            stmt = stmt.where(Scope.project_id.in_(project_ids))
        else:
            # Client has no projects, return empty
            return [], 0

    if status:
        stmt = stmt.where(Scope.status == status)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Scope.title.ilike(search_pattern),
                Scope.description.ilike(search_pattern),
            )
        )

    # Filter by favourite status if requested
    if is_favourite is not None:
        # Use a subquery to check favourite status
        fav_subquery = select(Favourite.scope_id).where(Favourite.user_id == user_id)
        
        if is_favourite:
            # Only scopes that are favourited by this user
            stmt = stmt.where(Scope.id.in_(fav_subquery))
        else:
            # Only scopes that are NOT favourited by this user
            stmt = stmt.where(~Scope.id.in_(fav_subquery))

    # Get total count (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Scope.updated_at.desc()).offset(offset).limit(page_size)

    # Load project and client relationships for efficient access
    stmt = stmt.options(
        selectinload(Scope.project).selectinload(Project.client)
    )

    result = await session.execute(stmt)
    scopes = list(result.scalars().all())

    return scopes, total


async def get_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, *, include_sections: bool = True
) -> Scope:
    """Get a scope by ID with access check."""
    stmt: Select[Scope] = select(Scope).where(Scope.id == scope_id)

    if include_sections:
        stmt = stmt.options(selectinload(Scope.sections))

    result = await session.execute(stmt)
    scope = result.scalar_one_or_none()

    if scope is None:
        raise ScopeNotFoundError("Scope not found")

    # Check workspace access
    has_access = await _check_workspace_access(session, scope.workspace_id, user_id)
    if not has_access:
        raise ScopeAccessError("Access denied")

    return scope


async def create_scope(
    session: AsyncSession, user_id: uuid.UUID, payload: ScopeCreate
) -> Scope:
    """Create a new scope."""
    # Check workspace access
    has_access = await _check_workspace_access(session, payload.workspace_id, user_id)
    if not has_access:
        raise ScopeAccessError("Access denied")

    # If project_id is provided, verify it belongs to the workspace
    if payload.project_id:
        from app.models import Project

        project_stmt = select(Project).where(
            Project.id == payload.project_id,
            Project.workspace_id == payload.workspace_id,
        )
        project_result = await session.execute(project_stmt)
        if project_result.scalar_one_or_none() is None:
            raise ScopeAccessError("Project not found or does not belong to workspace")

    scope = Scope(
        workspace_id=payload.workspace_id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        progress=payload.progress,
        due_date=payload.due_date,
        created_by=user_id,
    )

    session.add(scope)
    await session.flush()
    await session.refresh(scope)
    
    # Commit the scope immediately so it's persisted
    await session.commit()
    await session.refresh(scope)

    # If template_id is provided, apply template sections
    if payload.template_id:
        from app.services import templates as template_service
        
        try:
            template = await template_service.get_template(session, payload.template_id, user_id)
            
            # Verify template type is 'scope'
            if template.type != "scope":
                raise ScopeAccessError("Template type must be 'scope'")
            
            # Increment template usage count
            template.usage_count += 1
            await session.flush()
            
            # Extract sections from template
            template_sections = template.sections.get("sections", [])
            
            # Create scope sections from template (one by one to avoid bulk insert issues)
            for template_section in template_sections:
                section = ScopeSection(
                    scope_id=scope.id,
                    title=template_section.get("title", "Untitled Section"),
                    content=template_section.get("content", ""),
                    section_type=template_section.get("section_type"),
                    order_index=template_section.get("order", 0),
                    ai_generated=False,
                    confidence_score=0,
                )
                session.add(section)
                await session.flush()  # Flush after each to get the ID
        except template_service.TemplateNotFoundError:
            # Template not found, continue without applying template
            pass
        except template_service.TemplateAccessError:
            # User doesn't have access to template, continue without applying
            pass

    return scope


async def update_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, payload: ScopeUpdate
) -> Scope:
    """Update a scope."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)

    if payload.title is not None:
        scope.title = payload.title
    if payload.description is not None:
        scope.description = payload.description
    if payload.status is not None:
        scope.status = payload.status
    if payload.progress is not None:
        scope.progress = payload.progress
    if payload.due_date is not None:
        scope.due_date = payload.due_date

    await session.commit()
    await session.refresh(scope)

    return scope


async def update_scope_status(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, status: ScopeStatus
) -> Scope:
    """Update scope status."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)
    scope.status = status
    await session.commit()
    await session.refresh(scope)
    return scope


async def delete_scope(session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Delete a scope."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)
    await session.delete(scope)
    await session.commit()


async def duplicate_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Scope:
    """Duplicate a scope with all its sections."""
    original = await get_scope(session, scope_id, user_id, include_sections=True)

    # Create new scope
    new_scope = Scope(
        workspace_id=original.workspace_id,
        project_id=original.project_id,
        title=f"{original.title} (Copy)",
        description=original.description,
        status="draft",
        progress=0,
        due_date=original.due_date,
        created_by=user_id,
    )
    session.add(new_scope)
    await session.flush()
    await session.refresh(new_scope)

    # Copy sections
    for section in original.sections:
        new_section = ScopeSection(
            scope_id=new_scope.id,
            title=section.title,
            content=section.content,
            section_type=section.section_type,
            order_index=section.order_index,
            ai_generated=section.ai_generated,
            confidence_score=section.confidence_score,
        )
        session.add(new_section)

    await session.commit()
    await session.refresh(new_scope)

    # Reload with sections
    return await get_scope(session, new_scope.id, user_id, include_sections=True)


async def get_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Favourite]:
    """Get favourite record for scope and user."""
    stmt = select(Favourite).where(
        Favourite.scope_id == scope_id,
        Favourite.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Favourite:
    """Add scope to user's favourites."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # Check if already favourited
    existing = await get_scope_favourite(session, scope_id, user_id)
    if existing:
        return existing

    favourite = Favourite(scope_id=scope_id, user_id=user_id)
    session.add(favourite)
    await session.commit()
    await session.refresh(favourite)
    return favourite


async def remove_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Remove scope from user's favourites."""
    favourite = await get_scope_favourite(session, scope_id, user_id)
    if favourite:
        await session.delete(favourite)
        await session.commit()


# Scope Sections Service Functions


class ScopeSectionNotFoundError(Exception):
    """Raised when a requested scope section does not exist."""


async def list_scope_sections(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> List[ScopeSection]:
    """List all sections for a scope."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    stmt = (
        select(ScopeSection)
        .where(ScopeSection.scope_id == scope_id)
        .order_by(ScopeSection.order_index.asc(), ScopeSection.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_scope_section(
    session: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    content: Optional[str] = None,
    section_type: Optional[str] = None,
    order_index: Optional[int] = None,
) -> ScopeSection:
    """Create a new section for a scope."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # If order_index not provided, get the max and add 1
    if order_index is None:
        stmt = select(func.max(ScopeSection.order_index)).where(
            ScopeSection.scope_id == scope_id
        )
        result = await session.execute(stmt)
        max_order = result.scalar_one() or 0
        order_index = max_order + 1

    section = ScopeSection(
        scope_id=scope_id,
        title=title,
        content=content,
        section_type=section_type,
        order_index=order_index,
    )

    session.add(section)
    await session.commit()
    await session.refresh(section)
    return section


async def get_scope_section(
    session: AsyncSession, scope_id: uuid.UUID, section_id: uuid.UUID, user_id: uuid.UUID
) -> ScopeSection:
    """Get a scope section by ID."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    stmt = select(ScopeSection).where(
        ScopeSection.id == section_id,
        ScopeSection.scope_id == scope_id,
    )
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if section is None:
        raise ScopeSectionNotFoundError("Scope section not found")

    return section


async def update_scope_section(
    session: AsyncSession,
    scope_id: uuid.UUID,
    section_id: uuid.UUID,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    content: Optional[str] = None,
    order_index: Optional[int] = None,
) -> ScopeSection:
    """Update a scope section."""
    section = await get_scope_section(session, scope_id, section_id, user_id)

    if title is not None:
        section.title = title
    if content is not None:
        section.content = content
    if order_index is not None:
        section.order_index = order_index

    await session.commit()
    await session.refresh(section)
    return section


async def delete_scope_section(
    session: AsyncSession, scope_id: uuid.UUID, section_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a scope section."""
    section = await get_scope_section(session, scope_id, section_id, user_id)
    await session.delete(section)
    await session.commit()


async def reorder_scope_sections(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, section_ids: List[uuid.UUID]
) -> None:
    """Reorder scope sections."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # Verify all sections belong to this scope
    stmt = select(ScopeSection).where(
        ScopeSection.scope_id == scope_id,
        ScopeSection.id.in_(section_ids),
    )
    result = await session.execute(stmt)
    sections = {s.id: s for s in result.scalars().all()}

    if len(sections) != len(section_ids):
        raise ScopeSectionNotFoundError("One or more sections not found")

    # Update order_index for each section
    for order, section_id in enumerate(section_ids):
        sections[section_id].order_index = order

    await session.commit()


# Scope Export, Upload, and Extract Functions


async def export_scope(
    session: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    format: str,
    include_sections: bool = True,
    template: str = "standard",
) -> dict:
    """
    Export scope to PDF or DOCX format.
    Returns download URL and expiration time.
    Note: File storage infrastructure needs to be configured.
    """
    scope = await get_scope(session, scope_id, user_id, include_sections=include_sections)

    # TODO: Implement actual export generation
    # For now, return placeholder response
    # This should:
    # 1. Generate PDF/DOCX from scope data
    # 2. Upload to file storage (S3, local, etc.)
    # 3. Generate signed download URL
    # 4. Return URL with expiration

    from datetime import datetime, timedelta

    # Placeholder: Generate file path
    file_extension = "pdf" if format == "pdf" else "docx"
    # In production, this would be: f"https://storage.example.com/exports/{scope_id}.{file_extension}"
    download_url = f"/api/scopes/{scope_id}/exports/{scope_id}.{file_extension}"

    return {
        "download_url": download_url,
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
    }


async def upload_scope_document(
    session: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    filename: str,
    file_size: int,
    mime_type: str,
    file_url: str,
    extracted_text: Optional[str] = None,
) -> "Document":
    """
    Upload a document for a scope.
    Creates a Document record and links it to the scope.
    
    Args:
        extracted_text: Optional extracted text content from the document.
                        If provided, will be saved to document.extracted_text.
    """
    from app.models import Document
    from datetime import datetime

    scope = await get_scope(session, scope_id, user_id, include_sections=False)

    # Determine file type from extension
    file_type = None
    if filename.lower().endswith((".pdf",)):
        file_type = "pdf"
    elif filename.lower().endswith((".docx", ".doc")):
        file_type = "docx"
    elif filename.lower().endswith((".txt",)):
        file_type = "txt"
    elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
        file_type = "image"

    document = Document(
        scope_id=scope_id,
        workspace_id=scope.workspace_id,
        filename=filename,
        file_url=file_url,
        file_type=file_type,
        file_size=file_size,
        mime_type=mime_type,
        processing_status="pending",
        uploaded_by=user_id,
        extracted_text=extracted_text,  # Save extracted text if provided
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    return document


async def extract_scope_from_document(
    session: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    upload_id: uuid.UUID,
    extraction_type: str,
    template_id: Optional[uuid.UUID] = None,
    ai_model: Optional[str] = None,
    developer_level: str = "mid",
    developer_experience_years: int = 3,
) -> dict:
    """
    Trigger AI extraction from uploaded document.
    Integrates with ingestion service for processing.
    Returns extraction job ID and status.
    """
    from app.models import Document
    from app.core.config import get_settings
    from datetime import datetime
    import httpx

    settings = get_settings()
    scope = await get_scope(session, scope_id, user_id, include_sections=False)

    # Verify document belongs to scope
    doc_stmt = select(Document).where(
        Document.id == upload_id,
        Document.scope_id == scope_id,
    )
    doc_result = await session.execute(doc_stmt)
    document = doc_result.scalar_one_or_none()

    if document is None:
        raise ScopeNotFoundError("Document not found for this scope")

    # Update document status
    document.processing_status = "processing"
    await session.commit()

    # Call ingestion service API
    ingestion_url = getattr(settings, "ingestion_service_url", None) or "http://ingestion-service:8000"
    
    # Load template structure if template_id provided
    template_structure = None
    if template_id:
        from app.services import templates as template_service
        try:
            template = await template_service.get_template(session, template_id, user_id)
            if template.type == "scope":
                template_structure = template.sections
        except Exception as e:
            logger.warning(f"Failed to load template {template_id}: {e}")
    
    # Get document content from extracted_text field
    document_content = document.extracted_text or ""
    
    # If document has file_url but no extracted_text, try to read it
    if not document_content and document.file_url:
        # TODO: Read from actual storage (S3/local filesystem)
        # For now, log warning
        logger.warning(f"Document {upload_id} has file_url but no extracted_text stored. File reading not yet implemented.")
    
    try:
        # Increased timeout to 660s (11 minutes) to accommodate ingestion service's 600s timeout
        async with httpx.AsyncClient(timeout=660.0) as client:
            # First, create a document in ingestion service with the content
            # This allows ingestion service to process it
            doc_create_response = await client.post(
                f"{ingestion_url}/v1/documents",
                json={
                    "source_type": "client_brief",
                    "content": document_content,
                    "metadata": {
                        "project": scope.project.name if scope.project else None,
                        "client": scope.project.client.name if scope.project and scope.project.client else None,
                    }
                },
            )
            doc_create_response.raise_for_status()
            ingestion_doc_id = doc_create_response.json()["doc_id"]
            
            # Wait a moment for document to be processed
            import asyncio
            await asyncio.sleep(1)
            
            # Now call extract-for-scope with the ingestion document ID
            response = await client.post(
                f"{ingestion_url}/v1/documents/extract-for-scope",
                json={
                    "scopeId": str(scope_id),
                    "documentId": str(ingestion_doc_id),  # Use ingestion service doc ID
                    "templateId": str(template_id) if template_id else None,
                    "templateStructure": template_structure,  # Pass template structure directly
                    "workspaceId": str(scope.workspace_id),
                    "extractionType": extraction_type,
                    "aiModel": ai_model,
                    # developerLevel and developerExperienceYears removed - no longer used for hours estimation
                },
            )
            response.raise_for_status()
            result = response.json()
            
            # Log response for debugging
            logger.info(f"Extraction response for scope {scope_id}: status={result.get('status')}, sections_count={len(result.get('scopeSections') or result.get('scope_sections') or [])}")
            
            # Map generated scope to ScopeSection records
            # Check both camelCase and snake_case for compatibility
            scope_sections = result.get("scopeSections") or result.get("scope_sections")
            response_status = result.get("status", "").lower()
            
            if response_status == "completed" and scope_sections:
                # Successfully generated scope
                await _map_generated_scope_to_sections(
                    session,
                    scope_id,
                    scope_sections,
                    user_id,
                )
                
                # Update scope metadata
                scope.confidence_score = result.get("confidence_score", 0)
                scope.risk_level = result.get("risk_level", "low")
                scope.progress = min(50, scope.progress + 20)  # Increment progress
                
                # Update document status
                document.processing_status = "completed"
                await session.commit()
                
                return {
                    "extraction_id": result.get("extraction_id", uuid.uuid4()),
                    "status": "completed",
                    "estimated_time": result.get("estimated_time", 30),
                }
            elif response_status == "processing":
                # Still processing (e.g., timeout but will continue)
                logger.info(f"Scope extraction for {scope_id} is still processing. Estimated time: {result.get('estimated_time', 600)}s")
                document.processing_status = "processing"
                await session.commit()
                
                return {
                    "extraction_id": result.get("extraction_id", uuid.uuid4()),
                    "status": "processing",
                    "estimated_time": result.get("estimated_time", 600),
                    "message": "Scope generation is taking longer than expected. The extraction is continuing in the background. Please check back later or refresh the page.",
                }
            else:
                # Unknown status or no sections
                logger.warning(f"Scope extraction for {scope_id} returned status '{response_status}' with {len(scope_sections or [])} sections")
                document.processing_status = "processing"
                await session.commit()
                
                return {
                    "extraction_id": result.get("extraction_id", uuid.uuid4()),
                    "status": "processing",
                    "estimated_time": result.get("estimated_time", 600),
                }
    except httpx.TimeoutException as e:
        logger.warning(f"Extraction timeout for scope {scope_id}: {e}. Extraction will continue in background.")
        document.processing_status = "processing"
        await session.commit()
        # Return a response indicating background processing
        return {
            "extraction_id": uuid.uuid4(),
            "status": "processing",
            "estimated_time": 60,  # Longer estimate for background processing
            "message": "Extraction is taking longer than expected. The scope has been created and extraction will continue in the background.",
        }
    except httpx.RequestError as e:
        logger.error(f"Failed to call ingestion service: {e}")
        document.processing_status = "failed"
        await session.commit()
        raise ScopeAccessError(f"Failed to process document: {str(e)}")

    # Fallback: Return placeholder if service unavailable
    import uuid as uuid_lib
    extraction_id = uuid_lib.uuid4()
    estimated_time = 30
    if document.file_size:
        estimated_time = max(10, min(120, document.file_size // (1024 * 1024)))

    return {
        "extraction_id": extraction_id,
        "status": "processing",
        "estimated_time": estimated_time,
    }


async def _map_generated_scope_to_sections(
    session: AsyncSession,
    scope_id: uuid.UUID,
    scope_sections_data: list[dict],
    user_id: uuid.UUID,
) -> None:
    """
    Map generated scope sections to ScopeSection records.
    
    Args:
        scope_sections_data: List of section dictionaries from ingestion service
    """
    from app.models import ScopeSection
    import json
    
    # Create sections one by one to avoid SQLAlchemy bulk insert issues
    for idx, section_data in enumerate(scope_sections_data):
        section = ScopeSection(
            scope_id=scope_id,
            title=section_data.get("title", "Untitled Section"),
            content=json.dumps(section_data.get("content", {}), indent=2) if isinstance(section_data.get("content"), dict) else section_data.get("content", ""),
            section_type=section_data.get("section_type"),
            order_index=section_data.get("order_index", idx),
            ai_generated=True,
            confidence_score=section_data.get("confidence_score", 0),
        )
        session.add(section)
        await session.flush()  # Flush after each to get the ID

