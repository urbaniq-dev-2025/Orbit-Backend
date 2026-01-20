"""
Remaining Settings API endpoints to be added to settings.py.
This file contains workspace settings, teams, billing, 2FA, email verification, data export, and account deletion.
"""

# Workspace Settings
@router.get("/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
async def get_workspace_settings_endpoint(
    workspace_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    session: deps.SessionDep = Depends(),
) -> WorkspaceSettingsResponse:
    """Get workspace settings."""
    try:
        from app.services import workspaces as workspace_service
        from app.services import workspace_settings as settings_service
        
        # Verify user has access to workspace
        await workspace_service.get_workspace(session, workspace_id, current_user.id)
        
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
    current_user: User = Depends(deps.get_current_user),
    session: deps.SessionDep = Depends(),
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
    workspace_id: uuid.UUID = Query(..., alias="workspaceId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(deps.get_current_user),
    session: deps.SessionDep = Depends(),
) -> BillingHistoryResponse:
    """Get billing history for a workspace."""
    try:
        from app.models import BillingHistory
        from app.services import workspaces as workspace_service
        from sqlalchemy import select, func, desc
        
        # Verify workspace access
        await workspace_service.get_workspace(session, workspace_id, current_user.id)
        
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
