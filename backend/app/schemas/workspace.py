from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum
from typing import List, Optional

from pydantic import AnyUrl, BaseModel, EmailStr, Field


class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class WorkspaceMemberStatus(str, Enum):
    pending = "pending"
    active = "active"
    inactive = "inactive"


class WorkspaceCreateRequest(BaseModel):
    name: str
    website_url: Optional[AnyUrl] = Field(None, alias="website")
    logo_url: Optional[AnyUrl] = Field(None, alias="logo")
    primary_color: Optional[str] = Field(None, alias="primaryColor")
    secondary_color: Optional[str] = Field(None, alias="secondaryColor")
    team_size: Optional[str] = Field(None, alias="teamSize")
    data_handling: Optional[str] = Field(None, alias="dataHandling")

    class Config:
        allow_population_by_field_name = True


class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    website_url: Optional[AnyUrl] = Field(None, alias="website")
    logo_url: Optional[AnyUrl] = Field(None, alias="logo")
    primary_color: Optional[str] = Field(None, alias="primaryColor")
    secondary_color: Optional[str] = Field(None, alias="secondaryColor")

    class Config:
        allow_population_by_field_name = True


class WorkspaceMemberPublic(BaseModel):
    id: uuid.UUID
    role: WorkspaceRole
    status: WorkspaceMemberStatus
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    invited_email: Optional[EmailStr] = None
    invited_at: Optional[dt.datetime] = None
    joined_at: Optional[dt.datetime] = None

    class Config:
        orm_mode = True


class WorkspaceSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    brand_color: str
    secondary_color: str
    role: WorkspaceRole
    created_at: dt.datetime
    updated_at: dt.datetime

    @classmethod
    def from_listing(cls, workspace: "Workspace", role: str) -> "WorkspaceSummary":
        from app.models import Workspace as WorkspaceModel  # local import to avoid cycles

        if not isinstance(workspace, WorkspaceModel):
            raise TypeError("workspace must be a Workspace model instance")
        return cls(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            logo_url=workspace.logo_url,
            brand_color=workspace.brand_color,
            secondary_color=workspace.secondary_color,
            role=WorkspaceRole(role),
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    class Config:
        orm_mode = True


class WorkspaceDetail(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    brand_color: str
    secondary_color: str
    website_url: Optional[str] = None
    team_size: Optional[str] = None
    data_handling: Optional[str] = None
    role: WorkspaceRole
    created_at: dt.datetime
    updated_at: dt.datetime
    members: Optional[List[WorkspaceMemberPublic]] = None

    class Config:
        orm_mode = True


class WorkspaceInviteRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.member
    message: Optional[str] = None


class WorkspaceInviteResponse(BaseModel):
    id: uuid.UUID
    email: Optional[EmailStr] = None
    role: WorkspaceRole
    status: WorkspaceMemberStatus
    invited_at: Optional[dt.datetime] = None


class WorkspaceMemberUpdateRequest(BaseModel):
    role: WorkspaceRole

