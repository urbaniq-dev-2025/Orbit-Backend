"""
Admin-specific subscription and credit schemas for dashboard analytics.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SubscriptionStatus = Literal["active", "trialing", "past_due", "cancelled"]
PlanName = Literal["Enterprise", "Pro", "Starter", "Free"]
PurchaseStatus = Literal["completed", "pending", "failed", "refunded"]


class SubscriptionStatsData(BaseModel):
    """Subscription overview statistics."""
    total_subscribers: int = Field(..., alias="totalSubscribers")
    subscribers_growth: float = Field(..., alias="subscribersGrowth")
    mrr_from_subscriptions: float = Field(..., alias="mrrFromSubscriptions")
    mrr_growth: float = Field(..., alias="mrrGrowth")
    average_plan_value: float = Field(..., alias="averagePlanValue")
    avg_growth: float = Field(..., alias="avgGrowth")
    churn_rate: float = Field(..., alias="churnRate")
    churn_change: float = Field(..., alias="churnChange")

    class Config:
        allow_population_by_field_name = True


class PlanDistributionItem(BaseModel):
    """Plan distribution item."""
    name: PlanName
    subscribers: int
    revenue: float
    percentage: float
    price: float


class PlanDistributionData(BaseModel):
    """Plan distribution data."""
    plans: List[PlanDistributionItem]
    total_revenue: float = Field(..., alias="totalRevenue")
    total_subscribers: int = Field(..., alias="totalSubscribers")

    class Config:
        allow_population_by_field_name = True


class ConversionData(BaseModel):
    """Free to paid conversion metrics."""
    free_users: int = Field(..., alias="freeUsers")
    converted_last_30_days: int = Field(..., alias="convertedLast30Days")
    conversion_rate: float = Field(..., alias="conversionRate")
    avg_time_to_convert: int = Field(..., alias="avgTimeToConvert")

    class Config:
        allow_population_by_field_name = True


class CreditsSummaryData(BaseModel):
    """Credits summary statistics."""
    total_credits_sold: int = Field(..., alias="totalCreditsSold")
    credits_revenue: float = Field(..., alias="creditsRevenue")
    credits_consumed: int = Field(..., alias="creditsConsumed")
    credits_remaining: int = Field(..., alias="creditsRemaining")
    avg_credits_per_user: int = Field(..., alias="avgCreditsPerUser")

    class Config:
        allow_population_by_field_name = True


class CreditPackageItem(BaseModel):
    """Credit package information."""
    name: str
    credits: int
    price: float
    purchases: int
    revenue: float
    popular: bool


class CreditPackagesData(BaseModel):
    """Credit packages data."""
    packages: List[CreditPackageItem]
    total_packages: int = Field(..., alias="totalPackages")
    total_purchases: int = Field(..., alias="totalPurchases")
    total_revenue: float = Field(..., alias="totalRevenue")

    class Config:
        allow_population_by_field_name = True


class SubscriptionListItem(BaseModel):
    """Subscription list item."""
    id: str
    workspace_id: str = Field(..., alias="workspaceId")
    customer: str
    email: str
    plan: PlanName
    status: SubscriptionStatus
    mrr: float
    credits: int
    started: datetime
    renews: Optional[datetime] = None
    billing_cycle: Optional[Literal["monthly", "annual"]] = Field(None, alias="billingCycle")
    created_at: datetime = Field(..., alias="createdAt")

    class Config:
        allow_population_by_field_name = True


class SubscriptionListResponse(BaseModel):
    """Subscription list response."""
    subscriptions: List[SubscriptionListItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


class CreditPurchase(BaseModel):
    """Credit purchase item."""
    id: str
    workspace_id: str = Field(..., alias="workspaceId")
    customer: str
    package: str
    amount: float
    credits: int
    date: datetime
    method: str = Field(..., alias="method")
    transaction_id: str = Field(..., alias="transactionId")
    status: PurchaseStatus

    class Config:
        allow_population_by_field_name = True


class CreditPurchasesResponse(BaseModel):
    """Credit purchases response."""
    purchases: List[CreditPurchase]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


class TrendDataPoint(BaseModel):
    """Trend data point."""
    month: str
    year: int


class SubscriptionGrowthTrendPoint(TrendDataPoint):
    """Subscription growth trend point."""
    subscribers: int
    mrr: float


class SubscriptionGrowthTrend(BaseModel):
    """Subscription growth trend."""
    trend: List[SubscriptionGrowthTrendPoint]

    class Config:
        allow_population_by_field_name = True


class CreditPurchasesTrendPoint(TrendDataPoint):
    """Credit purchases trend point."""
    purchases: int
    revenue: float


class CreditPurchasesTrend(BaseModel):
    """Credit purchases trend."""
    trend: List[CreditPurchasesTrendPoint]

    class Config:
        allow_population_by_field_name = True


class PlanChangesTrendPoint(TrendDataPoint):
    """Plan changes trend point."""
    upgrades: int
    downgrades: int


class PlanChangesTrend(BaseModel):
    """Plan changes trend."""
    trend: List[PlanChangesTrendPoint]

    class Config:
        allow_population_by_field_name = True
