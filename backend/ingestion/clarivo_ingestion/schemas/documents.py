from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

DocumentSourceType = Literal["uploaded_file", "pasted_text", "url", "email", "client_brief"]
DocumentStatus = Literal["submitted", "processing", "completed", "failed", "cancelled"]
DocumentStage = Literal["ingestion", "clarification", "generation", "review"]


class DocumentMetadata(BaseModel):
    project: str | None = None
    client: str | None = None
    notes: str | None = None
    page_count: int | None = None
    language: str | None = None


class ClarificationItem(BaseModel):
    clarification_id: UUID
    question: str
    context: str | None = None
    status: Literal["pending", "answered"] = "pending"
    answer: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentCreateResponse(BaseModel):
    doc_id: UUID
    status: DocumentStatus
    message: str


class TextDocumentCreateRequest(BaseModel):
    source_type: DocumentSourceType
    content: str = Field(min_length=10, max_length=200_000)
    metadata: DocumentMetadata | None = None


class DocumentStatusResponse(BaseModel):
    doc_id: UUID
    status: DocumentStatus
    stage: DocumentStage
    progress: int = Field(ge=0, le=100)
    metadata: DocumentMetadata | None = None
    created_at: datetime
    updated_at: datetime
    links: dict[str, str] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    doc_id: UUID
    source_type: DocumentSourceType
    status: DocumentStatus = "submitted"
    stage: DocumentStage = "ingestion"
    progress: int = 0
    metadata: DocumentMetadata | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    clarifications: list[ClarificationItem] = Field(default_factory=list)
    original_filename: str | None = None
    content_length: int = 0
    content: str = ""
    scope: Any | None = None  # OutputFormatScopeDocument | ScopeDocument | None
    scope_version: int = 0
    scope_generated_at: datetime | None = None
    scope_history: list[Any] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class ClarificationListResponse(BaseModel):
    doc_id: UUID
    clarifications: list[ClarificationItem]


class ClarificationResponseRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class ModuleListResponse(BaseModel):
    doc_id: UUID
    modules: list[dict[str, Any]]


# New schema for scope extraction with hours
class ScopeExtractForScopeRequest(BaseModel):
    """Request for extracting scope with context."""
    scope_id: UUID = Field(..., alias="scopeId")
    document_id: UUID = Field(..., alias="documentId")
    template_id: UUID | None = Field(None, alias="templateId")
    template_structure: dict | None = Field(None, alias="templateStructure")  # Template sections structure
    workspace_id: UUID = Field(..., alias="workspaceId")
    extraction_type: Literal["full", "summary", "sections"] = "full"
    ai_model: str | None = Field(None, alias="aiModel")
    developer_level: Literal["junior", "mid", "senior"] = "mid"
    developer_experience_years: int = 3

    model_config = {"populate_by_name": True}


class ScopeSectionData(BaseModel):
    """Scope section data."""
    title: str
    content: str | dict
    section_type: str | None = None
    order_index: int = 0
    confidence_score: int = 0
    hours_breakdown: dict | None = None  # Kept for backward compatibility, but not used


class ScopeExtractForScopeResponse(BaseModel):
    """Response from scope extraction."""
    extraction_id: UUID = Field(..., alias="extractionId")
    status: str
    scope_sections: list[ScopeSectionData] = Field(default_factory=list, alias="scopeSections")
    confidence_score: int = Field(0, alias="confidenceScore")
    risk_level: str = Field("low", alias="riskLevel")
    total_hours: float = Field(0, alias="totalHours")
    estimated_time: int = Field(30, alias="estimatedTime")

    model_config = {"populate_by_name": True}
