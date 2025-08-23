from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json

class ChatUploadResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    participants: Optional[List[str]] = None
    user_display_name: Optional[str] = None
    created_at: datetime
    status: str
    error_log: Optional[str] = None

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, db_chat):
        """Convert database Chat object to schema"""
        participants_list = None
        if db_chat.participants:
            try:
                participants_list = json.loads(db_chat.participants)
            except (json.JSONDecodeError, TypeError):
                participants_list = None
        
        return cls(
            id=db_chat.id,
            user_id=db_chat.user_id,
            title=db_chat.title,
            participants=participants_list,
            user_display_name=db_chat.user_display_name,
            created_at=db_chat.created_at,
            status=db_chat.status,
            error_log=db_chat.error_log
        )

# class ChatParticipantsResponse(BaseModel):
#     id: str
#     participants: List[str]
#     current_user_display_name: Optional[str] = None

class UpdateUserDisplayName(BaseModel):
    user_display_name: str

class ChatDetailsResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    participants: Optional[List[str]] = None
    user_display_name: Optional[str] = None
    created_at: datetime
    status: str
    message_count: int = 0

    class Config:
        from_attributes = True