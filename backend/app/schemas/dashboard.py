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
    scopes: ScopeStats
    projects: ProjectStats
    quotations: QuotationStats
    proposals: ProposalStats
    recent_activity_count: int = Field(..., alias="recentActivityCount")

    class Config:
        allow_population_by_field_name = True

