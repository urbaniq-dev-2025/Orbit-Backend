from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivityLog,
    Project,
    Proposal,
    Quotation,
    Scope,
    Subscription,
    User,
    UsageMetric,
    Workspace,
    WorkspaceMember,
)


async def get_admin_stats(session: AsyncSession) -> dict:
    """Get admin dashboard statistics."""
    # Total users
    user_count_stmt = select(func.count(User.id))
    user_result = await session.execute(user_count_stmt)
    total_users = user_result.scalar() or 0

    # Active users
    active_user_count_stmt = select(func.count(User.id)).where(User.is_active == True)
    active_user_result = await session.execute(active_user_count_stmt)
    active_users = active_user_result.scalar() or 0

    # Total workspaces
    workspace_count_stmt = select(func.count(Workspace.id))
    workspace_result = await session.execute(workspace_count_stmt)
    total_workspaces = workspace_result.scalar() or 0

    # Total projects
    project_count_stmt = select(func.count(Project.id))
    project_result = await session.execute(project_count_stmt)
    total_projects = project_result.scalar() or 0

    # Total scopes
    scope_count_stmt = select(func.count(Scope.id))
    scope_result = await session.execute(scope_count_stmt)
    total_scopes = scope_result.scalar() or 0

    # Total quotations
    quotation_count_stmt = select(func.count(Quotation.id))
    quotation_result = await session.execute(quotation_count_stmt)
    total_quotations = quotation_result.scalar() or 0

    # Total proposals
    proposal_count_stmt = select(func.count(Proposal.id))
    proposal_result = await session.execute(proposal_count_stmt)
    total_proposals = proposal_result.scalar() or 0

    # AI requests (from usage metrics)
    ai_usage_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "ai_request"
    )
    ai_usage_result = await session.execute(ai_usage_stmt)
    total_ai_requests = ai_usage_result.scalar() or 0

    # Storage (from usage metrics)
    storage_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "storage_mb"
    )
    storage_result = await session.execute(storage_stmt)
    total_storage_mb = storage_result.scalar() or 0
    total_storage_gb = total_storage_mb / 1024.0 if total_storage_mb else 0.0

    return {
        "totalUsers": total_users,
        "activeUsers": active_users,
        "totalWorkspaces": total_workspaces,
        "totalProjects": total_projects,
        "totalScopes": total_scopes,
        "totalQuotations": total_quotations,
        "totalProposals": total_proposals,
        "totalAiRequests": int(total_ai_requests),
        "totalStorageGb": round(total_storage_gb, 2),
    }


