from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Favourite, Scope, ScopeSection, Workspace, WorkspaceMember
from app.schemas.scope import ScopeCreate, ScopeStatus, ScopeUpdate


class ScopeNotFoundError(Exception):
    """Raised when a requested scope does not exist."""


class ScopeAccessError(Exception):
    """Raised when a user attempts to access a scope they do not have permission for."""


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


async def list_scopes(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    status: Optional[ScopeStatus] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Scope], int]:
    """List scopes with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return [], 0

    # Build query
    stmt: Select[Scope] = select(Scope).where(Scope.workspace_id.in_(accessible_workspace_ids))

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return [], 0
        stmt = stmt.where(Scope.workspace_id == workspace_id)

    if project_id:
        stmt = stmt.where(Scope.project_id == project_id)

    if status:
        stmt = stmt.where(Scope.status == status)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Scope.title.ilike(search_pattern),
                Scope.description.ilike(search_pattern),
            )
        )

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Scope.updated_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    scopes = list(result.scalars().all())

    return scopes, total


async def get_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, *, include_sections: bool = True
) -> Scope:
    """Get a scope by ID with access check."""
    stmt: Select[Scope] = select(Scope).where(Scope.id == scope_id)

    if include_sections:
        stmt = stmt.options(selectinload(Scope.sections))

    result = await session.execute(stmt)
    scope = result.scalar_one_or_none()

    if scope is None:
        raise ScopeNotFoundError("Scope not found")

    # Check workspace access
    has_access = await _check_workspace_access(session, scope.workspace_id, user_id)
    if not has_access:
        raise ScopeAccessError("Access denied")

    return scope


async def create_scope(
    session: AsyncSession, user_id: uuid.UUID, payload: ScopeCreate
) -> Scope:
    """Create a new scope."""
    # Check workspace access
    has_access = await _check_workspace_access(session, payload.workspace_id, user_id)
    if not has_access:
        raise ScopeAccessError("Access denied")

    # If project_id is provided, verify it belongs to the workspace
    if payload.project_id:
        from app.models import Project

        project_stmt = select(Project).where(
            Project.id == payload.project_id,
            Project.workspace_id == payload.workspace_id,
        )
        project_result = await session.execute(project_stmt)
        if project_result.scalar_one_or_none() is None:
            raise ScopeAccessError("Project not found or does not belong to workspace")

    scope = Scope(
        workspace_id=payload.workspace_id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        progress=payload.progress,
        due_date=payload.due_date,
        created_by=user_id,
    )

    session.add(scope)
    await session.flush()
    await session.refresh(scope)

    # TODO: If template_id is provided, apply template sections

    return scope


async def update_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, payload: ScopeUpdate
) -> Scope:
    """Update a scope."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)

    if payload.title is not None:
        scope.title = payload.title
    if payload.description is not None:
        scope.description = payload.description
    if payload.status is not None:
        scope.status = payload.status
    if payload.progress is not None:
        scope.progress = payload.progress
    if payload.due_date is not None:
        scope.due_date = payload.due_date

    await session.commit()
    await session.refresh(scope)

    return scope


async def update_scope_status(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, status: ScopeStatus
) -> Scope:
    """Update scope status."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)
    scope.status = status
    await session.commit()
    await session.refresh(scope)
    return scope


async def delete_scope(session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Delete a scope."""
    scope = await get_scope(session, scope_id, user_id, include_sections=False)
    await session.delete(scope)
    await session.commit()


