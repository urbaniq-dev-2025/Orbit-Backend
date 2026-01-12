from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Proposal, ProposalSlide, ProposalView, Scope, WorkspaceMember
from app.schemas.proposal import (
    ProposalCreate,
    ProposalSendRequest,
    ProposalSlideCreate,
    ProposalStatus,
    ProposalUpdate,
    ProposalViewRequest,
)
from app.services.scopes import ScopeAccessError, ScopeNotFoundError


class ProposalNotFoundError(Exception):
    """Raised when a requested proposal does not exist."""


class ProposalAccessError(Exception):
    """Raised when a user attempts to access a proposal they do not have permission for."""


class ProposalSlideNotFoundError(Exception):
    """Raised when a requested proposal slide does not exist."""


async def _check_workspace_access(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if user has access to workspace."""
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


def _generate_shared_link() -> str:
    """Generate a unique shared link token."""
    return secrets.token_urlsafe(32)


async def list_proposals(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    scope_id: Optional[uuid.UUID] = None,
    status: Optional[ProposalStatus] = None,
) -> List[Proposal]:
    """List proposals with filters."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return []

    # Build query
    stmt: Select[Proposal] = select(Proposal).where(Proposal.workspace_id.in_(accessible_workspace_ids))

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return []
        stmt = stmt.where(Proposal.workspace_id == workspace_id)

    if scope_id:
        stmt = stmt.where(Proposal.scope_id == scope_id)

    if status:
        stmt = stmt.where(Proposal.status == status)

    stmt = stmt.order_by(Proposal.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: Optional[uuid.UUID] = None, *, include_slides: bool = True
) -> Proposal:
    """Get a proposal by ID with access check."""
    stmt: Select[Proposal] = select(Proposal).where(Proposal.id == proposal_id)

    if include_slides:
        stmt = stmt.options(selectinload(Proposal.slides))

    result = await session.execute(stmt)
    proposal = result.scalar_one_or_none()

    if proposal is None:
        raise ProposalNotFoundError("Proposal not found")

    # If user_id provided, check workspace access
    if user_id is not None:
        has_access = await _check_workspace_access(session, proposal.workspace_id, user_id)
        if not has_access:
            raise ProposalAccessError("Access denied")

    return proposal


async def get_proposal_by_shared_link(
    session: AsyncSession, shared_link: str, *, include_slides: bool = True
) -> Proposal:
    """Get a proposal by shared link (public access)."""
    stmt: Select[Proposal] = select(Proposal).where(Proposal.shared_link == shared_link)

    if include_slides:
        stmt = stmt.options(selectinload(Proposal.slides))

    result = await session.execute(stmt)
    proposal = result.scalar_one_or_none()

    if proposal is None:
        raise ProposalNotFoundError("Proposal not found")

    return proposal


async def create_proposal(
    session: AsyncSession, user_id: uuid.UUID, payload: ProposalCreate
) -> Proposal:
    """Create a new proposal."""
    # Verify scope access
    from app.services import scopes as scope_service

    scope = await scope_service.get_scope(session, payload.scope_id, user_id, include_sections=False)

    proposal = Proposal(
        scope_id=payload.scope_id,
        workspace_id=scope.workspace_id,
        name=payload.name,
        client_name=payload.client_name,
        template=payload.template,
        cover_color=payload.cover_color,
        status=payload.status,
        created_by=user_id,
    )

    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    return await get_proposal(session, proposal.id, user_id, include_slides=True)


async def update_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID, payload: ProposalUpdate
) -> Proposal:
    """Update a proposal."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)

    if payload.name is not None:
        proposal.name = payload.name
    if payload.client_name is not None:
        proposal.client_name = payload.client_name
    if payload.template is not None:
        proposal.template = payload.template
    if payload.cover_color is not None:
        proposal.cover_color = payload.cover_color
    if payload.status is not None:
        proposal.status = payload.status

    await session.commit()
    await session.refresh(proposal)

    return await get_proposal(session, proposal.id, user_id, include_slides=True)


async def delete_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a proposal."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)
    await session.delete(proposal)
    await session.commit()


async def send_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID, payload: ProposalSendRequest
) -> str:
    """Send a proposal and generate a shared link."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)

    # Generate shared link if not exists
    if not proposal.shared_link:
        proposal.shared_link = _generate_shared_link()

    # Update status and sent_at
    proposal.status = "sent"
    proposal.sent_at = datetime.now(timezone.utc)
    # Set expiration to 30 days from now
    proposal.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    await session.commit()
    await session.refresh(proposal)

    # TODO: Send emails to recipients using EmailDispatcher
    # For now, just return the shared link

    return proposal.shared_link


# Proposal Slides Service Functions


