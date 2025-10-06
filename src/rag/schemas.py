from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

class RAGQueryRequest(BaseModel):
    chat_id: str
    question: str = Field(..., min_length=1, max_length=1000)
    max_chunks: int = Field(default=5, ge=1, le=10)
    include_context: bool = Field(default=True)

class SearchResultResponse(BaseModel):
    vector_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_index: int
    speakers: List[str]
    message_count: int
    time_span: str  # Human readable time span

    class Config:
        from_attributes = True

class GenerateInsightRequest(BaseModel):
    chat_id: str
    insight_type_id: str

class InsightResponse(BaseModel):
    id: UUID
    chat_id: UUID
    insight_type_id: UUID
    content: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    tokens_used: Optional[int]
    generation_time_ms: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    chat_id: str
    chat_title: Optional[str]
    sources_used: List[SearchResultResponse]
    confidence: str  # "high", "medium", "low"
    response_time_ms: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSearchCapability(BaseModel):
    chat_id: str
    is_searchable: bool
    vector_status: str
    total_chunks: int
    indexed_at: Optional[datetime]
    reason: Optional[str] = None  # Why not searchable if applicable