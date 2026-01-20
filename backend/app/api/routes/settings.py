"""
API routes for Settings page functionality.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api import deps
from app.core.logging import get_logger
from app.models import User
from app.schemas.settings import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    AvatarUploadResponse,
    BillingHistoryItem,
    BillingHistoryResponse,
    DataExportInclude,
    DataExportListResponse,
    DataExportRequest,
    DataExportResponse,
    DataExportStatusResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    EmailVerificationSendResponse,
    LoginActivityItem,
    NotificationPreferenceItem,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    PasswordChangeRequest,
    PasswordChangeResponse,
    SecurityStatusResponse,
    TeamCreate,
    TeamListResponse,
    TeamMemberAdd,
    TeamMemberItem,
    TeamMemberUpdate,
    TeamMembersResponse,
    TeamResponse,
    TeamUpdate,
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorEnableResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdate,
)
from app.services import avatar as avatar_service
from app.services import notifications as notification_service
from app.services import password as password_service

router = APIRouter()
logger = get_logger(__name__)


# Avatar Upload
@router.post("/auth/avatar", response_model=AvatarUploadResponse, status_code=status.HTTP_200_OK)
async def upload_avatar(
    session: deps.SessionDep,
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user),
) -> AvatarUploadResponse:
    """Upload user avatar."""
    try:
        avatar_url = await avatar_service.upload_avatar(file, current_user.id)
        
        # Update user's avatar_url
        current_user.avatar_url = avatar_url
        await session.commit()
        await session.refresh(current_user)
        
        return AvatarUploadResponse(avatar_url=avatar_url, message="Avatar uploaded successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        ) from e


# Password Change
@router.post("/auth/password/change", response_model=PasswordChangeResponse)
async def change_password(
    payload: PasswordChangeRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> PasswordChangeResponse:
    """Change user password."""
    try:
        # Validate passwords match
        if payload.new_password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match",
            )
        
        await password_service.change_password(
            session,
            current_user,
            payload.current_password,
            payload.new_password,
        )
        
        return PasswordChangeResponse(
            message="Password changed successfully",
            last_password_change=current_user.last_password_change or current_user.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to change password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        ) from e


# Notification Preferences
@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    session: deps.SessionDep,
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> NotificationPreferencesResponse:
    """Get notification preferences for current user."""
    try:
        preferences = await notification_service.get_notification_preferences(
            session, current_user.id, workspace_id
        )
        
        return NotificationPreferencesResponse(
            preferences=[
                NotificationPreferenceItem(**pref) for pref in preferences
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences",
        ) from e


@router.put("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdateRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> NotificationPreferencesResponse:
    """Update notification preferences for current user."""
    try:
        preferences_data = [
            {
                "id": pref.id,
                "enabled": pref.enabled,
                "channels": pref.channels,
            }
            for pref in payload.preferences
        ]
        
        updated_preferences = await notification_service.update_notification_preferences(
            session,
            current_user.id,
            payload.workspace_id,
            preferences_data,
        )
        
        return NotificationPreferencesResponse(
            preferences=[
                NotificationPreferenceItem(**pref) for pref in updated_preferences
            ]
        )
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences",
        ) from e


# Security Status
@router.get("/auth/security/status", response_model=SecurityStatusResponse)
async def get_security_status(
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> SecurityStatusResponse:
    """Get security status for current user."""
    try:
        from app.models import UserSession, LoginActivity
        from sqlalchemy import select, desc
        
        # Get active sessions
        sessions_stmt = (
            select(UserSession)
            .where(UserSession.user_id == current_user.id, UserSession.is_active == True)
            .order_by(desc(UserSession.last_active))
            .limit(10)
        )
        sessions_result = await db_session.execute(sessions_stmt)
        sessions = sessions_result.scalars().all()
        
        # Get recent login activity
        activity_stmt = (
            select(LoginActivity)
            .where(LoginActivity.user_id == current_user.id)
            .order_by(desc(LoginActivity.timestamp))
            .limit(10)
        )
        activity_result = await db_session.execute(activity_stmt)
        activities = activity_result.scalars().all()
        
        return SecurityStatusResponse(
            email_verified=current_user.email_verified,
            two_factor_enabled=current_user.two_factor_enabled,
            last_password_change=current_user.last_password_change,
            active_sessions=[
                {
                    "id": session.id,
                    "device": session.device,
                    "ip_address": session.ip_address,
                    "location": None,  # TODO: Add geolocation lookup
                    "last_active": session.last_active,
                    "current": False,  # TODO: Compare with current session
                }
                for session in sessions
            ],
            recent_login_activity=[
                {
                    "timestamp": activity.timestamp,
                    "ip_address": activity.ip_address,
                    "device": activity.user_agent,  # TODO: Parse user agent
                    "location": activity.location,
                    "success": activity.success,
                    "failure_reason": activity.failure_reason,
                }
                for activity in activities
            ],
        )
    except Exception as e:
        logger.error(f"Failed to get security status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security status",
        ) from e


# Sessions Management
@router.get("/auth/sessions", response_model=SecurityStatusResponse)
async def get_active_sessions(
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> SecurityStatusResponse:
    """Get active sessions for current user."""
    # Reuse security status endpoint logic
    return await get_security_status(session=session, current_user=current_user)


@router.delete("/auth/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Revoke a specific session."""
    try:
        from app.models import UserSession
        from sqlalchemy import select
        
        session_stmt = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
        session_result = await session.execute(session_stmt)
        user_session = session_result.scalar_one_or_none()
        
        if not user_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        
        user_session.is_active = False
        await session.commit()
        
        return {"message": "Session revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session",
        ) from e


