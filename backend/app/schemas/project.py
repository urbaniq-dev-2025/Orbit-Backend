from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ProjectStatus = Literal["active", "archived", "completed", "on_hold"]


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    client_id: Optional[uuid.UUID] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)  # Kept for backward compatibility
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
    client_id: Optional[uuid.UUID] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)  # Kept for backward compatibility
    status: Optional[ProjectStatus] = None

    class Config:
        allow_population_by_field_name = True


class ProjectSummary(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: str
    description: Optional[str] = None
    client_id: Optional[uuid.UUID] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName")
    status: ProjectStatus
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        from_attributes = True


class ProjectDetail(ProjectSummary):
    scopes_count: int = Field(0, alias="scopesCount")
    engagement_type: Optional[str] = Field(None, alias="engagementType")
    progress: int = Field(0, ge=0, le=100)
    budget: Optional[float] = None
    team: Optional[List[uuid.UUID]] = None

    class Config:
        allow_population_by_field_name = True
        from_attributes = True


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectProgressUpdate(BaseModel):
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")


class ProjectTeamAssignRequest(BaseModel):
    team: List[uuid.UUID] = Field(..., description="List of user IDs to assign to the project")


class ProjectListResponse(BaseModel):
    """Response for listing projects with statistics."""
    projects: List[ProjectSummary] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict, description="Project statistics by status")

    class Config:
        populate_by_name = True
        from_attributes = True
