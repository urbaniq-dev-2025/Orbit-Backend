from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile

from clarivo_ingestion.core.config import Settings
from clarivo_ingestion.core.logging import get_logger
from clarivo_ingestion.exporters import scope_to_excel_bytes, scope_to_pdf_bytes
from clarivo_ingestion.schemas.documents import (
    ClarificationCategory,
    ClarificationItem,
    ClarificationListResponse,
    ClarificationResponseRequest,
    ClarificationStatus,
    DocumentCreateResponse,
    DocumentMetadata,
    DocumentRecord,
    DocumentStage,
    DocumentStatus,
    DocumentStatusResponse,
    ModuleListItem,
    TextDocumentCreateRequest,
)
from clarivo_ingestion.schemas.scope import ScopeDocument, OutputFormatScopeDocument
from clarivo_ingestion.services.llm_scope import LLMDocumentScopeGenerator
from clarivo_ingestion.services.scope import ScopeParser
from clarivo_ingestion.services.store import store
from clarivo_ingestion.utils.text_extraction import extract_text_from_bytes

logger = get_logger(__name__)


class DocumentService:
    """Business logic for document ingestion and clarification flow."""

    class DocumentNotFoundError(Exception):
        """Raised when a document is not found."""

    class ClarificationError(Exception):
        """Raised when clarification operations fail."""

    class ScopeNotAvailableError(Exception):
        """Raised when scope is requested but not yet generated."""

    def __init__(self, settings: Settings, input_dir: Path | None = None, output_dir: Path | None = None) -> None:
        self._settings = settings
        self._scope_parser = ScopeParser()
        self._llm_scope_generator: LLMDocumentScopeGenerator | None = None
        if settings.scope_generation_strategy in {"llm", "hybrid"} and (
            settings.gemini_api_key is not None or 
            settings.openai_api_key is not None or 
            settings.groq_api_key is not None
        ):
            try:
                self._llm_scope_generator = LLMDocumentScopeGenerator(
                    settings=settings, input_dir=input_dir, output_dir=output_dir
                )
            except LLMDocumentScopeGenerator.ConfigurationError as exc:
                logger.warning("LLM scope generator misconfigured: %s", exc)

    async def handle_file_upload(
        self,
        source_type: str,
        upload: UploadFile,
        metadata: dict[str, Any] | None,
    ) -> DocumentCreateResponse:
        doc_id = uuid4()
        content = await upload.read()
        text_content = extract_text_from_bytes(upload.filename, content)
        record = DocumentRecord(
            doc_id=doc_id,
            source_type=source_type,  # type: ignore[arg-type]
            metadata=DocumentMetadata(**metadata) if metadata else None,
            status=DocumentStatus.PROCESSING,
            stage=DocumentStage.INGESTION,
            progress=20,
            original_filename=upload.filename,
            content_length=len(content),
            content=text_content,
        )
        await store.save(record)

        await self._maybe_trigger_clarification(record, content_length=len(content))

        return DocumentCreateResponse(
            doc_id=doc_id,
            status=record.status,
            message="Document accepted for processing.",
        )

    async def handle_text_submission(
        self,
        request: TextDocumentCreateRequest,
    ) -> DocumentCreateResponse:
        doc_id = uuid4()
        record = DocumentRecord(
            doc_id=doc_id,
            source_type=request.source_type,
            metadata=request.metadata,
            status=DocumentStatus.PROCESSING,
            stage=DocumentStage.INGESTION,
            progress=20,
            content_length=len(request.content),
            content=request.content,
        )
        await store.save(record)

        await self._maybe_trigger_clarification(record, content_length=len(request.content))

        return DocumentCreateResponse(
            doc_id=doc_id,
            status=record.status,
            message="Document accepted for processing.",
        )

    async def get_status(self, doc_id: UUID) -> DocumentStatusResponse | None:
        record = await store.get(doc_id)
        if record is None:
            return None

        links: dict[str, str] = {}
        if record.status == DocumentStatus.AWAITING_CLARIFICATION:
            links["clarifications"] = f"/v1/documents/{doc_id}/clarifications"
        if record.scope is not None:
            links["scope"] = f"/v1/documents/{doc_id}/scope"

        return DocumentStatusResponse(
            doc_id=record.doc_id,
            status=record.status,
            stage=record.stage,
            progress=record.progress,
            clarification_required=record.status == DocumentStatus.AWAITING_CLARIFICATION,
            scope_available=record.scope is not None,
            last_updated=record.updated_at,
            links=links,
        )

    async def list_clarifications(self, doc_id: UUID) -> ClarificationListResponse | None:
        record = await store.get(doc_id)
        if record is None:
            return None
        await self._expire_clarifications(record)
        return ClarificationListResponse(doc_id=doc_id, items=record.clarifications)

    async def answer_clarification(
        self, doc_id: UUID, clarification_id: UUID, request: ClarificationResponseRequest
    ) -> None:
        record = await store.get(doc_id)
        if record is None:
            raise self.DocumentNotFoundError("Document not found")

        clarification = next(
            (item for item in record.clarifications if item.clarification_id == clarification_id),
            None,
        )
        if clarification is None:
            raise self.ClarificationError("Clarification not found")
        if clarification.status != ClarificationStatus.OPEN:
            raise self.ClarificationError("Clarification already answered or expired")

        clarification.answer = request.answer
        clarification.status = ClarificationStatus.ANSWERED
        clarification.answered_at = datetime.now(timezone.utc)
        record.content = "\n".join([record.content, request.answer]).strip()

        record.status = DocumentStatus.READY_FOR_PREPROCESSING
        record.stage = DocumentStage.PREPROCESSING
        record.progress = 100
        record.touch()

        await store.update(record)
        await self._generate_scope(record, save=True)

    async def cancel_document(self, doc_id: UUID) -> None:
        record = await store.get(doc_id)
        if record is None:
            raise self.DocumentNotFoundError("Document not found")

        record.status = DocumentStatus.CANCELLED
        record.stage = DocumentStage.INGESTION
        record.touch()
        await store.update(record)

    async def get_scope(self, doc_id: UUID) -> OutputFormatScopeDocument | ScopeDocument | None:
        record = await store.get(doc_id)
        if record is None:
            return None
        return record.scope

    async def get_modules(self, doc_id: UUID) -> list[ModuleListItem] | None:
        record = await store.get(doc_id)
        if record is None or record.scope is None:
            return None

        module_features = {module.name: module.features for module in record.scope.modules}
        for feature in record.scope.features:
            assigned = False
            for module in record.scope.modules:
                if feature.name in module.features:
                    assigned = True
                    break
            if not assigned:
                module_features.setdefault("Unassigned", []).append(feature.name)

        return [ModuleListItem(name=name, features=sorted(features)) for name, features in module_features.items()]

    async def get_scope_excel(self, doc_id: UUID) -> bytes:
        record = await store.get(doc_id)
        if record is None:
            raise self.DocumentNotFoundError("Document not found")
        if record.scope is None:
            raise self.ScopeNotAvailableError("Scope not available for this document")
        return scope_to_excel_bytes(record.scope)

    async def get_scope_pdf(self, doc_id: UUID) -> bytes:
        record = await store.get(doc_id)
        if record is None:
            raise self.DocumentNotFoundError("Document not found")
        if record.scope is None:
            raise self.ScopeNotAvailableError("Scope not available for this document")
        return scope_to_pdf_bytes(record.scope)

    async def _maybe_trigger_clarification(
        self, record: DocumentRecord, *, content_length: int
    ) -> None:
        if content_length >= self._settings.clarification_min_length:
            record.status = DocumentStatus.READY_FOR_PREPROCESSING
            record.stage = DocumentStage.PREPROCESSING
            record.progress = 100
            record.touch()
            await self._generate_scope(record, save=True)
            logger.info("Document %s ready for preprocessing", record.doc_id)
            return

        clarification = ClarificationItem.create_with_timeout(
            question="Please provide additional context: personas involved, goals, and KPIs discussed.",
            category=ClarificationCategory.CONTEXT,
            timeout_hours=self._settings.clarification_timeout_hours,
        )
        record.status = DocumentStatus.AWAITING_CLARIFICATION
        record.stage = DocumentStage.CLARIFICATION
        record.progress = 40
        record.clarifications.append(clarification)
        record.touch()
        await store.update(record)
        logger.info("Clarification requested for document %s", record.doc_id)

    async def _expire_clarifications(self, record: DocumentRecord) -> None:
        changed = False
        now = datetime.now(timezone.utc)
        for clarification in record.clarifications:
            if (
                clarification.status == ClarificationStatus.OPEN
                and clarification.expires_at is not None
                and clarification.expires_at < now
            ):
                clarification.status = ClarificationStatus.EXPIRED
                changed = True
        if changed:
            record.touch()
            await store.update(record)

    async def _generate_scope(self, record: DocumentRecord, save: bool = False) -> None:
        scope_source = self._compose_scope_source(record)
        if not scope_source.strip():
            logger.info("Skipping scope generation for document %s; no usable content.", record.doc_id)
            return
        scope = await self._generate_scope_with_strategy(scope_source, record.doc_id)
        record.scope_version += 1
        record.scope = scope
        record.scope_generated_at = datetime.now(timezone.utc)
        record.scope_history.append(scope.model_copy(deep=True))
        record.touch()
        if save:
            await store.update(record)

    async def _generate_scope_with_strategy(self, source: str, doc_id: UUID) -> ScopeDocument:
        strategy = self._settings.scope_generation_strategy
        if strategy in {"llm", "hybrid"} and self._llm_scope_generator is not None:
            try:
                return await self._llm_scope_generator.generate(source)
            except (
                LLMDocumentScopeGenerator.ProviderError,
                LLMDocumentScopeGenerator.ParseError,
            ) as exc:
                logger.warning("LLM scope generation failed for %s: %s", doc_id, exc)
                logger.info("Falling back to heuristic scope parser for document %s", doc_id)
        return self._scope_parser.parse(source)

    def _compose_scope_source(self, record: DocumentRecord) -> str:
        answered = [
            f"Clarification Answer: {item.answer}"
            for item in record.clarifications
            if item.answer
        ]
        return "\n".join(filter(None, [record.content, *answered]))

