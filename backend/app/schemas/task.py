from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderInfo(BaseModel):
    enabled: bool
    time: Optional[datetime] = None
    notified: Optional[bool] = False


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    priority: str = "none"  # 'none', 'low', 'medium', 'high'
    category: str = "general"
    reminder: Optional[ReminderInfo] = None
    workspace_id: UUID = Field(..., alias="workspaceId")
    project_id: Optional[UUID] = Field(None, alias="projectId")
    scope_id: Optional[UUID] = Field(None, alias="scopeId")

    class Config:
        allow_population_by_field_name = True


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    priority: Optional[str] = None
    category: Optional[str] = None
    reminder: Optional[ReminderInfo] = None

    class Config:
        allow_population_by_field_name = True


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    completed: bool
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    priority: str
    category: str
    reminder: Optional[ReminderInfo] = None
    project_id: Optional[UUID] = Field(None, alias="projectId")
    scope_id: Optional[UUID] = Field(None, alias="scopeId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int
