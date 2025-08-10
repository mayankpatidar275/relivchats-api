from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False) # Link to Clerk user ID
    name = Column(String, index=True, nullable=False) # Name of the chat, e.g., "Chat with John Doe"
    participants = Column(JSON, nullable=False) # List of participant names as JSON array
    me_identifier = Column(String, nullable=False) # User's selected name in the chat
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    content_hash = Column(String, unique=True, index=True, nullable=False) # For deduplication

    owner = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    ai_conversations = relationship("AIChatConversation", back_populates="chat", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    author = Column(String, nullable=False)
    message_text = Column(Text, nullable=False) # Renamed to avoid conflict with 'message' concept
    attachment_filename = Column(String, nullable=True) # Original filename from chat.txt
    attachment_url = Column(String, nullable=True) # S3 URL for the attachment

    chat = relationship("Chat", back_populates="messages")

class AIChatConversation(Base):
    __tablename__ = "ai_chat_conversations"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False) # Link to Clerk user ID
    title = Column(String, nullable=False) # e.g., "Conversation about our trip"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    chat = relationship("Chat", back_populates="ai_conversations")
    user = relationship("User", back_populates="ai_conversations")
    ai_messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_chat_conversations.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False) # 'user' or 'ai'
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    model_response_metadata = Column(JSON, nullable=True) # Store LLM specific data

    conversation = relationship("AIChatConversation", back_populates="ai_messages")

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False) # e.g., 'sentiment_analysis', 'common_phrases'
    data = Column(JSON, nullable=False) # JSONB field to store the actual insight data
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="insights")