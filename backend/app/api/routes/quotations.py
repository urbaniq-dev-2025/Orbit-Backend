from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api import deps
from app.schemas.quotation import (
    QuotationCreate,
    QuotationDetail,
    QuotationItemCreate,
    QuotationItemPublic,
    QuotationItemUpdate,
    QuotationReorderRequest,
    QuotationStatus,
    QuotationSummary,
    QuotationUpdate,
)
from app.services import quotations as quotation_service

router = APIRouter()


def _map_quotation_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, quotation_service.QuotationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, quotation_service.QuotationAccessError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, quotation_service.QuotationItemNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to process quotation request."
    )


@router.get("", response_model=List[QuotationSummary])
async def list_quotations(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    scope_id: Optional[uuid.UUID] = Query(None, alias="scopeId"),
    status: Optional[str] = Query(None),
) -> List[QuotationSummary]:
    """List quotations with filters."""
    try:
        quotation_status = (
            status if status in ["draft", "pending", "approved", "rejected"] else None
        )
        quotation_list = await quotation_service.list_quotations(
            session,
            current_user.id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            status=quotation_status,
        )

        return [
            QuotationSummary(
                id=q.id,
                scope_id=q.scope_id,
                workspace_id=q.workspace_id,
                name=q.name,
                status=q.status,
                total_hours=q.total_hours,
                design_hours=q.design_hours,
                frontend_hours=q.frontend_hours,
                backend_hours=q.backend_hours,
                qa_hours=q.qa_hours,
                created_by=q.created_by,
                created_at=q.created_at,
                updated_at=q.updated_at,
            )
            for q in quotation_list
        ]
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.post("", response_model=QuotationDetail, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    payload: QuotationCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> QuotationDetail:
    """Create a new quotation."""
    try:
        quotation = await quotation_service.create_quotation(session, current_user.id, payload)
        return await _build_quotation_detail(quotation)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.get("/{quotation_id}", response_model=QuotationDetail)
async def get_quotation(
    quotation_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> QuotationDetail:
    """Get quotation details with items."""
    try:
        quotation = await quotation_service.get_quotation(
            session, quotation_id, current_user.id, include_items=True
        )
        return await _build_quotation_detail(quotation)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.put("/{quotation_id}", response_model=QuotationDetail)
async def update_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> QuotationDetail:
    """Update a quotation."""
    try:
        quotation = await quotation_service.update_quotation(
            session, quotation_id, current_user.id, payload
        )
        return await _build_quotation_detail(quotation)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quotation(
    quotation_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a quotation."""
    try:
        await quotation_service.delete_quotation(session, quotation_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


# Quotation Items Endpoints


@router.get("/{quotation_id}/items", response_model=List[QuotationItemPublic])
async def list_quotation_items(
    quotation_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> List[QuotationItemPublic]:
    """List all items for a quotation."""
    try:
        items = await quotation_service.list_quotation_items(session, quotation_id, current_user.id)
        return [
            QuotationItemPublic(
                id=i.id,
                quotation_id=i.quotation_id,
                page=i.page,
                module=i.module,
                feature=i.feature,
                interactions=i.interactions,
                notes=i.notes,
                assumptions=i.assumptions,
                design=i.design,
                frontend=i.frontend,
                backend=i.backend,
                qa=i.qa,
                order_index=i.order_index,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ]
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.post("/{quotation_id}/items", response_model=QuotationItemPublic, status_code=status.HTTP_201_CREATED)
async def create_quotation_item(
    quotation_id: uuid.UUID,
    payload: QuotationItemCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> QuotationItemPublic:
    """Create a new item for a quotation."""
    try:
        item = await quotation_service.create_quotation_item(
            session, quotation_id, current_user.id, payload
        )
        return QuotationItemPublic(
            id=item.id,
            quotation_id=item.quotation_id,
            page=item.page,
            module=item.module,
            feature=item.feature,
            interactions=item.interactions,
            notes=item.notes,
            assumptions=item.assumptions,
            design=item.design,
            frontend=item.frontend,
            backend=item.backend,
            qa=item.qa,
            order_index=item.order_index,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.put("/{quotation_id}/items/{item_id}", response_model=QuotationItemPublic)
async def update_quotation_item(
    quotation_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: QuotationItemUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> QuotationItemPublic:
    """Update a quotation item."""
    try:
        update_data = payload.dict(exclude_unset=True, by_alias=False)
        # Convert order_index alias
        if "orderIndex" in update_data:
            update_data["order_index"] = update_data.pop("orderIndex")
        item = await quotation_service.update_quotation_item(
            session, quotation_id, item_id, current_user.id, update_data
        )
        return QuotationItemPublic(
            id=item.id,
            quotation_id=item.quotation_id,
            page=item.page,
            module=item.module,
            feature=item.feature,
            interactions=item.interactions,
            notes=item.notes,
            assumptions=item.assumptions,
            design=item.design,
            frontend=item.frontend,
            backend=item.backend,
            qa=item.qa,
            order_index=item.order_index,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.delete("/{quotation_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quotation_item(
    quotation_id: uuid.UUID,
    item_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Delete a quotation item."""
    try:
        await quotation_service.delete_quotation_item(session, quotation_id, item_id, current_user.id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


@router.put("/{quotation_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_quotation_items(
    quotation_id: uuid.UUID,
    payload: QuotationReorderRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> Response:
    """Reorder quotation items."""
    try:
        await quotation_service.reorder_quotation_items(
            session, quotation_id, current_user.id, payload.item_ids
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_quotation_exception(exc) from exc


# Helper Functions


def _build_quotation_detail(quotation) -> QuotationDetail:
    """Build QuotationDetail response with items."""
    items = [
        QuotationItemPublic(
            id=i.id,
            quotation_id=i.quotation_id,
            page=i.page,
            module=i.module,
            feature=i.feature,
            interactions=i.interactions,
            notes=i.notes,
            assumptions=i.assumptions,
            design=i.design,
            frontend=i.frontend,
            backend=i.backend,
            qa=i.qa,
            order_index=i.order_index,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in sorted(quotation.items, key=lambda x: (x.order_index, x.created_at))
    ]

    return QuotationDetail(
        id=quotation.id,
        scope_id=quotation.scope_id,
        workspace_id=quotation.workspace_id,
        name=quotation.name,
        status=quotation.status,
        total_hours=quotation.total_hours,
        design_hours=quotation.design_hours,
        frontend_hours=quotation.frontend_hours,
        backend_hours=quotation.backend_hours,
        qa_hours=quotation.qa_hours,
        created_by=quotation.created_by,
        created_at=quotation.created_at,
        updated_at=quotation.updated_at,
        items=items,
    )


