from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    __table_args__ = (
        Index("ix_conversation_history_workspace", "workspace_id"),
        Index("ix_conversation_history_conversation_id", "conversation_id"),
        Index("ix_conversation_history_created_at", "created_at"),
        Index("ix_conversation_history_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    intent_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    intent_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    actions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", backref="conversation_history")
    user: Mapped["User"] = relationship("User", backref="conversation_history")
