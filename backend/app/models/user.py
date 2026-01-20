from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, GUID


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    company = Column(String(255), nullable=True)
    job_role = Column(String(100), nullable=True)  # User's job title/role
    role = Column(String(50), default="user", nullable=False)  # 'admin' or 'user'
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    two_factor_secret = Column(String(255), nullable=True)
    two_factor_method = Column(String(10), nullable=True)  # 'totp' or 'sms'
    two_factor_backup_codes = Column(JSON, nullable=True)  # Array of backup codes
    onboarding_step = Column(String(50), default="none", nullable=False)
    onboarding_state = Column(JSON, nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    oauth_accounts = relationship(
        "UserOAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )


