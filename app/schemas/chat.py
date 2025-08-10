from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request Models
class ChatUploadRequest(BaseModel):
    # This will be used when user confirms the participants and `me` identifier
    file_name: str
    participants: List[str]
    me_identifier: str

class MessageBase(BaseModel):
    date: datetime
    author: str
    message_text: str
    attachment_filename: Optional[str] = None
    attachment_url: Optional[str] = None

class ChatCreate(BaseModel):
    name: str
    participants: List[str]
    me_identifier: str
    content_hash: str
    messages: List[MessageBase] # For internal use during chat creation

# Response Models
class MessageResponse(MessageBase):
    id: int
    chat_id: int

    class Config:
        from_attributes = True # Allow Pydantic to read from ORM attributes

class ChatResponse(BaseModel):
    id: int
    name: str
    participants: List[str]
    me_identifier: str
    imported_at: datetime
    content_hash: str

    class Config:
        from_attributes = True

class ParticipantSelectionResponse(BaseModel):
    # Response after initial file upload and parsing on backend
    file_name: str
    participants: List[str]
    message_count: int

class ParsedMessageTemp(BaseModel):
    date: datetime
    author: str
    message: str # Original 'message' field from parser
    attachment: Optional[str] = None # Original 'attachment' field from parser

class InsightResponse(BaseModel):
    id: int
    chat_id: int
    type: str
    data: Dict[str, Any]
    generated_at: datetime

    class Config:
        from_attributes = True