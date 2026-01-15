from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api import deps
from app.schemas.admin import (
    AdminStatsResponse,
    AIUsageData,
    AtRiskAccountsData,
    BusinessAnalytics,
    ChurnReasonsData,
    CohortRetentionData,
    ConversionFunnelData,
    ExpenseCategoriesData,
    ExpenseHistoryData,
    GeographicRevenueData,
    MRRWaterfallData,
    PlatformActivityData,
    RevenueBreakdownData,
    RevenueBySegmentData,
    RevenueForecastData,
    SubscriptionsListResponse,
    TransactionsData,
    UsersListResponse,
)
from app.schemas.client_admin import (
    ClientHealthDistributionData,
    ClientSegmentationData,
    ClientStatsData,
    RevenueByAccountTypeData,
)
from app.schemas.subscription_admin import (
    ConversionData,
    CreditPackagesData,
    CreditPurchasesResponse,
    CreditPurchasesTrend,
    CreditsSummaryData,
    PlanChangesTrend,
    PlanDistributionData,
    SubscriptionGrowthTrend,
    SubscriptionListResponse,
    SubscriptionStatsData,
)
from app.services import admin as admin_service
from app.services import export as export_service

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


@router.get("/geographic-revenue", response_model=GeographicRevenueData)
async def get_geographic_revenue(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> GeographicRevenueData:
    """Get geographic revenue distribution (admin only)."""
    try:
        geo_data = await admin_service.get_geographic_revenue(session)
        return GeographicRevenueData(**geo_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve geographic revenue data.",
        ) from exc


@router.get("/revenue-by-segment", response_model=RevenueBySegmentData)
async def get_revenue_by_segment(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> RevenueBySegmentData:
    """Get revenue breakdown by segment (plan and industry) (admin only)."""
    try:
        segment_data = await admin_service.get_revenue_by_segment(session)
        return RevenueBySegmentData(**segment_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve revenue by segment data.",
        ) from exc


@router.get("/mrr-waterfall", response_model=MRRWaterfallData)
async def get_mrr_waterfall(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> MRRWaterfallData:
    """Get MRR waterfall showing changes over time (admin only)."""
    try:
        waterfall_data = await admin_service.get_mrr_waterfall(session)
        return MRRWaterfallData(**waterfall_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve MRR waterfall data.",
        ) from exc


@router.get("/at-risk-accounts", response_model=AtRiskAccountsData)
async def get_at_risk_accounts(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> AtRiskAccountsData:
    """Get at-risk accounts (cancelled, past_due, or scheduled to cancel) (admin only)."""
    try:
        at_risk_data = await admin_service.get_at_risk_accounts(session)
        return AtRiskAccountsData(**at_risk_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve at-risk accounts data.",
        ) from exc


@router.get("/churn-reasons", response_model=ChurnReasonsData)
async def get_churn_reasons(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ChurnReasonsData:
    """Get churn reasons breakdown (admin only)."""
    try:
        churn_data = await admin_service.get_churn_reasons(session)
        return ChurnReasonsData(**churn_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve churn reasons data.",
        ) from exc


@router.get("/cohort-retention", response_model=CohortRetentionData)
async def get_cohort_retention(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> CohortRetentionData:
    """Get cohort retention rates (admin only)."""
    try:
        retention_data = await admin_service.get_cohort_retention(session)
        return CohortRetentionData(**retention_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve cohort retention data.",
        ) from exc


@router.get("/expense-categories", response_model=ExpenseCategoriesData)
async def get_expense_categories(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ExpenseCategoriesData:
    """Get expense categories with totals (admin only)."""
    try:
        categories_data = await admin_service.get_expense_categories(session)
        return ExpenseCategoriesData(**categories_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve expense categories data.",
        ) from exc


@router.get("/expense-history", response_model=ExpenseHistoryData)
async def get_expense_history(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ExpenseHistoryData:
    """Get expense history with pagination (admin only)."""
    try:
        history_data = await admin_service.get_expense_history(session, page=page, page_size=page_size)
        return ExpenseHistoryData(**history_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve expense history data.",
        ) from exc


@router.get("/revenue-forecast", response_model=RevenueForecastData)
async def get_revenue_forecast(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> RevenueForecastData:
    """Get revenue forecast for next 6 months (admin only)."""
    try:
        forecast_data = await admin_service.get_revenue_forecast(session)
        return RevenueForecastData(**forecast_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve revenue forecast data.",
        ) from exc


@router.get("/transactions", response_model=TransactionsData)
async def get_transactions(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> TransactionsData:
    """Get transactions with pagination (admin only)."""
    try:
        transactions_data = await admin_service.get_transactions(session, page=page, page_size=page_size)
        return TransactionsData(**transactions_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve transactions data.",
        ) from exc


@router.get("/export")
async def export_report(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    format: str = Query("xlsx", regex="^(xlsx|pdf)$", alias="format"),
) -> Response:
    """Export admin dashboard report in Excel or PDF format."""
    try:
        if format == "xlsx":
            file_content = await export_service.generate_excel_report(session)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"admin_dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:  # pdf
            file_content = await export_service.generate_pdf_report(session)
            media_type = "application/pdf"
            filename = f"admin_dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as exc:
        import traceback
        error_msg = str(exc)
        traceback_str = traceback.format_exc()
        print(f"Export error: {error_msg}")
        print(f"Traceback: {traceback_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate {format.upper()} report: {error_msg}",
        ) from exc


@router.get("/clients/stats", response_model=ClientStatsData)
async def get_client_stats(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ClientStatsData:
    """Get client dashboard statistics (admin only)."""
    try:
        stats_data = await admin_service.get_client_stats(session)
        return ClientStatsData(**stats_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve client statistics.",
        ) from exc


@router.get("/clients/health-distribution", response_model=ClientHealthDistributionData)
async def get_client_health_distribution(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ClientHealthDistributionData:
    """Get client health distribution breakdown (admin only)."""
    try:
        health_data = await admin_service.get_client_health_distribution(session)
        return ClientHealthDistributionData(**health_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve client health distribution.",
        ) from exc


@router.get("/clients/revenue-by-account-type", response_model=RevenueByAccountTypeData)
async def get_revenue_by_account_type(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> RevenueByAccountTypeData:
    """Get revenue breakdown by account type (companies vs individuals) (admin only)."""
    try:
        revenue_data = await admin_service.get_revenue_by_account_type(session)
        return RevenueByAccountTypeData(**revenue_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve revenue by account type.",
        ) from exc


@router.get("/clients/segmentation", response_model=ClientSegmentationData)
async def get_client_segmentation(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ClientSegmentationData:
    """Get client segmentation counts (admin only)."""
    try:
        segmentation_data = await admin_service.get_client_segmentation(session)
        return ClientSegmentationData(**segmentation_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve client segmentation.",
        ) from exc


# Subscription APIs
@router.get("/subscriptions/stats", response_model=SubscriptionStatsData)
async def get_subscription_stats(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> SubscriptionStatsData:
    """Get subscription overview statistics (admin only)."""
    try:
        stats_data = await admin_service.get_subscription_stats(session)
        return SubscriptionStatsData(**stats_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve subscription statistics.",
        ) from exc


@router.get("/subscriptions/plan-distribution", response_model=PlanDistributionData)
async def get_plan_distribution(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> PlanDistributionData:
    """Get plan distribution breakdown (admin only)."""
    try:
        distribution_data = await admin_service.get_plan_distribution(session)
        return PlanDistributionData(**distribution_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve plan distribution.",
        ) from exc


@router.get("/subscriptions/conversion", response_model=ConversionData)
async def get_conversion_metrics(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> ConversionData:
    """Get free to paid conversion metrics (admin only)."""
    try:
        conversion_data = await admin_service.get_conversion_metrics(session)
        return ConversionData(**conversion_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve conversion metrics.",
        ) from exc


@router.get("/subscriptions/list", response_model=SubscriptionListResponse)
async def get_subscription_list_enhanced(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
) -> SubscriptionListResponse:
    """Get enhanced subscription list with filtering (admin only)."""
    try:
        list_data = await admin_service.get_subscription_list_enhanced(
            session,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            plan=plan,
        )
        return SubscriptionListResponse(**list_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve subscription list.",
        ) from exc


@router.get("/subscriptions/trends/subscription-growth", response_model=SubscriptionGrowthTrend)
async def get_subscription_growth_trend(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    months: int = Query(6, ge=1, le=12),
) -> SubscriptionGrowthTrend:
    """Get subscription growth trend (admin only)."""
    try:
        trend_data = await admin_service.get_subscription_growth_trend(session, months=months)
        return SubscriptionGrowthTrend(**trend_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve subscription growth trend.",
        ) from exc


@router.get("/subscriptions/trends/plan-changes", response_model=PlanChangesTrend)
async def get_plan_changes_trend(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    months: int = Query(6, ge=1, le=12),
) -> PlanChangesTrend:
    """Get plan changes trend (admin only)."""
    try:
        trend_data = await admin_service.get_plan_changes_trend(session, months=months)
        return PlanChangesTrend(**trend_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve plan changes trend.",
        ) from exc


# Credits APIs
@router.get("/credits/summary", response_model=CreditsSummaryData)
async def get_credits_summary(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> CreditsSummaryData:
    """Get credits summary statistics (admin only)."""
    try:
        summary_data = await admin_service.get_credits_summary(session)
        return CreditsSummaryData(**summary_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve credits summary.",
        ) from exc


@router.get("/credits/packages", response_model=CreditPackagesData)
async def get_credit_packages(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
) -> CreditPackagesData:
    """Get credit packages with purchase statistics (admin only)."""
    try:
        packages_data = await admin_service.get_credit_packages(session)
        return CreditPackagesData(**packages_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve credit packages.",
        ) from exc


@router.get("/credits/purchases", response_model=CreditPurchasesResponse)
async def get_credit_purchases(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    search: Optional[str] = Query(None),
    package: Optional[str] = Query(None),
) -> CreditPurchasesResponse:
    """Get credit purchase history (admin only)."""
    try:
        purchases_data = await admin_service.get_credit_purchases(
            session,
            page=page,
            page_size=page_size,
            search=search,
            package=package,
        )
        return CreditPurchasesResponse(**purchases_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve credit purchases.",
        ) from exc


@router.get("/credits/trends/purchases", response_model=CreditPurchasesTrend)
async def get_credit_purchases_trend(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    months: int = Query(6, ge=1, le=12),
) -> CreditPurchasesTrend:
    """Get credit purchases trend (admin only)."""
    try:
        trend_data = await admin_service.get_credit_purchases_trend(session, months=months)
        return CreditPurchasesTrend(**trend_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve credit purchases trend.",
        ) from exc


@router.get("/subscriptions/export")
async def export_subscriptions(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    format: str = Query("xlsx", regex="^(xlsx|csv)$"),
    status: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Response:
    """Export subscriptions to Excel or CSV format (admin only)."""
    try:
        file_content = await export_service.generate_subscriptions_export(
            session,
            format=format,
            status=status,
            plan=plan,
            search=search,
        )
        
        if format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"subscriptions-export-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        else:
            media_type = "text/csv"
            filename = f"subscriptions-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate {format.upper()} export.",
        ) from exc


@router.get("/credits/export")
async def export_credit_purchases(
    session: deps.SessionDep,
    current_user=Depends(deps.get_admin_user),
    format: str = Query("xlsx", regex="^(xlsx|csv)$"),
    package: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Response:
    """Export credit purchases to Excel or CSV format (admin only)."""
    try:
        file_content = await export_service.generate_credit_purchases_export(
            session,
            format=format,
            package=package,
            search=search,
        )
        
        if format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"credit-purchases-export-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        else:
            media_type = "text/csv"
            filename = f"credit-purchases-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate {format.upper()} export.",
        ) from exc
