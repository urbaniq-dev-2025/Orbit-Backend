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
      "date": "ISO date string (YYYY-MM-DD) - for reminders",`n      "time": "Time string (HH:MM format) - for reminders",`n      "type": "event|deadline - for reminders"
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
- "Remind me to call Acme Corp tomorrow at 2pm" → create_reminder with title="Call Acme Corp", date="tomorrow date (YYYY-MM-DD)", time="14:00", type="event"
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

        # Ensure intent has required fields
        intent_data = parsed.get("intent", {})
        if not isinstance(intent_data, dict):
            intent_data = {"type": "query", "confidence": 0.5, "entities": {}}
        
        # Ensure required intent fields exist
        if "type" not in intent_data:
            intent_data["type"] = "query"
        if "confidence" not in intent_data:
            intent_data["confidence"] = 0.5
        if "entities" not in intent_data:
            intent_data["entities"] = {}
        
        # Execute actions automatically for create_reminder and create_task
        executed_actions = []
        created_entity_id = None
        
        if intent_data.get("type") == "create_reminder" and workspace_id:
            try:
                created_entity_id = await self._execute_create_reminder(
                    session, user_id, workspace_id, intent_data.get("entities", {})
                )
                logger.info(f"Created reminder {created_entity_id} from chatbot")
            except Exception as exc:
                logger.error(f"Failed to create reminder from chatbot: {exc}", exc_info=True)
                # Don't fail the whole request, just log the error
        
        # Ensure actions is a list
        actions_list = parsed.get("actions", [])
        if not isinstance(actions_list, list):
            actions_list = []
        
        
        # Post-process actions to fix reminder payloads - convert reminderTime to date/time
        for action in actions_list:
            if action.get("type") == "create_reminder" and action.get("data"):
                action_data = action["data"]
                # Convert reminderTime to date and time if present
                if "reminderTime" in action_data:
                    reminder_time_str = action_data.pop("reminderTime")
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(reminder_time_str.replace("Z", "+00:00"))
                        action_data["date"] = dt.strftime("%Y-%m-%d")
                        action_data["time"] = dt.strftime("%H:%M")
                        logger.info(f"Converted reminderTime to date/time: date={action_data['date']}, time={action_data['time']}")
                    except Exception as e:
                        logger.warning(f"Failed to convert reminderTime: {e}")
                        from datetime import date
                        action_data["date"] = date.today().strftime("%Y-%m-%d")
                        action_data["time"] = None
                # Ensure required fields are present
                if "date" not in action_data:
                    from datetime import date
                    action_data["date"] = date.today().strftime("%Y-%m-%d")
                if "type" not in action_data:
                    action_data["type"] = "event"
                # Ensure workspaceId is present
                if "workspaceId" not in action_data and workspace_id:
                    action_data["workspaceId"] = str(workspace_id)
        # Update response if entity was created
        response_text = parsed.get("response", "I understand. How can I help you?")
        if created_entity_id and intent_data.get("type") == "create_reminder":
            response_text = f"{response_text}\n\n✅ Reminder created successfully!"
        
        return ChatResponse(
            response=response_text,
            intent=IntentInfo(**intent_data),
            actions=[ActionData(**action) for action in actions_list],
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
        from datetime import datetime
        
        prompt_parts = [SYSTEM_PROMPT]

        # Add current date and time - CRITICAL for date parsing
        from datetime import timedelta
        now = datetime.now()
        current_date_iso = now.strftime("%Y-%m-%d")
        current_datetime_iso = now.isoformat()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        prompt_parts.append(f"\n\nIMPORTANT - Current Date and Time:")
        prompt_parts.append(f"- Today's date: {current_date_iso}")
        prompt_parts.append(f"- Current datetime: {current_datetime_iso}")
        prompt_parts.append(f"- When user says 'today', use: {current_date_iso}")
        prompt_parts.append(f"- When user says 'tomorrow', use: {tomorrow}")
        prompt_parts.append(f"- Always use dates >= {current_date_iso}. Never use dates from the past.")
        prompt_parts.append(f"- For reminders, use separate 'date' (YYYY-MM-DD) and 'time' (HH:MM) fields")
        prompt_parts.append(f"- NEVER use 'reminderTime' - it does not exist in the API schema")

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

    async def _execute_create_reminder(
        self,
        session: AsyncSession,
        user_id: UUID,
        workspace_id: UUID,
        entities: Dict[str, Any],
    ) -> Optional[UUID]:
        """Execute create_reminder action from chatbot intent."""
        from datetime import date, datetime
        from app.services import reminders as reminder_service
        
        # Extract title
        title = entities.get("title") or entities.get("reminderTitle")
        if not title:
            raise ValueError("Title is required for reminder")
        
        # Extract date - try multiple formats
        reminder_date = None
        date_str = entities.get("dueDate") or entities.get("date") or entities.get("reminderDate")
        if date_str:
            try:
                # Try parsing ISO date string (YYYY-MM-DD)
                if isinstance(date_str, str) and len(date_str) >= 10:
                    reminder_date = datetime.fromisoformat(date_str[:10]).date()
                elif isinstance(date_str, date):
                    reminder_date = date_str
            except (ValueError, AttributeError):
                # If parsing fails, use today as default
                reminder_date = date.today()
        
        if not reminder_date:
            # Default to today if no date provided
            reminder_date = date.today()
        
        # Extract time
        time_str = None
        reminder_time_str = entities.get("reminderTime") or entities.get("time")
        if reminder_time_str:
            # Parse ISO datetime or time string
            if isinstance(reminder_time_str, str):
                # Try to extract time from ISO datetime string
                if "T" in reminder_time_str:
                    try:
                        dt = datetime.fromisoformat(reminder_time_str.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M")
                    except (ValueError, AttributeError):
                        # If it's already HH:MM format, use it directly
                        if ":" in reminder_time_str and len(reminder_time_str) <= 5:
                            time_str = reminder_time_str
                elif ":" in reminder_time_str and len(reminder_time_str) <= 5:
                    time_str = reminder_time_str
        
        # Determine reminder type (default to "event")
        reminder_type = entities.get("type") or "event"
        if reminder_type not in ["deadline", "event"]:
            reminder_type = "event"
        
        # Extract optional project_id
        project_id = None
        if entities.get("projectId"):
            try:
                project_id = UUID(entities["projectId"])
            except (ValueError, TypeError):
                pass
        
        # Create the reminder
        reminder = await reminder_service.create_reminder(
            session=session,
            user_id=user_id,
            workspace_id=workspace_id,
            title=title,
            reminder_date=reminder_date,
            reminder_type=reminder_type,
            reminder_time=time_str,
            project_id=project_id,
            scope_id=None,  # Can be added later if needed
        )
        
        return reminder.id


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
