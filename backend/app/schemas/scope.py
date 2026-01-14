from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ScopeStatus = Literal["draft", "in_review", "approved", "rejected"]


class ScopeSectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    section_type: Optional[str] = Field(None, alias="sectionType", max_length=50)
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class ScopeSectionCreate(ScopeSectionBase):
    pass


class ScopeSectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        allow_population_by_field_name = True


class ScopeSectionPublic(ScopeSectionBase):
    id: uuid.UUID
    scope_id: uuid.UUID = Field(..., alias="scopeId")
    ai_generated: bool = Field(..., alias="aiGenerated")
    confidence_score: int = Field(..., alias="confidenceScore")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ScopeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: ScopeStatus = "draft"
    progress: int = Field(0, ge=0, le=100)
    due_date: Optional[datetime] = Field(None, alias="dueDate")

    class Config:
        allow_population_by_field_name = True


class ScopeCreate(ScopeBase):
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    project_id: Optional[uuid.UUID] = Field(None, alias="projectId")
    template_id: Optional[uuid.UUID] = Field(None, alias="templateId")

    class Config:
        allow_population_by_field_name = True


class ScopeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ScopeStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[datetime] = Field(None, alias="dueDate")

    class Config:
        allow_population_by_field_name = True


class ScopeStatusUpdate(BaseModel):
    status: ScopeStatus


class ScopeSummary(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    project_id: Optional[uuid.UUID] = Field(None, alias="projectId")
    title: str
    description: Optional[str] = None
    status: ScopeStatus
    progress: int
    confidence_score: int = Field(..., alias="confidenceScore")
    risk_level: str = Field(..., alias="riskLevel")
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ScopeDetail(ScopeSummary):
    sections: List[ScopeSectionPublic] = Field(default_factory=list)
    documents_count: int = Field(0, alias="documentsCount")
    comments_count: int = Field(0, alias="commentsCount")
    is_favourite: bool = Field(False, alias="isFavourite")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class ScopeListResponse(BaseModel):
    scopes: List[ScopeSummary]
    total: int
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


class ScopeReorderRequest(BaseModel):
    section_ids: List[uuid.UUID] = Field(..., alias="sectionIds", min_items=1)

    class Config:
        allow_population_by_field_name = True


class ScopeExportRequest(BaseModel):
    format: Literal["pdf", "docx"] = Field(..., description="Export format")
    include_sections: bool = Field(True, alias="includeSections", description="Include all sections")
    template: Literal["standard", "detailed"] = Field("standard", description="Export template")

    class Config:
        allow_population_by_field_name = True


class ScopeExportResponse(BaseModel):
    download_url: str = Field(..., alias="downloadUrl")
    expires_at: datetime = Field(..., alias="expiresAt")

    class Config:
        allow_population_by_field_name = True


class ScopeUploadResponse(BaseModel):
    upload_id: uuid.UUID = Field(..., alias="uploadId")
    status: str
    message: str

    class Config:
        allow_population_by_field_name = True


class ScopeExtractRequest(BaseModel):
    upload_id: uuid.UUID = Field(..., alias="uploadId")
    extraction_type: Literal["full", "summary", "sections"] = Field("full", alias="extractionType")

    class Config:
        allow_population_by_field_name = True


class ScopeExtractResponse(BaseModel):
    extraction_id: uuid.UUID = Field(..., alias="extractionId")
    status: str
    estimated_time: int = Field(..., alias="estimatedTime", description="Estimated time in seconds")

    class Config:
        allow_population_by_field_name = True


