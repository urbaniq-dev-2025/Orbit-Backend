from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api import deps
from app.schemas.template import (
    CategoryResponse,
    TemplateCreate,
    TemplateDetail,
    TemplateListResponse,
    TemplateSummary,
    TemplateUpdate,
)
from app.services import templates as template_service

router = APIRouter()


def _map_template_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, template_service.TemplateNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, template_service.TemplateAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to process template request."
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    type: Optional[str] = Query(None, description="Filter by template type: scope, prd, project"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> TemplateListResponse:
    """List templates with filters and pagination."""
    try:
        template_list, total = await template_service.list_templates(
            session,
            current_user.id,
            workspace_id=workspace_id,
            type=type if type in ["scope", "prd", "project"] else None,
            category=category,
            search=search,
            page=page,
            page_size=page_size,
        )

        summaries = [
            TemplateSummary(
                id=t.id,
                name=t.name,
                description=t.description,
                type=t.type,
                category=t.category,
                usage_count=t.usage_count,
                is_system=t.is_system,
                created_at=t.created_at,
            )
            for t in template_list
        ]

        return TemplateListResponse(templates=summaries, total=total)
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> TemplateDetail:
    """Get template details."""
    try:
        template = await template_service.get_template(session, template_id, current_user.id)
        return TemplateDetail(
            id=template.id,
            name=template.name,
            description=template.description,
            type=template.type,
            category=template.category,
            content=template.sections,  # Map sections to content
            variables=template.variables,
            usage_count=template.usage_count,
            is_system=template.is_system,
            workspace_id=template.workspace_id,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.post("", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> TemplateDetail:
    """Create a custom template."""
    try:
        template = await template_service.create_template(
            session, current_user.id, payload, workspace_id=workspace_id
        )
        return TemplateDetail(
            id=template.id,
            name=template.name,
            description=template.description,
            type=template.type,
            category=template.category,
            content=template.sections,
            variables=template.variables,
            usage_count=template.usage_count,
            is_system=template.is_system,
            workspace_id=template.workspace_id,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.put("/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> TemplateDetail:
    """Update a template."""
    try:
        template = await template_service.update_template(session, template_id, current_user.id, payload)
        return TemplateDetail(
            id=template.id,
            name=template.name,
            description=template.description,
            type=template.type,
            category=template.category,
            content=template.sections,
            variables=template.variables,
            usage_count=template.usage_count,
            is_system=template.is_system,
            workspace_id=template.workspace_id,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a template."""
    try:
        await template_service.delete_template(session, template_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.post("/{template_id}/clone", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
async def clone_template(
    template_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> TemplateDetail:
    """Clone a template."""
    try:
        template = await template_service.clone_template(
            session, template_id, current_user.id, workspace_id=workspace_id
        )
        return TemplateDetail(
            id=template.id,
            name=template.name,
            description=template.description,
            type=template.type,
            category=template.category,
            content=template.sections,
            variables=template.variables,
            usage_count=template.usage_count,
            is_system=template.is_system,
            workspace_id=template.workspace_id,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.get("/popular", response_model=List[TemplateSummary])
async def get_popular_templates(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    type: Optional[str] = Query(None, description="Filter by template type: scope, prd, project"),
    limit: int = Query(10, ge=1, le=50),
) -> List[TemplateSummary]:
    """Get popular templates (by usage count)."""
    try:
        templates = await template_service.get_popular_templates(
            session, current_user.id, limit=limit, type=type if type in ["scope", "prd", "project"] else None
        )
        return [
            TemplateSummary(
                id=t.id,
                name=t.name,
                description=t.description,
                type=t.type,
                category=t.category,
                usage_count=t.usage_count,
                is_system=t.is_system,
                created_at=t.created_at,
            )
            for t in templates
        ]
    except Exception as exc:
        raise _map_template_exception(exc) from exc


@router.get("/categories", response_model=CategoryResponse)
async def get_template_categories(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> CategoryResponse:
    """Get all unique template categories."""
    try:
        categories = await template_service.get_template_categories(session, current_user.id)
        return CategoryResponse(categories=categories)
    except Exception as exc:
        raise _map_template_exception(exc) from exc
