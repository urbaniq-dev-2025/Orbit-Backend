from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api import deps
from app.models import Subscription

router = APIRouter()


@router.get("/current")
async def get_current_subscription(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> dict:
    """Get current subscription for a workspace."""
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspaceId is required",
        )
    
    try:
        result = await session.execute(
            select(Subscription)
            .where(Subscription.workspace_id == workspace_id)
            .where(Subscription.status.in_(["active", "trialing"]))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return {
                "subscription": None,
                "plan": "free",
                "status": "active",
                "billingCycle": "monthly",
            }
        
        return {
            "subscription": {
                "id": str(subscription.id),
                "workspaceId": str(subscription.workspace_id),
                "plan": subscription.plan,
                "status": subscription.status,
                "billingCycle": subscription.billing_cycle,
                "currentPeriodStart": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "cancelAtPeriodEnd": subscription.cancel_at_period_end,
            },
            "plan": subscription.plan,
            "status": subscription.status,
            "billingCycle": subscription.billing_cycle,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve subscription: {str(exc)}",
        ) from exc
