from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from clarivo_ingestion.core.config import Settings
from clarivo_ingestion.core.logging import get_logger
from clarivo_ingestion.schemas.scope import ScopeDocument, OutputFormatScopeDocument
from clarivo_ingestion.services.rag_examples import RAGExampleRetriever

logger = get_logger(__name__)

_CANONICAL_MODULES = [
    "Authentication & Profile",
    "Location & Store Management",
    "Menu Management",
    "Cart & Ordering",
    "Payments & Checkout",
    "Order Tracking & History",
    "Offers & Promotions",
    "Rewards & Loyalty",
    "Notifications & Geofencing",
    "Support & Help Center",
    "Admin Back Office (Menu, Offers, Orders)",
    "POS & Third-Party Integrations",
    "Analytics & Reporting",
    "Infrastructure & DevOps",
    "QA, Testing & Release Pipeline",
]

_SYSTEM_PROMPT = (
    "You are an expert Senior Business Analyst at a top software development agency. "
    "Your task is to analyze a client requirement document and extract structured information into a comprehensive scope document.\n\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. Read the ENTIRE document carefully before extracting information\n"
    "2. Extract information accurately - do not paraphrase or summarize unless necessary\n"
    "3. Group related functionality into logical modules\n"
    "4. Extract specific features with clear names and detailed descriptions\n"
    "5. Identify user personas, their goals, and pain points\n"
    "6. Extract functional, technical, and non-functional requirements\n"
    "7. Only include information that is explicitly stated in the document\n"
    "8. If information is missing, leave arrays empty - do not invent details\n\n"
    "When organizing modules and features:\n"
    "- Group features by functional area (e.g., Authentication, Menu, Payments, etc.)\n"
    "- Use clear, descriptive names for modules (e.g., 'Customer Profile', 'Menu & Ordering', 'Payment & Checkout')\n"
    "- Each feature should have a meaningful name and a detailed summary describing what it does\n"
    "- Extract acceptance criteria from the document text\n"
    "- Set priority (P1, P2, P3) based on document language (must/critical = P1, should/nice-to-have = P2, future = P3)\n\n"
    "Return strictly valid JSON with the exact shape below. Do not include commentary, markdown code fences, or explanations.\n\n"
    "Expected JSON shape:\n"
    "{\n"
    '  "executive_summary": {\n'
    '    "overview": "string - 2-3 sentence summary of the product/app",\n'
    '    "key_points": ["string"] - array of 5-10 key features/capabilities\n'
    "  },\n"
    '  "personas": [\n'
    "    {\n"
    '      "name": "string - persona name (e.g., Customer, Admin)",\n'
    '      "description": "string - who this persona is",\n'
    '      "goals": ["string"] - what this persona wants to achieve,\n'
    '      "pain_points": ["string"] - problems this persona faces\n'
    "    }\n"
    "  ],\n"
    '  "modules": [\n'
    "    {\n"
    '      "name": "string - module name (e.g., Customer Profile, Menu & Ordering)",\n'
    '      "description": "string - brief description of what this module does",\n'
    '      "features": ["string"] - array of feature names (references to features array below)\n'
    "    }\n"
    "  ],\n"
    '  "features": [\n'
    "    {\n"
    '      "name": "string - specific feature name (e.g., Authentication, Browse Menu)",\n'
    '      "summary": "string - detailed description of what this feature does",\n'
    '      "priority": "P1" | "P2" | "P3" - priority level,\n'
    '      "dependencies": ["string"] - other features this depends on,\n'
    '      "acceptance_criteria": ["string"] - specific requirements for this feature\n'
    "    }\n"
    "  ],\n"
    '  "functional_requirements": [\n'
    "    {\n"
    '      "statement": "string - requirement statement (e.g., The app must support...)"\n'
    "    }\n"
    "  ],\n"
    '  "technical_requirements": [\n'
    "    {\n"
    '      "statement": "string - technical requirement (e.g., API integration, database, etc.)"\n'
    "    }\n"
    "  ],\n"
    '  "non_functional_requirements": [\n'
    "    {\n"
    '      "statement": "string - non-functional requirement (e.g., performance, scalability, etc.)"\n'
    "    }\n"
    "  ],\n"
    '  "open_questions": [\n'
    "    {\n"
    '      "question": "string - question that needs clarification"\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "IMPORTANT:\n"
    "- Extract information accurately from the document - do not make up details\n"
    "- Use the document's own language and terminology when possible\n"
    "- Group related features into logical modules\n"
    "- Ensure feature names in modules.features array match names in features array\n"
    "- Be thorough but concise - extract all relevant information\n"
    "- All arrays can be empty if no information is found in the document"
)

_USER_TEMPLATE = (
    "Analyze the following requirement document and extract all relevant information into the scope document format.\n"
    "Read the entire document carefully and extract:\n"
    "- Executive summary with overview and key points\n"
    "- User personas with their goals and pain points\n"
    "- Modules grouping related functionality\n"
    "- Detailed features with summaries, priorities, and acceptance criteria\n"
    "- Functional, technical, and non-functional requirements\n"
    "- Any open questions that need clarification\n\n"
    "Document content:\n"
    "-------------------\n"
    "{document_text}\n"
    "-------------------\n\n"
    "Now generate the complete scope document JSON following the exact format specified in the system prompt."
)


