"""
Service for password management.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.core.logging import get_logger
from app.models import User

logger = get_logger(__name__)


async def change_password(
    session: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change user password.
    
    Raises:
        ValueError: If current password is incorrect or new password is invalid
    """
    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    
    # Validate new password strength (basic validation)
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters long")
    
    # Hash and update password
    user.hashed_password = hash_password(new_password)
    user.last_password_change = datetime.utcnow()
    
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Password changed for user {user.id}")
