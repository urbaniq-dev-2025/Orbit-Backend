from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import Select, select
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


