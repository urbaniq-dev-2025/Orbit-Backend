from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ProjectStatus = Literal["active", "archived", "completed", "on_hold"]


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)
    status: ProjectStatus = "active"

    class Config:
        allow_population_by_field_name = True


class ProjectCreate(ProjectBase):
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")

    class Config:
        allow_population_by_field_name = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)
    status: Optional[ProjectStatus] = None

    class Config:
        allow_population_by_field_name = True


class ProjectSummary(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: str
    description: Optional[str] = None
    client_name: Optional[str] = Field(None, alias="clientName")
    status: ProjectStatus
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ProjectDetail(ProjectSummary):
    scopes_count: int = Field(0, alias="scopesCount")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