@router.post("/auth/sessions/revoke-all", status_code=status.HTTP_200_OK)
async def revoke_all_sessions(
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Revoke all sessions except current one."""
    try:
        from app.models import UserSession
        from sqlalchemy import select, update
        
        # Revoke all sessions (current session will be handled by token expiration)
        update_stmt = (
            update(UserSession)
            .where(UserSession.user_id == current_user.id, UserSession.is_active == True)
            .values(is_active=False)
        )
        result = await session.execute(update_stmt)
        await session.commit()
        
        return {
            "message": "All other sessions revoked successfully",
            "revoked_count": result.rowcount,
        }
    except Exception as e:
        logger.error(f"Failed to revoke all sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions",
        ) from e


# Workspace Settings
@router.get("/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
async def get_workspace_settings_endpoint(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> WorkspaceSettingsResponse:
    """Get workspace settings."""
    try:
        from app.services import workspaces as workspace_service
        from app.services import workspace_settings as settings_service
        
        # Verify user has access to workspace
        await workspace_service.get_workspace_for_user(session, workspace_id, current_user.id, include_members=False)
        
        settings = await settings_service.get_workspace_settings(session, workspace_id)
        
        return WorkspaceSettingsResponse(
            workspace_mode=settings.workspace_mode,
            require_scope_approval=settings.require_scope_approval,
            require_prd_approval=settings.require_prd_approval,
            auto_create_project=settings.auto_create_project,
            default_engagement_type=settings.default_engagement_type,
            ai_assist_enabled=settings.ai_assist_enabled,
            ai_model_preference=settings.ai_model_preference,
            show_client_health=settings.show_client_health,
            default_currency=settings.default_currency,
            timezone=settings.timezone,
            date_format=settings.date_format,
            time_format=settings.time_format,
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to get workspace settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace settings",
        ) from e


@router.put("/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
async def update_workspace_settings_endpoint(
    workspace_id: uuid.UUID,
    payload: WorkspaceSettingsUpdate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> WorkspaceSettingsResponse:
    """Update workspace settings."""
    try:
        from app.services import workspaces as workspace_service
        from app.services import workspace_settings as settings_service
        
        # Verify user has access and is admin/owner
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
        
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Update settings
        update_data = payload.model_dump(exclude_unset=True)
        settings = await settings_service.update_workspace_settings(
            session, workspace_id, **update_data
        )
        
        return WorkspaceSettingsResponse(
            workspace_mode=settings.workspace_mode,
            require_scope_approval=settings.require_scope_approval,
            require_prd_approval=settings.require_prd_approval,
            auto_create_project=settings.auto_create_project,
            default_engagement_type=settings.default_engagement_type,
            ai_assist_enabled=settings.ai_assist_enabled,
            ai_model_preference=settings.ai_model_preference,
            show_client_health=settings.show_client_health,
            default_currency=settings.default_currency,
            timezone=settings.timezone,
            date_format=settings.date_format,
            time_format=settings.time_format,
        )
    except HTTPException:
        raise
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to update workspace settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace settings",
        ) from e


# Billing History
@router.get("/billing/history", response_model=BillingHistoryResponse)
async def get_billing_history(
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(deps.get_current_user),
) -> BillingHistoryResponse:
    """Get billing history for a workspace."""
    try:
        from app.models import BillingHistory
        from app.services import workspaces as workspace_service
        
        # Verify workspace access
        await workspace_service.get_workspace_for_user(session, workspace_id, current_user.id, include_members=False)
        
        # Get billing history
        stmt = (
            select(BillingHistory)
            .where(BillingHistory.workspace_id == workspace_id)
            .order_by(desc(BillingHistory.billing_date))
        )
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        result = await session.execute(stmt)
        history_items = result.scalars().all()
        
        return BillingHistoryResponse(
            history=[
                BillingHistoryItem(
                    id=item.id,
                    description=item.description,
                    amount=float(item.amount),
                    currency=item.currency,
                    status=item.status,
                    invoice_url=item.invoice_url,
                    billing_date=item.billing_date,
                    due_date=item.due_date,
                    paid_at=item.paid_at,
                    payment_method=None,  # TODO: Implement payment method lookup
                )
                for item in history_items
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )
    except workspace_service.WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except workspace_service.WorkspaceAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to get billing history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing history",
        ) from e


# Teams Management
@router.get("/teams", response_model=TeamListResponse)
async def list_teams(
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> TeamListResponse:
    """List teams in a workspace."""
    try:
        from app.services import teams as team_service
        
        teams = await team_service.list_teams(session, current_user.id, workspace_id)
        
        team_responses = []
        for team in teams:
            # Get member count
            member_count = len(team.members) if team.members else 0
            
            # Get user's role in team
            user_role = None
            for member in (team.members or []):
                if member.user_id == current_user.id:
                    user_role = member.role
                    break
            
            team_responses.append(
                TeamResponse(
                    id=team.id,
                    name=team.name,
                    description=team.description,
                    workspace_id=team.workspace_id,
                    member_count=member_count,
                    role=user_role,
                    created_at=team.created_at,
                    updated_at=team.updated_at,
                )
            )
        
        return TeamListResponse(teams=team_responses)
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to list teams: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teams",
        ) from e


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamResponse:
    """Create a new team."""
    try:
        from app.services import teams as team_service
        
        team = await team_service.create_team(
            session,
            current_user.id,
            payload.workspace_id,
            payload.name,
            payload.description,
        )
        
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            workspace_id=team.workspace_id,
            member_count=1,  # Creator is added as member
            role="owner",
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to create team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team",
        ) from e


@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamResponse:
    """Update a team."""
    try:
        from app.services import teams as team_service
        
        team = await team_service.update_team(
            session,
            team_id,
            current_user.id,
            payload.name,
            payload.description,
        )
        
        # Get member count and user role
        team, user_role = await team_service.get_team(session, team_id, current_user.id)
        member_count_stmt = select(func.count()).select_from(
            select(TeamMember).where(TeamMember.team_id == team_id).subquery()
        )
        member_count_result = await session.execute(member_count_stmt)
        member_count = member_count_result.scalar_one() or 0
        
        return TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            workspace_id=team.workspace_id,
            member_count=member_count,
            role=user_role,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to update team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team",
        ) from e


@router.delete("/teams/{team_id}", status_code=status.HTTP_200_OK)
async def delete_team(
    team_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Delete a team."""
    try:
        from app.services import teams as team_service
        
        await team_service.delete_team(session, team_id, current_user.id)
        
        return {"message": "Team deleted successfully"}
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to delete team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team",
        ) from e


