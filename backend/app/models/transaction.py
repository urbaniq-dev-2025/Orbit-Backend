from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Transaction(Base):
    """Transaction model for cash flow tracking."""
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_workspace", "workspace_id"),
        Index("ix_transactions_date", "transaction_date"),
        Index("ix_transactions_type", "type"),
        Index("ix_transactions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "income", "expense", "transfer"
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # "pending", "completed", "failed", "cancelled"
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # "stripe", "bank_transfer", "cash", etc.
    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # External reference (e.g., Stripe charge ID)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)  # JSON metadata
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

    workspace: Mapped[Optional["Workspace"]] = relationship("Workspace", back_populates="transactions")
    creator: Mapped[Optional["User"]] = relationship("User", backref="transactions")
