import shutil
from pathlib import Path
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..auth.dependencies import get_current_user_id
from src.rag.models import AIConversation, AIMessage
from . import schemas, service

# Configure a directory to temporarily store uploaded files
UPLOAD_FOLDER = Path("uploads")
if not UPLOAD_FOLDER.exists():
    UPLOAD_FOLDER.mkdir()

router = APIRouter(
    prefix="/chats",
    tags=["chats"],
)

@router.post("/upload", response_model=schemas.ChatUploadResponse)
def upload_whatsapp_file(
    file: Annotated[UploadFile, File(...)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    category_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process WhatsApp chat file synchronously"""
    # 1. File Validation
    allowed_types = ["text/plain", "application/zip"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only .txt or .zip files are allowed."
        )

    # Add size validation
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # 2. Save the file to a temporary location
    file_path = None
    try:
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        # 3. Create a chat entry in the database with 'processing' status
        db_chat = service.create_chat(
            db, 
            user_id=user_id, 
            filename=file.filename,
            category_id=category_id  # Pass optional category
        )
        
        # 4. Process the file synchronously
        processed_chat = service.process_whatsapp_file(
            chat_id=db_chat.id,
            file_path=str(file_path),
            db=db
        )
        
        # 5. Return the completed chat with all metadata
        return schemas.ChatUploadResponse.from_orm(processed_chat)
         
    except Exception as e:
        # Handle any processing errors
        # Clean up the chat if it was created
        if 'db_chat' in locals():
            service.delete_chat(db, db_chat.id)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")
        
    finally:
        # 6. Clean up the temporary file
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as cleanup_error:
                # Log the cleanup error but don't fail the request
                print(f"Warning: Failed to clean up temp file {file_path}: {cleanup_error}")

@router.get("", response_model=List[schemas.ChatDetailsResponse])
def get_user_chats(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all chats for the current user"""
    chats = service.get_user_chats(db, user_id)
    
    # Convert to response format with message count and vector status
    chat_details = []
    for chat in chats:
        message_count = len(chat.messages) if chat.messages else 0
        chat_detail = schemas.ChatDetailsResponse(
            id=str(chat.id),
            user_id=chat.user_id,
            title=chat.title,
            participants=None,
            user_display_name=chat.user_display_name,
            created_at=chat.created_at,
            status=chat.status,
            vector_status=getattr(chat, 'vector_status', 'pending'),
            chunk_count=getattr(chat, 'chunk_count', 0),
            indexed_at=getattr(chat, 'indexed_at', None),
            message_count=message_count
        )
        
        # Parse participants if available
        if chat.participants:
            try:
                import json
                chat_detail.participants = json.loads(chat.participants)
            except:
                pass
        
        chat_details.append(chat_detail)
    
    return chat_details

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

@router.get("/{chat_id}/insights", response_model=List[schemas.InsightWithTypeResponse])
def get_chat_insights(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all available insight types for a chat with generation status"""
    # Verify user owns the chat
    chat = service.get_chat_by_id(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Check if chat is ready
    if chat.vector_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Chat is not ready. Current status: {chat.vector_status}"
        )
    
    try:
        insights = service.get_chat_insights_with_types(db, chat_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch insights: {str(e)}")

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
        raise HTTPException(
            status_code=500, 
            detail="Failed to delete chat"
        )

    # Schedule permanent cleanup in background
    background_tasks.add_task(
        service.delete_chat, 
        db, 
        chat.id
    )
    
    return schemas.ChatDeleteResponse(
        success=True,
        message="Chat successfully deleted",
        chat_id=chat_id
    )


@router.get("/{chat_id}/messages", response_model=List[schemas.ChatMessagesResponse])
def get_user_chats(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all chat messages"""
    messages = service.get_chat_messages(db, chat_id, user_id)
    return messages

@router.get("/{chat_id}/ai-conversation", response_model=schemas.AIConversationResponse)
def get_chat_ai_conversation_endpoint(
    chat_id: UUID,
    db: Session = Depends(get_db),
    user_id = Depends(get_current_user_id)
):
    """Get AI conversation history for a chat"""
    
    # Verify user owns the chat
    chat = service.get_chat_by_id(db, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if str(chat.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Get conversation
    conversation = service.get_chat_ai_conversation(db, chat_id, str(user_id))
    
    if not conversation:
        raise HTTPException(status_code=404, detail="No AI conversation found for this chat")
    
    # Sort messages chronologically
    sorted_messages = sorted(conversation.messages, key=lambda x: x.created_at)
    
    return schemas.AIConversationResponse(
        id=str(conversation.id),
        chat_id=str(conversation.chat_id),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            schemas.AIMessageResponse(
                id=str(msg.id),
                message_type=msg.message_type.value,
                content=msg.content,
                created_at=msg.created_at
            )
            for msg in sorted_messages
        ]
    )


# VECTOR-RELATED ENDPOINTS

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
