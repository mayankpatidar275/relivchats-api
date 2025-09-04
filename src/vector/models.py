from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import uuid

class MessageChunk(Base):
   __tablename__ = "message_chunks"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
   chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
   chunk_text = Column(Text, nullable=False)  # Combined messages content
   chunk_metadata = Column(JSON, nullable=True)  # Sender info, timestamp range, message_ids
   vector_id = Column(String, nullable=True)  # Reference to Qdrant vector
   chunk_index = Column(Integer, nullable=False)  # Order of chunk in chat (0, 1, 2...)
   token_count = Column(Integer, nullable=True)  # Approximate token count
   created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

   chat = relationship("Chat", back_populates="chunks")