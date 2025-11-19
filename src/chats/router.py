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
from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    NotFoundException,
    ForbiddenException,
    FileProcessingException,
    DatabaseException,
    ErrorCode
)
from ..monitoring import track_time, track_operation
from . import schemas, service, models

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
        "Chat upload initiated",
        extra={
            "user_id": user_id,
            "extra_data": {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size_bytes": file.size,
                "category_id": category_id
            }
        }
    )
    
    # 1. File Validation
    allowed_types = ["text/plain", "application/zip"]
    if file.content_type not in allowed_types:
        logger.warning(
            f"Invalid file type rejected: {file.content_type}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "allowed_types": allowed_types
                }
            }
        )
        raise FileProcessingException(
            f"Invalid file type. Only .txt or .zip files are allowed.",
            error_code=ErrorCode.INVALID_FILE_FORMAT
        )

    # Add size validation
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        logger.warning(
            f"File size exceeds limit: {file.size} bytes",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "filename": file.filename,
                    "file_size_bytes": file.size,
                    "max_size_bytes": settings.MAX_UPLOAD_SIZE_BYTES
                }
            }
        )
        raise FileProcessingException(
            f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
            error_code=ErrorCode.FILE_TOO_LARGE
        )

    # 2. Save the file to a temporary location
    file_path = None
    try:
        file_path = UPLOAD_FOLDER / file.filename
        
        with track_operation("save_uploaded_file", filename=file.filename):
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        logger.debug(
            f"File saved to temporary location: {file_path}",
            extra={"user_id": user_id, "extra_data": {"file_path": str(file_path)}}
        )
    
    except Exception as e:
        logger.error(
            f"Failed to save uploaded file: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "filename": file.filename,
                    "error_type": type(e).__name__
                }
            },
            exc_info=True
        )
        raise FileProcessingException(f"Failed to save file: {str(e)}")

    try:
        # 3. Create a chat entry in the database with 'processing' status
        db_chat = service.create_chat(
            db, 
            user_id=user_id, 
            filename=file.filename,
            category_id=category_id
        )
        
        logger.info(
            f"Chat record created with ID: {db_chat.id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(db_chat.id),
                    "status": db_chat.status
                }
            }
        )
        
        # 4. Process the file synchronously
        processed_chat = service.process_whatsapp_file(
            chat_id=db_chat.id,
            file_path=str(file_path),
            db=db
        )
        
        # 5. Log successful processing as business event
        log_business_event(
            event_type="chat_uploaded",
            user_id=user_id,
            chat_id=str(processed_chat.id),
            filename=file.filename,
            file_size_bytes=file.size,
            message_count=processed_chat.chat_metadata.get("total_messages", 0) if processed_chat.chat_metadata else 0,
            participant_count=processed_chat.participant_count,
            is_group_chat=processed_chat.is_group_chat
        )
        
        logger.info(
            f"Chat processed successfully: {processed_chat.id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(processed_chat.id),
                    "message_count": processed_chat.chat_metadata.get("total_messages", 0) if processed_chat.chat_metadata else 0,
                    "participant_count": processed_chat.participant_count
                }
            }
        )
        
        # 6. Return the completed chat with all metadata
        return schemas.ChatUploadResponse.from_orm(processed_chat)
         
    except FileProcessingException:
        # Re-raise our custom exceptions (already logged in service)
        raise
    
    except Exception as e:
        logger.error(
            f"Unexpected error during chat processing: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "filename": file.filename,
                    "chat_id": str(db_chat.id) if 'db_chat' in locals() else None,
                    "error_type": type(e).__name__
                }
            },
            exc_info=True
        )
        
        # Clean up the chat if it was created
        if 'db_chat' in locals():
            try:
                service.delete_chat(db, db_chat.id)
                logger.info(
                    f"Cleaned up failed chat: {db_chat.id}",
                    extra={"user_id": user_id}
                )
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup chat after error: {cleanup_error}",
                    extra={"user_id": user_id},
                    exc_info=True
                )
        
        raise FileProcessingException(f"Failed to process file: {str(e)}")
        
    finally:
        # 7. Clean up the temporary file
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(
                    f"Temporary file deleted: {file_path}",
                    extra={"user_id": user_id}
                )
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
    
    logger.debug(
        "Fetching user chats",
        extra={"user_id": user_id}
    )
    
    try:
        chats = service.get_user_chats(db, user_id)
        
        # Convert DB chat objects to schema using the classmethod
        response = []
        failed_conversions = 0
        
        for chat in chats:
            try:
                response.append(schemas.GetChatResponse.from_orm(chat))
            except Exception as e:
                failed_conversions += 1
                logger.warning(
                    f"Failed to convert chat to response schema: {e}",
                    extra={
                        "user_id": user_id,
                        "extra_data": {
                            "chat_id": str(chat.id),
                            "error_type": type(e).__name__
                        }
                    }
                )
                # Skip this chat so endpoint still returns others
                continue
        
        logger.info(
            f"Retrieved {len(response)} chats for user",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_count": len(response),
                    "failed_conversions": failed_conversions
                }
            }
        )
        
        return response
    
    except DatabaseException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list user chats: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseException(f"Failed to retrieve chats", original_error=e)


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
    
    logger.debug(
        "Fetching chat details",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": str(chat_id)}
        }
    )
    
    try:
        chat = service.get_chat_by_id(db, chat_id)
        
        if not chat:
            logger.warning(
                f"Chat not found: {chat_id}",
                extra={"user_id": user_id}
            )
            raise NotFoundException("Chat", str(chat_id))
        
        if chat.user_id != user_id:
            logger.warning(
                f"Unauthorized access attempt to chat: {chat_id}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "chat_owner": chat.user_id
                    }
                }
            )
            raise ForbiddenException("Not authorized to access this chat")
        
        logger.debug(
            f"Chat details retrieved: {chat_id}",
            extra={"user_id": user_id}
        )
        
        return schemas.GetChatResponse.from_orm(chat)
    
    except (NotFoundException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(
            f"Failed to get chat details: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat_id)}
            },
            exc_info=True
        )
        raise DatabaseException(f"Failed to retrieve chat", original_error=e)


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
    
    logger.debug(
        "Fetching chat messages",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": str(chat_id)}
        }
    )
    
    try:
        messages = service.get_chat_messages(db, chat_id, user_id)
        
        logger.info(
            f"Retrieved {len(messages)} messages",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "message_count": len(messages)
                }
            }
        )
        
        return messages
    
    except HTTPException as e:
        # get_chat_messages raises HTTPException for forbidden access
        if e.status_code == 403:
            logger.warning(
                f"Unauthorized access to chat messages: {chat_id}",
                extra={"user_id": user_id}
            )
            raise ForbiddenException("You do not have access to this chat")
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve messages: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat_id)}
            },
            exc_info=True
        )
        raise DatabaseException(f"Failed to retrieve messages", original_error=e)


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
    
    logger.debug(
        "Checking vector status",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": chat_id}
        }
    )
    
    try:
        chat = service.get_chat_by_id(db, chat_id)
        
        if not chat:
            logger.warning(
                f"Chat not found for vector status check: {chat_id}",
                extra={"user_id": user_id}
            )
            raise NotFoundException("Chat", chat_id)
        
        if chat.user_id != user_id:
            logger.warning(
                f"Unauthorized vector status check: {chat_id}",
                extra={"user_id": user_id}
            )
            raise ForbiddenException("Not authorized to access this chat")
        
        vector_status = getattr(chat, 'vector_status', 'pending')
        
        logger.debug(
            f"Vector status: {vector_status}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": chat_id,
                    "vector_status": vector_status
                }
            }
        )
        
        return schemas.VectorStatusResponse(
            chat_id=chat.id,
            vector_status=vector_status,
            chunk_count=getattr(chat, 'chunk_count', 0),
            indexed_at=getattr(chat, 'indexed_at', None),
            is_searchable=vector_status == 'completed'
        )
    
    except (NotFoundException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(
            f"Failed to check vector status: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": chat_id}
            },
            exc_info=True
        )
        raise DatabaseException(f"Failed to check vector status", original_error=e)


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
    
    logger.info(
        "Chat deletion requested",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": str(chat_id)}
        }
    )

    try:
        # Check if chat exists
        chat = service.get_chat_by_id(db, chat_id)
        if not chat:
            logger.warning(
                f"Delete attempt on non-existent chat: {chat_id}",
                extra={"user_id": user_id}
            )
            raise NotFoundException("Chat", str(chat_id))
        
        # Verify ownership
        if chat.user_id != user_id:
            logger.warning(
                f"Unauthorized delete attempt: {chat_id}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "chat_owner": chat.user_id
                    }
                }
            )
            raise ForbiddenException("Not authorized to delete this chat")
        
        # Soft delete chat and related data
        deleted_chat = service.soft_delete_chat(db, chat.id)
        if not deleted_chat:
            logger.error(
                f"Soft delete operation failed: {chat_id}",
                extra={"user_id": user_id}
            )
            raise DatabaseException("Failed to delete chat")

        # Schedule permanent cleanup in background
        background_tasks.add_task(service.delete_chat, db, chat.id)
        
        # Log business event
        log_business_event(
            event_type="chat_deleted",
            user_id=user_id,
            chat_id=str(chat_id),
            message_count=chat.chat_metadata.get("total_messages", 0) if chat.chat_metadata else 0
        )
        
        logger.info(
            f"Chat soft deleted successfully: {chat_id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "scheduled_permanent_deletion": True
                }
            }
        )
        
        return schemas.ChatDeleteResponse(
            success=True,
            message="Chat successfully deleted",
            chat_id=chat_id
        )
    
    except (NotFoundException, ForbiddenException, DatabaseException):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during chat deletion: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat_id)}
            },
            exc_info=True
        )
        raise DatabaseException(f"Failed to delete chat", original_error=e)


