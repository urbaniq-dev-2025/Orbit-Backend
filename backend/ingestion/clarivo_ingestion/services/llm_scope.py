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
    "2. Extract the document title/header - look for the main title at the beginning of the document, in headers, or in document metadata\n"
    "3. Extract information accurately - do not paraphrase or summarize unless necessary\n"
    "4. Group related functionality into logical technical modules \n"
    "5. Extract specific features with clear names and detailed descriptions\n"
    "6. Identify user personas, their goals, and pain points\n"
    "7. Extract functional, technical, and non-functional requirements\n"
    "8. Only include information that is explicitly stated in the document\n"
    "9. If information is missing, leave arrays empty - do not invent details\n\n"
    "When organizing modules and features:\n"
    "- Group features by technical area (e.g., Authentication, Menu, Payments, etc.)\n"
    "- Use clear, descriptive names for modules (e.g., 'Customer Profile', 'Menu & Ordering', 'Payment & Checkout')\n"
    "- Each module should have a meaningful name and a detailed summary describing what it does\n"
    "- Break down modules into features and sub-features(e.g., 'User Login' → 'Email/Password Login', 'Social Login')\n"
    "- Extract acceptance criteria from the document text\n"
    "- Set priority (P1, P2, P3) based on document language (must/critical = P1, should/nice-to-have = P2, future = P3)\n\n"
    "When suggesting modules:\n"
    "- Analyze the document type and business model to suggest relevant modules that are commonly needed\n"
    "- For SaaS products: suggest Subscription Management, Payment Gateway Integration, Billing & Invoicing\n"
    "- For e-commerce: suggest Shopping Cart, Checkout, Order Management, Inventory Management\n"
    "- For mobile apps: suggest Push Notifications, Offline Sync, App Store Integration\n"
    "- For platforms with users: suggest User Management, Role-Based Access Control, Analytics Dashboard\n"
    "- Only suggest modules that are NOT already explicitly mentioned in the document\n"
    "- Provide clear reasoning for why each module is suggested\n"
    "- Suggested modules should complement the extracted modules, not duplicate them\n\n"
    "Return strictly valid JSON with the exact shape below. Do not include commentary, markdown code fences, or explanations.\n\n"
    "Expected JSON shape:\n"
    "{\n"
    '  "document_title": "string - the main title/header of the document (extract from document header, title page, or first major heading)",\n'
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
    '  "suggested_modules": [\n'
    "    {\n"
    '      "name": "string - suggested module name (e.g., Subscription Management, Payment Gateway)",\n'
    '      "description": "string - brief description of why this module is suggested and what it would do",\n'
    '      "reason": "string - reason for suggestion (e.g., SaaS product typically requires subscription management)",\n'
    '      "features": ["string"] - array of suggested feature names for this module\n'
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
    "- Ensure feature names in modules.\n"
    "- Be thorough but concise - extract all relevant information\n"
    "- All arrays can be empty if no information is found in the document"
)

