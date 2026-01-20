from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class BillingHistory(Base):
    __tablename__ = "billing_history"
    __table_args__ = (
        Index("ix_billing_history_workspace", "workspace_id"),
        Index("ix_billing_history_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # 'paid', 'pending', 'failed', 'refunded'
    invoice_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="billing_history")
    # Note: subscription relationship removed to avoid circular dependency issues
    # Can be accessed via subscription_id foreign key if needed
