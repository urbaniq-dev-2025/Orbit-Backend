from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import uuid

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
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
) -> DashboardStatsResponse:
    """Get dashboard statistics."""
    try:
        stats = await dashboard_service.get_dashboard_stats(
            session, current_user.id, workspace_id=workspace_id
        )
        # Use model_validate for Pydantic v2 compatibility
        return DashboardStatsResponse.model_validate(stats)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve dashboard statistics.",
        ) from exc


@router.get("/pipeline", response_model=PipelineData)
async def get_pipeline_data(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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


@router.get("/calendar")
async def get_calendar_events(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
) -> dict:
    """Get calendar events (reminders) for dashboard."""
    try:
        from app.services import reminders as reminder_service
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        # If no date range provided, default to wider range (3 months back, 3 months forward)
        if not start_date:
            today = date.today()
            start_date = today - timedelta(days=90)  # 3 months back
        if not end_date:
            today = date.today()
            end_date = today + timedelta(days=90)  # 3 months forward
        
        logger.info(f"Fetching calendar events for workspace {workspace_id}, date range: {start_date} to {end_date}")
        
        reminder_list, total = await reminder_service.list_reminders(
            session,
            current_user.id,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=1000,  # Get all events for the date range
        )
        
        logger.info(f"Found {total} reminders, returning {len(reminder_list)} events")
        
        events = []
        for reminder in reminder_list:
            # Format time for response
            time_str = None
            if reminder.time:
                time_str = reminder.time.strftime("%H:%M")
            
            # Combine date and time for full datetime
            event_datetime = datetime.combine(reminder.date, reminder.time or time(0, 0))
            event_datetime = event_datetime.replace(tzinfo=timezone.utc)
            
            events.append({
                "id": str(reminder.id),
                "type": reminder.type,
                "title": reminder.title,
                "date": reminder.date.isoformat(),
                "time": time_str,
                "datetime": event_datetime.isoformat(),
                "scopeId": str(reminder.scope_id) if reminder.scope_id else None,
                "scopeName": reminder.scope.title if reminder.scope else None,
                "projectId": str(reminder.project_id) if reminder.project_id else None,
                "projectName": reminder.project.name if reminder.project else None,
            })
        
        return {
            "events": events,
            "total": total,
        }
    except Exception as exc:
        logger.error(f"Failed to get calendar events: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve calendar events.",
        ) from exc


@router.get("/pipeline/metrics")
async def get_pipeline_metrics(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
) -> dict:
    """Get pipeline metrics for dashboard."""
    # TODO: Implement pipeline metrics when needed
    return {
        "metrics": {},
    }

