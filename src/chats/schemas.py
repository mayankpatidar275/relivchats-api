from pydantic import BaseModel, ValidationError
from datetime import datetime
from typing import Optional, List
import json
from uuid import UUID

# export interface Chat {
#   id: string;
#   filename: string;
#   platform: "whatsapp" | "telegram" | "instagram" | "other";
#   category_id?: string;
#   category_slug?: string;
#   category_name?: string;
#   uploaded_at: string;
#   participant_count: number;
#   message_count: number;
#   date_range_start?: string;
#   date_range_end?: string;
#   file_size_bytes: number;
#   processing_status: "pending" | "processed" | "failed";
#   insights_unlocked: boolean; // NEW: Track if insights are unlocked
# }

class ChatUploadResponse(BaseModel):
    chat_id: UUID
    user_id: str
    title: Optional[str] = None
    filename: str
    participants: Optional[List[str]] = None
    user_display_name: Optional[str] = None
    chat_metadata: Optional[dict] = None  # Raw JSON with all stats
    category_id: Optional[UUID] = None
    category_slug: Optional[str] = None  # ADD THIS
    category_name: Optional[str] = None  # ADD THIS
    created_at: datetime
    insights_unlocked: bool  # check if insights exist
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
        
        # Get category info if exists
        category_slug = None
        category_name = None
        if db_chat.category:
            category_slug = db_chat.category.name  # 'romantic', 'friendship'
            category_name = db_chat.category.display_name  # 'Romantic'
        
         # Check if insights exist
        insights_unlocked = len(db_chat.insights) > 0
        
        return cls(
            chat_id=db_chat.id,
            user_id=db_chat.user_id,
            title=db_chat.title,
            filename=db_chat.title or "Unnamed Chat",
            participants=participants_list,
            user_display_name=db_chat.user_display_name,
            chat_metadata=db_chat.chat_metadata,  # Return raw JSON dict
            category_id=db_chat.category_id,
            category_slug=category_slug,
            category_name=category_name,
            created_at=db_chat.created_at,
            insights_unlocked=insights_unlocked,
            status=db_chat.status,
            vector_status=getattr(db_chat, 'vector_status', 'pending'),
            chunk_count=getattr(db_chat, 'chunk_count', 0),
            indexed_at=getattr(db_chat, 'indexed_at', None),
            error_log=db_chat.error_log
        )

class GetChatResponse(BaseModel):
    chat_id: UUID
    user_id: str
    title: Optional[str] = None
    filename: str
    participants: Optional[List[str]] = None
    user_display_name: Optional[str] = None
    chat_metadata: Optional[dict] = None  # Raw JSON with all stats
    category_id: Optional[UUID] = None
    category_slug: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime
    status: str
    insights_unlocked: bool  # NEW - check if any insights exist
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
        
        # Get category info if exists
        category_slug = None
        category_name = None
        if db_chat.category:
            category_slug = db_chat.category.name
            category_name = db_chat.category.display_name
        
        # Check if insights exist and are completed
        # insights_unlocked = any(
        #     insight.status == InsightStatus.COMPLETED 
        #     for insight in db_chat.insights
        # ) if db_chat.insights else False

        # Check if insights exist
        insights_unlocked = len(db_chat.insights) > 0
        
        return cls(
            chat_id=db_chat.id,
            user_id=db_chat.user_id,
            title=db_chat.title,
            filename=db_chat.title or "Unnamed Chat",
            participants=participants_list,
            user_display_name=db_chat.user_display_name,
            chat_metadata=db_chat.chat_metadata,  # Return raw JSON dict
            category_id=db_chat.category_id,
            category_slug=category_slug,
            category_name=category_name,
            insights_unlocked=insights_unlocked,
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

class InsightTypeBase(BaseModel):
    id: UUID
    name: str
    display_title: str
    description: Optional[str]
    icon: Optional[str]
    is_premium: bool

    class Config:
        from_attributes = True

class InsightWithTypeResponse(BaseModel):
    insight_type: InsightTypeBase
    status: str  # "pending", "generating", "completed", "failed"
    insight_id: Optional[UUID]  # null if not generated
    has_content: bool
    
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

class ChatDeleteResponse(BaseModel):
    success: bool
    message: str
    chat_id: UUID
    
# class ChatParticipantsResponse(BaseModel):
#     id: str
#     participants: List[str]
#     current_user_display_name: Optional[str] = None
