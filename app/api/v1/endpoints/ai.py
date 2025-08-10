from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db
from app.schemas.ai import AIChatRequest, AIMessageResponse, AIChatConversationResponse
from app.services.ai_service import ai_service
from app.api.v1.endpoints.auth import get_current_user_id # Import auth dependency
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/chats/{chat_id}/ai/ask",
    response_model=AIMessageResponse,
    summary="Sends a query to the AI for a specific chat and gets a response."
)
async def ask_ai_about_chat(
    chat_id: int,
    ai_request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Submits a natural language query about a specific chat to the AI.
    Optionally continues an existing AI conversation thread.
    """
    try:
        ai_response_message = await ai_service.ask_ai(db, chat_id, user_id, ai_request)
        return ai_response_message
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error asking AI about chat {chat_id} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI processing.")

@router.get(
    "/chats/{chat_id}/ai/conversations",
    response_model=List[AIChatConversationResponse],
    summary="Retrieves all AI conversation threads for a specific chat."
)
async def get_ai_conversations_for_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Fetches all AI conversation threads associated with a specific chat for the current user.
    """
    try:
        conversations = await ai_service.get_conversations(db, chat_id, user_id)
        # Convert ORM models to Pydantic response models
        return [AIChatConversationResponse.model_validate(conv) for conv in conversations]
    except Exception as e:
        logger.error(f"Error fetching AI conversations for chat {chat_id} by user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve AI conversations.")

@router.get(
    "/ai/conversations/{conversation_id}/messages",
    response_model=List[AIMessageResponse],
    summary="Retrieves all messages within a specific AI conversation thread."
)
async def get_ai_messages_in_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Fetches all messages within a specific AI conversation thread, ensuring user access.
    """
    try:
        messages = await ai_service.get_messages_in_conversation(db, conversation_id, user_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching messages for AI conversation {conversation_id} by user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve AI conversation messages.")