_USER_TEMPLATE = (
    "Analyze the following requirement document and extract all relevant information into the scope document format.\n"
    "Read the entire document carefully and extract:\n"
    "- Executive summary with overview and key points\n"
    "- User personas with their goals and pain points\n"
    "- Modules grouping related functionality\n"
    "- Suggested modules that would be beneficial based on the product type/business model\n"
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
        # Prefer OpenAI (for RAG), then Gemini, then Groq
        if (self._settings.openai_api_key is None and 
            self._settings.gemini_api_key is None and 
            self._settings.groq_api_key is None):
            raise self.ConfigurationError("Missing OPENAI_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY for LLM scope generation.")
        
        # Determine which API to use (priority: OpenAI > Gemini > Groq)
        # OpenAI is preferred for RAG model consistency
        if self._settings.openai_api_key is not None:
            self._api_provider = "openai"
            logger.info("Using OpenAI API for LLM scope generation (RAG-enabled)")
        elif self._settings.gemini_api_key is not None:
            self._api_provider = "gemini"
            logger.info("Using Gemini API for LLM scope generation")
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

    async def generate(self, content: str, template_structure: dict | None = None) -> ScopeDocument:
        """
        Generate scope document from content.
        
        Args:
            content: Document text to process
            template_structure: Optional template structure to guide module organization
        """
        if not content.strip():
            raise self.ParseError("No content available for LLM scope generation.")

        if self._api_provider == "gemini":
            raw_content = await self._call_gemini_api(content, template_structure)
        else:
            raw_content = await self._call_openai_compatible_api(content, template_structure)
        
        try:
            scope = self._parse_scope(raw_content)
            module_count = len(scope.modules) if scope.modules else 0
            feature_count = len(scope.features) if scope.features else 0
            logger.info("LLM scope generation succeeded with %d modules and %d features.", module_count, feature_count)
            return scope
        except self.ParseError as e:
            # If JSON parsing fails, log the raw content for debugging
            logger.error(f"JSON parsing failed. Raw content length: {len(raw_content)} chars")
            logger.debug(f"Raw content preview (first 5000 chars):\n{raw_content[:5000]}")
            # Re-raise to let caller handle (may want to fall back to heuristic parser)
            raise
    
    async def _call_gemini_api(self, content: str, template_structure: dict | None = None) -> str:
        """Call Gemini API with its specific format."""
        user_content = self._build_user_message(content, template_structure)
        
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
    
    async def _call_openai_compatible_api(self, content: str, template_structure: dict | None = None) -> str:
        """Call OpenAI-compatible API (OpenAI or Groq)."""
        payload = self._build_payload(content, template_structure)
        
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
            # Increased timeout for large documents: 600s (10 minutes) for read, 30s for connect
            # OpenAI API can take longer for large payloads and complex requests
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=30.0, read=600.0)) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("%s API request timed out after 600s: %s", provider_name, str(exc))
            raise self.ProviderError(f"{provider_name} API request timed out after 10 minutes. The request may be too large or the API is slow. Please try with a smaller document or split the content.") from exc
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

    def _build_payload(self, content: str, template_structure: dict | None = None) -> dict[str, Any]:
        # Build user message with RAG examples and template guidance if available
        user_content = self._build_user_message(content, template_structure)
        
        # Use appropriate model based on API
        if self._api_provider == "openai":
            model = self._settings.openai_model
        else:  # groq
            model = self._settings.groq_model
        
        # Adjust max_tokens based on model capabilities
        # gpt-4-turbo supports up to 4096 completion tokens
        # gpt-4o and gpt-4o-mini support higher limits
        # For large documents, we need more tokens for complete JSON response
        if "gpt-4-turbo" in model.lower():
            max_tokens = 4096  # gpt-4-turbo supports 4096 completion tokens
        elif "gpt-4o" in model.lower() or "gpt-4o-mini" in model.lower():
            max_tokens = 8000  # gpt-4o supports higher limits - increase for large JSON responses
        else:
            max_tokens = 4096  # Default to safe limit (for gpt-4-turbo)
        
        return {
            "model": model,
            "temperature": 0.1,  # Lower temperature for more consistent, accurate extraction
            "max_tokens": max_tokens,
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
    
    def _build_user_message(self, content: str, template_structure: dict | None = None) -> str:
        """
        Build the user message with RAG examples and template guidance if available.
        
        Args:
            content: Document text to process
            template_structure: Optional template structure to guide module organization
        """
        parts = []
        
        # Add template structure guidance if provided
        if template_structure:
            template_guidance = self._format_template_guidance(template_structure)
            if template_guidance:
                parts.append(template_guidance)
                logger.info("Including template structure guidance in prompt")
        
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
    
    def _format_template_guidance(self, template_structure: dict) -> str:
        """Format template structure as guidance for the LLM."""
        sections = template_structure.get("sections", [])
        if not sections:
            return ""
        
        parts = [
            "=== TEMPLATE STRUCTURE GUIDANCE ===",
            "Use the following template structure to organize modules and features:",
            "",
        ]
        
        for section in sections:
            section_title = section.get("title", "Untitled")
            section_type = section.get("section_type", "")
            section_desc = section.get("description", "")
            
            parts.append(f"- {section_title}")
            if section_type:
                parts.append(f"  Type: {section_type}")
            if section_desc:
                parts.append(f"  Description: {section_desc}")
            parts.append("")
        
        parts.append("IMPORTANT: Organize modules and features according to this template structure.")
        parts.append("The template provides guidance on how to group related functionality.")
        parts.append("")
        parts.append("=== END TEMPLATE GUIDANCE ===")
        parts.append("")
        
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
        
        # Try to parse directly first
        try:
            parsed_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed: {e}. Attempting to fix common JSON issues...")
            # Try to fix common JSON issues
            fixed_json = self._fix_json_common_issues(cleaned)
            try:
                parsed_data = json.loads(fixed_json)
                logger.info("Successfully parsed JSON after fixing common issues")
            except json.JSONDecodeError as e2:
                logger.warning(f"Fixed JSON still invalid: {e2}. Trying to extract JSON block...")
                # Try to extract JSON block
                json_candidate = self._extract_json_block(cleaned)
                if json_candidate is None:
                    # Log the problematic content for debugging (first 2000 chars)
                    logger.error(f"Failed to extract valid JSON. Content preview (first 2000 chars):\n{cleaned[:2000]}")
                    logger.error(f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}")
                    raise self.ParseError(f"LLM response did not contain valid JSON. Error at line {e.lineno}, column {e.colno}: {e.msg}")
                # Try to fix the extracted block too
                fixed_candidate = self._fix_json_common_issues(json_candidate)
                try:
                    parsed_data = json.loads(fixed_candidate)
                    logger.info("Successfully parsed extracted JSON block after fixing")
                except json.JSONDecodeError as e3:
                    logger.error(f"Extracted JSON block still invalid: {e3}")
                    logger.error(f"JSON block preview (first 2000 chars):\n{json_candidate[:2000]}")
                    raise self.ParseError(f"LLM response did not contain valid JSON even after extraction. Error: {e3.msg}")
        
        # Transform modules.features from objects to strings (feature names)
        if "modules" in parsed_data and isinstance(parsed_data["modules"], list):
            for module in parsed_data["modules"]:
                if "features" in module and isinstance(module["features"], list):
                    # Extract feature names if features are objects
                    feature_names = []
                    for feature in module["features"]:
                        if isinstance(feature, dict) and "name" in feature:
                            feature_names.append(feature["name"])
                        elif isinstance(feature, str):
                            feature_names.append(feature)
                    module["features"] = feature_names
        
        try:
            return ScopeDocument.model_validate(parsed_data)
        except ValidationError as exc:
            logger.error("LLM response failed schema validation: %s", exc)
            logger.debug("Failed JSON content: %s", json.dumps(parsed_data, indent=2)[:1000])
            raise self.ParseError("LLM response could not be coerced into ScopeDocument.") from exc

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
        # Try to find JSON object boundaries more accurately
        # Look for opening brace and try to find matching closing brace
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Count braces to find the matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found matching closing brace
                        candidate = text[start_idx:i+1]
                        return candidate
        
        # If we didn't find a matching brace, try the simple regex approach
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return None
    
    @staticmethod
    def _fix_json_common_issues(json_str: str) -> str:
        """Fix common JSON issues that LLMs sometimes produce."""
        fixed = json_str
        
        # Remove comments (JSON doesn't support comments)
        fixed = re.sub(r'//.*?$', '', fixed, flags=re.MULTILINE)
        fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)
        
        # Fix double opening braces (e.g., "{ { "name": ..." -> "{ "name": ...")
        fixed = re.sub(r'\{\s*\{', '{', fixed)
        
        # Fix double closing braces (e.g., "} }" -> "}")
        fixed = re.sub(r'\}\s*\}', '}', fixed)
        
        # Remove trailing commas before closing braces/brackets
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # Fix unescaped quotes in strings (basic attempt)
        # Replace single quotes with double quotes only in object keys (basic)
        fixed = re.sub(r"(\w+):\s*'([^']*)'", r'\1: "\2"', fixed)
        
        # Fix missing commas between object properties (look for } followed by { or "key":)
        # This is tricky, so we'll be conservative
        fixed = re.sub(r'\}\s*(\{|"[^"]+"\s*:)', r'}, \1', fixed)
        
        # Fix missing commas between array elements
        fixed = re.sub(r'\]\s*(\[|"[^"]+"|\{)', r'], \1', fixed)
        
        # Fix incomplete JSON by trying to close unclosed structures
        # Count braces and brackets to see if JSON is incomplete
        open_braces = fixed.count('{') - fixed.count('}')
        open_brackets = fixed.count('[') - fixed.count(']')
        
        # If JSON appears incomplete, try to close it
        if open_braces > 0 or open_brackets > 0:
            logger.warning(f"JSON appears incomplete: {open_braces} unclosed braces, {open_brackets} unclosed brackets")
            # Try to close arrays first, then objects
            fixed += ']' * open_brackets
            fixed += '}' * open_braces
        
        return fixed


