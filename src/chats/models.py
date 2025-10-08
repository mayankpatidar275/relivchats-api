from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..database import Base
import uuid

class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)  # E.g., The name of the chat group
    participants = Column(Text, nullable=True)  # JSON string of participant names
    chat_metadata = Column(JSON, nullable=True)  # All pre-computed stats
    partner_name = Column(String, nullable=True)  # Extracted partner name
    user_display_name = Column(String, nullable=True)  # User's selected display name
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(String, default="processing")  # 'processing', 'completed', 'failed'
    error_log = Column(Text, nullable=True)  # Store parsing errors for debugging
    
    # Vector-related fields
    vector_status = Column(String, default="pending")  # 'pending', 'indexing', 'completed', 'failed'
    indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    chunk_count = Column(Integer, default=0)
    
    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false')
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    category_id = Column(UUID(as_uuid=True), ForeignKey("analysis_categories.id", ondelete="SET NULL"), nullable=True)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="chat", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="chat", cascade="all, delete-orphan")
    chunks = relationship("MessageChunk", back_populates="chat", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="chats")
    category = relationship("AnalysisCategory", back_populates="chats")
    insights = relationship("Insight", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    chat = relationship("Chat", back_populates="messages")