from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.activity import ActivityListResponse, ActivityPublic
from app.services import activity as activity_service

router = APIRouter()


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
) -> ActivityListResponse:
    """List activities with pagination."""
    try:
        offset = (page - 1) * page_size
        activities, total = await activity_service.list_activities(
            session,
            current_user.id,
            workspace_id=workspace_id,
            limit=page_size,
            offset=offset,
        )

        activity_list = [
            ActivityPublic(
                id=a.id,
                workspace_id=a.workspace_id,
                user_id=a.user_id,
                action=a.action,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                payload=a.payload,
                created_at=a.created_at,
                user_name=a.user.full_name if a.user else None,
                user_email=a.user.email if a.user else None,
            )
            for a in activities
        ]

        return ActivityListResponse(
            activities=activity_list,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve activities.",
        ) from exc


@router.get("/workspace/{workspace_id}", response_model=ActivityListResponse)
async def list_workspace_activities(
    workspace_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
) -> ActivityListResponse:
    """List activities for a specific workspace."""
    try:
        offset = (page - 1) * page_size
        activities, total = await activity_service.list_workspace_activities(
            session,
            workspace_id,
            current_user.id,
            limit=page_size,
            offset=offset,
        )

        activity_list = [
            ActivityPublic(
                id=a.id,
                workspace_id=a.workspace_id,
                user_id=a.user_id,
                action=a.action,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                payload=a.payload,
                created_at=a.created_at,
                user_name=a.user.full_name if a.user else None,
                user_email=a.user.email if a.user else None,
            )
            for a in activities
        ]

        return ActivityListResponse(
            activities=activity_list,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve workspace activities.",
        ) from exc


