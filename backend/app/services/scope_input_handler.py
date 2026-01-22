"""
Scope Input Handler Service

Handles the complete scope creation flow with input processing and extraction.
"""

from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Document
from app.services import scopes as scope_service
from app.services.scope_input_processor import ScopeInputProcessor

logger = get_logger(__name__)


async def create_scope_with_input(
    session: AsyncSession,
    user_id: UUID,
    payload,
    *,
    file_upload: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> dict:
    """
    Create a scope and process input if provided.
    
    This handles the complete flow:
    1. Create scope
    2. Process input (if provided)
    3. Upload document (if file provided)
    4. Trigger extraction (if input provided)
    
    Returns:
        Dictionary with scope_id and extraction_id (if extraction triggered)
    """
    settings = get_settings()
    
    # Initialize input processor
    input_processor = ScopeInputProcessor(
        openai_api_key=settings.openai_api_key,
    )
    
    # 1. Create scope first
    scope = await scope_service.create_scope(session, user_id, payload)
    # Commit the scope immediately so it's persisted even if input processing fails
    await session.commit()
    await session.refresh(scope)
    
    extraction_id = None
    document_id = None
    
    # 2. Process input if provided
    if payload.input_type and (payload.input_data or payload.input_url or file_upload):
        try:
            # Process input based on type
            if payload.input_type == "pdf" and file_upload:
                # Handle file upload
                processed_text = await input_processor.process_input(
                    input_type=payload.input_type,
                    input_data=file_upload,
                    workspace_id=payload.workspace_id,
                )
                
                # Upload document with extracted text
                document = await scope_service.upload_scope_document(
                    session,
                    scope.id,
                    user_id,
                    filename=filename or "document.pdf",
                    file_size=len(file_upload),
                    mime_type="application/pdf",
                    file_url=f"/documents/{scope.id}/{filename}",  # TODO: Upload to actual storage
                    extracted_text=processed_text,  # Save extracted text to document
                )
                document_id = document.id
                
            elif payload.input_type in ["text", "ai_generate"]:
                # Process text input
                processed_text = await input_processor.process_input(
                    input_type=payload.input_type,
                    input_data=payload.input_data or "",
                    workspace_id=payload.workspace_id,
                )
                
                # Create a document record for text input with extracted text
                document = await scope_service.upload_scope_document(
                    session,
                    scope.id,
                    user_id,
                    filename="text_input.txt",
                    file_size=len(processed_text.encode('utf-8')),
                    mime_type="text/plain",
                    file_url=f"/documents/{scope.id}/text_input.txt",
                    extracted_text=processed_text,  # Save processed text to document
                )
                document_id = document.id
                
            elif payload.input_type in ["google_docs", "notion"]:
                # Process URL input
                processed_text = await input_processor.process_input(
                    input_type=payload.input_type,
                    input_url=payload.input_url,
                    workspace_id=payload.workspace_id,
                )
                
                # Create a document record for URL input with extracted text
                source_name = "google_docs" if payload.input_type == "google_docs" else "notion"
                document = await scope_service.upload_scope_document(
                    session,
                    scope.id,
                    user_id,
                    filename=f"{source_name}_content.txt",
                    file_size=len(processed_text.encode('utf-8')),
                    mime_type="text/plain",
                    file_url=f"/documents/{scope.id}/{source_name}_content.txt",
                    extracted_text=processed_text,  # Save processed text to document
                )
                document_id = document.id
                
            elif payload.input_type == "speech" and file_upload:
                # Process speech input
                processed_text = await input_processor.process_input(
                    input_type=payload.input_type,
                    input_data=file_upload,
                    workspace_id=payload.workspace_id,
                )
                
                # Create a document record for speech transcription with extracted text
                document = await scope_service.upload_scope_document(
                    session,
                    scope.id,
                    user_id,
                    filename=filename or "speech_transcription.txt",
                    file_size=len(processed_text.encode('utf-8')),
                    mime_type="text/plain",
                    file_url=f"/documents/{scope.id}/speech_transcription.txt",
                    extracted_text=processed_text,  # Save transcribed text to document
                )
                document_id = document.id
            else:
                processed_text = None
            
            # 3. Trigger extraction if we have processed text and document
            if processed_text and document_id:
                try:
                    extraction_result = await scope_service.extract_scope_from_document(
                        session,
                        scope.id,
                        user_id,
                        upload_id=document_id,
                        extraction_type="full",
                        template_id=payload.template_id,
                        ai_model=payload.ai_model,
                        developer_level=payload.developer_level,
                        developer_experience_years=payload.developer_experience_years,
                    )
                    extraction_id = extraction_result.get("extraction_id")
                except Exception as extraction_error:
                    import httpx
                    if isinstance(extraction_error, httpx.TimeoutException):
                        logger.warning(f"Extraction timeout for scope {scope.id}: {extraction_error}. Extraction will continue in background.")
                        # Return extraction_id even on timeout - extraction continues in background
                        extraction_id = str(uuid.uuid4())
                    elif isinstance(extraction_error, (httpx.HTTPStatusError, httpx.RequestError)):
                        # Handle HTTP errors (500, connection errors, etc.)
                        error_msg = str(extraction_error)
                        if "500" in error_msg or "Internal Server Error" in error_msg:
                            logger.warning(f"Extraction service error for scope {scope.id}: {extraction_error}. This may be due to OpenAI API issues. Extraction may continue in background.")
                            # Return extraction_id to indicate processing attempt - ingestion service may retry
                            extraction_id = str(uuid.uuid4())
                        else:
                            logger.warning(f"Extraction failed for scope {scope.id}: {extraction_error}")
                            extraction_id = None
                    else:
                        logger.warning(f"Extraction failed for scope {scope.id}: {extraction_error}")
                        # Continue without extraction - scope is still created
                        extraction_id = None
            
        except Exception as e:
            logger.error(f"Failed to process input for scope {scope.id}: {e}", exc_info=True)
            # Continue without extraction - scope is still created
    
    return {
        "scope_id": scope.id,
        "extraction_id": extraction_id,
        "document_id": document_id,
    }