class LLMDocumentScopeGenerator:
    """Call an external LLM to convert document text into a ScopeDocument."""

    class ConfigurationError(Exception):
        """Raised when configuration is incomplete."""

    class ProviderError(Exception):
        """Raised when the LLM provider returns an error."""

    class ParseError(Exception):
        """Raised when the LLM response cannot be parsed into the schema."""

    def __init__(self, settings: Settings, input_dir: Path | None = None, output_dir: Path | None = None) -> None:
        self._settings = settings
        # Prefer Gemini, then OpenAI, then Groq
        if (self._settings.gemini_api_key is None and 
            self._settings.openai_api_key is None and 
            self._settings.groq_api_key is None):
            raise self.ConfigurationError("Missing GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY for LLM scope generation.")
        
        # Determine which API to use (priority: Gemini > OpenAI > Groq)
        if self._settings.gemini_api_key is not None:
            self._api_provider = "gemini"
            logger.info("Using Gemini API for LLM scope generation")
        elif self._settings.openai_api_key is not None:
            self._api_provider = "openai"
            logger.info("Using OpenAI API for LLM scope generation")
        else:
            self._api_provider = "groq"
            logger.info("Using Groq API for LLM scope generation")
        
        # Initialize RAG retriever if directories are provided
        self._rag_retriever: RAGExampleRetriever | None = None
        if input_dir is not None and output_dir is not None:
            try:
                self._rag_retriever = RAGExampleRetriever(input_dir=input_dir, output_dir=output_dir, top_k=3)
                logger.info("RAG example retriever initialized with Input: %s, Output: %s", input_dir, output_dir)
            except Exception as exc:
                logger.warning("Failed to initialize RAG retriever: %s. Continuing without RAG examples.", exc)

    async def generate(self, content: str) -> ScopeDocument:
        if not content.strip():
            raise self.ParseError("No content available for LLM scope generation.")

        if self._api_provider == "gemini":
            raw_content = await self._call_gemini_api(content)
        else:
            raw_content = await self._call_openai_compatible_api(content)
        
        scope = self._parse_scope(raw_content)
        module_count = len(scope.modules) if scope.modules else 0
        feature_count = len(scope.features) if scope.features else 0
        logger.info("LLM scope generation succeeded with %d modules and %d features.", module_count, feature_count)
        return scope
    
    async def _call_gemini_api(self, content: str) -> str:
        """Call Gemini API with its specific format."""
        user_content = self._build_user_message(content)
        
        # Gemini uses a different payload structure with systemInstruction
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_content}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": _SYSTEM_PROMPT}
                ]
            },
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 6000,
            }
        }
        
        api_key = self._settings.gemini_api_key.get_secret_value()
        model = self._settings.gemini_model
        # Ensure model name has 'models/' prefix if not already present
        if not model.startswith("models/"):
            model = f"models/{model}"
        api_base = self._settings.gemini_api_base
        api_url = f"{api_base}/{model}:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                # Log response for debugging (first 500 chars)
                logger.debug("Gemini API response (first 500 chars): %s", str(response_data)[:500])
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("Gemini API returned %s: %s", exc.response.status_code, body)
            raise self.ProviderError(f"Gemini API error: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            logger.error("Gemini API request failed: %s", exc)
            raise self.ProviderError("Failed to reach Gemini API") from exc

        return self._extract_gemini_message(response_data)
    
    async def _call_openai_compatible_api(self, content: str) -> str:
        """Call OpenAI-compatible API (OpenAI or Groq)."""
        payload = self._build_payload(content)
        
        # Use OpenAI or Groq based on available API key
        if self._api_provider == "openai":
            api_key = self._settings.openai_api_key.get_secret_value()
            api_url = str(self._settings.openai_api_url)
            provider_name = "OpenAI"
        else:  # groq
            api_key = self._settings.groq_api_key.get_secret_value()
            api_url = str(self._settings.groq_api_url)
            provider_name = "Groq"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            payload_size = len(json.dumps(payload))
            logger.info("Calling %s API: %s (payload: %d bytes, model: %s)", 
                       provider_name, api_url, payload_size, payload.get("model", "unknown"))
            logger.debug("Full payload (first 500 chars): %s", json.dumps(payload)[:500])
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0)) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("%s API request timed out after 120s: %s", provider_name, str(exc))
            raise self.ProviderError(f"{provider_name} API request timed out. The request may be too large or the API is slow.") from exc
        except httpx.ConnectTimeout as exc:
            logger.error("%s API connection timeout: %s", provider_name, str(exc))
            raise self.ProviderError(f"Failed to connect to {provider_name} API (connection timeout)") from exc
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("%s API returned %s: %s", provider_name, exc.response.status_code, body)
            raise self.ProviderError(f"{provider_name} API error: {exc.response.status_code} - {body[:500]}") from exc
        except httpx.HTTPError as exc:
            logger.error("%s API request failed: %s (type: %s)", provider_name, str(exc), type(exc).__name__)
            raise self.ProviderError(f"Failed to reach {provider_name} API: {str(exc)}") from exc

        return self._extract_message(response.json())

    def _build_payload(self, content: str) -> dict[str, Any]:
        # Build user message with RAG examples if available
        user_content = self._build_user_message(content)
        
        # Use appropriate model based on API
        if self._api_provider == "openai":
            model = self._settings.openai_model
        else:  # groq
            model = self._settings.groq_model
        
        return {
            "model": model,
            "temperature": 0.1,  # Lower temperature for more consistent, accurate extraction
            "max_tokens": 6000,  # Increased for more detailed scope documents
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        }
    
    def _extract_gemini_message(self, data: dict[str, Any]) -> str:
        """Extract message content from Gemini API response."""
        try:
            # Log the full response for debugging (truncated to avoid huge logs)
            response_str = json.dumps(data, indent=2)
            logger.debug("Gemini API response structure (first 2000 chars): %s", response_str[:2000])
            if len(response_str) > 2000:
                logger.debug("... (response truncated, total length: %d)", len(response_str))
            
            # Check for errors first
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error("Gemini API error: %s", error_msg)
                raise self.ProviderError(f"Gemini API error: {error_msg}")
            
            # Extract from candidates
            candidates = data.get("candidates", [])
            if not candidates:
                # Check if there's a finishReason that indicates blocking
                logger.error("No candidates in Gemini response. Full response: %s", json.dumps(data, indent=2))
                raise self.ProviderError("No candidates in Gemini response. The model may have blocked the content.")
            
            candidate = candidates[0]
            
            # Check for finish reason
            finish_reason = candidate.get("finishReason", "")
            if finish_reason and finish_reason != "STOP":
                logger.warning("Gemini finish reason: %s", finish_reason)
                if finish_reason == "SAFETY":
                    raise self.ProviderError("Gemini blocked the response due to safety filters")
                elif finish_reason == "MAX_TOKENS":
                    logger.warning("Response was truncated due to max tokens")
            
            content = candidate.get("content", {})
            if not content:
                logger.error("No content in candidate. Candidate: %s", json.dumps(candidate, indent=2))
                raise self.ProviderError("No content in Gemini response candidate")
            
            parts = content.get("parts", [])
            if not parts:
                # Log at INFO level so we can see what's happening
                logger.info("No parts in content. Full response: %s", json.dumps(data, indent=2))
                logger.info("Candidate structure: %s", json.dumps(candidate, indent=2))
                logger.info("Content structure: %s", json.dumps(content, indent=2))
                raise self.ProviderError("No parts in Gemini response content")
            
            text = parts[0].get("text", "")
            if not text:
                logger.error("Empty text in parts. Parts: %s", json.dumps(parts, indent=2))
                raise self.ProviderError("Empty text in Gemini response")
            
            return text
            
        except self.ProviderError:
            # Re-raise provider errors as-is
            raise
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected Gemini response structure: %s", json.dumps(data, indent=2))
            raise self.ProviderError("Unexpected Gemini response structure.") from exc
    
    def _build_user_message(self, content: str) -> str:
        """Build the user message with RAG examples if available."""
        parts = []
        
        # Add RAG examples if retriever is available
        if self._rag_retriever is not None:
            try:
                examples = self._rag_retriever.find_similar_examples(content)
                if examples:
                    examples_text = self._rag_retriever.format_examples_for_prompt(examples)
                    parts.append(examples_text)
                    logger.info("Including %d RAG examples in prompt", len(examples))
            except Exception as exc:
                logger.warning("Failed to retrieve RAG examples: %s. Continuing without examples.", exc)
        
        # Add the current document
        parts.append(_USER_TEMPLATE.format(document_text=content.strip()))
        
        return "\n".join(parts)

    @staticmethod
    def _extract_message(data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected response payload: %s", json.dumps(data))
            raise LLMDocumentScopeGenerator.ProviderError("Unexpected LLM response structure.") from exc

    def _parse_scope(self, raw_content: str) -> ScopeDocument:
        cleaned = self._strip_code_fences(raw_content)
        try:
            return ScopeDocument.model_validate_json(cleaned)
        except ValidationError as exc:
            logger.debug("Direct JSON validation failed (%s). Attempting to locate JSON block.", exc)
            json_candidate = self._extract_json_block(cleaned)
            if json_candidate is None:
                raise self.ParseError("LLM response did not contain valid JSON.") from exc
            try:
                return ScopeDocument.model_validate_json(json_candidate)
            except ValidationError as inner_exc:
                logger.error("LLM response failed schema validation: %s", inner_exc)
                logger.debug("Failed JSON content: %s", json_candidate[:500])
                raise self.ParseError("LLM response could not be coerced into ScopeDocument.") from inner_exc

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            if stripped.endswith("```"):
                stripped = stripped[: -3].strip()
        return stripped

    @staticmethod
    def _extract_json_block(text: str) -> str | None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        candidate = match.group(0)
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return candidate


