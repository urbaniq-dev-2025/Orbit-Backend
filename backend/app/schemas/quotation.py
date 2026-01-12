from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

QuotationStatus = Literal["draft", "pending", "approved", "rejected"]


class QuotationItemBase(BaseModel):
    page: Optional[str] = Field(None, max_length=255)
    module: Optional[str] = Field(None, max_length=255)
    feature: Optional[str] = None
    interactions: Optional[str] = None
    notes: Optional[str] = None
    assumptions: Optional[str] = None
    design: int = Field(0, ge=0)
    frontend: int = Field(0, ge=0)
    backend: int = Field(0, ge=0)
    qa: int = Field(0, ge=0)
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemUpdate(BaseModel):
    page: Optional[str] = Field(None, max_length=255)
    module: Optional[str] = Field(None, max_length=255)
    feature: Optional[str] = None
    interactions: Optional[str] = None
    notes: Optional[str] = None
    assumptions: Optional[str] = None
    design: Optional[int] = Field(None, ge=0)
    frontend: Optional[int] = Field(None, ge=0)
    backend: Optional[int] = Field(None, ge=0)
    qa: Optional[int] = Field(None, ge=0)
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class QuotationItemPublic(QuotationItemBase):
    id: uuid.UUID
    quotation_id: uuid.UUID = Field(..., alias="quotationId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class QuotationBase(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    status: QuotationStatus = "draft"


class QuotationCreate(QuotationBase):
    scope_id: uuid.UUID = Field(..., alias="scopeId")
    items: Optional[List[QuotationItemCreate]] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class QuotationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[QuotationStatus] = None

    class Config:
        allow_population_by_field_name = True


class QuotationSummary(BaseModel):
    id: uuid.UUID
    scope_id: uuid.UUID = Field(..., alias="scopeId")
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: Optional[str] = None
    status: QuotationStatus
    total_hours: int = Field(..., alias="totalHours")
    design_hours: int = Field(..., alias="designHours")
    frontend_hours: int = Field(..., alias="frontendHours")
    backend_hours: int = Field(..., alias="backendHours")
    qa_hours: int = Field(..., alias="qaHours")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class QuotationDetail(QuotationSummary):
    items: List[QuotationItemPublic] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class QuotationReorderRequest(BaseModel):
    item_ids: List[uuid.UUID] = Field(..., alias="itemIds", min_items=1)

    class Config:
        allow_population_by_field_name = True

