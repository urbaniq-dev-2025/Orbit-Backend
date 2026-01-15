"""
Credit system models for managing credit packages, purchases, and balances.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class CreditPackage(Base):
    """Credit packages available for purchase."""
    __tablename__ = "credit_packages"
    __table_args__ = (
        Index("ix_credit_packages_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # e.g., "Starter Pack", "Growth Pack"
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # Number of credits in package
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # Price in dollars
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreditPurchase(Base):
    """Credit purchase transactions."""
    __tablename__ = "credit_purchases"
    __table_args__ = (
        Index("ix_credit_purchases_workspace", "workspace_id"),
        Index("ix_credit_purchases_package", "package_id"),
        Index("ix_credit_purchases_status", "status"),
        Index("ix_credit_purchases_date", "purchase_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("credit_packages.id", ondelete="RESTRICT"), nullable=False
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # Credits purchased
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # Purchase amount in dollars
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "Card •••• 4242", "PayPal"
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Payment processor transaction ID
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)  # completed, pending, failed, refunded
    purchase_date: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="credit_purchases")
    package: Mapped["CreditPackage"] = relationship("CreditPackage")


class WorkspaceCreditBalance(Base):
    """Current credit balance for each workspace."""
    __tablename__ = "workspace_credit_balances"
    __table_args__ = (
        Index("ix_workspace_credit_balances_workspace", "workspace_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Current credit balance
    total_purchased: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Total credits ever purchased
    total_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Total credits consumed
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="credit_balance")
