from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import deps
from app.schemas.ai_chat import ChatRequest, ChatResponse
from app.services import ai_chat as ai_chat_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ChatResponse:
    """Process AI chat message and return response with actions."""
    try:
        service = ai_chat_service.AIChatService()
        result = await service.process_message(
            session=session,
            message=request.message,
            user_id=current_user.id,
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            context=request.context.model_dump() if request.context else {},
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(exc)}",
        ) from exc
