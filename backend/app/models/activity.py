from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = (
        Index("ix_activity_workspace", "workspace_id"),
        Index("ix_activity_user", "user_id"),
        Index("ix_activity_entity", "entity_type", "entity_id"),
        Index("ix_activity_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped[Optional["Workspace"]] = relationship("Workspace", back_populates="activities")
    user: Mapped[Optional["User"]] = relationship("User", backref="activity_entries")


