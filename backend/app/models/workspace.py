from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_workspaces_slug"),
        Index("ix_workspaces_owner_id", "owner_id"),
        Index("ix_workspaces_slug", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    brand_color: Mapped[str] = mapped_column(String(7), default="#ff6b35", nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(7), default="#1a1a1a", nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_handling: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", backref="owned_workspaces")
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="workspace", cascade="all, delete-orphan"
    )
    scopes: Mapped[List["Scope"]] = relationship(
        "Scope", back_populates="workspace", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="workspace", cascade="all, delete-orphan"
    )
    templates: Mapped[List["Template"]] = relationship(
        "Template", back_populates="workspace", cascade="all, delete-orphan"
    )
    quotations: Mapped[List["Quotation"]] = relationship(
        "Quotation", back_populates="workspace", cascade="all, delete-orphan"
    )
    proposals: Mapped[List["Proposal"]] = relationship(
        "Proposal", back_populates="workspace", cascade="all, delete-orphan"
    )
    activities: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog", back_populates="workspace", cascade="all, delete-orphan"
    )
    usage_metrics: Mapped[List["UsageMetric"]] = relationship(
        "UsageMetric", back_populates="workspace", cascade="all, delete-orphan"
    )
    clients: Mapped[List["Client"]] = relationship(
        "Client", back_populates="workspace", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="workspace", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="workspace", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="workspace", cascade="all, delete-orphan"
    )
    credit_purchases: Mapped[List["CreditPurchase"]] = relationship(
        "CreditPurchase", back_populates="workspace", cascade="all, delete-orphan"
    )
    credit_balance: Mapped[Optional["WorkspaceCreditBalance"]] = relationship(
        "WorkspaceCreditBalance", back_populates="workspace", uselist=False, cascade="all, delete-orphan"
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_user"),
        Index("ix_workspace_members_workspace", "workspace_id"),
        Index("ix_workspace_members_user", "user_id"),
        Index(
            "ix_workspace_members_invited_email_unique",
            "workspace_id",
            "invited_email",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    invited_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invited_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped[Optional["User"]] = relationship("User", backref="workspace_memberships")


