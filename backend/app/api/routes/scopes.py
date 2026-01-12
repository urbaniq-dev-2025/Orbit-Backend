from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api import deps
from app.models import Comment, Document, Favourite, Scope
from app.schemas.scope import (
    ScopeCreate,
    ScopeDetail,
    ScopeListResponse,
    ScopeReorderRequest,
    ScopeSectionCreate,
    ScopeSectionPublic,
    ScopeSectionUpdate,
    ScopeStatusUpdate,
    ScopeSummary,
    ScopeUpdate,
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
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
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
            status=scope_status,
            search=search,
            page=page,
            page_size=page_size,
        )

        # Get favourite status for each scope
        scope_ids = [s.id for s in scope_list]
        favourites = {}
        if scope_ids:
            fav_stmt = select(Favourite.scope_id).where(
                Favourite.scope_id.in_(scope_ids),
                Favourite.user_id == current_user.id,
            )
            fav_result = await session.execute(fav_stmt)
            favourites = {row[0] for row in fav_result.all()}

        summaries = []
        for scope in scope_list:
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
    payload: ScopeCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ScopeDetail:
    """Create a new scope."""
    try:
        scope = await scope_service.create_scope(session, current_user.id, payload)
        return await _build_scope_detail(session, scope, current_user.id)
    except Exception as exc:
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


