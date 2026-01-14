from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Workspace, WorkspaceMember
from app.utils.slugify import slugify


DEFAULT_BRAND_COLOR = "#ff6b35"
DEFAULT_SECONDARY_COLOR = "#1a1a1a"
DEFAULT_DATA_HANDLING = "standard"


class WorkspaceAccessError(Exception):
    """Raised when a user attempts to access a workspace they do not belong to."""


class WorkspaceNotFoundError(Exception):
    """Raised when a requested workspace does not exist."""


@dataclass
class WorkspaceListing:
    workspace: Workspace
    role: str


async def _generate_unique_slug(session: AsyncSession, name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 2

    while True:
        stmt: Select[Workspace] = select(Workspace).where(Workspace.slug == slug)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def list_user_workspaces(session: AsyncSession, user_id: uuid.UUID) -> list[WorkspaceListing]:
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == "active",
        )
        .order_by(Workspace.created_at.desc())
    )
    result = await session.execute(stmt)
    listings = [WorkspaceListing(workspace=workspace, role=role) for workspace, role in result.all()]
    return listings


async def create_workspace(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    website_url: Optional[str] = None,
    team_size: Optional[str] = None,
    data_handling: Optional[str] = None,
) -> Workspace:
    slug = await _generate_unique_slug(session, name)
    workspace = Workspace(
        name=name,
        slug=slug,
        owner_id=owner_id,
        logo_url=logo_url,
        brand_color=brand_color or DEFAULT_BRAND_COLOR,
        secondary_color=secondary_color or DEFAULT_SECONDARY_COLOR,
        website_url=website_url,
        team_size=team_size,
        data_handling=data_handling or DEFAULT_DATA_HANDLING,
    )

    membership = WorkspaceMember(
        workspace=workspace,
        user_id=owner_id,
        role="owner",
        status="active",
        joined_at=dt.datetime.now(dt.timezone.utc),
        invited_email=None,
        invited_at=None,
    )
    session.add(workspace)
    session.add(membership)
    await session.commit()
    await session.refresh(workspace)
    return workspace


async def get_workspace_for_user(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    include_members: bool = False,
) -> tuple[Workspace, WorkspaceMember]:
    options: list = []
    if include_members:
        options.append(selectinload(Workspace.members).selectinload(WorkspaceMember.user))

    stmt = select(Workspace).where(Workspace.id == workspace_id).options(*options)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceNotFoundError

    membership_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    membership_result = await session.execute(membership_stmt)
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise WorkspaceAccessError

    return workspace, membership


async def update_workspace(
    session: AsyncSession,
    workspace: Workspace,
    *,
    name: Optional[str] = None,
    logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    website_url: Optional[str] = None,
    team_size: Optional[str] = None,
    data_handling: Optional[str] = None,
) -> Workspace:
    if name and name != workspace.name:
        workspace.name = name
        workspace.slug = await _generate_unique_slug(session, name)
    if logo_url is not None:
        workspace.logo_url = logo_url
    if brand_color is not None:
        workspace.brand_color = brand_color
    if secondary_color is not None:
        workspace.secondary_color = secondary_color
    if website_url is not None:
        workspace.website_url = website_url
    if team_size is not None:
        workspace.team_size = team_size
    if data_handling is not None:
        workspace.data_handling = data_handling

    workspace.updated_at = dt.datetime.now(dt.timezone.utc)
    await session.commit()
    await session.refresh(workspace)
    return workspace


async def delete_workspace(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a workspace. Only the owner can delete."""
    workspace, membership = await get_workspace_for_user(session, workspace_id, user_id)
    if membership.role != "owner":
        raise WorkspaceAccessError("Only the workspace owner can delete the workspace")
    await session.delete(workspace)
    await session.commit()


async def invite_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    email: str,
    role: str = "member",
    message: Optional[str] = None,
) -> WorkspaceMember:
    """Invite a member to a workspace."""
    workspace, membership = await get_workspace_for_user(session, workspace_id, user_id)
    if membership.role not in {"owner", "admin"}:
        raise WorkspaceAccessError("Only owners and admins can invite members")

    # Check if user already exists
    from app.models import User
    user_stmt = select(User).where(User.email == email.lower())
    user_result = await session.execute(user_stmt)
    existing_user = user_result.scalar_one_or_none()

    # Check if membership already exists
    if existing_user:
        member_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == existing_user.id,
        )
        member_result = await session.execute(member_stmt)
        existing_member = member_result.scalar_one_or_none()
        if existing_member:
            raise ValueError("User is already a member of this workspace")

    # Check if invitation already exists
    invite_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.invited_email == email.lower(),
        WorkspaceMember.user_id.is_(None),
    )
    invite_result = await session.execute(invite_stmt)
    existing_invite = invite_result.scalar_one_or_none()

    if existing_invite:
        # Update existing invitation
        existing_invite.role = role
        existing_invite.invited_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        await session.refresh(existing_invite)
        return existing_invite

    # Create new invitation
    now = dt.datetime.now(dt.timezone.utc)
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=existing_user.id if existing_user else None,
        invited_email=email.lower() if not existing_user else None,
        role=role,
        status="pending" if not existing_user else "active",
        invited_at=now if not existing_user else None,
        joined_at=now if existing_user else None,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def list_workspace_members(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[WorkspaceMember]:
    """List all members of a workspace."""
    workspace, membership = await get_workspace_for_user(session, workspace_id, user_id)
    stmt = (
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .options(selectinload(WorkspaceMember.user))
        .order_by(WorkspaceMember.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_member_role(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    role: str,
) -> WorkspaceMember:
    """Update a member's role."""
    workspace, membership = await get_workspace_for_user(session, workspace_id, user_id)
    if membership.role not in {"owner", "admin"}:
        raise WorkspaceAccessError("Only owners and admins can update member roles")

    # Cannot change owner role
    if role == "owner" and membership.role != "owner":
        raise WorkspaceAccessError("Only the current owner can assign owner role")

    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id,
    )
    member_result = await session.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    if member is None:
        raise WorkspaceNotFoundError("Member not found")

    # Cannot change owner's role
    if member.role == "owner" and role != "owner":
        raise WorkspaceAccessError("Cannot change owner's role")

    member.role = role
    await session.commit()
    await session.refresh(member)
    return member


async def remove_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Remove a member from a workspace."""
    workspace, membership = await get_workspace_for_user(session, workspace_id, user_id)
    if membership.role not in {"owner", "admin"}:
        raise WorkspaceAccessError("Only owners and admins can remove members")

    member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id,
    )
    member_result = await session.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    if member is None:
        raise WorkspaceNotFoundError("Member not found")

    # Cannot remove owner
    if member.role == "owner":
        raise WorkspaceAccessError("Cannot remove workspace owner")

    # Cannot remove yourself if you're the only admin/owner
    if member.user_id == user_id and membership.role in {"owner", "admin"}:
        admin_count_stmt = select(func.count()).select_from(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role.in_({"owner", "admin"}),
            WorkspaceMember.status == "active",
        )
        admin_count_result = await session.execute(admin_count_stmt)
        admin_count = admin_count_result.scalar_one()
        if admin_count <= 1:
            raise WorkspaceAccessError("Cannot remove the last admin/owner")

    await session.delete(member)
    await session.commit()

