from __future__ import annotations

import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID


class UsageMetric(Base):
    __tablename__ = "usage_metrics"
    __table_args__ = (
        UniqueConstraint("workspace_id", "metric_type", "period_start", name="uq_usage_metric_period"),
        Index("ix_usage_metrics_workspace", "workspace_id"),
        Index("ix_usage_metrics_period", "period_start", "period_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="usage_metrics")




