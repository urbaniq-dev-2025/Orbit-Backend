"""
Service functions for reminder management.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Reminder, Scope, WorkspaceMember


class ReminderNotFoundError(Exception):
    """Raised when a reminder is not found."""

    pass


class ReminderAccessError(Exception):
    """Raised when user doesn't have access to a reminder."""

    pass


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


async def create_reminder(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    title: str,
    reminder_date: date,
    reminder_type: str,
    reminder_time: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    scope_id: Optional[uuid.UUID] = None,
) -> Reminder:
    """Create a new reminder."""
    # Validate type
    if reminder_type not in ["deadline", "event"]:
        raise ValueError("Type must be 'deadline' or 'event'")

    # Check workspace access
    if not await _check_workspace_access(session, workspace_id, user_id):
        raise ReminderAccessError("Access denied to workspace")

    # Validate project if provided
    if project_id:
        project_stmt = select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        project_result = await session.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found or not in workspace")

    # Parse time string to time object
    time_obj = None
    if reminder_time:
        try:
            # Parse HH:MM format
            hour, minute = map(int, reminder_time.split(":"))
            time_obj = time(hour, minute)
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format (e.g., '09:00')")

    # Create reminder
    reminder = Reminder(
        workspace_id=workspace_id,
        title=title,
        date=reminder_date,
        time=time_obj,
        type=reminder_type,
        project_id=project_id,
        scope_id=scope_id,
        created_by=user_id,
    )
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def get_reminder(
    session: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID
) -> Reminder:
    """Get a reminder by ID with access check."""
    stmt = select(Reminder).where(Reminder.id == reminder_id)
    result = await session.execute(stmt)
    reminder = result.scalar_one_or_none()

    if reminder is None:
        raise ReminderNotFoundError("Reminder not found")

    # Check workspace access
    if not await _check_workspace_access(session, reminder.workspace_id, user_id):
        raise ReminderAccessError("Access denied")

    return reminder


async def list_reminders(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    reminder_type: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Reminder], int]:
    """List reminders with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return [], 0

    # Build query
    stmt = select(Reminder).where(Reminder.workspace_id.in_(accessible_workspace_ids))

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return [], 0
        stmt = stmt.where(Reminder.workspace_id == workspace_id)

    if start_date:
        stmt = stmt.where(Reminder.date >= start_date)

    if end_date:
        stmt = stmt.where(Reminder.date <= end_date)

    if reminder_type and reminder_type in ["deadline", "event"]:
        stmt = stmt.where(Reminder.type == reminder_type)

    if project_id:
        stmt = stmt.where(Reminder.project_id == project_id)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Reminder.date.asc(), Reminder.time.asc()).offset(offset).limit(page_size)

    # Load relationships
    from sqlalchemy.orm import selectinload

    stmt = stmt.options(
        selectinload(Reminder.project),
        selectinload(Reminder.scope),
    )

    result = await session.execute(stmt)
    reminders = list(result.scalars().all())

    return reminders, total


async def update_reminder(
    session: AsyncSession,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    title: Optional[str] = None,
    reminder_date: Optional[date] = None,
    reminder_time: Optional[str] = None,
    reminder_type: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    scope_id: Optional[uuid.UUID] = None,
) -> Reminder:
    """Update a reminder."""
    reminder = await get_reminder(session, reminder_id, user_id)

    if title is not None:
        reminder.title = title

    if reminder_date is not None:
        reminder.date = reminder_date

    if reminder_time is not None:
        if reminder_time == "":
            reminder.time = None
        else:
            try:
                hour, minute = map(int, reminder_time.split(":"))
                reminder.time = time(hour, minute)
            except (ValueError, AttributeError):
                raise ValueError("Time must be in HH:MM format (e.g., '09:00')")

    if reminder_type is not None:
        if reminder_type not in ["deadline", "event"]:
            raise ValueError("Type must be 'deadline' or 'event'")
        reminder.type = reminder_type

    if project_id is not None:
        if project_id:
            # Validate project
            project_stmt = select(Project).where(
                Project.id == project_id,
                Project.workspace_id == reminder.workspace_id,
            )
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError("Project not found or not in workspace")
        reminder.project_id = project_id

    if scope_id is not None:
        reminder.scope_id = scope_id

    await session.commit()
    await session.refresh(reminder)
    return reminder


async def delete_reminder(
    session: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a reminder."""
    reminder = await get_reminder(session, reminder_id, user_id)
    await session.delete(reminder)
    await session.commit()
