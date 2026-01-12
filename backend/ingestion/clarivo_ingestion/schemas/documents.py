from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator

from clarivo_ingestion.schemas.scope import ScopeDocument, OutputFormatScopeDocument

DocumentSourceType = Literal["uploaded_file", "pasted_text", "url", "email", "client_brief", "meeting_notes", "rfp", "proposal"]


class DocumentStatus(str, Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    READY_FOR_PREPROCESSING = "ready_for_preprocessing"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentStage(str, Enum):
    INGESTION = "ingestion"
    CLARIFICATION = "clarification"
    PREPROCESSING = "preprocessing"


class ClarificationStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"
    EXPIRED = "expired"


class ClarificationCategory(str, Enum):
    PERSONA_COVERAGE = "persona_coverage"
    FEATURE_GAPS = "feature_gaps"
    KPI_DETAILS = "kpi_details"
    CONTEXT = "context"
    OTHER = "other"


class DocumentMetadata(BaseModel):
    client_name: str | None = None
    project_name: str | None = None
    notes: str | None = None
    engagement_id: str | None = None


class TextDocumentCreateRequest(BaseModel):
    source_type: DocumentSourceType
    content: str = Field(min_length=1, max_length=200_000)
    metadata: DocumentMetadata | None = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: DocumentSourceType) -> DocumentSourceType:
        if value == "uploaded_file":
            raise ValueError("Use multipart upload for files")
        return value


class URLDocumentCreateRequest(BaseModel):
    source_type: Literal["url"] = "url"
    url: HttpUrl
    metadata: DocumentMetadata | None = None


class DocumentCreateResponse(BaseModel):
    doc_id: UUID
    status: DocumentStatus
    message: str


class ClarificationItem(BaseModel):
    clarification_id: UUID = Field(default_factory=uuid4)
    question: str
    category: ClarificationCategory
    status: ClarificationStatus = ClarificationStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    answer: str | None = None
    answered_at: datetime | None = None

    @staticmethod
    def create_with_timeout(
        question: str,
        category: ClarificationCategory,
        timeout_hours: int,
    ) -> ClarificationItem:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        return ClarificationItem(
            question=question,
            category=category,
            expires_at=expires_at,
        )


class ClarificationListResponse(BaseModel):
    doc_id: UUID
    items: list[ClarificationItem]


class ClarificationResponseRequest(BaseModel):
    answer: str = Field(min_length=3, max_length=10_000)


class ModuleListItem(BaseModel):
    name: str
    features: list[str] = Field(default_factory=list)


class ModuleListResponse(BaseModel):
    doc_id: UUID
    modules: list[ModuleListItem]


class DocumentStatusResponse(BaseModel):
    doc_id: UUID
    status: DocumentStatus
    stage: DocumentStage
    progress: int = Field(ge=0, le=100)
    clarification_required: bool = False
    scope_available: bool = False
    last_updated: datetime
    links: dict[str, str] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    doc_id: UUID
    source_type: DocumentSourceType
    status: DocumentStatus = DocumentStatus.SUBMITTED
    stage: DocumentStage = DocumentStage.INGESTION
    progress: int = 0
    metadata: DocumentMetadata | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    clarifications: list[ClarificationItem] = Field(default_factory=list)
    original_filename: str | None = None
    content_length: int = 0
    content: str = ""
    scope: OutputFormatScopeDocument | ScopeDocument | None = None  # Support both formats for backward compatibility
    scope_version: int = 0
    scope_generated_at: datetime | None = None
    scope_history: list[OutputFormatScopeDocument | ScopeDocument] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

