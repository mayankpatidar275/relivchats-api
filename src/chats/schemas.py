from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import json
from uuid import UUID

class ChatUploadResponse(BaseModel):
    id: UUID
    user_id: str
    title: Optional[str] = None
    participants: Optional[List[str]] = None
    user_display_name: Optional[str] = None
    created_at: datetime
    status: str
    vector_status: str = "pending"
    chunk_count: int = 0
    indexed_at: Optional[datetime] = None
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
            vector_status=getattr(db_chat, 'vector_status', 'pending'),
            chunk_count=getattr(db_chat, 'chunk_count', 0),
            indexed_at=getattr(db_chat, 'indexed_at', None),
            error_log=db_chat.error_log
        )
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
    vector_status: str = "pending"
    chunk_count: int = 0
    indexed_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True
        
class ChatMessagesResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender: Optional[str] = None
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class VectorStatusResponse(BaseModel):
    chat_id: str
    vector_status: str
    chunk_count: int
    indexed_at: Optional[datetime] = None
    is_searchable: bool

    class Config:
        from_attributes = True

class AIMessageResponse(BaseModel):
    id: str
    message_type: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AIConversationResponse(BaseModel):
    id: str
    chat_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[AIMessageResponse]
    
    class Config:
        from_attributes = True

# class ChatParticipantsResponse(BaseModel):
#     id: str
#     participants: List[str]
#     current_user_display_name: Optional[str] = None
