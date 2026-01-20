from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base, GUID


class WorkspaceSettings(Base):
    __tablename__ = "workspace_settings"
    __table_args__ = (
        Index("ix_workspace_settings_workspace", "workspace_id"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    workspace_mode = Column(String(10), default="team", nullable=False)  # 'solo' or 'team'
    require_scope_approval = Column(Boolean, default=True, nullable=False)
    require_prd_approval = Column(Boolean, default=True, nullable=False)
    auto_create_project = Column(Boolean, default=False, nullable=False)
    default_engagement_type = Column(String(20), default="fixed", nullable=False)  # 'fixed', 'hourly', 'retainer'
    ai_assist_enabled = Column(Boolean, default=True, nullable=False)
    ai_model_preference = Column(String(20), default="orbit-pro", nullable=False)  # 'orbit-lite', 'orbit-pro', 'orbit-ultra'
    show_client_health = Column(Boolean, default=True, nullable=False)
    default_currency = Column(String(3), default="USD", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    date_format = Column(String(20), default="MM/DD/YYYY", nullable=False)
    time_format = Column(String(5), default="12h", nullable=False)  # '12h' or '24h'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="settings")
