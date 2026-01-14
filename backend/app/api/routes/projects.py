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
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to process project request."
    )


@router.get("", response_model=List[ProjectSummary])
async def list_projects(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    status: Optional[str] = Query(None),
) -> List[ProjectSummary]:
    """List projects with filters."""
    try:
        project_status = (
            status if status in ["active", "archived", "completed", "on_hold"] else None
        )
        project_list = await project_service.list_projects(
            session,
            current_user.id,
            workspace_id=workspace_id,
            status=project_status,
        )

        return [
            ProjectSummary(
                id=p.id,
                workspace_id=p.workspace_id,
                name=p.name,
                description=p.description,
                client_name=p.client_name,
                status=p.status,
                created_by=p.created_by,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in project_list
        ]
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

    return ProjectDetail(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        description=project.description,
        client_name=project.client_name,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        scopes_count=scopes_count,
        engagement_type=getattr(project, "engagement_type", None),
        progress=getattr(project, "progress", 0),
        budget=float(project.budget) if project.budget else None,
        team=project.team if project.team else None,
    )


