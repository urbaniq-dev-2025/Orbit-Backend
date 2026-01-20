from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

from app.db.base import Base, GUID


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("ix_notification_preferences_user", "user_id"),
        Index("ix_notification_preferences_workspace", "workspace_id"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)  # NULL for global
    preference_type = Column(String(50), nullable=False)  # 'scope-updates', 'prd-updates', etc.
    enabled = Column(Boolean, default=True, nullable=False)
    channels = Column(PG_ARRAY(String), default=["email", "in-app"], nullable=False)  # ['email', 'in-app', 'push']
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
