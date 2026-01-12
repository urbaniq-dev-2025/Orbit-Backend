from __future__ import annotations

import datetime as dt
import secrets
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    create_password_reset_token,
    hash_password,
    hash_reset_code,
    verify_password_reset_token,
)
from app.models import PasswordReset, User

RESET_CODE_LENGTH = 6
RESET_CODE_TTL_MINUTES = 15


def _generate_reset_code() -> str:
    return f"{secrets.randbelow(10**RESET_CODE_LENGTH):0{RESET_CODE_LENGTH}d}"


async def issue_password_reset(
    session: AsyncSession, user: User
) -> Tuple[PasswordReset, str]:
    """Create a new password reset entry and return the raw code."""
    now = dt.datetime.now(dt.timezone.utc)
    expires_at = now + dt.timedelta(minutes=RESET_CODE_TTL_MINUTES)
    code = _generate_reset_code()
    code_hash = hash_reset_code(code)

    await session.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used.is_(False))
        .values(used=True, used_at=now)
    )

    reset = PasswordReset(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
        used=False,
    )
    session.add(reset)
    await session.commit()
    await session.refresh(reset)
    return reset, code


async def verify_reset_code(
    session: AsyncSession, user: User, code: str
) -> PasswordReset:
    """Validate a reset code for a user and return the matching record."""
    hashed = hash_reset_code(code)
    now = dt.datetime.now(dt.timezone.utc)

    result = await session.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user.id,
            PasswordReset.used.is_(False),
            PasswordReset.expires_at > now,
            PasswordReset.code_hash == hashed,
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        raise ValueError("Invalid or expired reset code")
    return reset


def build_reset_token(reset: PasswordReset) -> str:
    return create_password_reset_token(
        user_id=str(reset.user_id), reset_id=str(reset.id)
    )


async def consume_reset_token(
    session: AsyncSession, token: str
) -> Tuple[User, PasswordReset]:
    try:
        payload = verify_password_reset_token(token)
    except ValueError as exc:
        raise ValueError("Invalid reset token") from exc

    user_id = payload.get("sub")
    reset_id = payload.get("reset_id")
    if not user_id or not reset_id:
        raise ValueError("Invalid reset token")

    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("Invalid reset token")

    reset_result = await session.execute(
        select(PasswordReset).where(
            PasswordReset.id == reset_id,
            PasswordReset.user_id == user.id,
            PasswordReset.used.is_(False),
        )
    )
    reset = reset_result.scalar_one_or_none()
    if reset is None:
        raise ValueError("Invalid reset token")

    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    if expires_at < dt.datetime.now(dt.timezone.utc):
        raise ValueError("Invalid reset token")

    return user, reset


async def finalize_password_reset(
    session: AsyncSession, user: User, reset: PasswordReset, new_password: str
) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    user.hashed_password = hash_password(new_password)
    reset.used = True
    reset.used_at = now
    await session.commit()
