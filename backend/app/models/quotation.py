from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        Index("ix_quotations_scope", "scope_id"),
        Index("ix_quotations_workspace", "workspace_id"),
        Index("ix_quotations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    total_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    design_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frontend_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    backend_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qa_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    scope: Mapped["Scope"] = relationship("Scope", back_populates="quotations")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="quotations")
    creator: Mapped[Optional["User"]] = relationship("User", backref="quotations_created")
    items: Mapped[List["QuotationItem"]] = relationship(
        "QuotationItem", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    __table_args__ = (
        Index("ix_quotation_items_quotation", "quotation_id"),
        Index("ix_quotation_items_order", "quotation_id", "order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False
    )
    page: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    module: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    feature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interactions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assumptions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    design: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frontend: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    backend: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qa: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="items")




