"""
Admin-specific client schemas for dashboard analytics.
"""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field

AccountType = Literal["companies", "individuals"]


class ClientStatsData(BaseModel):
    """Client dashboard statistics."""
    total_clients: int = Field(..., alias="totalClients")
    total_clients_trend: float = Field(..., alias="totalClientsTrend")  # Percentage change
    active_this_month: int = Field(..., alias="activeThisMonth")
    active_this_month_trend: float = Field(..., alias="activeThisMonthTrend")  # Percentage change
    total_ltv: float = Field(..., alias="totalLtv")  # Total Lifetime Value in dollars
    total_ltv_trend: float = Field(..., alias="totalLtvTrend")  # Percentage change
    avg_account_age_months: float = Field(..., alias="avgAccountAgeMonths")
    at_risk_count: int = Field(..., alias="atRiskCount")
    at_risk_trend: int = Field(..., alias="atRiskTrend")  # Absolute change (can be negative)
    nps_score: int = Field(..., alias="npsScore")  # Net Promoter Score (0-100)
    nps_trend: int = Field(..., alias="npsTrend")  # Absolute change

    class Config:
        allow_population_by_field_name = True


class HealthCategory(BaseModel):
    """Client health category breakdown."""
    category: Literal["healthy", "moderate", "atRisk", "critical"]
    count: int
    percentage: float


class ClientHealthDistributionData(BaseModel):
    """Client health distribution data."""
    distribution: List[HealthCategory]
    total_clients: int = Field(..., alias="totalClients")

    class Config:
        allow_population_by_field_name = True


class AccountTypeRevenue(BaseModel):
    """Revenue breakdown by account type."""
    type: AccountType
    revenue: float  # Total revenue in dollars
    count: int  # Number of accounts
    percentage: float  # Percentage of total accounts


class RevenueByAccountTypeData(BaseModel):
    """Revenue breakdown by account type (companies vs individuals)."""
    revenue_by_type: List[AccountTypeRevenue] = Field(..., alias="revenueByType")
    total_revenue: float = Field(..., alias="totalRevenue")
    total_accounts: int = Field(..., alias="totalAccounts")

    class Config:
        allow_population_by_field_name = True


class ClientSegmentationData(BaseModel):
    """Client segmentation counts."""
    all_clients: int = Field(..., alias="allClients")
    champions: int = Field(..., alias="champions")
    at_risk: int = Field(..., alias="atRisk")
    new_clients: int = Field(..., alias="newClients")  # Created within last 30 days
    enterprise: int = Field(..., alias="enterprise")
    overdue: int = Field(..., alias="overdue")  # Clients with past_due subscriptions

    class Config:
        allow_population_by_field_name = True