async def duplicate_scope(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Scope:
    """Duplicate a scope with all its sections."""
    original = await get_scope(session, scope_id, user_id, include_sections=True)

    # Create new scope
    new_scope = Scope(
        workspace_id=original.workspace_id,
        project_id=original.project_id,
        title=f"{original.title} (Copy)",
        description=original.description,
        status="draft",
        progress=0,
        due_date=original.due_date,
        created_by=user_id,
    )
    session.add(new_scope)
    await session.flush()
    await session.refresh(new_scope)

    # Copy sections
    for section in original.sections:
        new_section = ScopeSection(
            scope_id=new_scope.id,
            title=section.title,
            content=section.content,
            section_type=section.section_type,
            order_index=section.order_index,
            ai_generated=section.ai_generated,
            confidence_score=section.confidence_score,
        )
        session.add(new_section)

    await session.commit()
    await session.refresh(new_scope)

    # Reload with sections
    return await get_scope(session, new_scope.id, user_id, include_sections=True)


async def get_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Favourite]:
    """Get favourite record for scope and user."""
    stmt = select(Favourite).where(
        Favourite.scope_id == scope_id,
        Favourite.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> Favourite:
    """Add scope to user's favourites."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # Check if already favourited
    existing = await get_scope_favourite(session, scope_id, user_id)
    if existing:
        return existing

    favourite = Favourite(scope_id=scope_id, user_id=user_id)
    session.add(favourite)
    await session.commit()
    await session.refresh(favourite)
    return favourite


async def remove_scope_favourite(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Remove scope from user's favourites."""
    favourite = await get_scope_favourite(session, scope_id, user_id)
    if favourite:
        await session.delete(favourite)
        await session.commit()


# Scope Sections Service Functions


class ScopeSectionNotFoundError(Exception):
    """Raised when a requested scope section does not exist."""


async def list_scope_sections(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID
) -> List[ScopeSection]:
    """List all sections for a scope."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    stmt = (
        select(ScopeSection)
        .where(ScopeSection.scope_id == scope_id)
        .order_by(ScopeSection.order_index.asc(), ScopeSection.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_scope_section(
    session: AsyncSession,
    scope_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    content: Optional[str] = None,
    section_type: Optional[str] = None,
    order_index: Optional[int] = None,
) -> ScopeSection:
    """Create a new section for a scope."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # If order_index not provided, get the max and add 1
    if order_index is None:
        stmt = select(func.max(ScopeSection.order_index)).where(
            ScopeSection.scope_id == scope_id
        )
        result = await session.execute(stmt)
        max_order = result.scalar_one() or 0
        order_index = max_order + 1

    section = ScopeSection(
        scope_id=scope_id,
        title=title,
        content=content,
        section_type=section_type,
        order_index=order_index,
    )

    session.add(section)
    await session.commit()
    await session.refresh(section)
    return section


async def get_scope_section(
    session: AsyncSession, scope_id: uuid.UUID, section_id: uuid.UUID, user_id: uuid.UUID
) -> ScopeSection:
    """Get a scope section by ID."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    stmt = select(ScopeSection).where(
        ScopeSection.id == section_id,
        ScopeSection.scope_id == scope_id,
    )
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if section is None:
        raise ScopeSectionNotFoundError("Scope section not found")

    return section


async def update_scope_section(
    session: AsyncSession,
    scope_id: uuid.UUID,
    section_id: uuid.UUID,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    content: Optional[str] = None,
    order_index: Optional[int] = None,
) -> ScopeSection:
    """Update a scope section."""
    section = await get_scope_section(session, scope_id, section_id, user_id)

    if title is not None:
        section.title = title
    if content is not None:
        section.content = content
    if order_index is not None:
        section.order_index = order_index

    await session.commit()
    await session.refresh(section)
    return section


async def delete_scope_section(
    session: AsyncSession, scope_id: uuid.UUID, section_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a scope section."""
    section = await get_scope_section(session, scope_id, section_id, user_id)
    await session.delete(section)
    await session.commit()


async def reorder_scope_sections(
    session: AsyncSession, scope_id: uuid.UUID, user_id: uuid.UUID, section_ids: List[uuid.UUID]
) -> None:
    """Reorder scope sections."""
    # Verify scope access
    await get_scope(session, scope_id, user_id, include_sections=False)

    # Verify all sections belong to this scope
    stmt = select(ScopeSection).where(
        ScopeSection.scope_id == scope_id,
        ScopeSection.id.in_(section_ids),
    )
    result = await session.execute(stmt)
    sections = {s.id: s for s in result.scalars().all()}

    if len(sections) != len(section_ids):
        raise ScopeSectionNotFoundError("One or more sections not found")

    # Update order_index for each section
    for order, section_id in enumerate(section_ids):
        sections[section_id].order_index = order

    await session.commit()

