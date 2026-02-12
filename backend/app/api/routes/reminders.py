"""
API routes for reminder management.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.core.logging import get_logger
from app.models import User
from app.schemas.reminder import (
    ReminderCreate,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdate,
)
from app.services import reminders as reminder_service

router = APIRouter()
logger = get_logger(__name__)


def _map_reminder_exception(exc: Exception) -> HTTPException:
    """Map reminder service exceptions to HTTP exceptions."""
    if isinstance(exc, reminder_service.ReminderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, reminder_service.ReminderAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to process reminder request.",
    )


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> ReminderResponse:
    """Create a new reminder."""
    try:
        reminder = await reminder_service.create_reminder(
            session,
            current_user.id,
            payload.workspace_id,
            payload.title,
            payload.reminder_date,
            payload.reminder_type,
            reminder_time=payload.reminder_time,
            project_id=payload.project_id,
            scope_id=payload.scope_id,
        )

        # Load relationships for response
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models import Reminder

        stmt = (
            select(Reminder)
            .options(selectinload(Reminder.project), selectinload(Reminder.scope))
            .where(Reminder.id == reminder.id)
        )
        result = await session.execute(stmt)
        reminder = result.scalar_one()

        # Format time for response
        time_str = None
        if reminder.time:
            time_str = reminder.time.strftime("%H:%M")

        return ReminderResponse(
            id=reminder.id,
            title=reminder.title,
            date=reminder.date,
            time=time_str,
            type=reminder.type,
            workspace_id=reminder.workspace_id,
            project_id=reminder.project_id,
            project_name=reminder.project.name if reminder.project else None,
            scope_id=reminder.scope_id,
            scope_name=reminder.scope.title if reminder.scope else None,
            created_by=reminder.created_by,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )
    except Exception as exc:
        logger.error(f"Failed to create reminder: {exc}", exc_info=True)
        raise _map_reminder_exception(exc) from exc


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    reminder_type: Optional[str] = Query(None, alias="type", description="Filter by type: 'deadline' or 'event'"),
    project_id: Optional[uuid.UUID] = Query(None, alias="projectId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ReminderListResponse:
    """List reminders with filters and pagination."""
    try:
        reminders, total = await reminder_service.list_reminders(
            session,
            current_user.id,
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date,
            reminder_type=reminder_type,
            project_id=project_id,
            page=page,
            page_size=page_size,
        )

        reminder_responses = []
        for reminder in reminders:
            # Format time for response
            time_str = None
            if reminder.time:
                time_str = reminder.time.strftime("%H:%M")

            reminder_responses.append(
                ReminderResponse(
                    id=reminder.id,
                    title=reminder.title,
                    reminder_date=reminder.date,
                    reminder_time=time_str,
                    reminder_type=reminder.type,
                    workspace_id=reminder.workspace_id,
                    project_id=reminder.project_id,
                    project_name=reminder.project.name if reminder.project else None,
                    scope_id=reminder.scope_id,
                    scope_name=reminder.scope.title if reminder.scope else None,
                    created_by=reminder.created_by,
                    created_at=reminder.created_at,
                    updated_at=reminder.updated_at,
                )
            )

        return ReminderListResponse(
            reminders=reminder_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
    except Exception as exc:
        logger.error(f"Failed to list reminders: {exc}", exc_info=True)
        raise _map_reminder_exception(exc) from exc


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> ReminderResponse:
    """Get a reminder by ID."""
    try:
        reminder = await reminder_service.get_reminder(session, reminder_id, current_user.id)

        # Load relationships
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models import Reminder

        stmt = (
            select(Reminder)
            .options(selectinload(Reminder.project), selectinload(Reminder.scope))
            .where(Reminder.id == reminder.id)
        )
        result = await session.execute(stmt)
        reminder = result.scalar_one()

        # Format time for response
        time_str = None
        if reminder.time:
            time_str = reminder.time.strftime("%H:%M")

        return ReminderResponse(
            id=reminder.id,
            title=reminder.title,
            reminder_date=reminder.date,
            reminder_time=time_str,
            reminder_type=reminder.type,
            workspace_id=reminder.workspace_id,
            project_id=reminder.project_id,
            project_name=reminder.project.name if reminder.project else None,
            scope_id=reminder.scope_id,
            scope_name=reminder.scope.title if reminder.scope else None,
            created_by=reminder.created_by,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )
    except Exception as exc:
        logger.error(f"Failed to get reminder: {exc}", exc_info=True)
        raise _map_reminder_exception(exc) from exc


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> ReminderResponse:
    """Update a reminder."""
    try:
        reminder = await reminder_service.update_reminder(
            session,
            reminder_id,
            current_user.id,
            title=payload.title,
            reminder_date=payload.reminder_date,
            reminder_time=payload.reminder_time,
            reminder_type=payload.reminder_type,
            project_id=payload.project_id,
            scope_id=payload.scope_id,
        )

        # Load relationships
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models import Reminder

        stmt = (
            select(Reminder)
            .options(selectinload(Reminder.project), selectinload(Reminder.scope))
            .where(Reminder.id == reminder.id)
        )
        result = await session.execute(stmt)
        reminder = result.scalar_one()

        # Format time for response
        time_str = None
        if reminder.time:
            time_str = reminder.time.strftime("%H:%M")

        return ReminderResponse(
            id=reminder.id,
            title=reminder.title,
            reminder_date=reminder.date,
            reminder_time=time_str,
            reminder_type=reminder.type,
            workspace_id=reminder.workspace_id,
            project_id=reminder.project_id,
            project_name=reminder.project.name if reminder.project else None,
            scope_id=reminder.scope_id,
            scope_name=reminder.scope.title if reminder.scope else None,
            created_by=reminder.created_by,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )
    except Exception as exc:
        logger.error(f"Failed to update reminder: {exc}", exc_info=True)
        raise _map_reminder_exception(exc) from exc


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a reminder."""
    try:
        await reminder_service.delete_reminder(session, reminder_id, current_user.id)
    except Exception as exc:
        logger.error(f"Failed to delete reminder: {exc}", exc_info=True)
        raise _map_reminder_exception(exc) from exc
