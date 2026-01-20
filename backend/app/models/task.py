from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_workspace", "workspace_id"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_completed", "completed"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_reminder_time", "reminder_time", postgresql_where=func.text("reminder_enabled = TRUE")),
        Index("ix_tasks_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    due_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20), default="none", nullable=False
    )  # 'none', 'low', 'medium', 'high'
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_time: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="tasks")
    project: Mapped[Optional["Project"]] = relationship("Project", backref="tasks")
    scope: Mapped[Optional["Scope"]] = relationship("Scope", backref="tasks")
    creator: Mapped["User"] = relationship("User", backref="created_tasks")