async def list_proposal_slides(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
) -> List[ProposalSlide]:
    """List all slides for a proposal."""
    # Verify proposal access if user_id provided
    if user_id is not None:
        await get_proposal(session, proposal_id, user_id, include_slides=False)

    stmt = (
        select(ProposalSlide)
        .where(ProposalSlide.proposal_id == proposal_id)
        .order_by(ProposalSlide.order_index.asc(), ProposalSlide.slide_number.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_proposal_slide(
    session: AsyncSession,
    proposal_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ProposalSlideCreate,
) -> ProposalSlide:
    """Create a new slide for a proposal."""
    # Verify proposal access
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)

    # Check if slide_number already exists
    existing_slide_stmt = select(ProposalSlide).where(
        ProposalSlide.proposal_id == proposal_id,
        ProposalSlide.slide_number == payload.slide_number,
    )
    existing_slide = (await session.execute(existing_slide_stmt)).scalar_one_or_none()
    if existing_slide:
        raise ValueError(f"Slide number {payload.slide_number} already exists")

    # If order_index not provided, get the max and add 1
    order_index = payload.order_index
    if order_index is None:
        stmt = select(func.max(ProposalSlide.order_index)).where(
            ProposalSlide.proposal_id == proposal_id
        )
        result = await session.execute(stmt)
        max_order = result.scalar_one() or 0
        order_index = max_order + 1

    slide = ProposalSlide(
        proposal_id=proposal_id,
        slide_number=payload.slide_number,
        title=payload.title,
        content=payload.content,
        slide_type=payload.slide_type,
        order_index=order_index,
    )

    session.add(slide)
    await session.flush()

    # Update slide_count
    slide_count_stmt = select(func.count(ProposalSlide.id)).where(
        ProposalSlide.proposal_id == proposal_id
    )
    slide_count = (await session.execute(slide_count_stmt)).scalar_one()
    proposal.slide_count = slide_count

    await session.commit()
    await session.refresh(slide)
    return slide


async def get_proposal_slide(
    session: AsyncSession,
    proposal_id: uuid.UUID,
    slide_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> ProposalSlide:
    """Get a proposal slide by ID."""
    # Verify proposal access if user_id provided
    if user_id is not None:
        await get_proposal(session, proposal_id, user_id, include_slides=False)

    stmt = select(ProposalSlide).where(
        ProposalSlide.id == slide_id,
        ProposalSlide.proposal_id == proposal_id,
    )
    result = await session.execute(stmt)
    slide = result.scalar_one_or_none()

    if slide is None:
        raise ProposalSlideNotFoundError("Proposal slide not found")

    return slide


async def update_proposal_slide(
    session: AsyncSession,
    proposal_id: uuid.UUID,
    slide_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: dict,
) -> ProposalSlide:
    """Update a proposal slide."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)
    slide = await get_proposal_slide(session, proposal_id, slide_id, user_id)

    if payload.get("title") is not None:
        slide.title = payload["title"]
    if payload.get("content") is not None:
        slide.content = payload["content"]
    if payload.get("order_index") is not None:
        slide.order_index = payload["order_index"]

    await session.commit()
    await session.refresh(slide)
    return slide


async def delete_proposal_slide(
    session: AsyncSession, proposal_id: uuid.UUID, slide_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a proposal slide."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)
    slide = await get_proposal_slide(session, proposal_id, slide_id, user_id)
    await session.delete(slide)
    await session.flush()

    # Update slide_count
    slide_count_stmt = select(func.count(ProposalSlide.id)).where(
        ProposalSlide.proposal_id == proposal_id
    )
    slide_count = (await session.execute(slide_count_stmt)).scalar_one()
    proposal.slide_count = slide_count

    await session.commit()


async def reorder_proposal_slides(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID, slide_ids: List[uuid.UUID]
) -> None:
    """Reorder proposal slides."""
    # Verify proposal access
    await get_proposal(session, proposal_id, user_id, include_slides=False)

    # Verify all slides belong to this proposal
    stmt = select(ProposalSlide).where(
        ProposalSlide.proposal_id == proposal_id,
        ProposalSlide.id.in_(slide_ids),
    )
    result = await session.execute(stmt)
    slides = {s.id: s for s in result.scalars().all()}

    if len(slides) != len(slide_ids):
        raise ProposalSlideNotFoundError("One or more slides not found")

    # Update order_index for each slide
    for order, slide_id in enumerate(slide_ids):
        slides[slide_id].order_index = order

    await session.commit()


# Proposal Views Service Functions


async def record_proposal_view(
    session: AsyncSession,
    proposal_id: uuid.UUID,
    payload: ProposalViewRequest,
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Record a view of a proposal (public endpoint)."""
    # Get proposal by ID (no user access check for public views)
    proposal = await get_proposal(session, proposal_id, user_id=None, include_slides=False)

    # Check if proposal is expired
    if proposal.expires_at and proposal.expires_at < datetime.now(timezone.utc):
        raise ProposalAccessError("This proposal link has expired")

    # Create view record
    view = ProposalView(
        proposal_id=proposal_id,
        viewer_email=payload.viewer_email,
        viewer_name=payload.viewer_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    session.add(view)
    await session.flush()

    # Update proposal view_count and viewed_at
    view_count_stmt = select(func.count(ProposalView.id)).where(
        ProposalView.proposal_id == proposal_id
    )
    view_count = (await session.execute(view_count_stmt)).scalar_one()
    proposal.view_count = view_count
    if not proposal.viewed_at:
        proposal.viewed_at = datetime.now(timezone.utc)
    proposal.status = "viewed"

    await session.commit()


async def get_proposal_analytics(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Get analytics for a proposal."""
    proposal = await get_proposal(session, proposal_id, user_id, include_slides=False)

    # Get all views
    views_stmt = (
        select(ProposalView)
        .where(ProposalView.proposal_id == proposal_id)
        .order_by(ProposalView.viewed_at.desc())
    )
    views_result = await session.execute(views_stmt)
    views = list(views_result.scalars().all())

    # Count unique viewers by email
    unique_emails = set()
    for view in views:
        if view.viewer_email:
            unique_emails.add(view.viewer_email.lower())

    views_data = [
        {
            "id": str(v.id),
            "viewerEmail": v.viewer_email,
            "viewerName": v.viewer_name,
            "viewedAt": v.viewed_at.isoformat() if v.viewed_at else None,
        }
        for v in views
    ]

    return {
        "view_count": len(views),
        "unique_viewers": len(unique_emails),
        "views": views_data,
    }