# ============================================================================
# PUBLIC STATS (NO AUTH)
# ============================================================================

@router.get("/public/{chat_id}/stats")
def get_public_chat_stats(
    chat_id: UUID,
    db: Session = Depends(get_db)
):
    """Get public chat statistics (no auth required)"""
    
    logger.debug(
        "Fetching public chat stats",
        extra={"extra_data": {"chat_id": str(chat_id)}}
    )
    
    try:
        chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
        
        if not chat:
            logger.warning(f"Public stats requested for non-existent chat: {chat_id}")
            raise NotFoundException("Chat", str(chat_id))
        
        logger.debug(
            f"Public stats retrieved for chat: {chat_id}",
            extra={"extra_data": {"chat_id": str(chat_id)}}
        )
        
        return {
            "id": str(chat.id),
            "filename": chat.title,
            "participants": json.loads(chat.participants) if chat.participants else [],
            "chat_metadata": chat.chat_metadata,
            "created_at": chat.created_at,
        }
    
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve public stats: {e}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        raise DatabaseException(f"Failed to retrieve public stats", original_error=e)


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
    
    logger.info(
        "Updating user display name",
        extra={
            "user_id": user_id,
            "extra_data": {
                "chat_id": chat_id,
                "new_display_name": request.user_display_name
            }
        }
    )
    
    try:
        chat = service.update_user_display_name(
            db, chat_id, user_id, request.user_display_name
        )
        
        if not chat:
            logger.warning(
                f"Chat not found or unauthorized: {chat_id}",
                extra={"user_id": user_id}
            )
            raise NotFoundException("Chat", chat_id)
        
        logger.info(
            f"Display name updated for chat: {chat_id}",
            extra={"user_id": user_id}
        )
        
        return schemas.ChatUploadResponse.from_orm(chat)
    
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update display name: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": chat_id}
            },
            exc_info=True
        )
        raise DatabaseException(f"Failed to update display name", original_error=e)




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
    
