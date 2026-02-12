from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    current_page: Optional[str] = Field(None, alias="currentPage")
    recent_entities: Optional[List[str]] = Field(None, alias="recentEntities")

    class Config:
        populate_by_name = True


class ChatRequest(BaseModel):
    message: str
    workspace_id: Optional[UUID] = Field(None, alias="workspaceId")
    conversation_id: Optional[UUID] = Field(None, alias="conversationId")
    context: Optional[ChatContext] = None

    class Config:
        populate_by_name = True


class IntentInfo(BaseModel):
    type: str  # 'navigate', 'query', 'create_task', 'create_reminder', 'create_entity', 'update_entity', 'search', 'get_insights'
    confidence: float
    entities: Optional[Dict[str, Any]] = None


class ActionData(BaseModel):
    type: str
    label: str
    icon: str
    data: Optional[Dict[str, Any]] = None
    route: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: IntentInfo
    actions: List[ActionData] = Field(default_factory=list)
    conversation_id: UUID = Field(..., alias="conversationId")
    suggestions: Optional[List[str]] = None

    class Config:
        populate_by_name = True
