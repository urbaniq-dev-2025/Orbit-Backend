from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ProposalStatus = Literal["draft", "sent", "viewed", "accepted", "rejected"]
ProposalTemplate = Literal["standard", "minimal", "detailed"]


class ProposalSlideBase(BaseModel):
    slide_number: int = Field(..., alias="slideNumber", ge=1)
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    slide_type: Optional[str] = Field(None, alias="slideType", max_length=50)
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class ProposalSlideCreate(ProposalSlideBase):
    pass


class ProposalSlideUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class ProposalSlidePublic(ProposalSlideBase):
    id: uuid.UUID
    proposal_id: uuid.UUID = Field(..., alias="proposalId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ProposalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)
    template: Optional[ProposalTemplate] = None
    cover_color: Optional[str] = Field(None, alias="coverColor", max_length=7)
    status: ProposalStatus = "draft"

    class Config:
        allow_population_by_field_name = True


class ProposalCreate(ProposalBase):
    scope_id: uuid.UUID = Field(..., alias="scopeId")

    class Config:
        allow_population_by_field_name = True


class ProposalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_name: Optional[str] = Field(None, alias="clientName", max_length=255)
    template: Optional[ProposalTemplate] = None
    cover_color: Optional[str] = Field(None, alias="coverColor", max_length=7)
    status: Optional[ProposalStatus] = None

    class Config:
        allow_population_by_field_name = True


class ProposalSummary(BaseModel):
    id: uuid.UUID
    scope_id: uuid.UUID = Field(..., alias="scopeId")
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: str
    client_name: Optional[str] = Field(None, alias="clientName")
    template: Optional[ProposalTemplate] = None
    cover_color: Optional[str] = Field(None, alias="coverColor")
    status: ProposalStatus
    slide_count: int = Field(..., alias="slideCount")
    view_count: int = Field(..., alias="viewCount")
    shared_link: Optional[str] = Field(None, alias="sharedLink")
    sent_at: Optional[datetime] = Field(None, alias="sentAt")
    viewed_at: Optional[datetime] = Field(None, alias="viewedAt")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ProposalDetail(ProposalSummary):
    slides: List[ProposalSlidePublic] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ProposalSendRequest(BaseModel):
    recipient_emails: List[str] = Field(..., alias="recipientEmails", min_items=1)
    message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class ProposalSendResponse(BaseModel):
    success: bool = True
    shared_link: str = Field(..., alias="sharedLink")

    class Config:
        allow_population_by_field_name = True


class ProposalViewRequest(BaseModel):
    viewer_email: Optional[str] = Field(None, alias="viewerEmail", max_length=255)
    viewer_name: Optional[str] = Field(None, alias="viewerName", max_length=255)

    class Config:
        allow_population_by_field_name = True


class ProposalAnalyticsResponse(BaseModel):
    view_count: int = Field(..., alias="viewCount")
    unique_viewers: int = Field(..., alias="uniqueViewers")
    views: List[dict] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class ProposalSlideReorderRequest(BaseModel):
    slide_ids: List[uuid.UUID] = Field(..., alias="slideIds", min_items=1)

    class Config:
        allow_population_by_field_name = True


