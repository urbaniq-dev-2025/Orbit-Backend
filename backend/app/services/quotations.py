from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Quotation, QuotationItem, Scope, WorkspaceMember
from app.schemas.quotation import QuotationCreate, QuotationItemCreate, QuotationStatus, QuotationUpdate
from app.services.scopes import ScopeAccessError, ScopeNotFoundError


class QuotationNotFoundError(Exception):
    """Raised when a requested quotation does not exist."""


class QuotationAccessError(Exception):
    """Raised when a user attempts to access a quotation they do not have permission for."""


class QuotationItemNotFoundError(Exception):
    """Raised when a requested quotation item does not exist."""


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


async def _calculate_totals(items: List[QuotationItem]) -> dict[str, int]:
    """Calculate total hours from items."""
    totals = {"total": 0, "design": 0, "frontend": 0, "backend": 0, "qa": 0}
    for item in items:
        totals["design"] += item.design
        totals["frontend"] += item.frontend
        totals["backend"] += item.backend
        totals["qa"] += item.qa
    totals["total"] = totals["design"] + totals["frontend"] + totals["backend"] + totals["qa"]
    return totals


async def list_quotations(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    scope_id: Optional[uuid.UUID] = None,
    status: Optional[QuotationStatus] = None,
) -> List[Quotation]:
    """List quotations with filters."""
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
    stmt: Select[Quotation] = select(Quotation).where(
        Quotation.workspace_id.in_(accessible_workspace_ids)
    )

    if workspace_id:
        if workspace_id not in accessible_workspace_ids:
            return []
        stmt = stmt.where(Quotation.workspace_id == workspace_id)

    if scope_id:
        stmt = stmt.where(Quotation.scope_id == scope_id)

    if status:
        stmt = stmt.where(Quotation.status == status)

    stmt = stmt.order_by(Quotation.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_quotation(
    session: AsyncSession, quotation_id: uuid.UUID, user_id: uuid.UUID, *, include_items: bool = True
) -> Quotation:
    """Get a quotation by ID with access check."""
    stmt: Select[Quotation] = select(Quotation).where(Quotation.id == quotation_id)

    if include_items:
        stmt = stmt.options(selectinload(Quotation.items))

    result = await session.execute(stmt)
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise QuotationNotFoundError("Quotation not found")

    # Check workspace access
    has_access = await _check_workspace_access(session, quotation.workspace_id, user_id)
    if not has_access:
        raise QuotationAccessError("Access denied")

    return quotation


async def create_quotation(
    session: AsyncSession, user_id: uuid.UUID, payload: QuotationCreate
) -> Quotation:
    """Create a new quotation."""
    # Verify scope access
    from app.services import scopes as scope_service

    scope = await scope_service.get_scope(session, payload.scope_id, user_id, include_sections=False)

    quotation = Quotation(
        scope_id=payload.scope_id,
        workspace_id=scope.workspace_id,
        name=payload.name,
        status=payload.status,
        created_by=user_id,
    )

    session.add(quotation)
    await session.flush()
    await session.refresh(quotation)

    # Add items if provided
    if payload.items:
        max_order = 0
        for item_data in payload.items:
            if item_data.order_index is None:
                item_data.order_index = max_order
                max_order += 1
            else:
                max_order = max(item_data.order_index + 1, max_order)

            item = QuotationItem(
                quotation_id=quotation.id,
                page=item_data.page,
                module=item_data.module,
                feature=item_data.feature,
                interactions=item_data.interactions,
                notes=item_data.notes,
                assumptions=item_data.assumptions,
                design=item_data.design,
                frontend=item_data.frontend,
                backend=item_data.backend,
                qa=item_data.qa,
                order_index=item_data.order_index or 0,
            )
            session.add(item)

        await session.flush()

    # Calculate and update totals
    items_result = await session.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation.id)
    )
    items = list(items_result.scalars().all())
    totals = await _calculate_totals(items)
    quotation.total_hours = totals["total"]
    quotation.design_hours = totals["design"]
    quotation.frontend_hours = totals["frontend"]
    quotation.backend_hours = totals["backend"]
    quotation.qa_hours = totals["qa"]

    await session.commit()
    await session.refresh(quotation)

    # Reload with items
    return await get_quotation(session, quotation.id, user_id, include_items=True)


async def update_quotation(
    session: AsyncSession, quotation_id: uuid.UUID, user_id: uuid.UUID, payload: QuotationUpdate
) -> Quotation:
    """Update a quotation."""
    quotation = await get_quotation(session, quotation_id, user_id, include_items=False)

    if payload.name is not None:
        quotation.name = payload.name
    if payload.status is not None:
        quotation.status = payload.status

    await session.commit()
    await session.refresh(quotation)

    # Recalculate totals
    items_result = await session.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation.id)
    )
    items = list(items_result.scalars().all())
    totals = await _calculate_totals(items)
    quotation.total_hours = totals["total"]
    quotation.design_hours = totals["design"]
    quotation.frontend_hours = totals["frontend"]
    quotation.backend_hours = totals["backend"]
    quotation.qa_hours = totals["qa"]

    await session.commit()
    await session.refresh(quotation)

    return await get_quotation(session, quotation.id, user_id, include_items=True)


