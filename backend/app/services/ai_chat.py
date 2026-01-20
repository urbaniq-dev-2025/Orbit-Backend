from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.models import Client, ConversationHistory, Project, Scope, Workspace
from app.schemas.ai_chat import ActionData, ChatResponse, IntentInfo
from app.services.llm_client import LLMClient

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Orbit, an AI assistant for project management. Your role is to:
1. Understand user intent (navigate, query, create, update, search)
2. Extract relevant entities (dates, priorities, titles, entity IDs)
3. Generate appropriate responses with actionable suggestions
4. Provide helpful, contextual information about the workspace

Available Actions:
- navigate: Navigate to pages (/dashboard/clients, /dashboard/projects, /dashboard/scopes, /dashboard/prds, /dashboard, /dashboard/settings)
- create_task: Create a task with title, dueDate, priority, category
- create_reminder: Create a calendar event/reminder
- create_entity: Create scope, client, project, or PRD
- query: Answer questions about workspace data
- search: Search for entities across the workspace
- get_insights: Get analytics/insights

Response Format (JSON):
{
  "response": "Natural language response to the user",
  "intent": {
    "type": "create_task|navigate|query|create_reminder|create_entity|update_entity|search|get_insights",
    "confidence": 0.0-1.0,
    "entities": {
      "title": "string (for tasks/entities)",
      "dueDate": "ISO date string (YYYY-MM-DD)",
      "priority": "none|low|medium|high",
      "category": "string",
      "route": "string (for navigation)",
      "reminderTime": "ISO datetime string (for reminders)"
    }
  },
  "actions": [
    {
      "type": "create_task|navigate|create_reminder|...",
      "label": "Action Button Label",
      "icon": "create|navigate|complete",
      "data": {
        "title": "string",
        "dueDate": "ISO date string",
        "priority": "string",
        "category": "string"
      },
      "route": "/dashboard/path (for navigate actions)"
    }
  ],
  "suggestions": ["Suggested follow-up question 1", "Suggested follow-up question 2"]
}

Navigation Examples:
- "Go to clients" → navigate to /dashboard/clients
- "Show me projects" → navigate to /dashboard/projects
- "Open scopes" → navigate to /dashboard/scopes
- "Take me to PRDs" → navigate to /dashboard/prds
- "Show dashboard" → navigate to /dashboard
- "Open settings" → navigate to /dashboard/settings

Task Creation Examples:
- "Create a task to review Q1 budget by Friday" → create_task with title="Review Q1 budget", dueDate="Friday date"
- "Remind me to call Acme Corp tomorrow at 2pm" → create_reminder with title="Call Acme Corp", reminderTime="tomorrow 2pm"
- "Add a task: Finalize design system (high priority)" → create_task with title="Finalize design system", priority="high"