async def get_ai_usage_data(session: AsyncSession) -> dict:
    """Get AI usage statistics."""
    # Total AI requests
    total_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type.like("ai_%")
    )
    total_result = await session.execute(total_stmt)
    total_requests = total_result.scalar() or 0

    # Requests by type
    type_stmt = (
        select(UsageMetric.metric_type, func.sum(UsageMetric.metric_value).label("count"))
        .where(UsageMetric.metric_type.like("ai_%"))
        .group_by(UsageMetric.metric_type)
    )
    type_result = await session.execute(type_stmt)
    requests_by_type = {row[0]: row[1] for row in type_result.all()}

    # Requests by workspace
    workspace_stmt = (
        select(
            UsageMetric.workspace_id,
            Workspace.name,
            func.sum(UsageMetric.metric_value).label("count"),
        )
        .join(Workspace, UsageMetric.workspace_id == Workspace.id)
        .where(UsageMetric.metric_type.like("ai_%"))
        .group_by(UsageMetric.workspace_id, Workspace.name)
        .order_by(func.sum(UsageMetric.metric_value).desc())
        .limit(10)
    )
    workspace_result = await session.execute(workspace_stmt)
    requests_by_workspace = [
        {"workspaceId": str(row[0]), "workspaceName": row[1], "count": row[2]}
        for row in workspace_result.all()
    ]

    # Requests by date (last 30 days)
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    date_stmt = (
        select(
            UsageMetric.period_start,
            func.sum(UsageMetric.metric_value).label("count"),
        )
        .where(
            UsageMetric.metric_type.like("ai_%"),
            UsageMetric.period_start >= thirty_days_ago,
        )
        .group_by(UsageMetric.period_start)
        .order_by(UsageMetric.period_start)
    )
    date_result = await session.execute(date_stmt)
    requests_by_date = [
        {"date": row[0].isoformat(), "count": row[1]} for row in date_result.all()
    ]

    # Total tokens used (from usage metrics if tracked)
    tokens_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "ai_tokens"
    )
    tokens_result = await session.execute(tokens_stmt)
    total_tokens_used = tokens_result.scalar() or 0

    # Total cost (from usage metrics if tracked)
    cost_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "ai_cost_cents"
    )
    cost_result = await session.execute(cost_stmt)
    total_cost_cents = cost_result.scalar() or 0
    total_cost = total_cost_cents / 100.0 if total_cost_cents else 0.0

    # Generate executive summary
    top_workspace = requests_by_workspace[0] if requests_by_workspace else None
    top_type = max(requests_by_type.items(), key=lambda x: x[1]) if requests_by_type else None
    
    executive_summary_parts = []
    if total_requests > 0:
        executive_summary_parts.append(f"Total AI requests: {int(total_requests):,}")
    if top_type:
        executive_summary_parts.append(f"Most used type: {top_type[0]} ({top_type[1]:,} requests)")
    if top_workspace:
        executive_summary_parts.append(f"Top workspace: {top_workspace.get('workspaceName', 'N/A')} ({top_workspace.get('count', 0):,} requests)")
    if total_tokens_used > 0:
        executive_summary_parts.append(f"Total tokens used: {int(total_tokens_used):,}")
    if total_cost > 0:
        executive_summary_parts.append(f"Total cost: ${total_cost:.2f}")
    
    executive_summary = ". ".join(executive_summary_parts) if executive_summary_parts else "No AI usage data available."

    return {
        "totalRequests": int(total_requests),
        "requestsByType": requests_by_type,
        "requestsByWorkspace": requests_by_workspace,
        "requestsByDate": requests_by_date,
        "totalTokensUsed": int(total_tokens_used),
        "totalCost": round(total_cost, 2),
        "executiveSummary": executive_summary,
    }


