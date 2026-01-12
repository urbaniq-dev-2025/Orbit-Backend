from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class UserPublic(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool

    class Config:
        orm_mode = True


