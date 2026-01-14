from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import decode_token
from app.db.session import get_session
from app.models import User
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/signin")


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = TokenPayload(**decode_token(token))
    except (JWTError, ValueError) as exc:
        logger.warning(
            "Token validation failed",
            extra={"error": str(exc), "token_preview": token[:20] + "..." if len(token) > 20 else token},
        )
        raise credentials_error

    if payload.sub is None or payload.type != "access":
        logger.warning(
            "Invalid token payload",
            extra={"has_sub": payload.sub is not None, "token_type": payload.type},
        )
        raise credentials_error

    result = await session.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        logger.warning(
            "User not found or inactive",
            extra={"user_id": str(payload.sub), "user_exists": user is not None, "is_active": user.is_active if user else None},
        )
        raise credentials_error
    return user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Verify that the current user is an admin."""
    # Check if user has admin role in database
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return current_user

