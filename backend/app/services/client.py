from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Client, Project, Scope, WorkspaceMember
from app.schemas.client import ClientCreate, ClientUpdate


async def list_clients(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Client], int]:
    """List clients with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return [], 0

    # Build base query
    base_stmt = select(Client).where(Client.workspace_id.in_(accessible_workspace_ids))

    # Apply workspace filter
    if workspace_id and workspace_id in accessible_workspace_ids:
        base_stmt = base_stmt.where(Client.workspace_id == workspace_id)

    # Apply status filter
    if status and status in ["prospect", "active", "past"]:
        base_stmt = base_stmt.where(Client.status == status)

    # Apply search filter
    if search:
        search_pattern = f"%{search.lower()}%"
        base_stmt = base_stmt.where(
            or_(
                Client.name.ilike(search_pattern),
                Client.industry.ilike(search_pattern),
                Client.contact_name.ilike(search_pattern),
                Client.contact_email.ilike(search_pattern),
            )
        )

    # Get total count
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    base_stmt = base_stmt.order_by(Client.updated_at.desc()).limit(page_size).offset(offset)

    # Execute query
    result = await session.execute(base_stmt)
    clients = result.scalars().all()

    return clients, total


class ClientNotFoundError(Exception):
    """Raised when a client is not found."""

    pass


class ClientAccessError(Exception):
    """Raised when user doesn't have access to a client."""

    pass


async def _check_workspace_access(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if user has access to a workspace."""
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_client(
    session: AsyncSession, client_id: uuid.UUID, user_id: uuid.UUID
) -> Client:
    """Get a client by ID with access check."""
    stmt = select(Client).where(Client.id == client_id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise ClientNotFoundError("Client not found")

    # Check workspace access
    if not await _check_workspace_access(session, client.workspace_id, user_id):
        raise ClientAccessError("Access denied")

    return client


async def create_client(
    session: AsyncSession, user_id: uuid.UUID, payload: ClientCreate
) -> Client:
    """Create a new client."""
    # Check workspace access
    if not await _check_workspace_access(session, payload.workspace_id, user_id):
        raise ClientAccessError("Access denied to workspace")

    # Check for duplicate email in workspace
    existing_stmt = select(Client).where(
        Client.workspace_id == payload.workspace_id,
        Client.contact_email == payload.contact_email,
    )
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise ValueError("Client with this email already exists in this workspace")

    client = Client(
        workspace_id=payload.workspace_id,
        name=payload.name,
        industry=payload.industry,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        status=payload.status,
        source=payload.source,
        notes=payload.notes,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        company_size=payload.company_size,
        health_score=50,  # Default health score
    )

    session.add(client)
    await session.commit()
    await session.refresh(client)

    return client


async def update_client(
    session: AsyncSession, client_id: uuid.UUID, user_id: uuid.UUID, payload: ClientUpdate
) -> Client:
    """Update an existing client."""
    client = await get_client(session, client_id, user_id)

    # Update fields if provided
    if payload.name is not None:
        client.name = payload.name
    if payload.industry is not None:
        client.industry = payload.industry
    if payload.contact_name is not None:
        client.contact_name = payload.contact_name
    if payload.contact_email is not None:
        # Check for duplicate email in workspace
        existing_stmt = select(Client).where(
            Client.workspace_id == client.workspace_id,
            Client.contact_email == payload.contact_email,
            Client.id != client_id,
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise ValueError("Client with this email already exists in this workspace")
        client.contact_email = payload.contact_email
    if payload.contact_phone is not None:
        client.contact_phone = payload.contact_phone
    if payload.status is not None:
        client.status = payload.status
    if payload.health_score is not None:
        client.health_score = payload.health_score
    if payload.source is not None:
        client.source = payload.source
    if payload.notes is not None:
        client.notes = payload.notes
    if payload.city is not None:
        client.city = payload.city
    if payload.state is not None:
        client.state = payload.state
    if payload.country is not None:
        client.country = payload.country
    if payload.company_size is not None:
        client.company_size = payload.company_size

    await session.commit()
    await session.refresh(client)

    return client


async def delete_client(
    session: AsyncSession, client_id: uuid.UUID, user_id: uuid.UUID, soft_delete: bool = True
) -> None:
    """Delete a client (soft delete by default)."""
    client = await get_client(session, client_id, user_id)

    if soft_delete:
        # Soft delete: set status to 'past' and add deleted_at timestamp
        # Note: deleted_at field needs to be added to model if not present
        client.status = "past"
        # TODO: Add deleted_at field to model if needed
    else:
        # Hard delete: check for related projects/scopes first
        # Check for projects using client_id (preferred) or client_name (backward compatibility)
        project_stmt = select(func.count(Project.id)).where(
            (Project.client_id == client_id) | 
            (
                (Project.client_id.is_(None)) & 
                (Project.workspace_id == client.workspace_id) & 
                (Project.client_name == client.name)
            )
        )
        project_result = await session.execute(project_stmt)
        project_count = project_result.scalar_one() or 0

        if project_count > 0:
            raise ValueError(
                f"Cannot delete client: {project_count} project(s) are associated with this client"
            )

        await session.delete(client)

    await session.commit()


async def get_client_stats(
    session: AsyncSession, user_id: uuid.UUID, *, workspace_id: Optional[uuid.UUID] = None
) -> dict:
    """Get client statistics."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return {
            "total_clients": 0,
            "active_clients": 0,
            "prospect_clients": 0,
            "past_clients": 0,
            "avg_health_score": 0.0,
        }

    # Build base query
    base_stmt = select(Client).where(Client.workspace_id.in_(accessible_workspace_ids))
    if workspace_id and workspace_id in accessible_workspace_ids:
        base_stmt = base_stmt.where(Client.workspace_id == workspace_id)

    # Total clients
    total_stmt = select(func.count(Client.id)).select_from(base_stmt.subquery())
    total_result = await session.execute(total_stmt)
    total_clients = total_result.scalar_one() or 0

    # Clients by status
    status_stmt = (
        select(Client.status, func.count(Client.id).label("count"))
        .where(Client.workspace_id.in_(accessible_workspace_ids))
        .group_by(Client.status)
    )
    if workspace_id and workspace_id in accessible_workspace_ids:
        status_stmt = status_stmt.where(Client.workspace_id == workspace_id)
    status_result = await session.execute(status_stmt)
    status_counts = {row[0]: row[1] for row in status_result.all()}

    # Average health score
    avg_stmt = select(func.avg(Client.health_score)).select_from(base_stmt.subquery())
    avg_result = await session.execute(avg_stmt)
    avg_health_score = float(avg_result.scalar_one() or 0)

    return {
        "total_clients": total_clients,
        "active_clients": status_counts.get("active", 0),
        "prospect_clients": status_counts.get("prospect", 0),
        "past_clients": status_counts.get("past", 0),
        "avg_health_score": round(avg_health_score, 2),
    }


