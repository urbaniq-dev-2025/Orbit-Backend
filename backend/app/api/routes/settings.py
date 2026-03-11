"""
API routes for Settings page functionality.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import desc, func, select

from app.api import deps
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import TeamMember, User
from app.schemas.settings import (
    AvatarUploadResponse,
    BillingHistoryItem,
    BillingHistoryResponse,
    DataExportListResponse,
    DataExportRequest,
    DataExportResponse,
    DataExportStatusResponse,
    EmailVerificationSendResponse,
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to upload avatar: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        ) from exc


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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to change password: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        ) from exc


# Notification Preferences
@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    session: deps.SessionDep,
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
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
        sessions_result = await session.execute(sessions_stmt)
        sessions = sessions_result.scalars().all()
        
        # Get recent login activity
        activity_stmt = (
            select(LoginActivity)
            .where(LoginActivity.user_id == current_user.id)
            .order_by(desc(LoginActivity.timestamp))
            .limit(10)
        )
        activity_result = await session.execute(activity_stmt)
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


# 2FA Management
@router.post("/auth/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa(
    payload: TwoFactorEnableRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TwoFactorEnableResponse:
    """Enable two-factor authentication for current user."""
    try:
        import pyotp
        import qrcode
        import io
        import base64
        import secrets
        
        if current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is already enabled",
            )
        
        if payload.method == "totp":
            # Generate TOTP secret
            secret = pyotp.random_base32()
            current_user.two_factor_secret = secret
            current_user.two_factor_method = "totp"
            
            # Generate QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=current_user.email,
                issuer_name="Orbit"
            )
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            qr_code = f"data:image/png;base64,{qr_code_data}"
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            current_user.two_factor_backup_codes = backup_codes
            
        elif payload.method == "sms":
            if not payload.phone_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number is required for SMS 2FA",
                )
            # For SMS, we'd integrate with an SMS provider
            # For now, just store the method and phone
            current_user.two_factor_secret = None
            current_user.two_factor_method = "sms"
            current_user.phone = payload.phone_number
            qr_code = None
            secret = None
            backup_codes = []
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA method",
            )
        
        # Don't enable yet - user needs to verify first
        # current_user.two_factor_enabled = True
        await session.commit()
        
        return TwoFactorEnableResponse(
            qr_code=qr_code,
            secret=secret,
            backup_codes=backup_codes,
            message="2FA setup initiated. Please verify with a code to complete setup.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable 2FA: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA",
        ) from e


@router.post("/auth/2fa/disable", response_model=dict)
async def disable_2fa(
    payload: TwoFactorDisableRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Disable two-factor authentication for current user."""
    try:
        from app.core.security import verify_password
        
        if not current_user.two_factor_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled",
            )
        
        # Verify password
        if not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password",
            )
        
        # Verify 2FA code if provided
        if payload.verification_code:
            import pyotp
            if current_user.two_factor_method == "totp" and current_user.two_factor_secret:
                totp = pyotp.TOTP(current_user.two_factor_secret)
                if not totp.verify(payload.verification_code, valid_window=1):
                    # Check backup codes
                    backup_codes = current_user.two_factor_backup_codes or []
                    if payload.verification_code not in backup_codes:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid verification code",
                        )
                    # Remove used backup code
                    backup_codes.remove(payload.verification_code)
                    current_user.two_factor_backup_codes = backup_codes
        
        # Disable 2FA
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.two_factor_method = None
        current_user.two_factor_backup_codes = None
        
        await session.commit()
        
        return {"message": "2FA disabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable 2FA: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA",
        ) from e


