import uuid
from uuid import UUID
import json
from datetime import datetime
from typing import List, Optional

import google.generativeai as genai
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import MessageChunk
from .chunking import chunk_chat_messages, ConversationChunk
from .qdrant_client import qdrant_store
from ..chats.models import Chat, Message
from ..config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class VectorService:
    def __init__(self):
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini API"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="semantic_similarity"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def create_chat_chunks(self, db: Session, chat_id: UUID) -> bool:
        """Create chunks for a chat and store them"""
        try:
            # Get chat and its messages
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")

            # Update status to indexing
            chat.vector_status = "indexing"
            db.commit()

            # Get all messages for this chat, ordered by timestamp
            messages = db.query(Message).filter(
                Message.chat_id == chat_id
            ).order_by(Message.timestamp).all()

            if not messages:
                chat.vector_status = "completed"
                chat.chunk_count = 0
                chat.indexed_at = datetime.utcnow()
                db.commit()
                return True

            # Create conversation chunks
            chunks = chunk_chat_messages(messages)

            # print("chunk_chat_messages:  ",chunks)
            
            if not chunks:
                chat.vector_status = "completed" 
                chat.chunk_count = 0
                chat.indexed_at = datetime.utcnow()
                db.commit()
                return True

            # Generate embeddings for chunks
            chunk_texts = [chunk.chunk_text for chunk in chunks]
            embeddings = self.generate_embeddings_batch(chunk_texts)

            # Prepare metadata for Qdrant
            qdrant_metadatas = []
            for chunk in chunks:
                metadata = chunk.metadata.copy()
                metadata.update({
                    "chat_id": str(chat_id),
                    "chunk_index": chunk.chunk_index,
                    "estimated_tokens": chunk.estimated_tokens,
                    "chunk_text": chunk.chunk_text  # Store text in metadata for retrieval
                })
                qdrant_metadatas.append(metadata)

            # Store vectors in Qdrant
            vector_ids = qdrant_store.add_vectors(embeddings, qdrant_metadatas)

            # Store chunk records in PostgreSQL
            db_chunks = []
            for chunk, vector_id in zip(chunks, vector_ids):
                db_chunk = MessageChunk(
                    id=uuid.uuid4(),
                    chat_id=chat_id,
                    chunk_text=chunk.chunk_text,
                    chunk_metadata=chunk.metadata, 
                    vector_id=vector_id,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.estimated_tokens
                )
                db_chunks.append(db_chunk)

            # Bulk insert chunks
            db.bulk_save_objects(db_chunks)

            # Update chat status
            chat.vector_status = "completed"
            chat.chunk_count = len(chunks)
            chat.indexed_at = datetime.utcnow()
            db.commit()

            print(f"Successfully indexed chat {chat_id}: {len(chunks)} chunks created")
            return True

        except Exception as e:
            print(f"Error creating chunks for chat {chat_id}: {e}")
            
            # Update chat status to failed
            try:
                chat = db.query(Chat).filter(Chat.id == chat_id).first()
                if chat:
                    chat.vector_status = "failed"
                    db.commit()
            except:
                pass

            # Clean up any partial data
            self.cleanup_failed_indexing(db, chat_id)
            return False

    def cleanup_failed_indexing(self, db: Session, chat_id: UUID):
        """Clean up partial indexing data on failure"""
        try:
            # Remove chunks from PostgreSQL
            db.query(MessageChunk).filter(MessageChunk.chat_id == chat_id).delete()
            db.commit()
            
            # Remove vectors from Qdrant
            qdrant_store.delete_vectors_by_chat_id(chat_id)
            
        except Exception as e:
            print(f"Error during cleanup for chat {chat_id}: {e}")

    def search_chat(
        self, 
        db: Session, 
        chat_id: uuid, 
        query: str, 
        limit: int = 5
    ) -> List[dict]:
        """Search for relevant chunks in a specific chat"""
        try:
            # Check if chat is indexed
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat or chat.vector_status != "completed":
                raise ValueError(f"Chat {chat_id} is not ready for search")

            # Generate query embedding
            query_embedding = self.generate_embedding(query)

            # Search in Qdrant
            search_results = qdrant_store.search_similar(
                query_vector=query_embedding,
                limit=limit,
                chat_id=chat_id
            )

            # Enhance results with chunk data from DB if needed
            enhanced_results = []
            for result in search_results:
                enhanced_results.append({
                    "vector_id": result["id"],
                    "similarity_score": result["score"],
                    "content": result["metadata"]["chunk_text"],
                    "metadata": result["metadata"],
                })

            # print("search_results: ", enhanced_results)
            return enhanced_results

        except Exception as e:
            print(f"Error searching chat {chat_id}: {e}")
            raise

    def reindex_chat(self, db: Session, chat_id: uuid) -> bool:
        """Re-index a chat (useful for failed indexings)"""
        try:
            # Clean up existing data
            self.cleanup_failed_indexing(db, chat_id)
            
            # Reset chat status
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.vector_status = "pending"
                chat.chunk_count = 0
                chat.indexed_at = None
                db.commit()
            
            # Re-create chunks
            return self.create_chat_chunks(db, chat_id)
            
        except Exception as e:
            print(f"Error reindexing chat {chat_id}: {e}")
            return False


# Global service instance
vector_service = VectorService()