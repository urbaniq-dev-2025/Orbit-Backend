"""
Service for managing teams.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Team, TeamMember, User, WorkspaceMember
from app.core.logging import get_logger

logger = get_logger(__name__)


class TeamNotFoundError(Exception):
    """Raised when a team is not found."""


class TeamAccessError(Exception):
    """Raised when user doesn't have access to a team."""


async def list_teams(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> List[Team]:
    """
    List teams in a workspace that the user has access to.
    """
    # Verify user has access to workspace
    workspace_member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_member_result = await session.execute(workspace_member_stmt)
    if workspace_member_result.scalar_one_or_none() is None:
        raise TeamAccessError("User does not have access to this workspace")
    
    # Get teams in workspace
    teams_stmt = (
        select(Team)
        .where(Team.workspace_id == workspace_id)
        .options(selectinload(Team.members))
        .order_by(Team.created_at.desc())
    )
    
    result = await session.execute(teams_stmt)
    return list(result.scalars().all())


async def get_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[Team, Optional[str]]:
    """
    Get a team by ID.
    
    Returns:
        Tuple of (team, user_role_in_team)
    """
    team_stmt = (
        select(Team)
        .where(Team.id == team_id)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
    )
    team_result = await session.execute(team_stmt)
    team = team_result.scalar_one_or_none()
    
    if team is None:
        raise TeamNotFoundError(f"Team {team_id} not found")
    
    # Verify user has access to workspace
    workspace_member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == team.workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_member_result = await session.execute(workspace_member_stmt)
    if workspace_member_result.scalar_one_or_none() is None:
        raise TeamAccessError("User does not have access to this team's workspace")
    
    # Get user's role in team
    team_member_stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
    )
    team_member_result = await session.execute(team_member_stmt)
    team_member = team_member_result.scalar_one_or_none()
    user_role = team_member.role if team_member else None
    
    return team, user_role


async def create_team(
    session: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
) -> Team:
    """
    Create a new team.
    """
    # Verify user has access to workspace
    workspace_member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_member_result = await session.execute(workspace_member_stmt)
    if workspace_member_result.scalar_one_or_none() is None:
        raise TeamAccessError("User does not have access to this workspace")
    
    # Create team
    team = Team(
        workspace_id=workspace_id,
        name=name,
        description=description,
        created_by=user_id,
    )
    session.add(team)
    await session.flush()
    
    # Add creator as owner
    team_member = TeamMember(
        team_id=team.id,
        user_id=user_id,
        role="owner",
    )
    session.add(team_member)
    
    await session.commit()
    await session.refresh(team)
    
    return team


async def update_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Team:
    """
    Update a team.
    Requires owner or admin role in team.
    """
    team, user_role = await get_team(session, team_id, user_id)
    
    if user_role not in {"owner", "admin"}:
        raise TeamAccessError("Insufficient permissions to update team")
    
    if name is not None:
        team.name = name
    if description is not None:
        team.description = description
    
    await session.commit()
    await session.refresh(team)
    
    return team


async def delete_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """
    Delete a team.
    Requires owner role in team.
    """
    team, user_role = await get_team(session, team_id, user_id)
    
    if user_role != "owner":
        raise TeamAccessError("Only team owner can delete the team")
    
    await session.delete(team)
    await session.commit()


async def get_team_members(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> List[TeamMember]:
    """
    Get members of a team.
    """
    team, _ = await get_team(session, team_id, user_id)
    
    members_stmt = (
        select(TeamMember)
        .where(TeamMember.team_id == team_id)
        .options(selectinload(TeamMember.user))
        .order_by(TeamMember.joined_at.asc())
    )
    
    result = await session.execute(members_stmt)
    return list(result.scalars().all())


async def add_team_member(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    member_user_id: uuid.UUID,
    role: str = "member",
) -> TeamMember:
    """
    Add a member to a team.
    Requires owner or admin role in team.
    """
    team, user_role = await get_team(session, team_id, user_id)
    
    if user_role not in {"owner", "admin"}:
        raise TeamAccessError("Insufficient permissions to add team members")
    
    # Check if member already exists
    existing_stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == member_user_id,
    )
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise ValueError("User is already a member of this team")
    
    # Verify member has access to workspace
    workspace_member_stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == team.workspace_id,
        WorkspaceMember.user_id == member_user_id,
        WorkspaceMember.status == "active",
    )
    workspace_member_result = await session.execute(workspace_member_stmt)
    if workspace_member_result.scalar_one_or_none() is None:
        raise ValueError("User does not have access to this workspace")
    
    # Add member
    team_member = TeamMember(
        team_id=team_id,
        user_id=member_user_id,
        role=role,
    )
    session.add(team_member)
    await session.commit()
    await session.refresh(team_member)
    
    return team_member


async def update_team_member_role(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
    role: str,
) -> TeamMember:
    """
    Update a team member's role.
    Requires owner or admin role in team.
    """
    team, user_role = await get_team(session, team_id, user_id)
    
    if user_role not in {"owner", "admin"}:
        raise TeamAccessError("Insufficient permissions to update team member roles")
    
    # Get member
    member_stmt = select(TeamMember).where(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id,
    )
    member_result = await session.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    
    if member is None:
        raise TeamNotFoundError("Team member not found")
    
    # Prevent changing owner role (only owner can change owner)
    if member.role == "owner" and user_role != "owner":
        raise TeamAccessError("Only team owner can change owner role")
    
    member.role = role
    await session.commit()
    await session.refresh(member)
    
    return member


async def remove_team_member(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    """
    Remove a member from a team.
    Requires owner or admin role in team.
    """
    team, user_role = await get_team(session, team_id, user_id)
    
    if user_role not in {"owner", "admin"}:
        raise TeamAccessError("Insufficient permissions to remove team members")
    
    # Get member
    member_stmt = select(TeamMember).where(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id,
    )
    member_result = await session.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    
    if member is None:
        raise TeamNotFoundError("Team member not found")
    
    # Prevent removing owner
    if member.role == "owner":
        raise ValueError("Cannot remove team owner")
    
    await session.delete(member)
    await session.commit()
