import os
import shutil
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..auth.dependencies import get_current_user_id
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
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Upload and process WhatsApp chat file"""
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
    try:
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # 3. Create a chat entry in the database with 'processing' status
    db_chat = service.create_chat(db, user_id=user_id)
    
    # 4. Add the background task to process the file
    background_tasks.add_task(
        service.process_whatsapp_file_background, 
        chat_id=db_chat.id, 
        file_path=str(file_path), 
        db=db
    )

    # 5. Return a 202 Accepted response with the new chat's details
    return schemas.ChatUploadResponse.from_orm(db_chat)

@router.get("/", response_model=List[schemas.ChatDetailsResponse])
def get_user_chats(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get all chats for the current user"""
    chats = service.get_user_chats(db, user_id)
    
    # Convert to response format with message count
    chat_details = []
    for chat in chats:
        message_count = len(chat.messages) if chat.messages else 0
        chat_detail = schemas.ChatDetailsResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            participants=None,
            user_display_name=chat.user_display_name,
            created_at=chat.created_at,
            status=chat.status,
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

@router.get("/{chat_id}", response_model=schemas.ChatUploadResponse)
def get_chat_details(
    chat_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific chat"""
    chat = service.get_chat_by_id(db, chat_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    return schemas.ChatUploadResponse.from_orm(chat)