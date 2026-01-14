from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api import deps
from app.models import WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceDetail,
    WorkspaceInviteRequest,
    WorkspaceInviteResponse,
    WorkspaceMemberPublic,
    WorkspaceMemberStatus,
    WorkspaceMemberUpdateRequest,
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


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a workspace."""
    try:
        await workspace_service.delete_workspace(session, workspace_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{workspace_id}/invite", response_model=WorkspaceInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceInviteRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> WorkspaceInviteResponse:
    """Invite a team member to the workspace."""
    try:
        member = await workspace_service.invite_member(
            session,
            workspace_id,
            current_user.id,
            email=payload.email,
            role=payload.role.value,
            message=payload.message,
        )
        return WorkspaceInviteResponse(
            id=member.id,
            email=member.invited_email or (member.user.email if member.user else None),
            role=WorkspaceRole(member.role),
            status=WorkspaceMemberStatus(member.status),
            invited_at=member.invited_at,
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberPublic])
async def list_members(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> List[WorkspaceMemberPublic]:
    """List all members of a workspace."""
    try:
        members = await workspace_service.list_workspace_members(
            session, workspace_id, current_user.id
        )
        return [
            WorkspaceMemberPublic(
                id=m.id,
                role=WorkspaceRole(m.role),
                status=WorkspaceMemberStatus(m.status),
                email=m.user.email if m.user else None,
                full_name=m.user.full_name if m.user else None,
                invited_email=m.invited_email,
                invited_at=m.invited_at,
                joined_at=m.joined_at,
            )
            for m in members
        ]
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.put("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberPublic)
async def update_member_role(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: WorkspaceMemberUpdateRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> WorkspaceMemberPublic:
    """Update a member's role."""
    try:
        member = await workspace_service.update_member_role(
            session,
            workspace_id,
            member_id,
            current_user.id,
            role=payload.role.value,
        )
        return WorkspaceMemberPublic(
            id=member.id,
            role=WorkspaceRole(member.role),
            status=WorkspaceMemberStatus(member.status),
            email=member.user.email if member.user else None,
            full_name=member.user.full_name if member.user else None,
            invited_email=member.invited_email,
            invited_at=member.invited_at,
            joined_at=member.joined_at,
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or member not found")
    except workspace_service.WorkspaceAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Remove a member from the workspace."""
    try:
        await workspace_service.remove_member(session, workspace_id, member_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or member not found")
    except workspace_service.WorkspaceAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{workspace_id}/logo", status_code=status.HTTP_200_OK)
async def upload_logo(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> dict:
    """
    Upload workspace logo.
    Note: This is a placeholder. File upload implementation will be added
    when file upload infrastructure is ready.
    """
    try:
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id
        )
        if membership.role not in {WorkspaceRole.owner.value, WorkspaceRole.admin.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        # TODO: Implement actual file upload when file storage is ready
        return {"message": "Logo upload endpoint - implementation pending"}
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


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


