from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.dashboard import (
    DashboardStatsResponse,
    PipelineData,
    RecentActivityResponse,
    UrgentItemsResponse,
)
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> DashboardStatsResponse:
    """Get dashboard statistics."""
    try:
        stats = await dashboard_service.get_dashboard_stats(
            session, current_user.id, workspace_id=workspace_id
        )
        return DashboardStatsResponse(**stats)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve dashboard statistics.",
        ) from exc


@router.get("/pipeline", response_model=PipelineData)
async def get_pipeline_data(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> PipelineData:
    """Get pipeline data grouped by status for scopes, projects, quotations, and proposals."""
    try:
        pipeline = await dashboard_service.get_pipeline_data(
            session, current_user.id, workspace_id=workspace_id
        )
        return PipelineData(**pipeline)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve pipeline data.",
        ) from exc


@router.get("/recent", response_model=RecentActivityResponse)
async def get_recent_activity(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    limit: int = Query(10, ge=1, le=50),
) -> RecentActivityResponse:
    """Get recent activity items (scopes, projects, PRDs)."""
    try:
        recent = await dashboard_service.get_recent_activity(
            session, current_user.id, workspace_id=workspace_id, limit=limit
        )
        return RecentActivityResponse(**recent)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve recent activity.",
        ) from exc


@router.get("/urgent", response_model=UrgentItemsResponse)
async def get_urgent_items(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    days: int = Query(7, ge=1, le=30),
) -> UrgentItemsResponse:
    """Get urgent items (PRDs with approaching due dates)."""
    try:
        urgent = await dashboard_service.get_urgent_items(
            session, current_user.id, workspace_id=workspace_id, days=days
        )
        return UrgentItemsResponse(**urgent)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve urgent items.",
        ) from exc


@router.get("/clients/active")
async def get_active_clients(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Get active clients list for dashboard."""
    try:
        clients = await dashboard_service.get_active_clients(
            session, current_user.id, workspace_id=workspace_id, limit=limit
        )
        return {"clients": clients}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve active clients.",
        ) from exc


@router.get("/projects/active")
async def get_active_projects(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Get active projects list for dashboard."""
    try:
        projects = await dashboard_service.get_active_projects(
            session, current_user.id, workspace_id=workspace_id, limit=limit
        )
        return {"projects": projects}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve active projects.",
        ) from exc


