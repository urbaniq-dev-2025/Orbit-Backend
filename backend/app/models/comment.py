from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_scope", "scope_id"),
        Index("ix_comments_section", "section_id"),
        Index("ix_comments_user", "user_id"),
        Index("ix_comments_parent", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("scope_sections.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
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

    scope: Mapped["Scope"] = relationship("Scope", back_populates="comments")
    section: Mapped[Optional["ScopeSection"]] = relationship("ScopeSection", back_populates="comments")
    user: Mapped["User"] = relationship("User", backref="comments")
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment", remote_side="Comment.id", back_populates="replies"
    )
    replies: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="parent", cascade="all, delete-orphan"
    )




