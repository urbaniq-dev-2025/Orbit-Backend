from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

TemplateType = Literal["scope", "prd", "project"]


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: TemplateType = Field("scope", description="Template type")
    category: Optional[str] = Field(None, max_length=100)
    content: Dict = Field(..., alias="content", description="Template structure (sections)")
    variables: Optional[List[str]] = Field(None, description="Placeholder variables")

    class Config:
        allow_population_by_field_name = True


class TemplateCreate(TemplateBase):
    workspace_id: Optional[uuid.UUID] = Field(None, alias="workspaceId")

    class Config:
        allow_population_by_field_name = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    content: Optional[Dict] = None
    variables: Optional[List[str]] = None

    class Config:
        allow_population_by_field_name = True


class TemplateSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: TemplateType
    category: Optional[str] = None
    usage_count: int = Field(..., alias="usageCount")
    is_system: bool = Field(..., alias="isSystem")
    created_at: datetime = Field(..., alias="createdAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class TemplateDetail(TemplateSummary):
    content: Dict = Field(..., description="Template structure")
    variables: Optional[List[str]] = None
    workspace_id: Optional[uuid.UUID] = Field(None, alias="workspaceId")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class TemplateListResponse(BaseModel):
    templates: List[TemplateSummary]
    total: int

    class Config:
        allow_population_by_field_name = True


class CategoryResponse(BaseModel):
    categories: List[str] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True
