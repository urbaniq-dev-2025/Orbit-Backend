from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.admin import (
    AdminStatsResponse,
    AIUsageData,
    BusinessAnalytics,
    ConversionFunnelData,
    PlatformActivityData,
    RevenueBreakdownData,
    SubscriptionsListResponse,
    UsersListResponse,
)
from app.services import admin as admin_service

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> AdminStatsResponse:
    """Get admin dashboard statistics."""
    try:
        stats = await admin_service.get_admin_stats(session)
        return AdminStatsResponse(**stats)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve admin statistics.",
        ) from exc


@router.get("/ai-usage", response_model=AIUsageData)
async def get_ai_usage(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> AIUsageData:
    """Get AI usage data and statistics."""
    try:
        usage_data = await admin_service.get_ai_usage_data(session)
        return AIUsageData(**usage_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve AI usage data.",
        ) from exc


@router.get("/users", response_model=UsersListResponse)
async def get_users(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> UsersListResponse:
    """List all users (admin only)."""
    try:
        users_data = await admin_service.get_users_list(session, page=page, page_size=page_size)
        return UsersListResponse(**users_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve users list.",
        ) from exc


@router.get("/subscriptions", response_model=SubscriptionsListResponse)
async def get_subscriptions(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> SubscriptionsListResponse:
    """List all subscriptions (admin only)."""
    try:
        subscriptions_data = await admin_service.get_subscriptions_list(
            session, page=page, page_size=page_size
        )
        return SubscriptionsListResponse(**subscriptions_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve subscriptions list.",
        ) from exc


@router.get("/business", response_model=BusinessAnalytics)
async def get_business_analytics(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> BusinessAnalytics:
    """Get business analytics (admin only)."""
    try:
        analytics = await admin_service.get_business_analytics(session)
        return BusinessAnalytics(**analytics)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve business analytics.",
        ) from exc


@router.get("/platform-activity", response_model=PlatformActivityData)
async def get_platform_activity(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> PlatformActivityData:
    """Get platform activity data (admin only)."""
    try:
        activity_data = await admin_service.get_platform_activity(session)
        return PlatformActivityData(**activity_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve platform activity data.",
        ) from exc


@router.get("/revenue-breakdown", response_model=RevenueBreakdownData)
async def get_revenue_breakdown(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> RevenueBreakdownData:
    """Get revenue breakdown data (admin only)."""
    try:
        revenue_data = await admin_service.get_revenue_breakdown(session)
        return RevenueBreakdownData(**revenue_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve revenue breakdown data.",
        ) from exc


@router.get("/conversion-funnel", response_model=ConversionFunnelData)
async def get_conversion_funnel(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ConversionFunnelData:
    """Get conversion funnel data (admin only)."""
    try:
        funnel_data = await admin_service.get_conversion_funnel(session)
        return ConversionFunnelData(**funnel_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve conversion funnel data.",
        ) from exc
