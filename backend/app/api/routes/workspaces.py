from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.models import WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceDetail,
    WorkspaceMemberPublic,
    WorkspaceMemberStatus,
    WorkspaceRole,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)
from app.services import workspaces as workspace_service

router = APIRouter()


@router.get("", response_model=List[WorkspaceSummary])
async def list_workspaces(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> List[WorkspaceSummary]:
    listings = await workspace_service.list_user_workspaces(session, current_user.id)
    return [WorkspaceSummary.from_listing(entry.workspace, entry.role) for entry in listings]


@router.post("", response_model=WorkspaceDetail, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> WorkspaceDetail:
    workspace = await workspace_service.create_workspace(
        session,
        owner_id=current_user.id,
        name=payload.name,
        logo_url=str(payload.logo_url) if payload.logo_url else None,
        brand_color=payload.primary_color,
        secondary_color=payload.secondary_color,
        website_url=str(payload.website_url) if payload.website_url else None,
        team_size=payload.team_size,
        data_handling=payload.data_handling,
    )
    # owner membership fetched separately
    _, membership = await workspace_service.get_workspace_for_user(
        session, workspace.id, current_user.id, include_members=True
    )
    return _build_workspace_detail(workspace, membership, include_members=True)


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
async def get_workspace(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    include_members: bool = Query(
        False, alias="includeMembers", description="Include member roster in the payload"
    ),
    current_user=Depends(deps.get_current_user),
) -> WorkspaceDetail:
    try:
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=include_members
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _build_workspace_detail(workspace, membership, include_members=include_members)


@router.put("/{workspace_id}", response_model=WorkspaceDetail)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdateRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> WorkspaceDetail:
    try:
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if membership.role not in {WorkspaceRole.owner.value, WorkspaceRole.admin.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    workspace = await workspace_service.update_workspace(
        session,
        workspace,
        name=payload.name,
        logo_url=str(payload.logo_url) if payload.logo_url else None,
        brand_color=payload.primary_color,
        secondary_color=payload.secondary_color,
        website_url=str(payload.website_url) if payload.website_url else None,
    )

    return _build_workspace_detail(workspace, membership, include_members=False)


def _build_workspace_detail(
    workspace,
    membership: WorkspaceMember,
    *,
    include_members: bool,
) -> WorkspaceDetail:
    members_payload: Optional[List[WorkspaceMemberPublic]] = None
    if include_members:
        members_payload = []
        for member in workspace.members:
            user = member.user
            members_payload.append(
                WorkspaceMemberPublic(
                    id=member.id,
                    role=WorkspaceRole(member.role),
                    status=WorkspaceMemberStatus(member.status),
                    email=getattr(user, "email", None),
                    full_name=getattr(user, "full_name", None),
                    invited_email=member.invited_email,
                    invited_at=member.invited_at,
                    joined_at=member.joined_at,
                )
            )

    return WorkspaceDetail(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        logo_url=workspace.logo_url,
        brand_color=workspace.brand_color,
        secondary_color=workspace.secondary_color,
        website_url=workspace.website_url,
        team_size=workspace.team_size,
        data_handling=workspace.data_handling,
        role=WorkspaceRole(membership.role),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        members=members_payload,
    )


