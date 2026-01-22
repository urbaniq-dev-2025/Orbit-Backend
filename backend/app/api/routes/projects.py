from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api import deps
from app.models import Scope
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListResponse,
    ProjectProgressUpdate,
    ProjectStatus,
    ProjectStatusUpdate,
    ProjectSummary,
    ProjectTeamAssignRequest,
    ProjectUpdate,
)
from app.services import projects as project_service

router = APIRouter()


def _map_project_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, project_service.ProjectNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, project_service.ProjectAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    # Log the actual exception for debugging
    import traceback
    print(f"Project exception: {exc}")
    print(traceback.format_exc())
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to process project request: {str(exc)}"
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    status: Optional[str] = Query(None),
    page_size: Optional[int] = Query(None, alias="pageSize"),
) -> ProjectListResponse:
    """List projects with filters and statistics."""
    try:
        # ProjectStatus is a Literal type, so we can pass the string directly if valid
        project_status: Optional[ProjectStatus] = None
        if status and status in ["active", "archived", "completed", "on_hold"]:
            project_status = status  # type: ignore
        
        project_list = await project_service.list_projects(
            session,
            current_user.id,
            workspace_id=workspace_id,
            status=project_status,
        )

        # Build project summaries
        projects = [
            ProjectSummary.model_validate({
                "id": p.id,
                "workspaceId": p.workspace_id,
                "name": p.name,
                "description": p.description,
                "clientId": p.client_id,
                "clientName": p.client_name,
                "status": p.status,
                "createdBy": p.created_by,
                "createdAt": p.created_at,
                "updatedAt": p.updated_at,
            })
            for p in project_list
        ]
        
        # Calculate stats
        stats = {
            "total": len(project_list),
            "active": sum(1 for p in project_list if p.status == "active"),
            "archived": sum(1 for p in project_list if p.status == "archived"),
            "completed": sum(1 for p in project_list if p.status == "completed"),
            "on_hold": sum(1 for p in project_list if p.status == "on_hold"),
            "byStatus": {
                "active": sum(1 for p in project_list if p.status == "active"),
                "archived": sum(1 for p in project_list if p.status == "archived"),
                "completed": sum(1 for p in project_list if p.status == "completed"),
                "on_hold": sum(1 for p in project_list if p.status == "on_hold"),
            }
        }

        return ProjectListResponse(projects=projects, stats=stats)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Create a new project."""
    try:
        project = await project_service.create_project(session, current_user.id, payload)
        return await _build_project_detail(session, project)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Get project details with scopes."""
    try:
        project = await project_service.get_project(
            session, project_id, current_user.id, include_scopes=True
        )
        return await _build_project_detail(session, project)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.put("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Update a project."""
    try:
        project = await project_service.update_project(session, project_id, current_user.id, payload)
        return await _build_project_detail(session, project)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a project."""
    try:
        await project_service.delete_project(session, project_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.put("/{project_id}/status", response_model=ProjectDetail)
async def update_project_status(
    project_id: uuid.UUID,
    payload: ProjectStatusUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Update project status."""
    try:
        project = await project_service.update_project_status(
            session, project_id, current_user.id, payload.status
        )
        return await _build_project_detail(session, project)
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.put("/{project_id}/progress", response_model=ProjectDetail)
async def update_project_progress(
    project_id: uuid.UUID,
    payload: ProjectProgressUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Update project progress."""
    try:
        project = await project_service.update_project_progress(
            session, project_id, current_user.id, payload.progress
        )
        return await _build_project_detail(session, project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise _map_project_exception(exc) from exc


@router.post("/{project_id}/team", response_model=ProjectDetail)
async def assign_project_team(
    project_id: uuid.UUID,
    payload: ProjectTeamAssignRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProjectDetail:
    """Assign team members to a project."""
    try:
        project = await project_service.assign_project_team(
            session, project_id, current_user.id, payload.team
        )
        return await _build_project_detail(session, project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise _map_project_exception(exc) from exc


# Helper Functions


async def _build_project_detail(session, project) -> ProjectDetail:
    """Build ProjectDetail response with scope count."""
    # Get scope count
    scope_count_stmt = select(func.count()).select_from(Scope).where(Scope.project_id == project.id)
    scope_count_result = await session.execute(scope_count_stmt)
    scopes_count = scope_count_result.scalar_one() or 0

    # Use model_validate with camelCase field names for Pydantic v2 compatibility
    return ProjectDetail.model_validate({
        "id": project.id,
        "workspaceId": project.workspace_id,
        "name": project.name,
        "description": project.description,
        "clientId": project.client_id,
        "clientName": project.client_name,
        "status": project.status,
        "createdBy": project.created_by,
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
        "scopesCount": scopes_count,
        "engagementType": getattr(project, "engagement_type", None),
        "progress": getattr(project, "progress", 0) or 0,
        "budget": float(project.budget) if project.budget else None,
        "team": project.team if project.team else None,
    })


