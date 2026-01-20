from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMClient:
    """Client for interacting with OpenAI API for AI chat."""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for AI chat")
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat request to OpenAI API and return the response."""
        if system_prompt:
            formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            formatted_messages = messages

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            logger.error("OpenAI API request timed out: %s", str(exc))
            raise Exception("AI service timeout. Please try again.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI API returned %s: %s", exc.response.status_code, exc.response.text)
            raise Exception(f"AI service error: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            logger.error("OpenAI API request failed: %s", str(exc))
            raise Exception("Failed to reach AI service. Please try again.") from exc

    async def chat_with_json_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Send a chat request expecting a JSON response."""
        if system_prompt:
            formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            formatted_messages = messages

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON response: %s", str(exc))
            raise Exception("AI service returned invalid JSON") from exc
        except httpx.TimeoutException as exc:
            logger.error("OpenAI API request timed out: %s", str(exc))
            raise Exception("AI service timeout. Please try again.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI API returned %s: %s", exc.response.status_code, exc.response.text)
            raise Exception(f"AI service error: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            logger.error("OpenAI API request failed: %s", str(exc))
            raise Exception("Failed to reach AI service. Please try again.") from exc
