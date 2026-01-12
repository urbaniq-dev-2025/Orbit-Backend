from __future__ import annotations

import uuid
from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = (
        UniqueConstraint("user_id", "scope_id", name="uq_favourites_user_scope"),
        Index("ix_favourites_user", "user_id"),
        Index("ix_favourites_scope", "scope_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("scopes.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", backref="favourites")
    scope: Mapped["Scope"] = relationship("Scope", back_populates="favourites")

