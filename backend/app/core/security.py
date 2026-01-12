from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any, Dict, Optional
PASSWORD_RESET_TOKEN_EXPIRES_MINUTES = 15

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

# Using argon2 for stronger default and to avoid bcrypt backend quirks in tests.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _build_token(data: Dict[str, Any], expires_delta: dt.timedelta) -> str:
    to_encode = data.copy()
    expire = dt.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    payload = {"sub": subject, "type": "access"}
    if extra:
        payload.update(extra)
    expires = dt.timedelta(minutes=settings.access_token_expires_minutes)
    return _build_token(payload, expires)


def create_refresh_token(subject: str, extra: Optional[Dict[str, Any]] = None) -> str:
    payload = {"sub": subject, "type": "refresh"}
    if extra:
        payload.update(extra)
    expires = dt.timedelta(minutes=settings.refresh_token_expires_minutes)
    return _build_token(payload, expires)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # pragma: no cover - thin wrapper
        raise exc


def create_state_token(data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> str:
    payload = {"type": "state"}
    payload.update(data)
    expires = dt.timedelta(seconds=ttl_seconds or settings.google_state_ttl_seconds)
    return _build_token(payload, expires)


def verify_state_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid state token") from exc
    if payload.get("type") != "state":
        raise ValueError("Invalid state token")
    return payload


def hash_reset_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_password_reset_token(
    *, user_id: str, reset_id: str, expires_minutes: Optional[int] = None
) -> str:
    payload = {"sub": user_id, "type": "password_reset", "reset_id": reset_id}
    expiry = dt.timedelta(minutes=expires_minutes or PASSWORD_RESET_TOKEN_EXPIRES_MINUTES)
    return _build_token(payload, expiry)


def verify_password_reset_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid password reset token") from exc
    if payload.get("type") != "password_reset":
        raise ValueError("Invalid password reset token")
    return payload


