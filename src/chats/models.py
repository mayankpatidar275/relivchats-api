from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    title = Column(String, nullable=True) # E.g., The name of the chat group
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(String, default="processing") # 'processing', 'completed', 'failed'

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="chats")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    sender = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    chat = relationship("Chat", back_populates="messages")