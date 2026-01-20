"""
Service for managing workspace settings.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkspaceSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_workspace_settings(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> WorkspaceSettings:
    """
    Get workspace settings, creating defaults if they don't exist.
    """
    stmt = select(WorkspaceSettings).where(WorkspaceSettings.workspace_id == workspace_id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings
        settings = WorkspaceSettings(
            workspace_id=workspace_id,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    
    return settings


async def update_workspace_settings(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    **kwargs,
) -> WorkspaceSettings:
    """
    Update workspace settings.
    
    Args:
        **kwargs: Settings fields to update
    """
    settings = await get_workspace_settings(session, workspace_id)
    
    # Update fields
    for key, value in kwargs.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)
    
    await session.commit()
    await session.refresh(settings)
    
    return settings
