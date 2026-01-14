from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Project, Scope, WorkspaceMember
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate
from app.services.workspaces import WorkspaceAccessError, WorkspaceNotFoundError


class ProjectNotFoundError(Exception):
    """Raised when a requested project does not exist."""


class ProjectAccessError(Exception):
    """Raised when a user attempts to access a project they do not have permission for."""


async def _check_workspace_access(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if user has access to workspace."""
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_projects(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    status: Optional[ProjectStatus] = None,
) -> List[Project]:
    """List projects with filters."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Build query
    stmt: Select[Project] = select(Project).where(Project.workspace_id.in_(accessible_workspace_ids))

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return []
        stmt = stmt.where(Project.workspace_id == workspace_id)

    if status:
        stmt = stmt.where(Project.status == status)

    stmt = stmt.order_by(Project.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_project(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, *, include_scopes: bool = False
) -> Project:
    """Get a project by ID with access check."""
    stmt: Select[Project] = select(Project).where(Project.id == project_id)

    if include_scopes:
        stmt = stmt.options(selectinload(Project.scopes))

    result = await session.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise ProjectNotFoundError("Project not found")

    # Check workspace access
    has_access = await _check_workspace_access(session, project.workspace_id, user_id)
    if not has_access:
        raise ProjectAccessError("Access denied")

    return project


async def create_project(
    session: AsyncSession, user_id: uuid.UUID, payload: ProjectCreate
) -> Project:
    """Create a new project."""
    # Check workspace access
    has_access = await _check_workspace_access(session, payload.workspace_id, user_id)
    if not has_access:
        raise ProjectAccessError("Access denied")

    project = Project(
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        client_name=payload.client_name,
        status=payload.status,
        created_by=user_id,
    )

    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def update_project(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, payload: ProjectUpdate
) -> Project:
    """Update a project."""
    project = await get_project(session, project_id, user_id, include_scopes=False)

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.client_name is not None:
        project.client_name = payload.client_name
    if payload.status is not None:
        project.status = payload.status

    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Delete a project."""
    project = await get_project(session, project_id, user_id, include_scopes=False)
    await session.delete(project)
    await session.commit()


async def update_project_status(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, status: str
) -> Project:
    """Update project status."""
    project = await get_project(session, project_id, user_id, include_scopes=False)
    project.status = status
    await session.commit()
    await session.refresh(project)
    return project


async def update_project_progress(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, progress: int
) -> Project:
    """Update project progress (0-100)."""
    if not 0 <= progress <= 100:
        raise ValueError("Progress must be between 0 and 100")
    project = await get_project(session, project_id, user_id, include_scopes=False)
    project.progress = progress
    await session.commit()
    await session.refresh(project)
    return project


async def assign_project_team(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, team: List[uuid.UUID]
) -> Project:
    """Assign team members to a project."""
    project = await get_project(session, project_id, user_id, include_scopes=False)
    
    # Validate that all team members have access to the workspace
    from app.models import User, WorkspaceMember
    workspace_members_stmt = select(WorkspaceMember.user_id).where(
        WorkspaceMember.workspace_id == project.workspace_id,
        WorkspaceMember.user_id.in_(team),
        WorkspaceMember.status == "active",
    )
    workspace_members_result = await session.execute(workspace_members_stmt)
    valid_user_ids = {row[0] for row in workspace_members_result.all()}
    
    invalid_user_ids = set(team) - valid_user_ids
    if invalid_user_ids:
        raise ValueError(
            f"Users {invalid_user_ids} do not have access to the workspace"
        )
    
    project.team = team
    await session.commit()
    await session.refresh(project)
    return project

