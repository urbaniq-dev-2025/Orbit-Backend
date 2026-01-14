from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, WorkspaceMember


async def list_clients(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Client], int]:
    """List clients with filters and pagination."""
    # Get workspaces user has access to
    workspace_stmt = select(WorkspaceMember.workspace_id).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.status == "active",
    )
    workspace_result = await session.execute(workspace_stmt)
    accessible_workspace_ids = [row[0] for row in workspace_result.all()]

    if not accessible_workspace_ids:
        return [], 0

    # Build base query
    base_stmt = select(Client).where(Client.workspace_id.in_(accessible_workspace_ids))

    # Apply workspace filter
    if workspace_id and workspace_id in accessible_workspace_ids:
        base_stmt = base_stmt.where(Client.workspace_id == workspace_id)

    # Apply status filter
    if status and status in ["prospect", "active", "past"]:
        base_stmt = base_stmt.where(Client.status == status)

    # Apply search filter
    if search:
        search_pattern = f"%{search.lower()}%"
        base_stmt = base_stmt.where(
            or_(
                Client.name.ilike(search_pattern),
                Client.industry.ilike(search_pattern),
                Client.contact_name.ilike(search_pattern),
                Client.contact_email.ilike(search_pattern),
            )
        )

    # Get total count
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    base_stmt = base_stmt.order_by(Client.updated_at.desc()).limit(page_size).offset(offset)

    # Execute query
    result = await session.execute(base_stmt)
    clients = result.scalars().all()

    return clients, total
