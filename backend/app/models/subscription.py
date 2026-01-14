from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_workspace", "workspace_id"),
        Index("ix_subscriptions_stripe_customer", "stripe_customer_id"),
        Index("ix_subscriptions_stripe_subscription", "stripe_subscription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)  # free, starter, pro, team, enterprise
    billing_cycle: Mapped[str] = mapped_column(String(50), default="monthly", nullable=False)  # monthly, annual
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, cancelled, past_due, trialing
    current_period_start: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="subscriptions")
