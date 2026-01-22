from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_role: Optional[str] = None  # User's job title/role
    role: str = "user"  # 'admin' or 'user'


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_role: Optional[str] = None


class UserPublic(UserBase):
    id: uuid.UUID
    role: str
    is_active: bool
    is_verified: bool
    email_verified: bool = False
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_role: Optional[str] = None

    class Config:
        from_attributes = True


