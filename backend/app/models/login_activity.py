from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, func

from app.db.base import Base, GUID


class LoginActivity(Base):
    __tablename__ = "login_activity"
    __table_args__ = (
        Index("ix_login_activity_user", "user_id"),
        Index("ix_login_activity_timestamp", "timestamp"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(255), nullable=True)
