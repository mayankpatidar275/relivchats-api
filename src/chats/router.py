"""
Chats API - Core chat operations
Endpoints:
- POST /chats/upload
- GET /chats (list user chats)
- GET /chats/{chat_id} (chat details)
- PUT /chats/{chat_id}/display-name
- GET /chats/{chat_id}/messages
- GET /chats/{chat_id}/vector-status
- DELETE /chats/{chat_id}
"""

import json
import shutil
from pathlib import Path
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..auth.dependencies import get_current_user_id
from . import schemas, service, models

from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    FileProcessingException,
    NotFoundException,
    ErrorCode
)

logger = get_logger(__name__)

# Configure a directory to temporarily store uploaded files
UPLOAD_FOLDER = Path("uploads")
if not UPLOAD_FOLDER.exists():
    UPLOAD_FOLDER.mkdir()

router = APIRouter(prefix="/chats", tags=["chats"])


# ============================================================================
# UPLOAD CHAT
# ============================================================================

@router.post("/upload", response_model=schemas.ChatUploadResponse)
def upload_whatsapp_file(
    file: Annotated[UploadFile, File(...)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    category_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process WhatsApp chat file synchronously"""
    
    logger.info(
        "Chat upload started",
        extra={
            "user_id": user_id,
            "extra_data": {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": file.size,
                "category_id": category_id
            }
        }
    )
    
    # 1. File Validation
    allowed_types = ["text/plain", "application/zip"]
    if file.content_type not in allowed_types:
        logger.warning(
            f"Invalid file type rejected: {file.content_type}",
            extra={"user_id": user_id, "extra_data": {"filename": file.filename}}
        )
        raise FileProcessingException(
            f"Invalid file type. Only .txt or .zip files are allowed.",
            error_code=ErrorCode.INVALID_FILE_FORMAT
        )
    
    # Add size validation
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        logger.warning(
            f"File too large: {file.size} bytes",
            extra={"user_id": user_id, "extra_data": {"filename": file.filename}}
        )
        raise FileProcessingException(
            f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
            error_code=ErrorCode.FILE_TOO_LARGE
        )
    
    # 2. Save the file to a temporary location
    file_path = None
    try:
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.debug(f"File saved to temporary location: {file_path}", extra={"user_id": user_id})
    
    except Exception as e:
        logger.error(
            f"Failed to save uploaded file: {e}",
            extra={"user_id": user_id, "extra_data": {"filename": file.filename}},
            exc_info=True
        )
        raise FileProcessingException(f"Failed to save file: {str(e)}")
    
    try:
        # 3. Create a chat entry in the database with 'processing' status
        db_chat = service.create_chat(
            db, 
            user_id=user_id, 
            filename=file.filename,
            category_id=category_id  # Pass optional category
        )
        
        logger.info(
            f"Chat record created: {db_chat.id}",
            extra={"user_id": user_id, "extra_data": {"chat_id": str(db_chat.id)}}
        )
        
        # 4. Process the file synchronously
        processed_chat = service.process_whatsapp_file(
            chat_id=db_chat.id,
            file_path=str(file_path),
            db=db
        )
        
        # Log successful processing as business event
        log_business_event(
            event_type="chat_uploaded",
            user_id=user_id,
            chat_id=str(processed_chat.id),
            filename=file.filename,
            message_count=processed_chat.chat_metadata.get("total_messages", 0) if processed_chat.chat_metadata else 0,
            participant_count=processed_chat.participant_count,
            processing_time_ms=0  # You can track this if needed
        )
        
        logger.info(
            f"Chat processed successfully: {processed_chat.id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(processed_chat.id),
                    "message_count": processed_chat.chat_metadata.get("total_messages", 0) if processed_chat.chat_metadata else 0
                }
            }
        )
        
        # 5. Return the completed chat
        return schemas.ChatUploadResponse.from_orm(processed_chat)
         
    except FileProcessingException:
        # Re-raise our custom exceptions
        raise
    
    except Exception as e:
        logger.error(
            f"Chat processing failed: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "filename": file.filename,
                    "chat_id": str(db_chat.id) if 'db_chat' in locals() else None
                }
            },
            exc_info=True
        )
        
        # Clean up the chat if it was created
        if 'db_chat' in locals():
            try:
                service.delete_chat(db, db_chat.id)
                logger.info(f"Cleaned up failed chat: {db_chat.id}", extra={"user_id": user_id})
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup chat: {cleanup_error}", exc_info=True)
        
        raise FileProcessingException(f"Failed to process file: {str(e)}")
        
    finally:
        # 6. Clean up the temporary file
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Temporary file deleted: {file_path}", extra={"user_id": user_id})
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up temp file {file_path}: {cleanup_error}",
                    extra={"user_id": user_id}
                )



# ============================================================================
# LIST USER CHATS
# ============================================================================

@router.get("", response_model=List[schemas.GetChatResponse])
def list_user_chats(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all chats for the current user"""
    chats = service.get_user_chats(db, user_id)

    # Convert DB chat objects to schema using the classmethod
    response = []
    for chat in chats:
        try:
            response.append(schemas.GetChatResponse.from_orm(chat))
        except Exception:
            # If conversion fails for any chat, skip it so endpoint still returns others
            continue

    return response


# ============================================================================
# GET SINGLE CHAT
# ============================================================================

@router.get("/{chat_id}", response_model=schemas.GetChatResponse)
def get_chat_details(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific chat"""
    chat = service.get_chat_by_id(db, chat_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    return schemas.GetChatResponse.from_orm(chat)


# ============================================================================
# UPDATE DISPLAY NAME
# ============================================================================

@router.put("/{chat_id}/display-name", response_model=schemas.ChatUploadResponse)
def update_user_display_name(
    chat_id: str,
    request: schemas.UpdateUserDisplayName,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Update user's display name for a chat"""
    chat = service.update_user_display_name(
        db, chat_id, user_id, request.user_display_name
    )
    
    if not chat:
        raise HTTPException(
            status_code=404, 
            detail="Chat not found or not authorized"
        )
    
    return schemas.ChatUploadResponse.from_orm(chat)


# ============================================================================
# GET CHAT MESSAGES
# ============================================================================

@router.get("/{chat_id}/messages", response_model=List[schemas.ChatMessagesResponse])
def get_chat_messages(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all messages for a chat"""
    messages = service.get_chat_messages(db, chat_id, user_id)
    return messages


# ============================================================================
# VECTOR STATUS
# ============================================================================

@router.get("/{chat_id}/vector-status", response_model=schemas.VectorStatusResponse)
def get_chat_vector_status(
    chat_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get vector indexing status for a chat"""
    chat = service.get_chat_by_id(db, chat_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    return schemas.VectorStatusResponse(
        chat_id=chat.id,
        vector_status=getattr(chat, 'vector_status', 'pending'),
        chunk_count=getattr(chat, 'chunk_count', 0),
        indexed_at=getattr(chat, 'indexed_at', None),
        is_searchable=getattr(chat, 'vector_status', 'pending') == 'completed'
    )


# ============================================================================
# DELETE CHAT
# ============================================================================

@router.delete("/{chat_id}", response_model=schemas.ChatDeleteResponse)
def soft_delete_chat(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Soft delete chat and schedule permanent cleanup
    """

    # Check if chat exists
    chat = service.get_chat_by_id(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=404, 
            detail="Chat not found"
        )
    
    # Soft delete chat and related data
    deleted_chat = service.soft_delete_chat(db, chat.id)
    if not deleted_chat:
        raise HTTPException(status_code=500, detail="Failed to delete chat")

    # Schedule permanent cleanup in background
    background_tasks.add_task(service.delete_chat, db, chat.id)
    
    return schemas.ChatDeleteResponse(
        success=True,
        message="Chat successfully deleted",
        chat_id=chat_id
    )


# ============================================================================
# PUBLIC STATS (NO AUTH)
# ============================================================================

@router.get("/public/{chat_id}/stats")
def get_public_chat_stats(
    chat_id: UUID,
    db: Session = Depends(get_db)
):
    """Get public chat statistics (no auth required)"""
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return {
        "id": str(chat.id),
        "filename": chat.title,
        "participants": json.loads(chat.participants) if chat.participants else [],
        "chat_metadata": chat.chat_metadata,
        "created_at": chat.created_at,
    }



# ============================================================================
# AI CONVERSATION (LEGACY - CONSIDER MOVING TO /rag)
# ============================================================================

# @router.get("/{chat_id}/ai-conversation", response_model=schemas.AIConversationResponse)
# def get_chat_ai_conversation_endpoint(
#     chat_id: UUID,
#     db: Session = Depends(get_db),
#     user_id = Depends(get_current_user_id)
# ):
#     """Get AI conversation history for a chat"""
    
#     # Verify user owns the chat
#     chat = service.get_chat_by_id(db, chat_id)
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
    
#     if str(chat.user_id) != str(user_id):
#         raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
#     # Get conversation
#     conversation = service.get_chat_ai_conversation(db, chat_id, str(user_id))
    
#     if not conversation:
#         raise HTTPException(status_code=404, detail="No AI conversation found for this chat")
    
#     # Sort messages chronologically
#     sorted_messages = sorted(conversation.messages, key=lambda x: x.created_at)
    
#     return schemas.AIConversationResponse(
#         id=str(conversation.id),
#         chat_id=str(conversation.chat_id),
#         created_at=conversation.created_at,
#         updated_at=conversation.updated_at,
#         messages=[
#             schemas.AIMessageResponse(
#                 id=str(msg.id),
#                 message_type=msg.message_type.value,
#                 content=msg.content,
#                 created_at=msg.created_at
#             )
#             for msg in sorted_messages
#         ]
#     )









# @router.delete("/{chat_id}", status_code=204)
# def delete_chat_endpoint(
#     chat_id: UUID,
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: Session = Depends(get_db),
# ):
#     """Delete a specific chat"""
#     chat = service.get_chat_by_id(db, chat_id)
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
#     if chat.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Not authorized")

#     success = service.delete_chat(db, chat_id)
#     if not success:
#         raise HTTPException(status_code=500, detail="Failed to delete chat")
#     return

# @router.post("/{chat_id}/reindex")
# def reindex_chat_vectors(
#     chat_id: str,
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: Session = Depends(get_db)
# ):
#     """Re-trigger vector indexing for a chat"""
#     chat = service.get_chat_by_id(db, chat_id)
    
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
    
#     if chat.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
#     if chat.status != "completed":
#         raise HTTPException(
#             status_code=400, 
#             detail="Chat must be successfully parsed before indexing"
#         )
    
#     try:
#         # Import here to avoid circular imports
#         from ..vector.service import vector_service
        
#         success = vector_service.reindex_chat(db, chat_id)
        
#         if success:
#             return {"message": "Reindexing started successfully", "chat_id": chat_id}
#         else:
#             raise HTTPException(status_code=500, detail="Failed to start reindexing")
            
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")









# # Optional: Add a timeout-based hybrid endpoint for large files
# @router.post("/upload-with-timeout", response_model=schemas.ChatUploadResponse)
# async def upload_whatsapp_file_with_timeout(
#     file: Annotated[UploadFile, File(...)],
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: Session = Depends(get_db),
#     timeout_seconds: int = 30
# ):
#     """Upload with timeout fallback to background processing"""
#     import asyncio
#     from concurrent.futures import ThreadPoolExecutor
    
#     # Same validation logic as above
#     allowed_types = ["text/plain", "application/zip"]
#     if file.content_type not in allowed_types:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid file type. Only .txt or .zip files are allowed."
#         )

#     if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
#         raise HTTPException(
#             status_code=413,
#             detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
#         )

#     # Save file
#     file_path = None
#     try:
#         file_path = UPLOAD_FOLDER / file.filename
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

#     try:
#         db_chat = service.create_chat(db, user_id=user_id)
        
#         # Try processing with timeout
#         with ThreadPoolExecutor() as executor:
#             future = executor.submit(
#                 service.process_whatsapp_file_sync,
#                 db_chat.id,
#                 str(file_path),
#                 db
#             )
            
#             try:
#                 # Wait for completion with timeout
#                 processed_chat = await asyncio.wait_for(
#                     asyncio.wrap_future(future),
#                     timeout=timeout_seconds
#                 )
#                 return schemas.ChatUploadResponse.from_orm(processed_chat)
                
#             except asyncio.TimeoutError:
#                 # Fallback to background processing
#                 # Update chat status to indicate background processing
#                 service.update_chat_status(db, db_chat.id, "processing_background")
                
#                 # Start background task (you'd need to implement this)
#                 # background_tasks.add_task(service.continue_processing, db_chat.id, str(file_path), db)
                
#                 return schemas.ChatUploadResponse(
#                     id=db_chat.id,
#                     status="processing_background",
#                     message="File is large and is being processed in the background. You'll be notified when ready.",
#                     participants=[]
#                 )
                
#     except Exception as e:
#         if 'db_chat' in locals():
#             service.delete_chat(db, db_chat.id)
#         raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")
        
#     finally:
#         if file_path and file_path.exists():
#             try:
#                 file_path.unlink()
#             except Exception:
#                 pass




# @router.get("/{chat_id}/participants", response_model=schemas.ChatParticipantsResponse)
# def get_chat_participants(
#     chat_id: str,
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: Session = Depends(get_db)
# ):
#     """Get participants list for a chat"""
#     chat = service.get_chat_by_id(db, chat_id)
    
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
    
#     if chat.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
#     if not chat.participants:
#         raise HTTPException(status_code=400, detail="Chat participants not available")
    
#     try:
#         import json
#         participants = json.loads(chat.participants)
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=500, detail="Error parsing participants data")
    
#     return schemas.ChatParticipantsResponse(
#         id=chat.id,
#         participants=participants,
#         current_user_display_name=chat.user_display_name
#     )