async def get_users_list(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Get list of all users for admin."""
    offset = (page - 1) * page_size

    # Get users with workspace count
    users_stmt = (
        select(
            User.id,
            User.email,
            User.full_name,
            User.is_active,
            User.is_verified,
            User.onboarding_completed,
            User.created_at,
            func.count(WorkspaceMember.workspace_id).label("workspace_count"),
        )
        .outerjoin(WorkspaceMember, User.id == WorkspaceMember.user_id)
        .group_by(
            User.id,
            User.email,
            User.full_name,
            User.is_active,
            User.is_verified,
            User.onboarding_completed,
            User.created_at,
        )
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users_result = await session.execute(users_stmt)
    users = [
        {
            "id": str(row[0]),
            "email": row[1],
            "fullName": row[2],
            "isActive": row[3],
            "isVerified": row[4],
            "onboardingCompleted": row[5],
            "createdAt": row[6],
            "workspaceCount": row[7] or 0,
        }
        for row in users_result.all()
    ]

    # Get total count
    count_stmt = select(func.count(User.id))
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    return {
        "users": users,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasMore": (offset + page_size) < total,
    }


async def get_subscriptions_list(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Get list of subscriptions for admin."""
    try:
        offset = (page - 1) * page_size

        # Get subscriptions with workspace info
        subscriptions_stmt = (
            select(
                Subscription.id,
                Subscription.workspace_id,
                Workspace.name,
                Subscription.plan,
                Subscription.status,
                Subscription.billing_cycle,
                Subscription.created_at,
                Subscription.current_period_end,
            )
            .join(Workspace, Subscription.workspace_id == Workspace.id)
            .order_by(Subscription.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        subscriptions_result = await session.execute(subscriptions_stmt)
        subscriptions = [
            {
                "id": str(row[0]),
                "workspaceId": str(row[1]),
                "workspaceName": row[2],
                "plan": row[3],
                "status": row[4],
                "billingCycle": row[5],
                "createdAt": row[6],
                "expiresAt": row[7],
            }
            for row in subscriptions_result.all()
        ]

        # Get total count
        count_stmt = select(func.count(Subscription.id))
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        return {
            "subscriptions": subscriptions,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasMore": (offset + page_size) < total,
        }
    except Exception:
        # If Subscription table doesn't exist yet, return empty list
        return {
            "subscriptions": [],
            "total": 0,
            "page": page,
            "pageSize": page_size,
            "hasMore": False,
        }


async def get_business_analytics(session: AsyncSession) -> dict:
    """Get business analytics for admin - all data from live database queries."""
    now = datetime.utcnow()
    start_of_this_month = datetime(now.year, now.month, 1)
    start_of_last_month = datetime(
        (now.year if now.month > 1 else now.year - 1),
        (now.month - 1 if now.month > 1 else 12),
        1
    )
    start_of_last_month_end = start_of_this_month - timedelta(days=1)
    start_of_this_year = datetime(now.year, 1, 1)
    
    # Total users
    total_users_stmt = select(func.count(User.id))
    total_users_result = await session.execute(total_users_stmt)
    total_users = total_users_result.scalar() or 0

    # Users this month
    users_this_month_stmt = select(func.count(User.id)).where(
        User.created_at >= start_of_this_month
    )
    users_this_month_result = await session.execute(users_this_month_stmt)
    users_this_month = users_this_month_result.scalar() or 0

    # Users last month
    users_last_month_stmt = select(func.count(User.id)).where(
        User.created_at >= start_of_last_month,
        User.created_at < start_of_this_month
    )
    users_last_month_result = await session.execute(users_last_month_stmt)
    users_last_month = users_last_month_result.scalar() or 0

    # Calculate user growth percentage
    user_growth = (
        ((users_this_month - users_last_month) / users_last_month * 100)
        if users_last_month > 0
        else (100.0 if users_this_month > 0 else 0.0)
    )

    # Total workspaces
    total_workspaces_stmt = select(func.count(Workspace.id))
    total_workspaces_result = await session.execute(total_workspaces_stmt)
    total_workspaces = total_workspaces_result.scalar() or 0

    # Workspaces this month
    workspaces_this_month_stmt = select(func.count(Workspace.id)).where(
        Workspace.created_at >= start_of_this_month
    )
    workspaces_this_month_result = await session.execute(workspaces_this_month_stmt)
    workspaces_this_month = workspaces_this_month_result.scalar() or 0

    # Workspaces last month
    workspaces_last_month_stmt = select(func.count(Workspace.id)).where(
        Workspace.created_at >= start_of_last_month,
        Workspace.created_at < start_of_this_month
    )
    workspaces_last_month_result = await session.execute(workspaces_last_month_stmt)
    workspaces_last_month = workspaces_last_month_result.scalar() or 0

    # Calculate workspace growth percentage
    workspace_growth = (
        ((workspaces_this_month - workspaces_last_month) / workspaces_last_month * 100)
        if workspaces_last_month > 0
        else (100.0 if workspaces_this_month > 0 else 0.0)
    )

    # Calculate retention rate (users who created workspaces)
    users_with_workspaces_stmt = (
        select(func.count(func.distinct(WorkspaceMember.user_id)))
    )
    users_with_workspaces_result = await session.execute(users_with_workspaces_stmt)
    users_with_workspaces = users_with_workspaces_result.scalar() or 0

    retention_rate = (
        (users_with_workspaces / total_users * 100) if total_users > 0 else 0.0
    )

    # Active workspaces (with activity in last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    active_workspaces_stmt = (
        select(func.count(func.distinct(ActivityLog.workspace_id)))
        .where(ActivityLog.created_at >= thirty_days_ago)
    )
    active_workspaces_result = await session.execute(active_workspaces_stmt)
    active_workspaces = active_workspaces_result.scalar() or 0

    # Calculate churn rate (workspaces created but inactive in last 60 days)
    sixty_days_ago = now - timedelta(days=60)
    
    # Total workspaces created more than 30 days ago (established workspaces)
    established_workspaces_stmt = select(func.count(Workspace.id)).where(
        Workspace.created_at < (now - timedelta(days=30))
    )
    established_workspaces_result = await session.execute(established_workspaces_stmt)
    established_workspaces = established_workspaces_result.scalar() or 0
    
    # Workspaces with activity in last 60 days
    active_recent_stmt = (
        select(func.count(func.distinct(ActivityLog.workspace_id)))
        .where(ActivityLog.created_at >= sixty_days_ago)
    )
    active_recent_result = await session.execute(active_recent_stmt)
    active_recent = active_recent_result.scalar() or 0
    
    # Churn = established workspaces that are inactive
    inactive_established = max(0, established_workspaces - active_recent)
    
    churn_rate = (
        (inactive_established / established_workspaces * 100)
        if established_workspaces > 0
        else 0.0
    )

    # Revenue - query from usage metrics if tracked, otherwise 0
    revenue_total_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "revenue_cents"
    )
    revenue_total_result = await session.execute(revenue_total_stmt)
    revenue_total_cents = revenue_total_result.scalar() or 0
    revenue_total = revenue_total_cents / 100.0 if revenue_total_cents else 0.0

    # Monthly revenue (this month)
    revenue_monthly_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "revenue_cents",
        UsageMetric.period_start >= start_of_this_month.date()
    )
    revenue_monthly_result = await session.execute(revenue_monthly_stmt)
    revenue_monthly_cents = revenue_monthly_result.scalar() or 0
    revenue_monthly = revenue_monthly_cents / 100.0 if revenue_monthly_cents else 0.0

    # Annual revenue (this year)
    revenue_annual_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "revenue_cents",
        UsageMetric.period_start >= start_of_this_year.date()
    )
    revenue_annual_result = await session.execute(revenue_annual_stmt)
    revenue_annual_cents = revenue_annual_result.scalar() or 0
    revenue_annual = revenue_annual_cents / 100.0 if revenue_annual_cents else 0.0

    # Revenue growth (this month vs last month)
    revenue_last_month_stmt = select(func.sum(UsageMetric.metric_value)).where(
        UsageMetric.metric_type == "revenue_cents",
        UsageMetric.period_start >= start_of_last_month.date(),
        UsageMetric.period_start < start_of_this_month.date()
    )
    revenue_last_month_result = await session.execute(revenue_last_month_stmt)
    revenue_last_month_cents = revenue_last_month_result.scalar() or 0
    revenue_last_month = revenue_last_month_cents / 100.0 if revenue_last_month_cents else 0.0

    revenue_growth = (
        ((revenue_monthly - revenue_last_month) / revenue_last_month * 100)
        if revenue_last_month > 0
        else (100.0 if revenue_monthly > 0 else 0.0)
    )

    return {
        "revenue": {
            "total": round(revenue_total, 2),
            "monthly": round(revenue_monthly, 2),
            "annual": round(revenue_annual, 2),
        },
        "growthMetrics": {
            "userGrowth": round(user_growth, 2),
            "workspaceGrowth": round(workspace_growth, 2),
            "revenueGrowth": round(revenue_growth, 2),
        },
        "userAcquisition": {
            "total": total_users,
            "thisMonth": users_this_month,
            "lastMonth": users_last_month,
        },
        "retentionRate": round(retention_rate, 2),
        "activeWorkspaces": active_workspaces,
        "churnRate": round(churn_rate, 2),
    }


