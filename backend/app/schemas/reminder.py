from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    reminder_date: date_type = Field(..., alias="date", description="Date for the reminder")
    reminder_time: Optional[str] = Field(None, alias="time", description="Time in HH:MM format (e.g., '09:00')")
    reminder_type: str = Field(..., alias="type", description="Type: 'deadline' or 'event'")
    workspace_id: UUID = Field(..., alias="workspaceId")
    project_id: Optional[UUID] = Field(None, alias="projectId", description="Optional project link")
    scope_id: Optional[UUID] = Field(None, alias="scopeId", description="Optional scope link")

    class Config:
        populate_by_name = True


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    reminder_date: Optional[date_type] = Field(None, alias="date")
    reminder_time: Optional[str] = Field(None, alias="time", description="Time in HH:MM format (e.g., '09:00')")
    reminder_type: Optional[str] = Field(None, alias="type", description="Type: 'deadline' or 'event'")
    project_id: Optional[UUID] = Field(None, alias="projectId")
    scope_id: Optional[UUID] = Field(None, alias="scopeId")

    class Config:
        populate_by_name = True


class ReminderResponse(BaseModel):
    id: UUID
    title: str
    reminder_date: date_type = Field(..., alias="date")
    reminder_time: Optional[str] = Field(None, alias="time", description="Time in HH:MM format")
    reminder_type: str = Field(..., alias="type")
    workspace_id: UUID = Field(..., alias="workspaceId")
    project_id: Optional[UUID] = Field(None, alias="projectId")
    project_name: Optional[str] = Field(None, alias="projectName")
    scope_id: Optional[UUID] = Field(None, alias="scopeId")
    scope_name: Optional[str] = Field(None, alias="scopeName")
    created_by: UUID = Field(..., alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class ReminderListResponse(BaseModel):
    reminders: list[ReminderResponse]
    total: int
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        populate_by_name = True