@router.get("/teams/{team_id}/members", response_model=TeamMembersResponse)
async def get_team_members(
    team_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamMembersResponse:
    """Get members of a team."""
    try:
        from app.services import teams as team_service
        
        members = await team_service.get_team_members(session, team_id, current_user.id)
        
        member_items = []
        for member in members:
            user = member.user
            member_items.append(
                TeamMemberItem(
                    id=member.id,
                    user_id=member.user_id,
                    email=user.email if user else "",
                    full_name=user.full_name if user else "",
                    role=member.role,
                    joined_at=member.joined_at,
                )
            )
        
        return TeamMembersResponse(members=member_items)
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to get team members: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team members",
        ) from e


@router.post("/teams/{team_id}/members", response_model=TeamMemberItem, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMemberAdd,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamMemberItem:
    """Add a member to a team."""
    try:
        from app.services import teams as team_service
        
        member = await team_service.add_team_member(
            session,
            team_id,
            current_user.id,
            payload.user_id,
            payload.role,
        )
        
        # Get user info
        from app.models import User
        user_stmt = select(User).where(User.id == member.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        return TeamMemberItem(
            id=member.id,
            user_id=member.user_id,
            email=user.email if user else "",
            full_name=user.full_name if user else "",
            role=member.role,
            joined_at=member.joined_at,
        )
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to add team member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member",
        ) from e


@router.put("/teams/{team_id}/members/{member_id}", response_model=TeamMemberItem)
async def update_team_member(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: TeamMemberUpdate,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamMemberItem:
    """Update a team member's role."""
    try:
        from app.services import teams as team_service
        
        member = await team_service.update_team_member_role(
            session,
            team_id,
            current_user.id,
            member_id,
            payload.role,
        )
        
        # Get user info
        from app.models import User
        user_stmt = select(User).where(User.id == member.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        return TeamMemberItem(
            id=member.id,
            user_id=member.user_id,
            email=user.email if user else "",
            full_name=user.full_name if user else "",
            role=member.role,
            joined_at=member.joined_at,
        )
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team or member not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except Exception as e:
        logger.error(f"Failed to update team member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team member",
        ) from e


@router.delete("/teams/{team_id}/members/{member_id}", status_code=status.HTTP_200_OK)
async def remove_team_member(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Remove a member from a team."""
    try:
        from app.services import teams as team_service
        
        await team_service.remove_team_member(session, team_id, current_user.id, member_id)
        
        return {"message": "Member removed from team successfully"}
    except team_service.TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team or member not found",
        )
    except team_service.TeamAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to remove team member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member",
        ) from e
