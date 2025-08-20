import os
import shutil
from pathlib import Path
from typing import Annotated

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
        # We need to read the file in a streaming fashion to avoid memory issues
        # with very large files before we save it.
        file_path = UPLOAD_FOLDER / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # 3. Create a chat entry in the database with 'processing' status
    db_chat = service.create_chat(db, user_id=user_id)
    
    # 4. Add the background task to process the file
    background_tasks.add_task(service.process_whatsapp_file_background, chat_id=db_chat.id, file_path=file_path, db=db)

    # 5. Return a 202 Accepted response with the new chat's details
    return db_chat