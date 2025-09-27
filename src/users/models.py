from sqlalchemy import Column, String, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false')
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    chats = relationship("Chat", back_populates="owner", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")