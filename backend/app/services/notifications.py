"""
Service for managing notification preferences.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationPreference
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default notification preferences
DEFAULT_PREFERENCES = [
    {
        "id": "scope-updates",
        "label": "Scope Updates",
        "description": "Get notified when scopes are created or modified",
        "enabled": True,
        "channels": ["email", "in-app"],
    },
    {
        "id": "prd-updates",
        "label": "PRD Updates",
        "description": "Notifications when PRDs need attention or are updated",
        "enabled": True,
        "channels": ["email", "in-app"],
    },
    {
        "id": "quotation-alerts",
        "label": "Quotation Alerts",
        "description": "Receive alerts when quotations need attention",
        "enabled": True,
        "channels": ["email"],
    },
    {
        "id": "team-activity",
        "label": "Team Activity",
        "description": "Notifications about team member actions",
        "enabled": False,
        "channels": ["in-app"],
    },
    {
        "id": "deadline-reminders",
        "label": "Deadline Reminders",
        "description": "Reminders before project deadlines",
        "enabled": True,
        "channels": ["email", "in-app", "push"],
    },
    {
        "id": "review-requests",
        "label": "Review Requests",
        "description": "Get notified when someone requests your review",
        "enabled": True,
        "channels": ["email", "in-app"],
    },
    {
        "id": "weekly-digest",
        "label": "Weekly Digest",
        "description": "Summary of your weekly activity",
        "enabled": True,
        "channels": ["email"],
    },
    {
        "id": "marketing",
        "label": "Product Updates",
        "description": "Tips, updates, and new feature announcements",
        "enabled": False,
        "channels": ["email"],
    },
]


async def get_notification_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """
    Get notification preferences for a user.
    
    Returns list of preference dictionaries with current settings.
    """
    # Get existing preferences from database
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    if workspace_id:
        stmt = stmt.where(NotificationPreference.workspace_id == workspace_id)
    else:
        stmt = stmt.where(NotificationPreference.workspace_id.is_(None))
    
    result = await session.execute(stmt)
    existing_prefs = {pref.preference_type: pref for pref in result.scalars().all()}
    
    # Build response with defaults or existing values
    preferences = []
    for default_pref in DEFAULT_PREFERENCES:
        pref_type = default_pref["id"]
        existing_pref = existing_prefs.get(pref_type)
        
        preferences.append({
            "id": pref_type,
            "label": default_pref["label"],
            "description": default_pref["description"],
            "enabled": existing_pref.enabled if existing_pref else default_pref["enabled"],
            "channels": list(existing_pref.channels) if existing_pref else default_pref["channels"],
        })
    
    return preferences


async def update_notification_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID],
    preferences: List[dict],
) -> List[dict]:
    """
    Update notification preferences for a user.
    
    Args:
        preferences: List of dicts with 'id', 'enabled', 'channels'
    """
    # Get existing preferences
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    if workspace_id:
        stmt = stmt.where(NotificationPreference.workspace_id == workspace_id)
    else:
        stmt = stmt.where(NotificationPreference.workspace_id.is_(None))
    
    result = await session.execute(stmt)
    existing_prefs = {pref.preference_type: pref for pref in result.scalars().all()}
    
    # Update or create preferences
    for pref_data in preferences:
        pref_type = pref_data["id"]
        existing_pref = existing_prefs.get(pref_type)
        
        if existing_pref:
            # Update existing
            existing_pref.enabled = pref_data["enabled"]
            existing_pref.channels = pref_data["channels"]
            session.add(existing_pref)
        else:
            # Create new
            new_pref = NotificationPreference(
                user_id=user_id,
                workspace_id=workspace_id,
                preference_type=pref_type,
                enabled=pref_data["enabled"],
                channels=pref_data["channels"],
            )
            session.add(new_pref)
    
    await session.commit()
    
    # Return updated preferences
    return await get_notification_preferences(session, user_id, workspace_id)
