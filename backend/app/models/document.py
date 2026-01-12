from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_scope", "scope_id"),
        Index("ix_documents_workspace", "workspace_id"),
        Index("ix_documents_status", "processing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    scope: Mapped[Optional["Scope"]] = relationship("Scope", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship("User", backref="uploaded_documents")