async def get_platform_activity(session: AsyncSession) -> dict:
    """Get platform activity data for admin."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Activities by date (last 30 days)
    activities_by_date_stmt = (
        select(
            func.date(ActivityLog.created_at).label("date"),
            func.count(ActivityLog.id).label("count"),
        )
        .where(ActivityLog.created_at >= thirty_days_ago)
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at))
    )
    activities_by_date_result = await session.execute(activities_by_date_stmt)
    activities_by_date = [
        {"date": row[0].isoformat(), "count": row[1]} for row in activities_by_date_result.all()
    ]

    # Activities by type
    activities_by_type_stmt = (
        select(ActivityLog.action, func.count(ActivityLog.id).label("count"))
        .where(ActivityLog.created_at >= thirty_days_ago)
        .group_by(ActivityLog.action)
        .order_by(func.count(ActivityLog.id).desc())
    )
    activities_by_type_result = await session.execute(activities_by_type_stmt)
    activities_by_type = {row[0]: row[1] for row in activities_by_type_result.all()}

    # Top workspaces by activity
    top_workspaces_stmt = (
        select(
            ActivityLog.workspace_id,
            Workspace.name,
            func.count(ActivityLog.id).label("count"),
        )
        .join(Workspace, ActivityLog.workspace_id == Workspace.id)
        .where(ActivityLog.created_at >= thirty_days_ago)
        .group_by(ActivityLog.workspace_id, Workspace.name)
        .order_by(func.count(ActivityLog.id).desc())
        .limit(10)
    )
    top_workspaces_result = await session.execute(top_workspaces_stmt)
    top_workspaces = [
        {
            "workspaceId": str(row[0]),
            "workspaceName": row[1],
            "count": row[2],
        }
        for row in top_workspaces_result.all()
    ]

    # Recent activities
    recent_activities_stmt = (
        select(
            ActivityLog.id,
            ActivityLog.action,
            ActivityLog.entity_type,
            ActivityLog.created_at,
            Workspace.name.label("workspace_name"),
            User.full_name.label("user_name"),
        )
        .join(Workspace, ActivityLog.workspace_id == Workspace.id)
        .outerjoin(User, ActivityLog.user_id == User.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
    )
    recent_activities_result = await session.execute(recent_activities_stmt)
    recent_activities = [
        {
            "id": str(row[0]),
            "action": row[1],
            "entityType": row[2],
            "createdAt": row[3].isoformat(),
            "workspaceName": row[4],
            "userName": row[5] or "Unknown",
        }
        for row in recent_activities_result.all()
    ]

    return {
        "activitiesByDate": activities_by_date,
        "activitiesByType": activities_by_type,
        "topWorkspaces": top_workspaces,
        "recentActivities": recent_activities,
    }


async def get_revenue_breakdown(session: AsyncSession) -> dict:
    """Get revenue breakdown data for admin."""
    try:
        now = datetime.utcnow()
        start_of_this_month = datetime(now.year, now.month, 1)
        six_months_ago = start_of_this_month - timedelta(days=180)

        # Plan pricing mapping (adjust based on your actual pricing)
        plan_pricing = {
            "free": 0.0,
            "starter": 24.0,  # $24/month
            "pro": 48.0,  # $48/month
            "team": 120.0,  # $120/month
            "enterprise": 500.0,  # $500/month
        }

        # Revenue by plan
        revenue_by_plan_stmt = (
            select(
                Subscription.plan,
                func.count(Subscription.id).label("count"),
            )
            .where(Subscription.status == "active")
            .group_by(Subscription.plan)
        )
        revenue_by_plan_result = await session.execute(revenue_by_plan_stmt)
        revenue_by_plan = []
        total_mrr = 0.0
        for row in revenue_by_plan_result.all():
            plan = row[0]
            count = row[1]
            mrr = plan_pricing.get(plan, 0.0) * count
            total_mrr += mrr
            revenue_by_plan.append({
                "plan": plan,
                "count": count,
                "revenue": round(mrr, 2),
            })
    except Exception:
        # If Subscription table doesn't exist yet, return empty data
        revenue_by_plan = []
        total_mrr = 0.0
        now = datetime.utcnow()
        start_of_this_month = datetime(now.year, now.month, 1)

        # MRR breakdown by month (last 6 months)
        mrr_breakdown = []
        for i in range(6):
            month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            
            try:
                # Get subscriptions active during this month
                subscriptions_stmt = select(Subscription.plan, func.count(Subscription.id)).where(
                    Subscription.status == "active",
                    Subscription.created_at < month_end,
                    (Subscription.current_period_end.is_(None)) | (Subscription.current_period_end >= month_start),
                ).group_by(Subscription.plan)
                
                subscriptions_result = await session.execute(subscriptions_stmt)
                month_mrr = sum(plan_pricing.get(row[0], 0.0) * row[1] for row in subscriptions_result.all())
            except Exception:
                month_mrr = 0.0
            
            mrr_breakdown.append({
                "month": month_start.strftime("%b"),
                "mrr": round(month_mrr, 2),
            })
        
        mrr_breakdown.reverse()  # Oldest to newest

    # Revenue trend (from usage metrics if available, otherwise from subscriptions)
    revenue_trend = []
    for i in range(6):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        
        # Try to get from usage metrics first
        revenue_stmt = select(func.sum(UsageMetric.metric_value)).where(
            UsageMetric.metric_type == "revenue_cents",
            UsageMetric.period_start >= month_start.date(),
            UsageMetric.period_start < month_end.date(),
        )
        revenue_result = await session.execute(revenue_stmt)
        revenue_cents = revenue_result.scalar() or 0
        revenue = revenue_cents / 100.0 if revenue_cents else 0.0
        
        revenue_trend.append({
            "month": month_start.strftime("%b"),
            "revenue": round(revenue, 2),
        })
    
    revenue_trend.reverse()

    total_arr = total_mrr * 12

    return {
        "revenueByPlan": revenue_by_plan,
        "mrrBreakdown": mrr_breakdown,
        "revenueTrend": revenue_trend,
        "totalMrr": round(total_mrr, 2),
        "totalArr": round(total_arr, 2),
    }


async def get_conversion_funnel(session: AsyncSession) -> dict:
    """Get conversion funnel data for admin."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Total visitors (approximate - users who signed up)
    # In a real system, you'd track this separately, but we'll use signups as proxy
    total_visitors_stmt = select(func.count(User.id)).where(
        User.created_at >= thirty_days_ago
    )
    total_visitors_result = await session.execute(total_visitors_stmt)
    total_visitors = total_visitors_result.scalar() or 0

    # Signups (users created in last 30 days)
    signups_stmt = select(func.count(User.id)).where(
        User.created_at >= thirty_days_ago
    )
    signups_result = await session.execute(signups_stmt)
    signups = signups_result.scalar() or 0

    # Activated (users who completed onboarding)
    activated_stmt = select(func.count(User.id)).where(
        User.created_at >= thirty_days_ago,
        User.onboarding_completed == True,
    )
    activated_result = await session.execute(activated_stmt)
    activated = activated_result.scalar() or 0

    # Paid (users with active paid subscriptions)
    try:
        paid_stmt = (
            select(func.count(func.distinct(WorkspaceMember.user_id)))
            .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
            .join(Subscription, Subscription.workspace_id == Workspace.id)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(
                User.created_at >= thirty_days_ago,
                Subscription.status == "active",
                Subscription.plan != "free",
            )
        )
        paid_result = await session.execute(paid_stmt)
        paid = paid_result.scalar() or 0
    except Exception:
        # If Subscription table doesn't exist yet, return 0
        paid = 0

    # Calculate conversion rates
    signup_rate = (signups / total_visitors * 100) if total_visitors > 0 else 0.0
    activation_rate = (activated / signups * 100) if signups > 0 else 0.0
    paid_rate = (paid / activated * 100) if activated > 0 else 0.0

    stages = [
        {
            "stage": "Visitors",
            "value": total_visitors,
            "rate": 100.0,
        },
        {
            "stage": "Signups",
            "value": signups,
            "rate": round(signup_rate, 2),
        },
        {
            "stage": "Activated",
            "value": activated,
            "rate": round(activation_rate, 2),
        },
        {
            "stage": "Paid",
            "value": paid,
            "rate": round(paid_rate, 2),
        },
    ]

    return {
        "stages": stages,
        "conversionRates": {
            "signup": round(signup_rate, 2),
            "activation": round(activation_rate, 2),
            "paid": round(paid_rate, 2),
        },
        "totalVisitors": total_visitors,
    }
