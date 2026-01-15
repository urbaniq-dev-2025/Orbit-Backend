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
    """Platform activity data for admin with timeline/heatmap support."""
    # Summary metrics
    total_actions: int = Field(0, alias="totalActions")
    total_actions_period: str = Field("6 months", alias="totalActionsPeriod")
    average_daily_actions: float = Field(0.0, alias="averageDailyActions")
    trend_percentage: float = Field(0.0, alias="trendPercentage")
    trend_direction: str = Field("increase", alias="trendDirection")  # "increase" or "decrease"
    
    # Timeline heatmaps
    activity_heatmap: List[Dict[str, Any]] = Field(default_factory=list, alias="activityHeatmap")  # Daily by day of week
    hourly_activity_heatmap: List[Dict[str, Any]] = Field(default_factory=list, alias="hourlyActivityHeatmap")  # Hourly by day of week
    peak_hour: Optional[str] = Field(None, alias="peakHour")  # e.g., "11AM"
    most_active_day: Optional[str] = Field(None, alias="mostActiveDay")  # e.g., "Fri"
    
    # Activity breakdowns
    activity_by_entity_type: List[Dict[str, Any]] = Field(default_factory=list, alias="activityByEntityType")  # By entity type
    activities_by_date: List[Dict[str, Any]] = Field(default_factory=list, alias="activitiesByDate")  # Simple date/count
    activities_by_type: Dict[str, int] = Field(default_factory=dict, alias="activitiesByType")  # By action type
    
    # Other data
    top_workspaces: List[Dict[str, Any]] = Field(default_factory=list, alias="topWorkspaces")
    recent_activities: List[Dict[str, Any]] = Field(default_factory=list, alias="recentActivities")

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


class GeographicRevenueData(BaseModel):
    """Geographic revenue distribution data optimized for world map visualization."""
    revenue_by_country: List[Dict[str, Any]] = Field(..., alias="revenueByCountry")
    revenue_by_state: List[Dict[str, Any]] = Field(..., alias="revenueByState")
    revenue_by_city: List[Dict[str, Any]] = Field(..., alias="revenueByCity")
    total_revenue: float = Field(..., alias="totalRevenue")

    class Config:
        allow_population_by_field_name = True


class RevenueBySegmentData(BaseModel):
    """Revenue breakdown by segment (plan and company size)."""
    revenue_by_plan: List[Dict[str, Any]] = Field(..., alias="revenueByPlan")
    revenue_by_company_size: List[Dict[str, Any]] = Field(..., alias="revenueByCompanySize")
    total_revenue: float = Field(..., alias="totalRevenue")

    class Config:
        allow_population_by_field_name = True


class MRRWaterfallData(BaseModel):
    """MRR Waterfall data showing changes over time."""
    periods: List[Dict[str, Any]]
    starting_mrr: float = Field(..., alias="startingMrr")
    ending_mrr: float = Field(..., alias="endingMrr")
    net_change: float = Field(..., alias="netChange")

    class Config:
        allow_population_by_field_name = True


class AtRiskAccount(BaseModel):
    """At-risk account information."""
    workspace_id: str = Field(..., alias="workspaceId")
    workspace_name: str = Field(..., alias="workspaceName")
    subscription_id: str = Field(..., alias="subscriptionId")
    plan: str
    status: str
    mrr: float
    risk_reason: str = Field(..., alias="riskReason")
    current_period_end: Optional[datetime] = Field(None, alias="currentPeriodEnd")
    days_until_cancellation: Optional[int] = Field(None, alias="daysUntilCancellation")

    class Config:
        allow_population_by_field_name = True


class AtRiskAccountsData(BaseModel):
    """At-risk accounts data."""
    accounts: List[AtRiskAccount]
    total_count: int = Field(..., alias="totalCount")
    total_at_risk_mrr: float = Field(..., alias="totalAtRiskMrr")

    class Config:
        allow_population_by_field_name = True


