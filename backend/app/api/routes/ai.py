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
    from app.core.logging import get_logger
    
    logger = get_logger(__name__)
    try:
        # Handle context - convert to dict safely
        context_dict = {}
        if request.context:
            try:
                # Use model_dump() for Pydantic v2
                context_dict = request.context.model_dump() if hasattr(request.context, 'model_dump') else dict(request.context)
            except Exception as e:
                logger.warning(f"Failed to parse context: {e}, using empty dict")
                context_dict = {}
        
        service = ai_chat_service.AIChatService()
        result = await service.process_message(
            session=session,
            message=request.message,
            user_id=current_user.id,
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            context=context_dict,
        )
        return result
    except Exception as exc:
        logger.error(f"Error processing chat message: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(exc)}",
        ) from exc