# Email Verification
@router.post("/auth/verify/resend", response_model=EmailVerificationSendResponse)
async def resend_email_verification(
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> EmailVerificationSendResponse:
    """Resend email verification."""
    try:
        if current_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )
        
        from app.services.email import get_email_dispatcher
        from app.core.security import create_state_token
        import datetime as dt
        
        # Generate verification token
        token_data = {
            "user_id": str(current_user.id),
            "email": current_user.email,
            "type": "email_verification",
            "exp": int((dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)).timestamp()),
        }
        token = create_state_token(token_data)
        
        # Send verification email
        dispatcher = get_email_dispatcher()
        verification_url = f"{get_settings().frontend_url}/verify-email?token={token}"
        await dispatcher.send_email_verification(current_user.email, verification_url)
        
        return EmailVerificationSendResponse(
            message="Verification email sent successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend verification email: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        ) from e


# Get Team Details
@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team_details(
    team_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> TeamResponse:
    """Get team details with members."""
    try:
        from app.services import teams as team_service
        
        team, user_role = await team_service.get_team(session, team_id, current_user.id)
        
        # Get member count
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
        logger.error(f"Failed to get team details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team details",
        ) from e


# Leave Team
@router.post("/teams/{team_id}/leave", status_code=status.HTTP_200_OK)
async def leave_team(
    team_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Leave a team."""
    try:
        from app.services import teams as team_service
        
        # Get team member
        member_stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
        )
        member_result = await session.execute(member_stmt)
        member = member_result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not a member of this team",
            )
        
        # Check if user is the owner
        if member.role == "owner":
            # Check if there are other members
            other_members_stmt = select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id != current_user.id,
            )
            other_members_result = await session.execute(other_members_stmt)
            other_members = other_members_result.scalars().all()
            
            if other_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Team owner cannot leave. Transfer ownership first or delete the team.",
                )
        
        # Remove member
        await session.delete(member)
        await session.commit()
        
        return {"message": "Left team successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to leave team: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave team",
        ) from e


# Invitation Management
@router.post("/workspaces/{workspace_id}/invitations/{invitation_id}/resend", status_code=status.HTTP_200_OK)
async def resend_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Resend a workspace invitation."""
    try:
        from app.models import WorkspaceMember
        from app.services import workspaces as workspace_service
        from app.services.email import get_email_dispatcher
        
        # Verify access
        await workspace_service.get_workspace_for_user(session, workspace_id, current_user.id, include_members=False)
        
        # Get invitation
        invite_stmt = select(WorkspaceMember).where(
            WorkspaceMember.id == invitation_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id.is_(None),  # Pending invitation
        )
        invite_result = await session.execute(invite_stmt)
        invitation = invite_result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found",
            )
        
        # Resend invitation email
        dispatcher = get_email_dispatcher()
        await dispatcher.send_workspace_invitation(
            invitation.invited_email or "",
            workspace_id,
            invitation.role,
        )
        
        return {"message": "Invitation resent successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend invitation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation",
        ) from e


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> Response:
    """Cancel a workspace invitation."""
    try:
        from app.models import WorkspaceMember
        from app.services import workspaces as workspace_service
        
        # Verify access
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
        
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Get invitation
        invite_stmt = select(WorkspaceMember).where(
            WorkspaceMember.id == invitation_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id.is_(None),  # Pending invitation
        )
        invite_result = await session.execute(invite_stmt)
        invitation = invite_result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found",
            )
        
        # Delete invitation
        await session.delete(invitation)
        await session.commit()
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel invitation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation",
        ) from e


@router.get("/workspaces/{workspace_id}/invitations", response_model=List[dict])
async def get_pending_invitations(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> List[dict]:
    """Get pending invitations for a workspace."""
    try:
        from app.models import WorkspaceMember
        from app.services import workspaces as workspace_service
        
        # Verify access
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
        
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Get pending invitations
        invites_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id.is_(None),  # Pending invitations
            WorkspaceMember.status == "pending",
        )
        invites_result = await session.execute(invites_stmt)
        invitations = invites_result.scalars().all()
        
        return [
            {
                "id": str(inv.id),
                "email": inv.invited_email,
                "role": inv.role,
                "status": inv.status,
                "invitedAt": inv.invited_at.isoformat() if inv.invited_at else None,
                "invitedBy": {
                    "id": str(inv.invited_by) if inv.invited_by else None,
                },
                "expiresAt": (inv.invited_at + dt.timedelta(days=7)).isoformat() if inv.invited_at else None,
            }
            for inv in invitations
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pending invitations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations",
        ) from e


