from pydantic import BaseModel
from datetime import datetime

class ChatUploadResponse(BaseModel):
    id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True