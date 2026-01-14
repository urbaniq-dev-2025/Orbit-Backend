from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.client import ClientListResponse, ClientSummary
from app.services import client as client_service

router = APIRouter()


@router.get("", response_model=ClientListResponse)
async def list_clients(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    status: Optional[str] = Query(None, description="Filter by status: prospect, active, past"),
    search: Optional[str] = Query(None, description="Search in name, industry, contact name, or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ClientListResponse:
    """List clients with filters and pagination."""
    try:
        clients, total = await client_service.list_clients(
            session,
            current_user.id,
            workspace_id=workspace_id,
            status=status,
            search=search,
            page=page,
            page_size=page_size,
        )

        client_summaries = [
            ClientSummary(
                id=c.id,
                workspace_id=c.workspace_id,
                name=c.name,
                logo_url=c.logo_url,
                status=c.status,
                industry=c.industry,
                contact_name=c.contact_name,
                contact_email=c.contact_email,
                contact_phone=c.contact_phone,
                health_score=c.health_score,
                city=c.city,
                state=c.state,
                country=c.country,
                created_at=c.created_at,
                updated_at=c.updated_at,
                last_activity=c.last_activity,
            )
            for c in clients
        ]

        return ClientListResponse(
            clients=client_summaries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve clients.",
        ) from exc