class ChurnReasonItem(BaseModel):
    """Churn reason breakdown item."""
    reason: str
    count: int
    percentage: float
    total_mrr_lost: float = Field(..., alias="totalMrrLost")

    class Config:
        allow_population_by_field_name = True


class ChurnReasonsData(BaseModel):
    """Churn reasons data."""
    reasons: List[ChurnReasonItem]
    total_churned: int = Field(..., alias="totalChurned")
    total_mrr_lost: float = Field(..., alias="totalMrrLost")

    class Config:
        allow_population_by_field_name = True


class CohortRetentionPeriod(BaseModel):
    """Cohort retention period data."""
    cohort: str  # e.g., "2024-01"
    signups: int
    retention_by_month: Dict[str, float] = Field(..., alias="retentionByMonth")  # {"0": 100.0, "1": 85.0, ...}

    class Config:
        allow_population_by_field_name = True


class CohortRetentionData(BaseModel):
    """Cohort retention data."""
    cohorts: List[CohortRetentionPeriod]
    average_retention: Dict[str, float] = Field(..., alias="averageRetention")

    class Config:
        allow_population_by_field_name = True


class ExpenseCategoryItem(BaseModel):
    """Expense category item."""
    id: str
    name: str
    description: Optional[str] = None
    total_amount: float = Field(..., alias="totalAmount")
    expense_count: int = Field(..., alias="expenseCount")
    is_active: bool = Field(..., alias="isActive")

    class Config:
        allow_population_by_field_name = True


class ExpenseCategoriesData(BaseModel):
    """Expense categories data."""
    categories: List[ExpenseCategoryItem]
    total_amount: float = Field(..., alias="totalAmount")
    total_expenses: int = Field(..., alias="totalExpenses")

    class Config:
        allow_population_by_field_name = True


class ExpenseHistoryItem(BaseModel):
    """Expense history item."""
    id: str
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
    category_id: str = Field(..., alias="categoryId")
    category_name: str = Field(..., alias="categoryName")
    amount: float
    currency: str
    description: Optional[str] = None
    expense_date: datetime = Field(..., alias="expenseDate")
    vendor: Optional[str] = None
    created_by: Optional[str] = Field(None, alias="createdBy")

    class Config:
        allow_population_by_field_name = True


class ExpenseHistoryData(BaseModel):
    """Expense history data."""
    expenses: List[ExpenseHistoryItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")
    total_amount: float = Field(..., alias="totalAmount")

    class Config:
        allow_population_by_field_name = True


class RevenueForecastPeriod(BaseModel):
    """Revenue forecast period."""
    period: str  # e.g., "2024-02"
    forecasted_revenue: float = Field(..., alias="forecastedRevenue")
    confidence_lower: float = Field(..., alias="confidenceLower")
    confidence_upper: float = Field(..., alias="confidenceUpper")
    growth_rate: float = Field(..., alias="growthRate")

    class Config:
        allow_population_by_field_name = True


class RevenueForecastData(BaseModel):
    """Revenue forecast data."""
    forecast: List[RevenueForecastPeriod]
    current_mrr: float = Field(..., alias="currentMrr")
    projected_mrr: float = Field(..., alias="projectedMrr")
    growth_rate: float = Field(..., alias="growthRate")

    class Config:
        allow_population_by_field_name = True


class TransactionItem(BaseModel):
    """Transaction item."""
    id: str
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
    type: str
    status: str
    amount: float
    currency: str
    description: Optional[str] = None
    transaction_date: datetime = Field(..., alias="transactionDate")
    payment_method: Optional[str] = Field(None, alias="paymentMethod")
    reference_id: Optional[str] = Field(None, alias="referenceId")

    class Config:
        allow_population_by_field_name = True


class TransactionsData(BaseModel):
    """Transactions data."""
    transactions: List[TransactionItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")
    total_income: float = Field(..., alias="totalIncome")
    total_expenses: float = Field(..., alias="totalExpenses")
    net_cash_flow: float = Field(..., alias="netCashFlow")

    class Config:
        allow_population_by_field_name = True