# Billing Subscription Management
@router.get("/billing/subscription", response_model=dict)
async def get_subscription(
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Get current subscription for a workspace."""
    try:
        from app.models import Subscription
        from app.services import workspaces as workspace_service
        
        # Verify workspace access
        await workspace_service.get_workspace_for_user(session, workspace_id, current_user.id, include_members=False)
        
        # Get active subscription
        sub_stmt = (
            select(Subscription)
            .where(
                Subscription.workspace_id == workspace_id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            return {
                "id": None,
                "workspaceId": str(workspace_id),
                "plan": "free",
                "tier": "Free",
                "status": "active",
                "currentPeriodStart": None,
                "currentPeriodEnd": None,
                "cancelAtPeriodEnd": False,
                "price": 0.0,
                "billingCycle": "monthly",
                "currency": "USD",
                "features": [],
            }
        
        # Map plan to tier name
        tier_map = {
            "free": "Free",
            "starter": "Starter",
            "pro": "Pro",
            "team": "Team",
            "enterprise": "Enterprise",
        }
        
        # Get plan features (simplified - in production, fetch from plan config)
        features_map = {
            "free": ["Basic features"],
            "starter": ["Basic features", "Priority support"],
            "pro": ["Unlimited scopes", "AI assistance", "Priority support"],
            "team": ["Unlimited scopes", "AI assistance", "Team collaboration", "Priority support"],
            "enterprise": ["Everything in Team", "Custom integrations", "Dedicated support"],
        }
        
        # Get plan price (simplified - in production, fetch from plan config)
        price_map = {
            "free": 0.0,
            "starter": 9.99,
            "pro": 29.99,
            "team": 79.99,
            "enterprise": 199.99,
        }
        
        return {
            "id": str(subscription.id),
            "workspaceId": str(subscription.workspace_id),
            "plan": subscription.plan,
            "tier": tier_map.get(subscription.plan, subscription.plan.title()),
            "status": subscription.status,
            "currentPeriodStart": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancelAtPeriodEnd": subscription.cancel_at_period_end,
            "price": price_map.get(subscription.plan, 0.0),
            "billingCycle": subscription.billing_cycle,
            "currency": "USD",
            "features": features_map.get(subscription.plan, []),
        }
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
        logger.error(f"Failed to get subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription",
        ) from e


@router.put("/billing/subscription", response_model=dict)
async def update_subscription(
    payload: dict,
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Update subscription plan or billing cycle."""
    try:
        from app.models import Subscription
        from app.services import workspaces as workspace_service
        
        # Verify workspace access
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
        
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Get current subscription
        sub_stmt = (
            select(Subscription)
            .where(
                Subscription.workspace_id == workspace_id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )
        
        # Update subscription (in production, this would integrate with Stripe)
        if "plan" in payload:
            subscription.plan = payload["plan"]
        if "billingCycle" in payload:
            subscription.billing_cycle = payload["billingCycle"]
        
        await session.commit()
        await session.refresh(subscription)
        
        # Return updated subscription (reuse get_subscription logic)
        return await get_subscription(session, workspace_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription",
        ) from e


@router.post("/billing/subscription/cancel", response_model=dict)
async def cancel_subscription(
    payload: dict,
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Cancel subscription at end of billing period."""
    try:
        from app.models import Subscription
        from app.services import workspaces as workspace_service
        
        # Verify workspace access
        workspace, membership = await workspace_service.get_workspace_for_user(
            session, workspace_id, current_user.id, include_members=False
        )
        
        if membership.role not in {"owner", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        # Get current subscription
        sub_stmt = (
            select(Subscription)
            .where(
                Subscription.workspace_id == workspace_id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub_result = await session.execute(sub_stmt)
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )
        
        # Cancel at period end
        subscription.cancel_at_period_end = True
        subscription.cancellation_reason = payload.get("reason")
        
        await session.commit()
        await session.refresh(subscription)
        
        return {
            "message": "Subscription will cancel at end of billing period",
            "cancelAt": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        ) from e


# Payment Methods (Stub - would integrate with Stripe in production)
@router.get("/billing/payment-methods", response_model=dict)
async def get_payment_methods(
    session: deps.SessionDep,
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """Get payment methods for a workspace."""
    try:
        from app.services import workspaces as workspace_service
        
        # Verify workspace access
        await workspace_service.get_workspace_for_user(session, workspace_id, current_user.id, include_members=False)
        
        # In production, this would fetch from Stripe
        # For now, return empty list
        return {"paymentMethods": []}
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
        logger.error(f"Failed to get payment methods: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment methods",
        ) from e


# Data Export
@router.post("/data-export", response_model=DataExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_data_export(
    payload: DataExportRequest,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> DataExportResponse:
    """Request a data export."""
    try:
        from app.models import DataExport
        from datetime import datetime, timedelta, timezone
        
        # Create export record
        export = DataExport(
            user_id=current_user.id,
            workspace_id=payload.workspace_id,
            data_types=payload.data_types,
            format=payload.format,
            status="processing",
        )
        session.add(export)
        await session.flush()
        
        # In production, this would trigger a background job
        # For now, estimate completion time
        estimated_completion = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        return DataExportResponse(
            export_id=export.id,
            status="processing",
            estimated_time=5,  # minutes
            message="Data export is being processed. You will be notified when it's ready.",
        )
    except Exception as e:
        logger.error(f"Failed to request data export: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request data export",
        ) from e


@router.get("/data-export/{export_id}", response_model=DataExportStatusResponse)
async def get_export_status(
    export_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> DataExportStatusResponse:
    """Get data export status."""
    try:
        from app.models import DataExport
        
        export_stmt = select(DataExport).where(
            DataExport.id == export_id,
            DataExport.user_id == current_user.id,
        )
        export_result = await session.execute(export_stmt)
        export = export_result.scalar_one_or_none()
        
        if not export:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export not found",
            )
        
        return DataExportStatusResponse(
            id=export.id,
            status=export.status,
            format=export.format,
            file_url=export.download_url,
            file_size=export.file_size,
            expires_at=export.expires_at,
            created_at=export.created_at,
            completed_at=export.completed_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export status",
        ) from e


@router.get("/data-export", response_model=DataExportListResponse)
async def list_data_exports(
    session: deps.SessionDep,
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(deps.get_current_user),
) -> DataExportListResponse:
    """List data exports for current user."""
    try:
        from app.models import DataExport
        
        stmt = select(DataExport).where(DataExport.user_id == current_user.id)
        
        if workspace_id:
            stmt = stmt.where(DataExport.workspace_id == workspace_id)
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(DataExport.created_at)).offset(offset).limit(page_size)
        
        result = await session.execute(stmt)
        exports = result.scalars().all()
        
        return DataExportListResponse(
            exports=[
                DataExportStatusResponse(
                    id=exp.id,
                    status=exp.status,
                    format=exp.format,
                    file_url=exp.download_url,
                    file_size=exp.file_size,
                    expires_at=exp.expires_at,
                    created_at=exp.created_at,
                    completed_at=exp.completed_at,
                )
                for exp in exports
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )
    except Exception as e:
        logger.error(f"Failed to list data exports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data exports",
        ) from e


@router.get("/data-export/{export_id}/download")
async def download_data_export(
    export_id: uuid.UUID,
    session: deps.SessionDep,
    current_user: User = Depends(deps.get_current_user),
) -> Response:
    """Download a data export file."""
    try:
        from app.models import DataExport
        from pathlib import Path
        
        export_stmt = select(DataExport).where(
            DataExport.id == export_id,
            DataExport.user_id == current_user.id,
        )
        export_result = await session.execute(export_stmt)
        export = export_result.scalar_one_or_none()
        
        if not export:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export not found",
            )
        
        if export.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export is not ready for download",
            )
        
        if not export.download_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        
        # In production, this would stream from S3 or similar
        # For now, return a placeholder
        file_path = Path(export.download_url)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        
        file_bytes = file_path.read_bytes()
        
        # Determine content type
        if export.format == "json":
            media_type = "application/json"
        elif export.format == "csv":
            media_type = "text/csv"
        elif export.format == "pdf":
            media_type = "application/pdf"
        else:
            media_type = "application/octet-stream"
        
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="export_{export_id}.{export.format}"',
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export",
        ) from e
