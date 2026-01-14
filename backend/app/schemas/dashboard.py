from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScopeStats(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(..., alias="byStatus")
    draft: int
    in_review: int = Field(..., alias="inReview")
    approved: int
    rejected: int

    class Config:
        allow_population_by_field_name = True


class ProjectStats(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(..., alias="byStatus")
    active: int
    archived: int
    completed: int

    class Config:
        allow_population_by_field_name = True


class QuotationStats(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(..., alias="byStatus")
    total_hours: int = Field(..., alias="totalHours")
    draft: int
    pending: int
    approved: int
    rejected: int

    class Config:
        allow_population_by_field_name = True


class ProposalStats(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(..., alias="byStatus")
    total_views: int = Field(..., alias="totalViews")
    draft: int
    sent: int
    viewed: int
    accepted: int
    rejected: int

    class Config:
        allow_population_by_field_name = True


class ClientStats(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(..., alias="byStatus")
    prospect: int
    active: int
    past: int

    class Config:
        allow_population_by_field_name = True


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    brand_color: str = Field(..., alias="brandColor")
    secondary_color: str = Field(..., alias="secondaryColor")

    class Config:
        allow_population_by_field_name = True


class MemberInfo(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, alias="fullName")
    role: str
    status: str

    class Config:
        allow_population_by_field_name = True


class DashboardStatsResponse(BaseModel):
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
    workspace: Optional[WorkspaceInfo] = None
    members: List[MemberInfo] = Field(default_factory=list)
    clients: ClientStats
    scopes: ScopeStats
    projects: ProjectStats
    quotations: QuotationStats
    proposals: ProposalStats
    recent_activity_count: int = Field(..., alias="recentActivityCount")

    class Config:
        allow_population_by_field_name = True


class PipelineData(BaseModel):
    scopes: Dict[str, int] = Field(default_factory=dict)
    projects: Dict[str, int] = Field(default_factory=dict)
    quotations: Dict[str, int] = Field(default_factory=dict)
    proposals: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True


class RecentItem(BaseModel):
    id: str
    title: str
    status: str
    updated_at: str = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True


class RecentActivityResponse(BaseModel):
    scopes: List[RecentItem] = Field(default_factory=list)
    projects: List[RecentItem] = Field(default_factory=list)
    prds: List[RecentItem] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class UrgentPRD(BaseModel):
    id: str
    title: str
    priority: str
    due_date: str = Field(..., alias="dueDate")
    days_remaining: int = Field(..., alias="daysRemaining")

    class Config:
        allow_population_by_field_name = True


class UrgentItemsResponse(BaseModel):
    prds: List[UrgentPRD] = Field(default_factory=list)
    tasks: List[dict] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True

