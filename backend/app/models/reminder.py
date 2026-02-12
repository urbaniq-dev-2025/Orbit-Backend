from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_workspace", "workspace_id"),
        Index("ix_reminders_date", "date"),
        Index("ix_reminders_type", "type"),
        Index("ix_reminders_project", "project_id"),
        Index("ix_reminders_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'deadline' or 'event'
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="reminders")
    project: Mapped[Optional["Project"]] = relationship("Project", backref="reminders")
    scope: Mapped[Optional["Scope"]] = relationship("Scope", backref="reminders")
    creator: Mapped["User"] = relationship("User", backref="created_reminders")
