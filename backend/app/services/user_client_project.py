"""
Service functions for managing user relationships with clients and projects.
Provides helper functions to get user's accessible clients and projects.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Client, Project, WorkspaceMember


async def get_user_accessible_clients(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
) -> List[Client]:
    """
    Get all clients accessible to a user.
    
    A user can access clients if:
    - The client belongs to a workspace the user is a member of
    """
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    if workspace_id:
        workspace_stmt = workspace_stmt.where(WorkspaceMember.workspace_id == workspace_id)
    
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Get clients from accessible workspaces
    client_stmt = (
        select(Client)
        .where(Client.workspace_id.in_(accessible_workspace_ids))
        .order_by(Client.name.asc())
    )
    
    result = await session.execute(client_stmt)
    return list(result.scalars().all())


async def get_user_accessible_projects(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
) -> List[Project]:
    """
    Get all projects accessible to a user.
    
    A user can access projects if:
    - The project belongs to a workspace the user is a member of
    - Optionally filtered by client_id
    """
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    if workspace_id:
        workspace_stmt = workspace_stmt.where(WorkspaceMember.workspace_id == workspace_id)
    
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Get projects from accessible workspaces
    project_stmt = (
        select(Project)
        .where(Project.workspace_id.in_(accessible_workspace_ids))
        .options(selectinload(Project.client))
    )
    
    if client_id:
        project_stmt = project_stmt.where(Project.client_id == client_id)
    
    project_stmt = project_stmt.order_by(Project.name.asc())
    
    result = await session.execute(project_stmt)
    return list(result.scalars().all())


async def get_client_projects_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Tuple[List[Project], bool]:
    """
    Get projects for a specific client that the user can access.
    
    Returns:
        Tuple of (projects list, has_access)
    """
    # Verify user has access to the client's workspace
    client_stmt = select(Client).where(Client.id == client_id)
    client_result = await session.execute(client_stmt)
    client = client_result.scalar_one_or_none()
    
    if client is None:
        return [], False
    
    # Check workspace access
    workspace_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == client.workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    has_access = workspace_result.scalar_one_or_none() is not None
    
    if not has_access:
        return [], False
    
    # Get projects for this client
    project_stmt = (
        select(Project)
        .where(
            Project.client_id == client_id,
            Project.workspace_id == client.workspace_id,
        )
        .order_by(Project.name.asc())
    )
    
    result = await session.execute(project_stmt)
    projects = list(result.scalars().all())
    
    return projects, True


async def get_user_clients_with_project_counts(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    """
    Get clients accessible to user with project and scope counts.
    
    Returns list of dicts with:
    - client: Client object
    - project_count: Number of projects for this client
    - scope_count: Number of scopes across all projects for this client
    """
    from sqlalchemy import func
    from app.models import Scope
    
    clients = await get_user_accessible_clients(session, user_id, workspace_id=workspace_id)
    
    result = []
    for client in clients:
        # Count projects
        project_count_stmt = select(func.count(Project.id)).where(
            Project.client_id == client.id
        )
        project_count_result = await session.execute(project_count_stmt)
        project_count = project_count_result.scalar_one() or 0
        
        # Count scopes (via projects)
        if project_count > 0:
            project_ids_stmt = select(Project.id).where(Project.client_id == client.id)
            project_ids_result = await session.execute(project_ids_stmt)
            project_ids = [row[0] for row in project_ids_result.all()]
            
            scope_count_stmt = select(func.count(Scope.id)).where(
                Scope.project_id.in_(project_ids)
            )
            scope_count_result = await session.execute(scope_count_stmt)
            scope_count = scope_count_result.scalar_one() or 0
        else:
            scope_count = 0
        
        result.append({
            "client": client,
            "project_count": project_count,
            "scope_count": scope_count,
        })
    
    return result
