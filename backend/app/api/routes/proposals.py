from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.api import deps
from app.schemas.proposal import (
    ProposalAnalyticsResponse,
    ProposalCreate,
    ProposalDetail,
    ProposalSendRequest,
    ProposalSendResponse,
    ProposalSlideCreate,
    ProposalSlidePublic,
    ProposalSlideReorderRequest,
    ProposalSlideUpdate,
    ProposalStatus,
    ProposalSummary,
    ProposalUpdate,
    ProposalViewRequest,
)
from app.services import proposals as proposal_service

router = APIRouter()


def _map_proposal_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, proposal_service.ProposalNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, proposal_service.ProposalAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, proposal_service.ProposalSlideNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to process proposal request."
    )


@router.get("", response_model=List[ProposalSummary])
async def list_proposals(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    scope_id: Optional[uuid.UUID] = Query(None, alias="scopeId"),
    status: Optional[str] = Query(None),
) -> List[ProposalSummary]:
    """List proposals with filters."""
    try:
        proposal_status = (
            status if status in ["draft", "sent", "viewed", "accepted", "rejected"] else None
        )
        proposal_list = await proposal_service.list_proposals(
            session,
            current_user.id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            status=proposal_status,
        )

        return [
            ProposalSummary(
                id=p.id,
                scope_id=p.scope_id,
                workspace_id=p.workspace_id,
                name=p.name,
                client_name=p.client_name,
                template=p.template,
                cover_color=p.cover_color,
                status=p.status,
                slide_count=p.slide_count,
                view_count=p.view_count,
                shared_link=p.shared_link,
                sent_at=p.sent_at,
                viewed_at=p.viewed_at,
                expires_at=p.expires_at,
                created_by=p.created_by,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in proposal_list
        ]
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.post("", response_model=ProposalDetail, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    payload: ProposalCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalDetail:
    """Create a new proposal."""
    try:
        proposal = await proposal_service.create_proposal(session, current_user.id, payload)
        return await _build_proposal_detail(proposal)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.get("/{proposal_id}", response_model=ProposalDetail)
async def get_proposal(
    proposal_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalDetail:
    """Get proposal details with slides."""
    try:
        proposal = await proposal_service.get_proposal(
            session, proposal_id, current_user.id, include_slides=True
        )
        return await _build_proposal_detail(proposal)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.put("/{proposal_id}", response_model=ProposalDetail)
async def update_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalDetail:
    """Update a proposal."""
    try:
        proposal = await proposal_service.update_proposal(
            session, proposal_id, current_user.id, payload
        )
        return await _build_proposal_detail(proposal)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(
    proposal_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a proposal."""
    try:
        await proposal_service.delete_proposal(session, proposal_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.post("/{proposal_id}/send", response_model=ProposalSendResponse)
async def send_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalSendRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalSendResponse:
    """Send a proposal and generate a shared link."""
    try:
        shared_link = await proposal_service.send_proposal(
            session, proposal_id, current_user.id, payload
        )
        return ProposalSendResponse(shared_link=shared_link)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.get("/shared/{shared_link}", response_model=ProposalDetail)
async def get_proposal_by_shared_link(
    shared_link: str,
    session: deps.SessionDep,
) -> ProposalDetail:
    """Get a proposal by shared link (public endpoint, no auth required)."""
    try:
        proposal = await proposal_service.get_proposal_by_shared_link(
            session, shared_link, include_slides=True
        )
        return await _build_proposal_detail(proposal)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.post("/shared/{shared_link}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_proposal_view(
    shared_link: str,
    payload: ProposalViewRequest,
    request: Request,
    session: deps.SessionDep,
) -> Response:
    """Record a view of a proposal (public endpoint, no auth required)."""
    try:
        # Get proposal to find its ID
        proposal = await proposal_service.get_proposal_by_shared_link(
            session, shared_link, include_slides=False
        )

        # Get IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        await proposal_service.record_proposal_view(
            session,
            proposal.id,
            payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.get("/{proposal_id}/analytics", response_model=ProposalAnalyticsResponse)
async def get_proposal_analytics(
    proposal_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalAnalyticsResponse:
    """Get analytics for a proposal."""
    try:
        analytics = await proposal_service.get_proposal_analytics(
            session, proposal_id, current_user.id
        )
        return ProposalAnalyticsResponse(**analytics)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


# Proposal Slides Endpoints


@router.get("/{proposal_id}/slides", response_model=List[ProposalSlidePublic])
async def list_proposal_slides(
    proposal_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> List[ProposalSlidePublic]:
    """List all slides for a proposal."""
    try:
        slides = await proposal_service.list_proposal_slides(
            session, proposal_id, current_user.id
        )
        return [
            ProposalSlidePublic(
                id=s.id,
                proposal_id=s.proposal_id,
                slide_number=s.slide_number,
                title=s.title,
                content=s.content,
                slide_type=s.slide_type,
                order_index=s.order_index,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in slides
        ]
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.post("/{proposal_id}/slides", response_model=ProposalSlidePublic, status_code=status.HTTP_201_CREATED)
async def create_proposal_slide(
    proposal_id: uuid.UUID,
    payload: ProposalSlideCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalSlidePublic:
    """Create a new slide for a proposal."""
    try:
        slide = await proposal_service.create_proposal_slide(
            session, proposal_id, current_user.id, payload
        )
        return ProposalSlidePublic(
            id=slide.id,
            proposal_id=slide.proposal_id,
            slide_number=slide.slide_number,
            title=slide.title,
            content=slide.content,
            slide_type=slide.slide_type,
            order_index=slide.order_index,
            created_at=slide.created_at,
            updated_at=slide.updated_at,
        )
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.put("/{proposal_id}/slides/{slide_id}", response_model=ProposalSlidePublic)
async def update_proposal_slide(
    proposal_id: uuid.UUID,
    slide_id: uuid.UUID,
    payload: ProposalSlideUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ProposalSlidePublic:
    """Update a proposal slide."""
    try:
        update_data = payload.dict(exclude_unset=True, by_alias=False)
        # Convert order_index alias
        if "orderIndex" in update_data:
            update_data["order_index"] = update_data.pop("orderIndex")
        slide = await proposal_service.update_proposal_slide(
            session, proposal_id, slide_id, current_user.id, update_data
        )
        return ProposalSlidePublic(
            id=slide.id,
            proposal_id=slide.proposal_id,
            slide_number=slide.slide_number,
            title=slide.title,
            content=slide.content,
            slide_type=slide.slide_type,
            order_index=slide.order_index,
            created_at=slide.created_at,
            updated_at=slide.updated_at,
        )
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.delete("/{proposal_id}/slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal_slide(
    proposal_id: uuid.UUID,
    slide_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a proposal slide."""
    try:
        await proposal_service.delete_proposal_slide(session, proposal_id, slide_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


@router.put("/{proposal_id}/slides/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_proposal_slides(
    proposal_id: uuid.UUID,
    payload: ProposalSlideReorderRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Reorder proposal slides."""
    try:
        await proposal_service.reorder_proposal_slides(
            session, proposal_id, current_user.id, payload.slide_ids
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_proposal_exception(exc) from exc


# Helper Functions


def _build_proposal_detail(proposal) -> ProposalDetail:
    """Build ProposalDetail response with slides."""
    slides = [
        ProposalSlidePublic(
            id=s.id,
            proposal_id=s.proposal_id,
            slide_number=s.slide_number,
            title=s.title,
            content=s.content,
            slide_type=s.slide_type,
            order_index=s.order_index,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sorted(proposal.slides, key=lambda x: (x.order_index, x.slide_number))
    ]

    return ProposalDetail(
        id=proposal.id,
        scope_id=proposal.scope_id,
        workspace_id=proposal.workspace_id,
        name=proposal.name,
        client_name=proposal.client_name,
        template=proposal.template,
        cover_color=proposal.cover_color,
        status=proposal.status,
        slide_count=proposal.slide_count,
        view_count=proposal.view_count,
        shared_link=proposal.shared_link,
        sent_at=proposal.sent_at,
        viewed_at=proposal.viewed_at,
        expires_at=proposal.expires_at,
        created_by=proposal.created_by,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        slides=slides,
    )


