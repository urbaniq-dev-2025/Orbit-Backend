from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.dashboard import DashboardStatsResponse
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


