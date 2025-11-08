from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean, TIMESTAMP, JSON, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import uuid
import enum
from sqlalchemy.dialects.postgresql import JSONB

# TODO: move these to categories folder
class InsightStatus(enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisCategory(Base):
    __tablename__ = "analysis_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # romantic, family, business
    display_name = Column(String, nullable=False)  # "Romantic Relationship"
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)  # emoji or icon name
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    chats = relationship("Chat", back_populates="category")
    insight_types = relationship("CategoryInsightType", back_populates="category", cascade="all, delete-orphan")

class InsightType(Base):
    __tablename__ = "insight_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # conflict_analysis, red_flags
    display_title = Column(String, nullable=False)  # "Conflict Analysis"
    description = Column(Text, nullable=True)  # What this insight provides
    icon = Column(String, nullable=True)
    prompt_template = Column(Text, nullable=False)  # Gemini prompt template
    rag_query_keywords = Column(Text, nullable=True)  # "conflicts, arguments, fights"
    response_schema = Column(JSONB, nullable=False)  # Gemini JSON schema
    required_metadata_fields = Column(JSONB, nullable=True)  # ["total_messages", "user_stats"]

    # Premium & cost tracking
    is_premium = Column(Boolean, default=False, nullable=False)
    credit_cost = Column(Integer, default=1, nullable=False)  # For future payment
    estimated_tokens = Column(Integer, nullable=True)  # Avg tokens used
    avg_generation_time_ms = Column(Integer, nullable=True)  # Performance tracking
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    supports_group_chats = Column(Boolean, default=False, nullable=False)
    max_participants = Column(Integer, nullable=True)  # NULL = unlimited
    
    # Relationships
    categories = relationship("CategoryInsightType", back_populates="insight_type", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="insight_type", cascade="all, delete-orphan")

class CategoryInsightType(Base):
    __tablename__ = "category_insight_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("analysis_categories.id", ondelete="CASCADE"), nullable=False)
    insight_type_id = Column(UUID(as_uuid=True), ForeignKey("insight_types.id", ondelete="CASCADE"), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)  # Order in UI
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    category = relationship("AnalysisCategory", back_populates="insight_types")
    insight_type = relationship("InsightType", back_populates="categories")
    
    __table_args__ = (
        Index('idx_category_insight_type', 'category_id', 'insight_type_id', unique=True),
    )

class Insight(Base):
    __tablename__ = "insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    insight_type_id = Column(UUID(as_uuid=True), ForeignKey("insight_types.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    content = Column(JSON, nullable=True)  # Structured insight data
    status = Column(Enum(InsightStatus), default=InsightStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    tokens_used = Column(Integer, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    rag_chunks_used = Column(Integer, nullable=True)  # How many chunks retrieved
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="insights")
    insight_type = relationship("InsightType", back_populates="insights")
    
    __table_args__ = (
        Index('idx_chat_insight_type', 'chat_id', 'insight_type_id', unique=True),
    )

class ChatInsightGenerationStatus(enum.Enum):
    NOT_STARTED = "not_started"      # Default state
    QUEUED = "queued"                 # Unlock triggered, waiting
    GENERATING = "generating"         # At least 1 insight being generated
    COMPLETED = "completed"           # All insights successful
    PARTIAL_FAILURE = "partial_failure"  # Some failed, some succeeded
    FAILED = "failed"                 # All insights failed
class InsightGenerationJob(Base):
    __tablename__ = "insight_generation_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, unique=True, nullable=False, index=True)  # External job ID
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("analysis_categories.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    
    # Job status
    status = Column(String, default="queued", nullable=False)  # queued, running, completed, failed
    
    # Insights tracking
    total_insights = Column(Integer, nullable=False)
    completed_insights = Column(Integer, default=0)
    failed_insights = Column(Integer, default=0)
    
    # Timing
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    estimated_completion_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Performance
    total_tokens_used = Column(Integer, default=0)
    total_generation_time_ms = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    failed_insight_ids = Column(JSON, nullable=True)  # List of failed insight IDs
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())



# Why this matters:

# Atomic job tracking: One record per unlock
# Frontend can poll this instead of querying all insights
# Analytics goldmine: Track which categories take longest, cost most
# Retry logic: Know exactly what failed




class MessageType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false')
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat = relationship("Chat", back_populates="ai_conversations")
    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")


class AIMessage(Base):
    __tablename__ = "ai_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(Enum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    conversation = relationship("AIConversation", back_populates="messages")