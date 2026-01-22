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
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeSectionCreate(ScopeSectionBase):
    pass


class ScopeSectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    order_index: Optional[int] = Field(None, alias="orderIndex", ge=0)

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeSectionPublic(ScopeSectionBase):
    id: uuid.UUID
    scope_id: uuid.UUID = Field(..., alias="scopeId")
    ai_generated: bool = Field(..., alias="aiGenerated")
    confidence_score: int = Field(..., alias="confidenceScore")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name
        from_attributes = True


class ScopeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: ScopeStatus = "draft"
    progress: int = Field(0, ge=0, le=100)
    due_date: Optional[datetime] = Field(None, alias="dueDate")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeCreate(ScopeBase):
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    project_id: Optional[uuid.UUID] = Field(None, alias="projectId")
    template_id: Optional[uuid.UUID] = Field(None, alias="templateId")
    
    # Input options for scope creation
    input_type: Optional[Literal["pdf", "text", "speech", "ai_generate", "google_docs", "notion"]] = Field(
        None, alias="inputType"
    )
    input_data: Optional[str] = Field(None, alias="inputData")  # Text content or file content
    input_url: Optional[str] = Field(None, alias="inputUrl")  # For Google Docs/Notion URLs
    
    # AI Model selection (based on subscription)
    ai_model: Optional[str] = Field(None, alias="aiModel")  # "gpt-4", "claude-3", "gpt-3.5", etc.
    
    # Hours estimation preferences
    developer_level: Literal["junior", "mid", "senior"] = Field("mid", alias="developerLevel")
    developer_experience_years: int = Field(3, alias="developerExperienceYears", ge=1, le=10)

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ScopeStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[datetime] = Field(None, alias="dueDate")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


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
    # Additional fields for frontend
    project_name: Optional[str] = Field(None, alias="projectName")
    client_id: Optional[uuid.UUID] = Field(None, alias="clientId")
    client_name: Optional[str] = Field(None, alias="clientName")
    is_favourite: bool = Field(False, alias="isFavourite")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name
        from_attributes = True  # Pydantic v2: renamed from orm_mode


class ScopeDetail(ScopeSummary):
    sections: List[ScopeSectionPublic] = Field(default_factory=list)
    documents_count: int = Field(0, alias="documentsCount")
    comments_count: int = Field(0, alias="commentsCount")
    is_favourite: bool = Field(False, alias="isFavourite")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name
        from_attributes = True  # Pydantic v2: renamed from orm_mode


class ScopeListResponse(BaseModel):
    scopes: List[ScopeSummary]
    total: int
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeReorderRequest(BaseModel):
    section_ids: List[uuid.UUID] = Field(..., alias="sectionIds", min_items=1)

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeExportRequest(BaseModel):
    format: Literal["pdf", "docx"] = Field(..., description="Export format")
    include_sections: bool = Field(True, alias="includeSections", description="Include all sections")
    template: Literal["standard", "detailed"] = Field("standard", description="Export template")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeExportResponse(BaseModel):
    download_url: str = Field(..., alias="downloadUrl")
    expires_at: datetime = Field(..., alias="expiresAt")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeUploadResponse(BaseModel):
    upload_id: uuid.UUID = Field(..., alias="uploadId")
    status: str
    message: str

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeExtractRequest(BaseModel):
    upload_id: uuid.UUID = Field(..., alias="uploadId")
    extraction_type: Literal["full", "summary", "sections"] = Field("full", alias="extractionType")
    template_id: Optional[uuid.UUID] = Field(None, alias="templateId")  # Template to guide structure
    ai_model: Optional[str] = Field(None, alias="aiModel")  # AI model to use
    developer_level: Literal["junior", "mid", "senior"] = Field("mid", alias="developerLevel")
    developer_experience_years: int = Field(3, alias="developerExperienceYears", ge=1, le=10)

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


class ScopeExtractResponse(BaseModel):
    extraction_id: uuid.UUID = Field(..., alias="extractionId")
    status: str
    estimated_time: int = Field(..., alias="estimatedTime", description="Estimated time in seconds")

    class Config:
        populate_by_name = True  # Pydantic v2: renamed from allow_population_by_field_name


# Features Tab Schemas
class SubFeature(BaseModel):
    """Sub-feature within a feature."""
    name: str
    description: Optional[str] = None

    class Config:
        populate_by_name = True


class FeatureItem(BaseModel):
    """Feature item for Features tab."""
    name: str
    description: Optional[str] = None
    subFeatures: List[SubFeature] = Field(default_factory=list, alias="subFeatures")

    class Config:
        populate_by_name = True


class ModuleItem(BaseModel):
    """Module item for Features tab."""
    name: str
    description: Optional[str] = None
    summary: Optional[str] = None
    features: List[FeatureItem] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ScopeFeaturesResponse(BaseModel):
    """Response for Features tab - modules and features without status/hours."""
    modules: List[ModuleItem] = Field(default_factory=list)

    class Config:
        populate_by_name = True