async def get_client_projects(
    session: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    limit: int = 10,
) -> Tuple[List[Project], int]:
    """Get projects associated with a client."""
    client = await get_client(session, client_id, user_id)

    # Use client_id for direct relationship (preferred)
    # Fallback to client_name for backward compatibility with old projects
    project_stmt = (
        select(Project)
        .where(
            (Project.client_id == client_id) | 
            (
                (Project.client_id.is_(None)) & 
                (Project.workspace_id == client.workspace_id) & 
                (Project.client_name == client.name)
            )
        )
        .order_by(Project.updated_at.desc())
    )

    # Get total count
    count_stmt = select(func.count(Project.id)).where(
        (Project.client_id == client_id) | 
        (
            (Project.client_id.is_(None)) & 
            (Project.workspace_id == client.workspace_id) & 
            (Project.client_name == client.name)
        )
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one() or 0

    # Apply limit
    project_stmt = project_stmt.limit(limit)

    result = await session.execute(project_stmt)
    projects = result.scalars().all()

    return projects, total


async def get_client_scopes(
    session: AsyncSession,
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    limit: int = 10,
) -> Tuple[List[Scope], int]:
    """Get scopes associated with a client (via projects)."""
    client = await get_client(session, client_id, user_id)

    # Get projects for this client using client_id (preferred) or client_name (backward compatibility)
    projects_stmt = select(Project.id).where(
        (Project.client_id == client_id) | 
        (
            (Project.client_id.is_(None)) & 
            (Project.workspace_id == client.workspace_id) & 
            (Project.client_name == client.name)
        )
    )
    projects_result = await session.execute(projects_stmt)
    project_ids = [row[0] for row in projects_result.all()]

    if not project_ids:
        return [], 0

    # Get scopes for these projects with project relationship loaded
    scope_stmt = (
        select(Scope)
        .where(Scope.project_id.in_(project_ids))
        .options(selectinload(Scope.project))
        .order_by(Scope.updated_at.desc())
    )

    # Get total count
    count_stmt = select(func.count(Scope.id)).where(Scope.project_id.in_(project_ids))
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one() or 0

    # Apply limit
    scope_stmt = scope_stmt.limit(limit)

    result = await session.execute(scope_stmt)
    scopes = result.scalars().all()

    return scopes, total


async def update_client_logo(
    session: AsyncSession, client_id: uuid.UUID, user_id: uuid.UUID, logo_url: str
) -> Client:
    """Update client logo URL."""
    client = await get_client(session, client_id, user_id)
    client.logo_url = logo_url
    await session.commit()
    await session.refresh(client)
    return client


def _compute_location(city: Optional[str], state: Optional[str], country: Optional[str]) -> Optional[str]:
    """Compute location string from city, state, country."""
    parts = []
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    if country:
        parts.append(country)
    return ", ".join(parts) if parts else None


async def _get_client_project_count(
    session: AsyncSession, client: Client
) -> int:
    """Get project count for a client."""
    # Use client_id for direct relationship (preferred)
    # Fallback to client_name for backward compatibility
    stmt = select(func.count(Project.id)).where(
        (Project.client_id == client.id) | 
        (
            (Project.client_id.is_(None)) & 
            (Project.workspace_id == client.workspace_id) & 
            (Project.client_name == client.name)
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one() or 0


async def _get_client_scope_count(
    session: AsyncSession, client: Client
) -> int:
    """Get scope count for a client."""
    # Get project IDs for this client using client_id (preferred) or client_name (backward compatibility)
    projects_stmt = select(Project.id).where(
        (Project.client_id == client.id) | 
        (
            (Project.client_id.is_(None)) & 
            (Project.workspace_id == client.workspace_id) & 
            (Project.client_name == client.name)
        )
    )
    projects_result = await session.execute(projects_stmt)
    project_ids = [row[0] for row in projects_result.all()]

    if not project_ids:
        return 0

    # Count scopes for these projects
    stmt = select(func.count(Scope.id)).where(Scope.project_id.in_(project_ids))
    result = await session.execute(stmt)
    return result.scalar_one() or 0
