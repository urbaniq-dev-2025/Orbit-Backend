from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActivityLog, Client, Project, Proposal, Quotation, Scope, User, Workspace, WorkspaceMember


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
            "clients": {
                "total": 0,
                "byStatus": {},
                "prospect": 0,
                "active": 0,
                "past": 0,
            },
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
    scope_status_stmt = (
        select(Scope.status, func.count(Scope.id).label("count"))
        .where(Scope.workspace_id.in_(accessible_workspace_ids))
        .group_by(Scope.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_status_stmt = scope_status_stmt.where(Scope.workspace_id == workspace_id)
    scope_status_result = await session.execute(scope_status_stmt)
    scope_status_counts = {row[0]: row[1] for row in scope_status_result.all()}

    scope_total_stmt = select(func.count(Scope.id)).where(Scope.workspace_id.in_(accessible_workspace_ids))
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_total_stmt = scope_total_stmt.where(Scope.workspace_id == workspace_id)
    scope_total = (await session.execute(scope_total_stmt)).scalar_one() or 0

    # Project Statistics
    project_status_stmt = (
        select(Project.status, func.count(Project.id).label("count"))
        .where(Project.workspace_id.in_(accessible_workspace_ids))
        .group_by(Project.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_status_stmt = project_status_stmt.where(Project.workspace_id == workspace_id)
    project_status_result = await session.execute(project_status_stmt)
    project_status_counts = {row[0]: row[1] for row in project_status_result.all()}

    project_total_stmt = select(func.count(Project.id)).where(
        Project.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_total_stmt = project_total_stmt.where(Project.workspace_id == workspace_id)
    project_total = (await session.execute(project_total_stmt)).scalar_one() or 0

    # Quotation Statistics
    quotation_status_stmt = (
        select(Quotation.status, func.count(Quotation.id).label("count"))
        .where(Quotation.workspace_id.in_(accessible_workspace_ids))
        .group_by(Quotation.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        quotation_status_stmt = quotation_status_stmt.where(Quotation.workspace_id == workspace_id)
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
    proposal_status_stmt = (
        select(Proposal.status, func.count(Proposal.id).label("count"))
        .where(Proposal.workspace_id.in_(accessible_workspace_ids))
        .group_by(Proposal.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        proposal_status_stmt = proposal_status_stmt.where(Proposal.workspace_id == workspace_id)
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

    # Client Statistics
    client_status_stmt = (
        select(Client.status, func.count(Client.id).label("count"))
        .where(Client.workspace_id.in_(accessible_workspace_ids))
        .group_by(Client.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        client_status_stmt = client_status_stmt.where(Client.workspace_id == workspace_id)
    client_status_result = await session.execute(client_status_stmt)
    client_status_counts = {row[0]: row[1] for row in client_status_result.all()}

    client_total_stmt = select(func.count(Client.id)).where(
        Client.workspace_id.in_(accessible_workspace_ids)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        client_total_stmt = client_total_stmt.where(Client.workspace_id == workspace_id)
    client_total = (await session.execute(client_total_stmt)).scalar_one() or 0

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
        "clients": {
            "total": client_total,
            "byStatus": client_status_counts,
            "prospect": client_status_counts.get("prospect", 0),
            "active": client_status_counts.get("active", 0),
            "past": client_status_counts.get("past", 0),
        },
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


async def get_pipeline_data(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
) -> dict:
    """Get pipeline data grouped by status for scopes, projects, quotations, and proposals."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return {
            "scopes": {},
            "projects": {},
            "quotations": {},
            "proposals": {},
        }

    # Build workspace filter
    workspace_filter = (
        lambda stmt: stmt.where(Scope.workspace_id == workspace_id)
        if workspace_id and workspace_id in accessible_workspace_ids
        else stmt.where(Scope.workspace_id.in_(accessible_workspace_ids))
    )

    # Scope counts by status
    scope_status_stmt = (
        select(Scope.status, func.count(Scope.id).label("count"))
        .where(Scope.workspace_id.in_(accessible_workspace_ids))
        .group_by(Scope.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_status_stmt = scope_status_stmt.where(Scope.workspace_id == workspace_id)
    scope_status_result = await session.execute(scope_status_stmt)
    scope_counts = {row[0]: row[1] for row in scope_status_result.all()}

    # Project counts by status
    project_status_stmt = (
        select(Project.status, func.count(Project.id).label("count"))
        .where(Project.workspace_id.in_(accessible_workspace_ids))
        .group_by(Project.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_status_stmt = project_status_stmt.where(Project.workspace_id == workspace_id)
    project_status_result = await session.execute(project_status_stmt)
    project_counts = {row[0]: row[1] for row in project_status_result.all()}

    # Quotation counts by status
    quotation_status_stmt = (
        select(Quotation.status, func.count(Quotation.id).label("count"))
        .where(Quotation.workspace_id.in_(accessible_workspace_ids))
        .group_by(Quotation.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        quotation_status_stmt = quotation_status_stmt.where(Quotation.workspace_id == workspace_id)
    quotation_status_result = await session.execute(quotation_status_stmt)
    quotation_counts = {row[0]: row[1] for row in quotation_status_result.all()}

    # Proposal counts by status
    proposal_status_stmt = (
        select(Proposal.status, func.count(Proposal.id).label("count"))
        .where(Proposal.workspace_id.in_(accessible_workspace_ids))
        .group_by(Proposal.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        proposal_status_stmt = proposal_status_stmt.where(Proposal.workspace_id == workspace_id)
    proposal_status_result = await session.execute(proposal_status_stmt)
    proposal_counts = {row[0]: row[1] for row in proposal_status_result.all()}

    return {
        "scopes": {
            "draft": scope_counts.get("draft", 0),
            "in_review": scope_counts.get("in_review", 0),
            "approved": scope_counts.get("approved", 0),
            "completed": scope_counts.get("completed", 0),
        },
        "projects": {
            "planning": project_counts.get("planning", 0),
            "active": project_counts.get("active", 0),
            "on_hold": project_counts.get("on_hold", 0),
            "completed": project_counts.get("completed", 0),
        },
        "quotations": {
            "draft": quotation_counts.get("draft", 0),
            "pending": quotation_counts.get("pending", 0),
            "approved": quotation_counts.get("approved", 0),
            "rejected": quotation_counts.get("rejected", 0),
        },
        "proposals": {
            "draft": proposal_counts.get("draft", 0),
            "sent": proposal_counts.get("sent", 0),
            "viewed": proposal_counts.get("viewed", 0),
            "approved": proposal_counts.get("accepted", 0),  # Note: API uses "accepted" but response shows "approved"
        },
    }


async def get_recent_activity(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    limit: int = 10,
) -> dict:
    """Get recent activity items (scopes, projects, PRDs)."""
    from datetime import datetime, timezone

    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return {
            "scopes": [],
            "projects": [],
            "prds": [],
        }

    # Recent scopes
    scope_stmt = (
        select(Scope.id, Scope.title, Scope.status, Scope.updated_at)
        .where(Scope.workspace_id.in_(accessible_workspace_ids))
        .order_by(Scope.updated_at.desc())
        .limit(limit)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        scope_stmt = scope_stmt.where(Scope.workspace_id == workspace_id)
    scope_result = await session.execute(scope_stmt)
    recent_scopes = [
        {
            "id": str(row[0]),
            "title": row[1],
            "status": row[2],
            "updatedAt": row[3].isoformat() if row[3] else None,
        }
        for row in scope_result.all()
    ]

    # Recent projects
    project_stmt = (
        select(Project.id, Project.name, Project.status, Project.updated_at)
        .where(Project.workspace_id.in_(accessible_workspace_ids))
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_stmt = project_stmt.where(Project.workspace_id == workspace_id)
    project_result = await session.execute(project_stmt)
    recent_projects = [
        {
            "id": str(row[0]),
            "title": row[1],  # Using name as title
            "status": row[2],
            "updatedAt": row[3].isoformat() if row[3] else None,
        }
        for row in project_result.all()
    ]

    # Recent PRDs (PRD model doesn't exist yet, return empty list)
    # TODO: Implement when PRD model is created
    recent_prds = []

    return {
        "scopes": recent_scopes,
        "projects": recent_projects,
        "prds": recent_prds,
    }


async def get_urgent_items(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    days: int = 7,
) -> dict:
    """Get urgent items (PRDs with approaching due dates)."""
    from datetime import datetime, timedelta, timezone

    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return {
            "prds": [],
            "tasks": [],
        }

    # Urgent PRDs (PRD model doesn't exist yet, return empty list)
    # TODO: Implement when PRD model is created
    # This would query PRDs with due_date within the next `days` days
    urgent_prds = []

    # Tasks (placeholder - no task model exists yet)
    urgent_tasks = []

    return {
        "prds": urgent_prds,
        "tasks": urgent_tasks,
    }


async def get_active_clients(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    limit: int = 10,
) -> List[dict]:
    """Get active clients list for dashboard."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Get active clients
    client_stmt = (
        select(Client.id, Client.name, Client.logo_url, Client.status, Client.health_score, Client.city, Client.state, Client.country, Client.updated_at)
        .where(
            Client.workspace_id.in_(accessible_workspace_ids),
            Client.status == "active",
        )
        .order_by(Client.updated_at.desc())
        .limit(limit)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        client_stmt = client_stmt.where(Client.workspace_id == workspace_id)
    
    client_result = await session.execute(client_stmt)
    clients = [
        {
            "id": str(row[0]),
            "name": row[1],
            "logoUrl": row[2],
            "status": row[3],
            "healthScore": row[4],
            "city": row[5],
            "state": row[6],
            "country": row[7],
            "updatedAt": row[8].isoformat() if row[8] else None,
        }
        for row in client_result.all()
    ]
    
    return clients


async def get_active_projects(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    limit: int = 10,
) -> List[dict]:
    """Get active projects list for dashboard."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Get active projects
    project_stmt = (
        select(Project.id, Project.name, Project.status, Project.client_name, Project.updated_at)
        .where(
            Project.workspace_id.in_(accessible_workspace_ids),
            Project.status == "active",
        )
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        project_stmt = project_stmt.where(Project.workspace_id == workspace_id)
    
    project_result = await session.execute(project_stmt)
    projects = [
        {
            "id": str(row[0]),
            "name": row[1],
            "status": row[2],
            "clientName": row[3],
            "updatedAt": row[4].isoformat() if row[4] else None,
        }
        for row in project_result.all()
    ]
    
    return projects

