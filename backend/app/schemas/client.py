from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ClientStatus = Literal["prospect", "active", "past"]


class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(..., min_length=1, max_length=100)
    contact_name: str = Field(..., alias="contactName", min_length=1, max_length=255)
    contact_email: str = Field(..., alias="contactEmail", max_length=255)
    contact_phone: Optional[str] = Field(None, alias="contactPhone", max_length=50)
    status: ClientStatus = "prospect"
    source: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    class Config:
        allow_population_by_field_name = True


class ClientCreate(ClientBase):
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")

    class Config:
        allow_population_by_field_name = True


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, min_length=1, max_length=100)
    contact_name: Optional[str] = Field(None, alias="contactName", min_length=1, max_length=255)
    contact_email: Optional[str] = Field(None, alias="contactEmail", max_length=255)
    contact_phone: Optional[str] = Field(None, alias="contactPhone", max_length=50)
    status: Optional[ClientStatus] = None
    source: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    class Config:
        allow_population_by_field_name = True


class ClientSummary(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: str
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    status: ClientStatus
    industry: str
    contact_name: str = Field(..., alias="contactName")
    contact_email: str = Field(..., alias="contactEmail")
    contact_phone: Optional[str] = Field(None, alias="contactPhone")
    health_score: int = Field(..., alias="healthScore", ge=0, le=100)
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    last_activity: Optional[datetime] = Field(None, alias="lastActivity")

    class Config:
        allow_population_by_field_name = True


class ClientListResponse(BaseModel):
    clients: List[ClientSummary]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True
