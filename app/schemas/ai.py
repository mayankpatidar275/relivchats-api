from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AIChatConversationCreate(BaseModel):
    chat_id: int
    title: str
    user_id: str # Will be inferred from auth, but good for schema clarity

class AIMessageCreate(BaseModel):
    conversation_id: int
    sender: str # 'user' or 'ai'
    text: str
    model_response_metadata: Optional[Dict[str, Any]] = None

class AIMessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: str
    text: str
    created_at: datetime
    model_response_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class AIChatConversationResponse(BaseModel):
    id: int
    chat_id: int
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AIChatRequest(BaseModel):
    prompt: str
    conversation_id: Optional[int] = None # If continuing an existing conversation