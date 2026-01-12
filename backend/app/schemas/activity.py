from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActivityPublic(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = Field(None, alias="workspaceId")
    user_id: Optional[uuid.UUID] = Field(None, alias="userId")
    action: str
    entity_type: Optional[str] = Field(None, alias="entityType")
    entity_id: Optional[uuid.UUID] = Field(None, alias="entityId")
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(..., alias="createdAt")
    user_name: Optional[str] = Field(None, alias="userName")
    user_email: Optional[str] = Field(None, alias="userEmail")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ActivityListResponse(BaseModel):
    activities: list[ActivityPublic]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


