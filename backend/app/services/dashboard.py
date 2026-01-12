from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActivityLog, Project, Proposal, Quotation, Scope, User, Workspace, WorkspaceMember


async def get_dashboard_stats(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
) -> dict:
    """Get dashboard statistics for a user."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return {
            "workspace_id": str(workspace_id) if workspace_id else None,
            "workspace": None,
            "members": [],
            "scopes": {
                "total": 0,
                "byStatus": {},
                "draft": 0,
                "inReview": 0,
                "approved": 0,
                "rejected": 0,
            },
            "projects": {
                "total": 0,
                "byStatus": {},
                "active": 0,
                "archived": 0,
                "completed": 0,
            },
            "quotations": {
                "total": 0,
                "byStatus": {},
                "totalHours": 0,
                "draft": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            },
            "proposals": {
                "total": 0,
                "byStatus": {},
                "totalViews": 0,
                "draft": 0,
                "sent": 0,
                "viewed": 0,
                "accepted": 0,
                "rejected": 0,
            },
            "recentActivityCount": 0,
        }

    # Build base query filters
    workspace_filter = (
        lambda stmt: stmt.where(Scope.workspace_id == workspace_id)
        if workspace_id and workspace_id in accessible_workspace_ids
        else stmt.where(Scope.workspace_id.in_(accessible_workspace_ids))
    )

    # Scope Statistics
    scope_stmt: Select[Scope] = select(Scope).where(Scope.workspace_id.in_(accessible_workspace_ids))
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_stmt = scope_stmt.where(Scope.workspace_id == workspace_id)

    scope_status_stmt = (
        select(Scope.status, func.count(Scope.id).label("count"))
        .select_from(scope_stmt.subquery())
        .group_by(Scope.status)
    )
    scope_status_result = await session.execute(scope_status_stmt)
    scope_status_counts = {row[0]: row[1] for row in scope_status_result.all()}

    scope_total_stmt = select(func.count(Scope.id)).where(Scope.workspace_id.in_(accessible_workspace_ids))
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_total_stmt = scope_total_stmt.where(Scope.workspace_id == workspace_id)
    scope_total = (await session.execute(scope_total_stmt)).scalar_one() or 0

    # Project Statistics
    project_stmt: Select[Project] = select(Project).where(
        Project.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_stmt = project_stmt.where(Project.workspace_id == workspace_id)

    project_status_stmt = (
        select(Project.status, func.count(Project.id).label("count"))
        .select_from(project_stmt.subquery())
        .group_by(Project.status)
    )
    project_status_result = await session.execute(project_status_stmt)
    project_status_counts = {row[0]: row[1] for row in project_status_result.all()}

    project_total_stmt = select(func.count(Project.id)).where(
        Project.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_total_stmt = project_total_stmt.where(Project.workspace_id == workspace_id)
    project_total = (await session.execute(project_total_stmt)).scalar_one() or 0

    # Quotation Statistics
    quotation_stmt: Select[Quotation] = select(Quotation).where(
        Quotation.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        quotation_stmt = quotation_stmt.where(Quotation.workspace_id == workspace_id)

    quotation_status_stmt = (
        select(Quotation.status, func.count(Quotation.id).label("count"))
        .select_from(quotation_stmt.subquery())
        .group_by(Quotation.status)
    )
    quotation_status_result = await session.execute(quotation_status_stmt)
    quotation_status_counts = {row[0]: row[1] for row in quotation_status_result.all()}

    quotation_total_stmt = select(func.count(Quotation.id)).where(
        Quotation.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        quotation_total_stmt = quotation_total_stmt.where(Quotation.workspace_id == workspace_id)
    quotation_total = (await session.execute(quotation_total_stmt)).scalar_one() or 0

    quotation_hours_stmt = select(func.sum(Quotation.total_hours)).where(
        Quotation.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        quotation_hours_stmt = quotation_hours_stmt.where(Quotation.workspace_id == workspace_id)
    quotation_total_hours = (await session.execute(quotation_hours_stmt)).scalar_one() or 0

    # Proposal Statistics
    proposal_stmt: Select[Proposal] = select(Proposal).where(
        Proposal.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        proposal_stmt = proposal_stmt.where(Proposal.workspace_id == workspace_id)

    proposal_status_stmt = (
        select(Proposal.status, func.count(Proposal.id).label("count"))
        .select_from(proposal_stmt.subquery())
        .group_by(Proposal.status)
    )
    proposal_status_result = await session.execute(proposal_status_stmt)
    proposal_status_counts = {row[0]: row[1] for row in proposal_status_result.all()}

    proposal_total_stmt = select(func.count(Proposal.id)).where(
        Proposal.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        proposal_total_stmt = proposal_total_stmt.where(Proposal.workspace_id == workspace_id)
    proposal_total = (await session.execute(proposal_total_stmt)).scalar_one() or 0

    proposal_views_stmt = select(func.sum(Proposal.view_count)).where(
        Proposal.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        proposal_views_stmt = proposal_views_stmt.where(Proposal.workspace_id == workspace_id)
    proposal_total_views = (await session.execute(proposal_views_stmt)).scalar_one() or 0

    # Recent Activity Count (last 7 days)
    from datetime import datetime, timedelta, timezone

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    activity_stmt = select(func.count(ActivityLog.id)).where(
        ActivityLog.workspace_id.in_(accessible_workspace_ids),
        ActivityLog.created_at >= seven_days_ago,
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        activity_stmt = activity_stmt.where(ActivityLog.workspace_id == workspace_id)
    recent_activity_count = (await session.execute(activity_stmt)).scalar_one() or 0

    # Fetch workspace and member information if workspace_id is provided
    workspace_info = None
    members_info: List[dict] = []

    if workspace_id and workspace_id in accessible_workspace_ids:
        # Fetch workspace details
        workspace_stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        )
        workspace_result = await session.execute(workspace_stmt)
        workspace = workspace_result.scalar_one_or_none()

        if workspace:
            workspace_info = {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "logo_url": workspace.logo_url,
                "brand_color": workspace.brand_color,
                "secondary_color": workspace.secondary_color,
            }

            # Fetch active members
            members_stmt = (
                select(WorkspaceMember)
                .where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.status == "active",
                )
                .options(selectinload(WorkspaceMember.user))
            )
            members_result = await session.execute(members_stmt)
            members = members_result.scalars().all()

            for member in members:
                user = member.user
                members_info.append(
                    {
                        "id": str(member.id),
                        "email": user.email if user else member.invited_email,
                        "full_name": user.full_name if user else None,
                        "role": member.role,
                        "status": member.status,
                    }
                )

    return {
        "workspace_id": str(workspace_id) if workspace_id else None,
        "workspace": workspace_info,
        "members": members_info,
        "scopes": {
            "total": scope_total,
            "byStatus": scope_status_counts,
            "draft": scope_status_counts.get("draft", 0),
            "inReview": scope_status_counts.get("in_review", 0),
            "approved": scope_status_counts.get("approved", 0),
            "rejected": scope_status_counts.get("rejected", 0),
        },
        "projects": {
            "total": project_total,
            "byStatus": project_status_counts,
            "active": project_status_counts.get("active", 0),
            "archived": project_status_counts.get("archived", 0),
            "completed": project_status_counts.get("completed", 0),
        },
        "quotations": {
            "total": quotation_total,
            "byStatus": quotation_status_counts,
            "totalHours": quotation_total_hours or 0,
            "draft": quotation_status_counts.get("draft", 0),
            "pending": quotation_status_counts.get("pending", 0),
            "approved": quotation_status_counts.get("approved", 0),
            "rejected": quotation_status_counts.get("rejected", 0),
        },
        "proposals": {
            "total": proposal_total,
            "byStatus": proposal_status_counts,
            "totalViews": proposal_total_views or 0,
            "draft": proposal_status_counts.get("draft", 0),
            "sent": proposal_status_counts.get("sent", 0),
            "viewed": proposal_status_counts.get("viewed", 0),
            "accepted": proposal_status_counts.get("accepted", 0),
            "rejected": proposal_status_counts.get("rejected", 0),
        },
        "recentActivityCount": recent_activity_count,
    }

