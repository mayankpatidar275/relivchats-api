from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Tuple

from app.db.session import get_db
from app.schemas.chat import ChatResponse, MessageResponse, ParticipantSelectionResponse, InsightResponse
from app.services.chat_service import chat_service
from app.api.v1.endpoints.auth import get_current_user_id # Import auth dependency
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary storage for file content and parsed data after initial upload
# In a real production system, this would be a more robust caching solution like Redis
# keyed by a unique upload ID or user session ID. For this example, we'll use a simple dict.
# NOTE: This is NOT suitable for a multi-worker or highly concurrent setup without a shared cache.
_temp_uploaded_chats: Dict[str, Tuple[str, Dict[str, bytes]]] = {} # {user_id: (raw_chat_text, media_files)}


@router.post(
    "/upload-and-parse",
    response_model=ParticipantSelectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Uploads and parses a WhatsApp chat file, returns participants for selection."
)
async def upload_and_parse_chat(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id) # Protect this endpoint
):
    """
    Uploads a WhatsApp chat file (.txt or .zip), processes it, and returns the
    extracted participants and basic chat info for the user to select their name.
    The raw file content and extracted media are temporarily stored on the backend
    for the subsequent `POST /chats` call.
    """
    try:
        response_data, raw_chat_text, media_files = await chat_service.process_uploaded_file(file, user_id)
        
        # Store raw_chat_text and media_files temporarily
        _temp_uploaded_chats[user_id] = (raw_chat_text, media_files)
        logger.info(f"Temporarily stored uploaded chat data for user {user_id}.")

        return response_data
    except ValueError as e:
        logger.warning(f"File upload/parse error for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled error during file upload/parse for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during file processing.")

@router.post(
    "/chats",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Finalizes chat creation after participant selection, saving messages and media."
)
async def create_chat(
    file_name: str = Form(...),
    participants: str = Form(...), # Send as comma-separated string, convert to list in service
    me_identifier: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id) # Protect this endpoint
):
    """
    Uses the temporarily stored raw chat content and extracted media, along with user's
    selected participant info, to finalize chat creation.
    Parses the full chat, uploads media to S3, saves messages to DB, and indexes for AI.
    """
    try:
        # Retrieve temporarily stored data
        if user_id not in _temp_uploaded_chats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chat file found for processing. Please upload the file again."
            )
        raw_chat_text, media_files = _temp_uploaded_chats.pop(user_id) # Pop to remove after use

        # Convert participants string back to list
        parsed_participants = [p.strip() for p in participants.split(',')]
        
        new_chat = await chat_service.create_chat(
            db=db,
            user_id=user_id,
            raw_chat_text=raw_chat_text,
            media_files=media_files,
            file_name=file_name,
            participants=parsed_participants,
            me_identifier=me_identifier
        )
        return ChatResponse.model_validate(new_chat)
    except ValueError as e:
        logger.warning(f"Chat creation error for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled error during chat creation for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during chat creation.")

@router.get(
    "/chats",
    response_model=List[ChatResponse],
    summary="Retrieves a list of all chats imported by the current user."
)
async def get_my_chats(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Fetches all chats associated with the authenticated user, ordered by import date.
    """
    try:
        chats = await chat_service.get_user_chats(db, user_id)
        return chats
    except Exception as e:
        logger.error(f"Error fetching chats for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve chats.")

@router.get(
    "/chats/{chat_id}/messages",
    response_model=List[MessageResponse],
    summary="Retrieves all messages for a specific chat."
)
async def get_chat_messages(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves all messages for a specified chat, ensuring the user has access.
    Includes S3 URLs for media attachments.
    """
    try:
        messages = await chat_service.get_chat_messages(db, chat_id, user_id)
        return messages
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching messages for chat {chat_id} by user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve chat messages.")

@router.get(
    "/chats/{chat_id}/insights",
    response_model=List[InsightResponse],
    summary="Retrieves pre-computed insights for a specific chat."
)
async def get_chat_insights(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Fetches pre-computed insights (e.g., sentiment, common phrases) for a specific chat.
    """
    try:
        insights = await chat_service.get_chat_insights(db, chat_id, user_id)
        return insights
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching insights for chat {chat_id} by user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve chat insights.")


@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletes a chat and all its associated data."
)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Deletes a specific chat, including all its messages, AI conversations, and insights.
    """
    try:
        await chat_service.delete_chat(db, chat_id, user_id)
        return {} # FastAPI returns 204 No Content for empty dict
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id} by user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete chat.")