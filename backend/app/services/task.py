from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Task
from app.schemas.task import TaskCreate, TaskUpdate

logger = get_logger(__name__)


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""


class TaskAccessError(Exception):
    """Raised when a user attempts to access a task they don't have permission for."""


async def create_task(
    session: AsyncSession, task_data: TaskCreate, user_id: UUID
) -> Task:
    """Create a new task."""
    task = Task(
        workspace_id=task_data.workspace_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority,
        category=task_data.category,
        reminder_enabled=task_data.reminder.enabled if task_data.reminder else False,
        reminder_time=task_data.reminder.time if task_data.reminder and task_data.reminder.enabled else None,
        reminder_notified=False,
        project_id=task_data.project_id,
        scope_id=task_data.scope_id,
        created_by=user_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: UUID, user_id: UUID) -> Optional[Task]:
    """Get a task by ID."""
    result = await session.execute(
        select(Task).where(
            and_(Task.id == task_id, Task.created_by == user_id)
        )
    )
    return result.scalar_one_or_none()


async def list_tasks(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID,
    completed: Optional[bool] = None,
    overdue: Optional[bool] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    due_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[Task], int]:
    """List tasks with filters."""
    query = select(Task).where(
        and_(Task.workspace_id == workspace_id, Task.created_by == user_id)
    )

    if completed is not None:
        query = query.where(Task.completed == completed)

    if overdue:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        query = query.where(
            and_(Task.due_date < now, Task.completed == False)
        )

    if priority:
        query = query.where(Task.priority == priority)

    if category:
        query = query.where(Task.category == category)

    if due_date:
        query = query.where(func.date(Task.due_date) == func.date(due_date))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.desc())
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    tasks = result.scalars().all()

    return list(tasks), total


async def update_task(
    session: AsyncSession, task_id: UUID, task_data: TaskUpdate, user_id: UUID
) -> Task:
    """Update a task."""
    result = await session.execute(
        select(Task).where(
            and_(Task.id == task_id, Task.created_by == user_id)
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")

    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.category is not None:
        task.category = task_data.category
    if task_data.reminder is not None:
        task.reminder_enabled = task_data.reminder.enabled
        task.reminder_time = task_data.reminder.time if task_data.reminder.enabled else None

    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task_id: UUID, user_id: UUID) -> None:
    """Delete a task."""
    result = await session.execute(
        select(Task).where(
            and_(Task.id == task_id, Task.created_by == user_id)
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found")

    await session.delete(task)
    await session.commit()
