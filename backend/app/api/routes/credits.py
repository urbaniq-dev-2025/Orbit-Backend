from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api import deps
from app.models import WorkspaceCreditBalance

router = APIRouter()


@router.get("/balance")
async def get_credit_balance(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> dict:
    """Get credit balance for a workspace."""
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspaceId is required",
        )
    
    try:
        result = await session.execute(
            select(WorkspaceCreditBalance)
            .where(WorkspaceCreditBalance.workspace_id == workspace_id)
        )
        balance = result.scalar_one_or_none()
        
        if not balance:
            return {
                "workspaceId": str(workspace_id),
                "balance": 0,
                "totalPurchased": 0,
                "totalConsumed": 0,
            }
        
        return {
            "workspaceId": str(balance.workspace_id),
            "balance": balance.balance,
            "totalPurchased": balance.total_purchased,
            "totalConsumed": balance.total_consumed,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve credit balance: {str(exc)}",
        ) from exc