async def delete_quotation(
    session: AsyncSession, quotation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a quotation."""
    quotation = await get_quotation(session, quotation_id, user_id, include_items=False)
    await session.delete(quotation)
    await session.commit()


# Quotation Items Service Functions


async def list_quotation_items(
    session: AsyncSession, quotation_id: uuid.UUID, user_id: uuid.UUID
) -> List[QuotationItem]:
    """List all items for a quotation."""
    # Verify quotation access
    await get_quotation(session, quotation_id, user_id, include_items=False)

    stmt = (
        select(QuotationItem)
        .where(QuotationItem.quotation_id == quotation_id)
        .order_by(QuotationItem.order_index.asc(), QuotationItem.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_quotation_item(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: QuotationItemCreate,
) -> QuotationItem:
    """Create a new item for a quotation."""
    # Verify quotation access
    quotation = await get_quotation(session, quotation_id, user_id, include_items=False)

    # If order_index not provided, get the max and add 1
    order_index = payload.order_index
    if order_index is None:
        stmt = select(func.max(QuotationItem.order_index)).where(
            QuotationItem.quotation_id == quotation_id
        )
        result = await session.execute(stmt)
        max_order = result.scalar_one() or 0
        order_index = max_order + 1

    item = QuotationItem(
        quotation_id=quotation_id,
        page=payload.page,
        module=payload.module,
        feature=payload.feature,
        interactions=payload.interactions,
        notes=payload.notes,
        assumptions=payload.assumptions,
        design=payload.design,
        frontend=payload.frontend,
        backend=payload.backend,
        qa=payload.qa,
        order_index=order_index,
    )

    session.add(item)
    await session.flush()

    # Recalculate totals
    items_result = await session.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
    )
    items = list(items_result.scalars().all())
    totals = await _calculate_totals(items)
    quotation.total_hours = totals["total"]
    quotation.design_hours = totals["design"]
    quotation.frontend_hours = totals["frontend"]
    quotation.backend_hours = totals["backend"]
    quotation.qa_hours = totals["qa"]

    await session.commit()
    await session.refresh(item)
    return item


async def get_quotation_item(
    session: AsyncSession, quotation_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID
) -> QuotationItem:
    """Get a quotation item by ID."""
    # Verify quotation access
    await get_quotation(session, quotation_id, user_id, include_items=False)

    stmt = select(QuotationItem).where(
        QuotationItem.id == item_id,
        QuotationItem.quotation_id == quotation_id,
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        raise QuotationItemNotFoundError("Quotation item not found")

    return item


async def update_quotation_item(
    session: AsyncSession,
    quotation_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: dict,
) -> QuotationItem:
    """Update a quotation item."""
    quotation = await get_quotation(session, quotation_id, user_id, include_items=False)
    item = await get_quotation_item(session, quotation_id, item_id, user_id)

    if payload.get("page") is not None:
        item.page = payload["page"]
    if payload.get("module") is not None:
        item.module = payload["module"]
    if payload.get("feature") is not None:
        item.feature = payload["feature"]
    if payload.get("interactions") is not None:
        item.interactions = payload["interactions"]
    if payload.get("notes") is not None:
        item.notes = payload["notes"]
    if payload.get("assumptions") is not None:
        item.assumptions = payload["assumptions"]
    if payload.get("design") is not None:
        item.design = payload["design"]
    if payload.get("frontend") is not None:
        item.frontend = payload["frontend"]
    if payload.get("backend") is not None:
        item.backend = payload["backend"]
    if payload.get("qa") is not None:
        item.qa = payload["qa"]
    if payload.get("order_index") is not None:
        item.order_index = payload["order_index"]

    await session.flush()

    # Recalculate totals
    items_result = await session.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
    )
    items = list(items_result.scalars().all())
    totals = await _calculate_totals(items)
    quotation.total_hours = totals["total"]
    quotation.design_hours = totals["design"]
    quotation.frontend_hours = totals["frontend"]
    quotation.backend_hours = totals["backend"]
    quotation.qa_hours = totals["qa"]

    await session.commit()
    await session.refresh(item)
    return item


async def delete_quotation_item(
    session: AsyncSession, quotation_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Delete a quotation item."""
    quotation = await get_quotation(session, quotation_id, user_id, include_items=False)
    item = await get_quotation_item(session, quotation_id, item_id, user_id)
    await session.delete(item)
    await session.flush()

    # Recalculate totals
    items_result = await session.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
    )
    items = list(items_result.scalars().all())
    totals = await _calculate_totals(items)
    quotation.total_hours = totals["total"]
    quotation.design_hours = totals["design"]
    quotation.frontend_hours = totals["frontend"]
    quotation.backend_hours = totals["backend"]
    quotation.qa_hours = totals["qa"]

    await session.commit()


async def reorder_quotation_items(
    session: AsyncSession, quotation_id: uuid.UUID, user_id: uuid.UUID, item_ids: List[uuid.UUID]
) -> None:
    """Reorder quotation items."""
    # Verify quotation access
    await get_quotation(session, quotation_id, user_id, include_items=False)

    # Verify all items belong to this quotation
    stmt = select(QuotationItem).where(
        QuotationItem.quotation_id == quotation_id,
        QuotationItem.id.in_(item_ids),
    )
    result = await session.execute(stmt)
    items = {i.id: i for i in result.scalars().all()}

    if len(items) != len(item_ids):
        raise QuotationItemNotFoundError("One or more items not found")

    # Update order_index for each item
    for order, item_id in enumerate(item_ids):
        items[item_id].order_index = order

    await session.commit()