#     logger.debug(
#         "Fetching AI conversation",
#         extra={
#             "user_id": user_id,
#             "extra_data": {"chat_id": str(chat_id)}
#         }
#     )
    
#     try:
#         # Verify user owns the chat
#         chat = service.get_chat_by_id(db, chat_id)
#         if not chat:
#             logger.warning(
#                 f"Chat not found for AI conversation: {chat_id}",
#                 extra={"user_id": user_id}
#             )
#             raise NotFoundException("Chat", str(chat_id))
        
#         if str(chat.user_id) != str(user_id):
#             logger.warning(
#                 f"Unauthorized AI conversation access: {chat_id}",
#                 extra={"user_id": user_id}
#             )
#             raise ForbiddenException("Not authorized to access this chat")
        
#         # Get conversation
#         conversation = service.get_chat_ai_conversation(db, chat_id, str(user_id))
        
#         if not conversation:
#             logger.info(
#                 f"No AI conversation found for chat: {chat_id}",
#                 extra={"user_id": user_id}
#             )
#             raise NotFoundException("AI conversation", str(chat_id))
        
#         # Sort messages chronologically
#         sorted_messages = sorted(conversation.messages, key=lambda x: x.created_at)
        
#         logger.debug(
#             f"AI conversation retrieved with {len(sorted_messages)} messages",
#             extra={
#                 "user_id": user_id,
#                 "extra_data": {
#                     "chat_id": str(chat_id),
#                     "message_count": len(sorted_messages)
#                 }
#             }
#         )
        
#         return schemas.AIConversationResponse(
#             id=str(conversation.id),
#             chat_id=str(conversation.chat_id),
#             created_at=conversation.created_at,
#             updated_at=conversation.updated_at,
#             messages=[
#                 schemas.AIMessageResponse(
#                     id=str(msg.id),
#                     message_type=msg.message_type.value,
#                     content=msg.content,
#                     created_at=msg.created_at
#                 )
#                 for msg in sorted_messages
#             ]
#         )
    
#     except (NotFoundException, ForbiddenException):
#         raise
#     except Exception as e:
#         logger.error(
#             f"Failed to retrieve AI conversation: {e}",
#             extra={
#                 "user_id": user_id,
#                 "extra_data": {"chat_id": str(chat_id)}
#             },
#             exc_info=True
#         )
#         raise DatabaseException(f"Failed to retrieve AI conversation", original_error=e)


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
