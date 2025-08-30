from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)  # E.g., The name of the chat group
    participants = Column(Text, nullable=True)  # JSON string of participant names
    user_display_name = Column(String, nullable=True)  # User's selected display name
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(String, default="processing")  # 'processing', 'completed', 'failed'
    error_log = Column(Text, nullable=True)  # Store parsing errors for debugging
    
    # Vector-related fields
    vector_status = Column(String, default="pending")  # 'pending', 'indexing', 'completed', 'failed'
    indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    chunk_count = Column(Integer, default=0)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    chunks = relationship("MessageChunk", back_populates="chat", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="chats")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    chat = relationship("Chat", back_populates="messages")