from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Template, WorkspaceMember


class TemplateNotFoundError(Exception):
    """Raised when a requested template does not exist."""


class TemplateAccessError(Exception):
    """Raised when a user attempts to access a template they do not have permission for."""


async def _check_workspace_access(
    session: AsyncSession, workspace_id: Optional[uuid.UUID], user_id: uuid.UUID
) -> bool:
    """Check if user has access to workspace (or if template is public/system)."""
    if workspace_id is None:
        # Public/system templates are accessible to all
        return True

    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_templates(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Template], int]:
    """List templates with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    # Build query - include public/system templates and user's workspace templates
    stmt: Select[Template] = select(Template).where(
        or_(
            Template.is_public == True,  # noqa: E712
            Template.is_system == True,  # noqa: E712
            Template.workspace_id.in_(accessible_workspace_ids),
        )
    )

    if workspace_id:
        if workspace_id in accessible_workspace_ids:
            stmt = stmt.where(
                or_(
                    Template.workspace_id == workspace_id,
                    Template.is_public == True,  # noqa: E712
                    Template.is_system == True,  # noqa: E712
                )
            )
        else:
            # User doesn't have access to this workspace, only show public/system
            stmt = stmt.where(
                or_(
                    Template.is_public == True,  # noqa: E712
                    Template.is_system == True,  # noqa: E712
                )
            )

    if type:
        stmt = stmt.where(Template.type == type)

    if category:
        stmt = stmt.where(Template.category == category)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Template.name.ilike(search_pattern),
                Template.description.ilike(search_pattern),
            )
        )

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Template.usage_count.desc(), Template.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    templates = list(result.scalars().all())

    return templates, total


async def get_template(
    session: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID
) -> Template:
    """Get a template by ID with access check."""
    stmt: Select[Template] = select(Template).where(Template.id == template_id)
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise TemplateNotFoundError("Template not found")

    # Check access: public/system templates are accessible, workspace templates need access
    if not template.is_public and not template.is_system:
        has_access = await _check_workspace_access(session, template.workspace_id, user_id)
        if not has_access:
            raise TemplateAccessError("Access denied")

    return template


async def create_template(
    session: AsyncSession, user_id: uuid.UUID, payload, workspace_id: Optional[uuid.UUID] = None
) -> Template:
    """Create a new template."""
    # If workspace_id provided, verify access
    if workspace_id:
        has_access = await _check_workspace_access(session, workspace_id, user_id)
        if not has_access:
            raise TemplateAccessError("Access denied")

    template = Template(
        workspace_id=workspace_id or payload.workspace_id,
        name=payload.name,
        description=payload.description,
        type=payload.type,
        category=payload.category,
        sections=payload.content,  # Map content to sections
        variables=payload.variables,
        is_public=False,
        is_system=False,
        created_by=user_id,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def update_template(
    session: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID, payload
) -> Template:
    """Update a template."""
    template = await get_template(session, template_id, user_id)

    # Only creator or workspace admin can update (system templates cannot be updated)
    if template.is_system:
        raise TemplateAccessError("System templates cannot be updated")

    if template.created_by != user_id:
        # Check if user is workspace admin
        if template.workspace_id:
            member_stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == template.workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
            )
            member_result = await session.execute(member_stmt)
            member = member_result.scalar_one_or_none()
            if not member or member.role not in ["owner", "admin"]:
                raise TemplateAccessError("Only template creator or workspace admin can update")

    if payload.name is not None:
        template.name = payload.name
    if payload.description is not None:
        template.description = payload.description
    if payload.category is not None:
        template.category = payload.category
    if payload.content is not None:
        template.sections = payload.content
    if payload.variables is not None:
        template.variables = payload.variables

    await session.commit()
    await session.refresh(template)
    return template


async def delete_template(session: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Delete a template."""
    template = await get_template(session, template_id, user_id)

    # System templates cannot be deleted
    if template.is_system:
        raise TemplateAccessError("System templates cannot be deleted")

    # Only creator or workspace admin can delete
    if template.created_by != user_id:
        if template.workspace_id:
            member_stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == template.workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
            )
            member_result = await session.execute(member_stmt)
            member = member_result.scalar_one_or_none()
            if not member or member.role not in ["owner", "admin"]:
                raise TemplateAccessError("Only template creator or workspace admin can delete")

    await session.delete(template)
    await session.commit()


async def clone_template(
    session: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID, workspace_id: Optional[uuid.UUID] = None
) -> Template:
    """Clone a template."""
    original = await get_template(session, template_id, user_id)

    # If workspace_id provided, verify access
    if workspace_id:
        has_access = await _check_workspace_access(session, workspace_id, user_id)
        if not has_access:
            raise TemplateAccessError("Access denied")

    new_template = Template(
        workspace_id=workspace_id or original.workspace_id,
        name=f"{original.name} (Copy)",
        description=original.description,
        type=original.type,
        category=original.category,
        sections=original.sections,
        table_columns=original.table_columns,
        variables=original.variables,
        is_public=False,
        is_system=False,
        created_by=user_id,
    )

    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)
    return new_template


async def get_popular_templates(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 10,
    type: Optional[str] = None,
) -> List[Template]:
    """Get popular templates (by usage count)."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    stmt: Select[Template] = select(Template).where(
        or_(
            Template.is_public == True,  # noqa: E712
            Template.is_system == True,  # noqa: E712
            Template.workspace_id.in_(accessible_workspace_ids),
        )
    )

    if type:
        stmt = stmt.where(Template.type == type)

    stmt = stmt.order_by(Template.usage_count.desc(), Template.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_template_categories(session: AsyncSession, user_id: uuid.UUID) -> List[str]:
    """Get all unique template categories."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    stmt = (
        select(Template.category)
        .where(
            or_(
                Template.is_public == True,  # noqa: E712
                Template.is_system == True,  # noqa: E712
                Template.workspace_id.in_(accessible_workspace_ids),
            ),
            Template.category.isnot(None),
        )
        .distinct()
        .order_by(Template.category)
    )

    result = await session.execute(stmt)
    categories = [row[0] for row in result.all() if row[0]]
    return categories
