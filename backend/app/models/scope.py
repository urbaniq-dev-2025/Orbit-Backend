from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Scope(Base):
    __tablename__ = "scopes"
    __table_args__ = (
        Index("ix_scopes_workspace", "workspace_id"),
        Index("ix_scopes_project", "project_id"),
        Index("ix_scopes_status", "status"),
        Index("ix_scopes_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), default="low", nullable=False)
    due_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
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

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="scopes")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="scopes")
    sections: Mapped[List["ScopeSection"]] = relationship(
        "ScopeSection", back_populates="scope", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="scope", cascade="all, delete-orphan"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="scope", cascade="all, delete-orphan"
    )
    favourites: Mapped[List["Favourite"]] = relationship(
        "Favourite", back_populates="scope", cascade="all, delete-orphan"
    )
    quotations: Mapped[List["Quotation"]] = relationship(
        "Quotation", back_populates="scope", cascade="all, delete-orphan"
    )
    proposals: Mapped[List["Proposal"]] = relationship(
        "Proposal", back_populates="scope", cascade="all, delete-orphan"
    )


class ScopeSection(Base):
    __tablename__ = "scope_sections"
    __table_args__ = (
        Index("ix_scope_sections_scope", "scope_id"),
        Index("ix_scope_sections_order", "scope_id", "order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    scope: Mapped["Scope"] = relationship("Scope", back_populates="sections")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="section", cascade="all, delete-orphan"
    )


