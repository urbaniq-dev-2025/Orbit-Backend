from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ClientStatus = Literal["prospect", "active", "past"]
CompanySize = Literal["SMB", "Mid-Market", "Enterprise"]


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
    company_size: Optional[CompanySize] = Field(None, alias="companySize")

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
    health_score: Optional[int] = Field(None, alias="healthScore", ge=0, le=100)
    source: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    company_size: Optional[CompanySize] = Field(None, alias="companySize")

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
    source: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None  # Computed from city, state, country
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    company_size: Optional[CompanySize] = Field(None, alias="companySize")
    project_count: Optional[int] = Field(0, alias="projectCount")
    scope_count: Optional[int] = Field(0, alias="scopeCount")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    last_activity: Optional[datetime] = Field(None, alias="lastActivity")

    class Config:
        allow_population_by_field_name = True


class RecentProject(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True


class ClientDetail(ClientSummary):
    recent_projects: List[RecentProject] = Field(default_factory=list, alias="recentProjects")

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


class ClientStatsResponse(BaseModel):
    total_clients: int = Field(..., alias="totalClients")
    active_clients: int = Field(..., alias="activeClients")
    prospect_clients: int = Field(..., alias="prospectClients")
    past_clients: int = Field(..., alias="pastClients")
    avg_health_score: float = Field(..., alias="avgHealthScore")

    class Config:
        allow_population_by_field_name = True


class ClientProjectItem(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    description: Optional[str] = None
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True


class ClientProjectsResponse(BaseModel):
    projects: List[ClientProjectItem]
    total: int

    class Config:
        allow_population_by_field_name = True


class ClientScopeItem(BaseModel):
    id: uuid.UUID
    name: str = Field(..., alias="name")
    status: str
    project_id: uuid.UUID = Field(..., alias="projectId")
    project_name: str = Field(..., alias="projectName")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True


class ClientScopesResponse(BaseModel):
    scopes: List[ClientScopeItem]
    total: int

    class Config:
        allow_population_by_field_name = True


class ClientLogoResponse(BaseModel):
    logo_url: str = Field(..., alias="logoUrl")

    class Config:
        allow_population_by_field_name = True
