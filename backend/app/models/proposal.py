from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        Index("ix_proposals_scope", "scope_id"),
        Index("ix_proposals_workspace", "workspace_id"),
        Index("ix_proposals_status", "status"),
        Index("ix_proposals_shared_link", "shared_link", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    template: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cover_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shared_link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
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

    scope: Mapped["Scope"] = relationship("Scope", back_populates="proposals")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="proposals")
    creator: Mapped[Optional["User"]] = relationship("User", backref="proposals_created")
    slides: Mapped[List["ProposalSlide"]] = relationship(
        "ProposalSlide", back_populates="proposal", cascade="all, delete-orphan"
    )
    views: Mapped[List["ProposalView"]] = relationship(
        "ProposalView", back_populates="proposal", cascade="all, delete-orphan"
    )


class ProposalSlide(Base):
    __tablename__ = "proposal_slides"
    __table_args__ = (
        Index("ix_proposal_slides_proposal", "proposal_id"),
        Index("ix_proposal_slides_order", "proposal_id", "order_index"),
        UniqueConstraint(
            "proposal_id", "slide_number", name="uq_proposal_slides_proposal_slide_number"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False
    )
    slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slide_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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

    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="slides")


class ProposalView(Base):
    __tablename__ = "proposal_views"
    __table_args__ = (
        Index("ix_proposal_views_proposal", "proposal_id"),
        Index("ix_proposal_views_email", "viewer_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False
    )
    viewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    viewer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    viewed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="views")




