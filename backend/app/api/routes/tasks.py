from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from app.services import task as task_service

router = APIRouter()


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> TaskResponse:
    """Create a new task."""
    try:
        task = await task_service.create_task(session, task_data, current_user.id)
        reminder = None
        if task.reminder_enabled:
            from app.schemas.task import ReminderInfo
            reminder = ReminderInfo(
                enabled=task.reminder_enabled,
                time=task.reminder_time,
                notified=task.reminder_notified,
            )
        return TaskResponse.model_validate({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "dueDate": task.due_date,
            "priority": task.priority,
            "category": task.category,
            "reminder": reminder,
            "projectId": task.project_id,
            "scopeId": task.scope_id,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create task: {str(exc)}",
        ) from exc


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: UUID = Query(..., alias="workspaceId"),
    completed: Optional[bool] = None,
    overdue: Optional[bool] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    due_date: Optional[datetime] = Query(None, alias="dueDate"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TaskListResponse:
    """List tasks with filters."""
    try:
        tasks, total = await task_service.list_tasks(
            session=session,
            workspace_id=workspace_id,
            user_id=current_user.id,
            completed=completed,
            overdue=overdue,
            priority=priority,
            category=category,
            due_date=due_date,
            limit=limit,
            offset=offset,
        )
        task_responses = []
        for task in tasks:
            reminder = None
            if task.reminder_enabled:
                from app.schemas.task import ReminderInfo
                reminder = ReminderInfo(
                    enabled=task.reminder_enabled,
                    time=task.reminder_time,
                    notified=task.reminder_notified,
                )
            task_responses.append(TaskResponse.model_validate({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "completed": task.completed,
                "dueDate": task.due_date,
                "priority": task.priority,
                "category": task.category,
                "reminder": reminder,
                "projectId": task.project_id,
                "scopeId": task.scope_id,
                "createdAt": task.created_at,
                "updatedAt": task.updated_at,
            }))
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to list tasks: {str(exc)}",
        ) from exc


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> TaskResponse:
    """Update a task."""
    try:
        task = await task_service.update_task(session, task_id, task_data, current_user.id)
        reminder = None
        if task.reminder_enabled:
            from app.schemas.task import ReminderInfo
            reminder = ReminderInfo(
                enabled=task.reminder_enabled,
                time=task.reminder_time,
                notified=task.reminder_notified,
            )
        return TaskResponse.model_validate({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "dueDate": task.due_date,
            "priority": task.priority,
            "category": task.category,
            "reminder": reminder,
            "projectId": task.project_id,
            "scopeId": task.scope_id,
            "createdAt": task.created_at,
            "updatedAt": task.updated_at,
        })
    except task_service.TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update task: {str(exc)}",
        ) from exc


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> dict:
    """Delete a task."""
    try:
        await task_service.delete_task(session, task_id, current_user.id)
        return {"success": True, "message": "Task deleted successfully"}
    except task_service.TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete task: {str(exc)}",
        ) from exc
