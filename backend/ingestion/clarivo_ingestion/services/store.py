from __future__ import annotations

import asyncio
from uuid import UUID

from clarivo_ingestion.schemas.documents import ClarificationItem, DocumentRecord


class InMemoryDocumentStore:
    """Thread-safe in-memory persistence layer for early development."""

    def __init__(self) -> None:
        self._documents: dict[UUID, DocumentRecord] = {}
        self._lock = asyncio.Lock()

    async def save(self, record: DocumentRecord) -> None:
        async with self._lock:
            self._documents[record.doc_id] = record

    async def get(self, doc_id: UUID) -> DocumentRecord | None:
        async with self._lock:
            return self._documents.get(doc_id)

    async def update(self, record: DocumentRecord) -> None:
        async with self._lock:
            self._documents[record.doc_id] = record

    async def add_clarification(self, doc_id: UUID, clarification: ClarificationItem) -> None:
        async with self._lock:
            record = self._documents.get(doc_id)
            if record is None:
                raise KeyError("Document not found")
            record.clarifications.append(clarification)
            self._documents[doc_id] = record

    async def delete(self, doc_id: UUID) -> None:
        async with self._lock:
            self._documents.pop(doc_id, None)


store = InMemoryDocumentStore()