Be helpful, concise, and action-oriented. Always provide actionable suggestions when appropriate."""


class AIChatService:
    """Service for processing AI chat messages."""

    def __init__(self):
        try:
            self.llm = LLMClient()
        except ValueError as exc:
            logger.warning("LLM client not available: %s", str(exc))
            self.llm = None

    async def process_message(
        self,
        session: AsyncSession,
        message: str,
        user_id: UUID,
        workspace_id: Optional[UUID],
        conversation_id: Optional[UUID],
        context: Dict[str, Any],
    ) -> ChatResponse:
        """Process a user message and return AI response with actions."""
        if not self.llm:
            raise Exception("AI chat is not available. Please configure OPENAI_API_KEY.")

        # Generate or use existing conversation ID
        if not conversation_id:
            conversation_id = uuid.uuid4()

        # Get workspace context
        workspace_context = {}
        if workspace_id:
            try:
                workspace_context = await _get_workspace_context(session, workspace_id)
            except Exception as exc:
                logger.warning("Failed to get workspace context: %s", str(exc))

        # Get conversation history
        history = await self._get_conversation_history(session, conversation_id, limit=10)

        # Build prompt with context
        prompt = self._build_prompt(message, workspace_context, history, context)

        # Call LLM
        try:
            llm_response = await self.llm.chat_with_json_response(
                messages=[{"role": "user", "content": message}],
                system_prompt=prompt,
                temperature=0.7,
            )
        except Exception as exc:
            logger.error("LLM call failed: %s", str(exc))
            # Return a fallback response
            return ChatResponse(
                response="I'm sorry, I'm having trouble processing your request right now. Please try again.",
                intent=IntentInfo(type="query", confidence=0.0),
                conversation_id=conversation_id,
            )

        # Parse and validate response
        parsed = self._parse_response(llm_response)

        # Store messages in conversation history
        await self._store_message(
            session, user_id, workspace_id, conversation_id, message, "user"
        )
        await self._store_message(
            session,
            user_id,
            workspace_id,
            conversation_id,
            parsed["response"],
            "assistant",
            parsed.get("intent"),
            parsed.get("actions"),
        )

        return ChatResponse(
            response=parsed["response"],
            intent=IntentInfo(**parsed["intent"]),
            actions=[ActionData(**action) for action in parsed.get("actions", [])],
            conversation_id=conversation_id,
            suggestions=parsed.get("suggestions"),
        )

    def _build_prompt(
        self,
        message: str,
        workspace_context: Dict[str, Any],
        history: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        """Build the system prompt with workspace context."""
        prompt_parts = [SYSTEM_PROMPT]

        # Add workspace context
        if workspace_context:
            prompt_parts.append("\n\nWorkspace Context:")
            if "client_count" in workspace_context:
                prompt_parts.append(f"- Active Clients: {workspace_context.get('client_count', 0)}")
            if "project_count" in workspace_context:
                prompt_parts.append(f"- Active Projects: {workspace_context.get('project_count', 0)}")
            if "scope_count" in workspace_context:
                prompt_parts.append(f"- Active Scopes: {workspace_context.get('scope_count', 0)}")

        # Add conversation history
        if history:
            prompt_parts.append("\n\nRecent Conversation:")
            for msg in history[-5:]:  # Last 5 messages
                prompt_parts.append(f"{msg['role']}: {msg['message']}")

        # Add current context
        if context.get("current_page"):
            prompt_parts.append(f"\n\nCurrent Page: {context['current_page']}")

        return "\n".join(prompt_parts)

    def _parse_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        # Ensure required fields exist
        if "response" not in llm_response:
            llm_response["response"] = "I understand. How can I help you?"

        if "intent" not in llm_response:
            llm_response["intent"] = {"type": "query", "confidence": 0.5, "entities": {}}
        elif not isinstance(llm_response["intent"], dict):
            llm_response["intent"] = {"type": "query", "confidence": 0.5, "entities": {}}

        # Ensure actions is a list
        if "actions" not in llm_response:
            llm_response["actions"] = []
        elif not isinstance(llm_response["actions"], list):
            llm_response["actions"] = []

        return llm_response

    async def _get_conversation_history(
        self, session: AsyncSession, conversation_id: UUID, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a conversation ID."""
        result = await session.execute(
            select(ConversationHistory)
            .where(ConversationHistory.conversation_id == conversation_id)
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [
            {"role": msg.role, "message": msg.message, "created_at": msg.created_at.isoformat()}
            for msg in reversed(messages)  # Reverse to get chronological order
        ]

    async def _store_message(
        self,
        session: AsyncSession,
        user_id: UUID,
        workspace_id: Optional[UUID],
        conversation_id: UUID,
        message: str,
        role: str,
        intent: Optional[Dict[str, Any]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Store a message in conversation history."""
        if not workspace_id:
            # Try to get user's default workspace
            result = await session.execute(
                select(Workspace).where(Workspace.owner_id == user_id).limit(1)
            )
            workspace = result.scalar_one_or_none()
            if not workspace:
                logger.warning("No workspace found for user %s, skipping conversation history", user_id)
                return
            workspace_id = workspace.id

        conversation_msg = ConversationHistory(
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            message=message,
            intent_type=intent.get("type") if intent else None,
            intent_confidence=intent.get("confidence") if intent else None,
            actions=actions,
        )
        session.add(conversation_msg)
        await session.commit()


async def _get_workspace_context(session: AsyncSession, workspace_id: UUID) -> Dict[str, Any]:
    """Get workspace context for AI chat."""
    # Get counts
    client_count = await session.scalar(
        select(func.count()).select_from(Client).where(Client.workspace_id == workspace_id)
    )
    project_count = await session.scalar(
        select(func.count()).select_from(Project).where(Project.workspace_id == workspace_id)
    )
    scope_count = await session.scalar(
        select(func.count()).select_from(Scope).where(Scope.workspace_id == workspace_id)
    )

    return {
        "client_count": client_count or 0,
        "project_count": project_count or 0,
        "scope_count": scope_count or 0,
    }
