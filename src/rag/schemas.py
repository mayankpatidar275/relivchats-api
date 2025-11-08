from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

# ============================================================================
# LEGACY SCHEMAS (Keep for backward compatibility if needed)
# ============================================================================

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
    time_span: str

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

# ============================================================================
# NEW INSIGHT GENERATION SCHEMAS
# ============================================================================

class GenerateInsightRequest(BaseModel):
    """Request to generate a new insight"""
    chat_id: str
    insight_type_id: str

class RegenerateInsightRequest(BaseModel):
    """Request to regenerate a failed insight"""
    insight_id: str

class InsightGenerationMetadata(BaseModel):
    """Metadata about the insight generation process"""
    rag_chunks_used: int
    tokens_used: Optional[int]
    generation_time_ms: int
    model_used: str
    confidence_score: Optional[float] = None
    
class UnlockInsightsRequest(BaseModel):
    chat_id: UUID
    category_id: UUID  # User selects category to unlock


class InsightGenerationJob(BaseModel):
    job_id: str
    status: str  # 'queued', 'processing', 'completed', 'failed'
    total_insights: int
    completed_insights: int
    

class UnlockInsightsResponse(BaseModel):
    success: bool
    job_id: str
    coins_deducted: int
    remaining_balance: int
    total_insights: int  # How many insights will be generated
    estimated_time_seconds: int

class InsightResponse(BaseModel):
    """Complete insight response with structured content"""
    id: UUID
    chat_id: UUID
    insight_type_id: UUID
    insight_type_name: str
    display_title: str
    icon: str
    is_premium: bool
    content: Optional[Dict[str, Any]]  # Structured JSON from Gemini
    status: str  # 'generating', 'completed', 'failed'
    error_message: Optional[str]
    generation_metadata: Optional[InsightGenerationMetadata]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class InsightTypeResponse(BaseModel):
    """Insight type definition for frontend"""
    id: UUID
    name: str
    display_title: str
    description: str
    icon: str
    is_premium: bool
    credit_cost: int
    estimated_generation_time_seconds: Optional[int] = None
    is_active: bool
    
    class Config:
        from_attributes = True

class ChatInsightsSummary(BaseModel):
    """Summary of all insights for a chat"""
    chat_id: UUID
    total_insights: int
    completed_insights: int
    failed_insights: int
    generating_insights: int
    available_insight_types: List[InsightTypeResponse]
    generated_insights: List[InsightResponse]

# ============================================================================
# INTERNAL SERVICE SCHEMAS (not exposed via API)
# ============================================================================

class RAGChunk(BaseModel):
    """Single chunk retrieved from vector DB"""
    content: str
    speakers: List[str]
    message_count: int
    time_span: str
    similarity_score: float
    metadata: Dict[str, Any]

class InsightPromptContext(BaseModel):
    """Context passed to prompt builder"""
    user_display_name: str
    partner_name: Optional[str]
    chat_metadata: Dict[str, Any]  # Filtered metadata based on required_fields
    rag_chunks: List[RAGChunk]
    chat_title: Optional[str]

class GeminiStructuredRequest(BaseModel):
    """Request format for Gemini structured output"""
    prompt: str
    response_schema: Dict[str, Any]  # JSON schema for structured output
    temperature: float = 0.7
    max_tokens: Optional[int] = None


# src/rag/schemas.py - ADD these response models

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ... existing schemas ...

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percentage: float
    total_insights: int
    completed_insights: int
    failed_insights: int
    started_at: Optional[datetime]
    estimated_completion_at: Optional[datetime]
    completed_at: Optional[datetime]

class ChatInsightsResponse(BaseModel):
    chat_id: UUID
    generation_status: str
    unlocked_at: Optional[datetime]
    total_requested: int
    total_completed: int
    total_failed: int
    insights: List[InsightResponse]