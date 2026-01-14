from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_users: int = Field(..., alias="totalUsers")
    active_users: int = Field(..., alias="activeUsers")
    total_workspaces: int = Field(..., alias="totalWorkspaces")
    total_projects: int = Field(..., alias="totalProjects")
    total_scopes: int = Field(..., alias="totalScopes")
    total_quotations: int = Field(..., alias="totalQuotations")
    total_proposals: int = Field(..., alias="totalProposals")
    total_ai_requests: int = Field(default=0, alias="totalAiRequests")
    total_storage_gb: float = Field(default=0.0, alias="totalStorageGb")

    class Config:
        allow_population_by_field_name = True


class AIUsageData(BaseModel):
    """AI usage statistics."""
    total_requests: int = Field(..., alias="totalRequests")
    requests_by_type: Dict[str, int] = Field(..., alias="requestsByType")
    requests_by_workspace: List[Dict[str, Any]] = Field(..., alias="requestsByWorkspace")
    requests_by_date: List[Dict[str, Any]] = Field(..., alias="requestsByDate")
    total_tokens_used: int = Field(default=0, alias="totalTokensUsed")
    total_cost: float = Field(default=0.0, alias="totalCost")
    executive_summary: Optional[str] = Field(default="", alias="executiveSummary")

    class Config:
        allow_population_by_field_name = True


class UserListItem(BaseModel):
    """User list item for admin."""
    id: str
    email: str
    full_name: Optional[str] = Field(None, alias="fullName")
    is_active: bool = Field(..., alias="isActive")
    is_verified: bool = Field(..., alias="isVerified")
    onboarding_completed: bool = Field(..., alias="onboardingCompleted")
    created_at: datetime = Field(..., alias="createdAt")
    workspace_count: int = Field(default=0, alias="workspaceCount")

    class Config:
        allow_population_by_field_name = True


class UsersListResponse(BaseModel):
    """List of users for admin."""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


class SubscriptionListItem(BaseModel):
    """Subscription list item for admin."""
    id: str
    workspace_id: str = Field(..., alias="workspaceId")
    workspace_name: str = Field(..., alias="workspaceName")
    plan: str
    status: str
    billing_cycle: Optional[str] = Field(None, alias="billingCycle")
    created_at: datetime = Field(..., alias="createdAt")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")

    class Config:
        allow_population_by_field_name = True


class SubscriptionsListResponse(BaseModel):
    """List of subscriptions for admin."""
    subscriptions: List[SubscriptionListItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


class BusinessAnalytics(BaseModel):
    """Business analytics for admin."""
    revenue: Dict[str, float]
    growth_metrics: Dict[str, float] = Field(..., alias="growthMetrics")
    user_acquisition: Dict[str, int] = Field(..., alias="userAcquisition")
    retention_rate: float = Field(..., alias="retentionRate")
    active_workspaces: int = Field(..., alias="activeWorkspaces")
    churn_rate: float = Field(..., alias="churnRate")

    class Config:
        allow_population_by_field_name = True


class PlatformActivityData(BaseModel):
    """Platform activity data for admin."""
    activities_by_date: List[Dict[str, Any]] = Field(..., alias="activitiesByDate")
    activities_by_type: Dict[str, int] = Field(..., alias="activitiesByType")
    top_workspaces: List[Dict[str, Any]] = Field(..., alias="topWorkspaces")
    recent_activities: List[Dict[str, Any]] = Field(..., alias="recentActivities")

    class Config:
        allow_population_by_field_name = True


class RevenueBreakdownData(BaseModel):
    """Revenue breakdown data for admin."""
    revenue_by_plan: List[Dict[str, Any]] = Field(..., alias="revenueByPlan")
    mrr_breakdown: List[Dict[str, Any]] = Field(..., alias="mrrBreakdown")
    revenue_trend: List[Dict[str, Any]] = Field(..., alias="revenueTrend")
    total_mrr: float = Field(..., alias="totalMrr")
    total_arr: float = Field(..., alias="totalArr")

    class Config:
        allow_population_by_field_name = True


class ConversionFunnelData(BaseModel):
    """Conversion funnel data for admin."""
    stages: List[Dict[str, Any]]
    conversion_rates: Dict[str, float] = Field(..., alias="conversionRates")
    total_visitors: int = Field(..., alias="totalVisitors")

    class Config:
        allow_population_by_field_name = True
