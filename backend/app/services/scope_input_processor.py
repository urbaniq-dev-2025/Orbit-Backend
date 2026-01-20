"""
Scope Input Processor Service

Handles multiple input sources for scope creation:
- PDF/DOCX uploads
- Text paste
- Speech transcription
- AI generation
- Google Docs URLs
- Notion URLs
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal, Optional, Union
from uuid import UUID

import httpx
from fastapi import UploadFile

from app.core.logging import get_logger

logger = get_logger(__name__)


class ScopeInputProcessor:
    """Processes input from various sources for scope creation."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        google_api_credentials: Optional[str] = None,
        notion_api_key: Optional[str] = None,
    ):
        """
        Initialize input processor.

        Args:
            openai_api_key: OpenAI API key for Whisper (speech transcription) and AI generation
            google_api_credentials: Google API credentials path for Docs access
            notion_api_key: Notion API integration token
        """
        self.openai_api_key = openai_api_key
        self.google_api_credentials = google_api_credentials
        self.notion_api_key = notion_api_key
        
        # If no API key provided, try to get from settings
        if not self.openai_api_key:
            from app.core.config import get_settings
            settings = get_settings()
            self.openai_api_key = settings.openai_api_key

    async def process_input(
        self,
        input_type: Literal["pdf", "text", "speech", "ai_generate", "google_docs", "notion"],
        input_data: Union[str, bytes, UploadFile, None] = None,
        input_url: Optional[str] = None,
        workspace_id: Optional[UUID] = None,
    ) -> str:
        """
        Process input from various sources and return unified text.

        Args:
            input_type: Type of input source
            input_data: Input data (text, file bytes, or UploadFile)
            input_url: URL for Google Docs or Notion
            workspace_id: Workspace ID for context

        Returns:
            Extracted/processed text ready for RAG processing
        """
        if input_type == "pdf":
            return await self._extract_from_pdf(input_data)
        elif input_type == "text":
            if isinstance(input_data, str):
                return input_data
            elif isinstance(input_data, bytes):
                return input_data.decode("utf-8")
            else:
                raise ValueError("Text input must be string or bytes")
        elif input_type == "speech":
            return await self._transcribe_speech(input_data)
        elif input_type == "ai_generate":
            return await self._generate_from_description(input_data)
        elif input_type == "google_docs":
            if not input_url:
                raise ValueError("Google Docs URL is required")
            return await self._extract_from_google_docs(input_url)
        elif input_type == "notion":
            if not input_url:
                raise ValueError("Notion URL is required")
            return await self._extract_from_notion(input_url)
        else:
            raise ValueError(f"Unsupported input type: {input_type}")

    async def _extract_from_pdf(self, file_data: Union[bytes, UploadFile]) -> str:
        """Extract text from PDF file."""
        # Read file content
        if isinstance(file_data, UploadFile):
            content = await file_data.read()
        else:
            content = file_data

        # Use existing text extraction utility
        from clarivo_ingestion.utils.text_extraction import extract_text_from_bytes

        text = extract_text_from_bytes("document.pdf", content)
        if not text.strip():
            raise ValueError("No text extracted from PDF")
        return text

    async def _transcribe_speech(self, audio_file: Union[bytes, UploadFile]) -> str:
        """
        Transcribe speech to text using OpenAI Whisper API.

        Note: Requires OpenAI API key configured.
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured for speech transcription")

        # Read audio content
        if isinstance(audio_file, UploadFile):
            audio_content = await audio_file.read()
        else:
            audio_content = audio_file

        # Call OpenAI Whisper API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.openai_api_key}"},
                files={"file": ("audio.mp3", audio_content, "audio/mpeg")},
                data={"model": "whisper-1"},
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")

    async def _generate_from_description(self, description: str) -> str:
        """
        Generate detailed requirements from a brief description using AI.

        Note: This uses the same LLM service as scope generation.
        For now, returns the description as-is. Can be enhanced to
        expand the description into detailed requirements.
        """
        # TODO: Implement AI expansion of description
        # For now, return description as-is
        logger.info("AI generation from description - returning description as-is (expansion not yet implemented)")
        return description

    async def _extract_from_google_docs(self, url: str) -> str:
        """
        Extract content from Google Docs URL.

        Note: Requires Google API credentials and OAuth setup.
        Uses Google Docs API to fetch document content.
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError:
            raise ValueError(
                "Google API client libraries not installed. "
                "Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        if not self.google_api_credentials:
            raise ValueError("Google API credentials not configured")

        # Parse Google Docs ID from URL
        doc_id = self._parse_google_docs_id(url)
        if not doc_id:
            raise ValueError(f"Invalid Google Docs URL: {url}")

        try:
            # Load credentials (assuming service account or OAuth token)
            # For service account:
            # from google.oauth2 import service_account
            # credentials = service_account.Credentials.from_service_account_file(self.google_api_credentials)
            
            # For OAuth (user token):
            # credentials = Credentials.from_authorized_user_file(self.google_api_credentials)
            
            # For now, use a placeholder - in production, implement proper OAuth flow
            # This requires user authentication flow
            logger.warning("Google Docs extraction requires OAuth setup - using placeholder")
            
            # Placeholder: Return error with instructions
            raise NotImplementedError(
                "Google Docs integration requires OAuth setup. "
                "Please configure Google OAuth credentials and implement authentication flow."
            )
            
            # Once credentials are set up, use this:
            # service = build('docs', 'v1', credentials=credentials)
            # document = service.documents().get(documentId=doc_id).execute()
            # 
            # # Extract text content
            # content = []
            # for element in document.get('body', {}).get('content', []):
            #     if 'paragraph' in element:
            #         for text_element in element['paragraph'].get('elements', []):
            #             if 'textRun' in text_element:
            #                 content.append(text_element['textRun'].get('content', ''))
            # 
            # return ''.join(content)
            
        except HttpError as e:
            logger.error(f"Google Docs API error: {e}")
            raise ValueError(f"Failed to fetch Google Docs content: {str(e)}")

    async def _extract_from_notion(self, url: str) -> str:
        """
        Extract content from Notion page URL.

        Note: Requires Notion API integration token.
        Uses Notion API to fetch page content.
        """
        try:
            from notion_client import Client
        except ImportError:
            raise ValueError(
                "Notion client library not installed. "
                "Install with: pip install notion-client"
            )

        if not self.notion_api_key:
            raise ValueError("Notion API key not configured")

        # Parse Notion page ID from URL
        page_id = self._parse_notion_page_id(url)
        if not page_id:
            raise ValueError(f"Invalid Notion URL: {url}")

        try:
            # Initialize Notion client
            notion = Client(auth=self.notion_api_key)
            
            # Fetch page content
            page = notion.pages.retrieve(page_id=page_id)
            
            # Get page blocks
            blocks = notion.blocks.children.list(block_id=page_id)
            
            # Extract text from blocks
            content_parts = []
            for block in blocks.get("results", []):
                block_type = block.get("type")
                
                if block_type == "paragraph":
                    text = block.get("paragraph", {}).get("rich_text", [])
                    content_parts.append(" ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "heading_1":
                    text = block.get("heading_1", {}).get("rich_text", [])
                    content_parts.append("# " + " ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "heading_2":
                    text = block.get("heading_2", {}).get("rich_text", [])
                    content_parts.append("## " + " ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "heading_3":
                    text = block.get("heading_3", {}).get("rich_text", [])
                    content_parts.append("### " + " ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "bulleted_list_item":
                    text = block.get("bulleted_list_item", {}).get("rich_text", [])
                    content_parts.append("- " + " ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "numbered_list_item":
                    text = block.get("numbered_list_item", {}).get("rich_text", [])
                    content_parts.append("1. " + " ".join([t.get("plain_text", "") for t in text]))
                elif block_type == "code":
                    text = block.get("code", {}).get("rich_text", [])
                    content_parts.append("```\n" + " ".join([t.get("plain_text", "") for t in text]) + "\n```")
            
            return "\n\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Notion API error: {e}")
            raise ValueError(f"Failed to fetch Notion content: {str(e)}")

    def _parse_google_docs_id(self, url: str) -> Optional[str]:
        """Extract Google Docs ID from URL."""
        # Google Docs URL format: https://docs.google.com/document/d/{DOC_ID}/edit
        import re

        pattern = r"/document/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def _parse_notion_page_id(self, url: str) -> Optional[str]:
        """Extract Notion page ID from URL."""
        # Notion URL format: https://www.notion.so/{PAGE_ID} or https://{workspace}.notion.site/{PAGE_ID}
        import re

        # Extract UUID from URL
        pattern = r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
        match = re.search(pattern, url)
        if match:
            page_id = match.group(1)
            # Convert to proper UUID format if needed
            if len(page_id) == 32:
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            return page_id
        return None
