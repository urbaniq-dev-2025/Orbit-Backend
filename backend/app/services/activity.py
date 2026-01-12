from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActivityLog, User, WorkspaceMember


async def log_activity(
    session: AsyncSession,
    *,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    workspace_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> ActivityLog:
    """Log an activity entry."""
    activity = ActivityLog(
        action=action,
        user_id=user_id,
        workspace_id=workspace_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    session.add(activity)
    await session.commit()
    await session.refresh(activity)
    return activity


async def list_activities(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[ActivityLog], int]:
    """List activities for a user with optional workspace filter."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    # Build query
    stmt: Select[ActivityLog] = select(ActivityLog).where(
        ActivityLog.workspace_id.in_(accessible_workspace_ids)
    )

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return [], 0
        stmt = stmt.where(ActivityLog.workspace_id == workspace_id)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    stmt = (
        stmt.options(selectinload(ActivityLog.user))
        .order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    activities = list(result.scalars().all())

    return activities, total


async def list_workspace_activities(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[ActivityLog], int]:
    """List activities for a specific workspace."""
    # Verify workspace access
    workspace_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    if workspace_result.scalar_one_or_none() is None:
        return [], 0

    # Build query
    stmt: Select[ActivityLog] = select(ActivityLog).where(
        ActivityLog.workspace_id == workspace_id
    )

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    stmt = (
        stmt.options(selectinload(ActivityLog.user))
        .order_by(ActivityLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    activities = list(result.scalars().all())

    return activities, total


