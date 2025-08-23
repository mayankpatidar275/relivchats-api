from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    chats = relationship("Chat", back_populates="owner", cascade="all, delete-orphan")