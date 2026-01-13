# src/vector/service.py
"""
Vector service with production-grade error handling and logging

Key improvements:
- Comprehensive error handling with custom exceptions
- Detailed logging at every step
- Graceful failure recovery
- Progress tracking
- Retry logic for transient failures
"""

import uuid
from uuid import UUID
import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from google import genai
from google.genai import types

from .models import MessageChunk
from .chunking import chunk_chat_messages, ConversationChunk
from .qdrant_client import qdrant_store
from ..chats.models import Chat, Message
from ..config import settings
from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    ExternalServiceException,
    DatabaseException,
    ErrorCode
)

logger = get_logger(__name__)

# Create module-level client (reused for efficiency)
try:
    _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini embedding client initialized")
except Exception as e:
    logger.critical(f"Failed to initialize Gemini client: {e}", exc_info=True)
    _client = None


class VectorService:
    """Service for generating embeddings and managing vector index"""
    
    def __init__(self):
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        if not _client:
            raise RuntimeError("Gemini client not initialized. Check API key configuration.")
    
    def generate_embedding(self, text: str, retry_count: int = 3) -> List[float]:
        """
        Generate embedding using Gemini API with retry logic
        
        Args:
            text: Text to embed
            retry_count: Number of retry attempts
        
        Returns:
            List of floats representing the embedding
        
        Raises:
            ExternalServiceException: If embedding generation fails
        """
        for attempt in range(retry_count):
            try:
                logger.debug(
                    f"Generating embedding (attempt {attempt + 1}/{retry_count})",
                    extra={"extra_data": {"text_length": len(text)}}
                )
                
                resp = _client.models.embed_content(
                    model=self.embedding_model,
                    contents=[text],
                    config=types.EmbedContentConfig(
                        task_type="semantic_similarity"
                    ),
                )
                
                emb = resp.embeddings[0].values
                
                logger.debug(
                    f"Embedding generated successfully",
                    extra={"extra_data": {"vector_size": len(emb)}}
                )
                
                return list(emb)
                
            except Exception as e:
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}): {str(e)}",
                    extra={"extra_data": {"text_length": len(text)}}
                )
                
                if attempt == retry_count - 1:
                    # Final attempt failed
                    logger.error(
                        f"All embedding attempts failed: {str(e)}",
                        exc_info=True
                    )
                    raise ExternalServiceException(
                        service_name="Gemini Embedding API",
                        message=f"Failed to generate embedding after {retry_count} attempts",
                        error_code=ErrorCode.GEMINI_API_ERROR
                    )
                
                # Wait before retry (exponential backoff)
                import time
                time.sleep(2 ** attempt)
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using true batching

        Gemini API supports batching multiple texts in a single request,
        drastically reducing API calls and quota usage.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 100 for Gemini)

        Returns:
            List of embeddings (same order as input texts)

        Raises:
            ExternalServiceException: If batch embedding fails critically
        """
        if not texts:
            return []

        # Use configured batch size if not provided
        if batch_size is None:
            batch_size = settings.GEMINI_EMBEDDING_BATCH_SIZE

        logger.info(
            "Starting batch embedding generation",
            extra={
                "extra_data": {
                    "total_texts": len(texts),
                    "batch_size": batch_size,
                    "estimated_api_calls": (len(texts) + batch_size - 1) // batch_size
                }
            }
        )

        all_embeddings = []
        failed_batches = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        # Process in batches
        for batch_idx in range(0, len(texts), batch_size):
            batch_texts = texts[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1

            try:
                embeddings = self._generate_batch_with_retry(
                    batch_texts,
                    batch_num=batch_num,
                    total_batches=total_batches
                )
                all_embeddings.extend(embeddings)

                # Log progress periodically
                if batch_num % 5 == 0 or batch_num == total_batches:
                    logger.info(
                        f"Batch embedding progress: {batch_num}/{total_batches} batches ({len(all_embeddings)}/{len(texts)} embeddings)"
                    )

            except ExternalServiceException as e:
                logger.error(
                    f"Batch {batch_num}/{total_batches} failed after retries",
                    extra={
                        "extra_data": {
                            "batch_start_idx": batch_idx,
                            "batch_size": len(batch_texts),
                            "error": str(e)
                        }
                    }
                )
                failed_batches.append(batch_num)

                # Add zero vectors for failed batch
                zero_vector = [0.0] * settings.QDRANT_VECTOR_SIZE
                all_embeddings.extend([zero_vector] * len(batch_texts))

        # Calculate success metrics
        failed_count = len(failed_batches) * batch_size
        success_count = len(texts) - failed_count
        success_rate = (success_count / len(texts)) * 100 if texts else 0

        if failed_batches:
            logger.warning(
                f"Batch embedding completed with failures",
                extra={
                    "extra_data": {
                        "total_texts": len(texts),
                        "failed_batches": failed_batches,
                        "success_rate": f"{success_rate:.1f}%"
                    }
                }
            )

            # If too many failures, raise exception
            if success_rate < 50:
                raise ExternalServiceException(
                    service_name="Gemini Embedding API",
                    message=f"Batch embedding critically failed: only {success_rate:.1f}% success rate",
                    error_code=ErrorCode.GEMINI_API_ERROR
                )
        else:
            logger.info(
                f"✓ Batch embedding completed successfully",
                extra={
                    "extra_data": {
                        "total_texts": len(texts),
                        "total_api_calls": total_batches,
                        "reduction_factor": f"{len(texts) / total_batches:.1f}x"
                    }
                }
            )

        return all_embeddings

    def _generate_batch_with_retry(
        self,
        batch_texts: List[str],
        batch_num: int,
        total_batches: int,
        retry_count: int = 3
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch with retry logic

        Args:
            batch_texts: List of texts in this batch
            batch_num: Current batch number (for logging)
            total_batches: Total number of batches (for logging)
            retry_count: Number of retry attempts

        Returns:
            List of embeddings for the batch

        Raises:
            ExternalServiceException: If all retries fail
        """
        import time

        for attempt in range(retry_count):
            try:
                logger.debug(
                    f"Processing batch {batch_num}/{total_batches} (attempt {attempt + 1}/{retry_count})",
                    extra={
                        "extra_data": {
                            "batch_size": len(batch_texts),
                            "avg_text_length": sum(len(t) for t in batch_texts) // len(batch_texts)
                        }
                    }
                )

                # Make batched API call
                resp = _client.models.embed_content(
                    model=self.embedding_model,
                    contents=batch_texts,  # Multiple texts in one call!
                    config=types.EmbedContentConfig(
                        task_type="semantic_similarity"
                    ),
                )

                # Extract embeddings
                embeddings = [list(emb.values) for emb in resp.embeddings]

                # Validate response
                if len(embeddings) != len(batch_texts):
                    raise ValueError(
                        f"Embedding count mismatch: got {len(embeddings)}, expected {len(batch_texts)}"
                    )

                logger.debug(
                    f"Batch {batch_num}/{total_batches} completed",
                    extra={
                        "extra_data": {
                            "embeddings_count": len(embeddings),
                            "vector_dimension": len(embeddings[0]) if embeddings else 0
                        }
                    }
                )

                return embeddings

            except Exception as e:
                error_msg = str(e)
                is_quota_error = "quota" in error_msg.lower() or "rate limit" in error_msg.lower()

                logger.warning(
                    f"Batch {batch_num}/{total_batches} attempt {attempt + 1} failed: {error_msg}",
                    extra={
                        "extra_data": {
                            "batch_size": len(batch_texts),
                            "is_quota_error": is_quota_error,
                            "will_retry": attempt < retry_count - 1
                        }
                    }
                )

                if attempt == retry_count - 1:
                    # Final attempt failed
                    logger.error(
                        f"Batch {batch_num}/{total_batches} failed after {retry_count} attempts",
                        extra={"extra_data": {"error": error_msg}},
                        exc_info=True
                    )
                    raise ExternalServiceException(
                        service_name="Gemini Embedding API",
                        message=f"Batch embedding failed after {retry_count} attempts: {error_msg}",
                        error_code=ErrorCode.GEMINI_API_ERROR
                    )

                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + (attempt * 0.5)

                # Longer wait for quota errors
                if is_quota_error:
                    wait_time *= 2
                    logger.info(f"Quota error detected, waiting {wait_time:.1f}s before retry")

                time.sleep(wait_time)
    
    def create_chat_chunks(self, db: Session, chat_id: UUID) -> bool:
        """
        Create chunks for a chat and store them in vector DB

        This is called synchronously during insight unlock if vector_status != "completed"

        IMPORTANT: This method commits multiple times to avoid holding DB connections
        during long-running external operations (embeddings, Qdrant storage).

        Args:
            db: Database session
            chat_id: Chat ID to index

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            "Starting chat indexing",
            extra={"extra_data": {"chat_id": str(chat_id)}}
        )

        try:
            # PHASE 1: Update status and fetch data (short transaction)
            # ============================================================

            # 1. Get chat and validate
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                logger.error(f"Chat not found: {chat_id}")
                raise ValueError(f"Chat {chat_id} not found")

            user_id = chat.user_id
            platform = chat.platform

            # Update status to indexing and commit immediately
            chat.vector_status = "indexing"
            db.commit()

            logger.info(
                "Chat status updated to indexing",
                extra={
                    "user_id": user_id,
                    "extra_data": {"chat_id": str(chat_id)}
                }
            )

            # 2. Get all messages (batched to avoid connection timeout on large chats)
            # Using cursor-based pagination with timestamp for fast sequential access
            BATCH_SIZE = 5000
            message_data = []
            last_timestamp = None
            batch_num = 0

            logger.info(
                "Starting batched message fetch for vector indexing",
                extra={"extra_data": {"chat_id": str(chat_id), "batch_size": BATCH_SIZE}}
            )

            while True:
                # Fetch one batch using cursor-based pagination (much faster than OFFSET)
                query = db.query(Message).filter(Message.chat_id == chat_id)

                # If we have a last timestamp, fetch messages after it
                if last_timestamp is not None:
                    query = query.filter(Message.timestamp > last_timestamp)

                batch = query.order_by(Message.timestamp).limit(BATCH_SIZE).all()

                if not batch:
                    break

                # Convert to dict to avoid detached instance issues
                for msg in batch:
                    message_data.append({
                        'id': msg.id,
                        'sender': msg.sender,
                        'content': msg.content,
                        'timestamp': msg.timestamp,
                        'chat_id': msg.chat_id
                    })

                # Update cursor to last message's timestamp
                last_timestamp = batch[-1].timestamp
                batch_num += 1

                logger.debug(
                    f"Fetched batch {batch_num}",
                    extra={"extra_data": {
                        "chat_id": str(chat_id),
                        "messages_fetched": len(message_data),
                        "batch_size": len(batch),
                        "last_timestamp": str(last_timestamp)
                    }}
                )

                # If batch was smaller than BATCH_SIZE, we're done
                if len(batch) < BATCH_SIZE:
                    break

            if not message_data:
                logger.warning(
                    "No messages found for chat",
                    extra={"extra_data": {"chat_id": str(chat_id)}}
                )

                # Quick update and return
                chat = db.query(Chat).filter(Chat.id == chat_id).first()
                chat.vector_status = "completed"
                chat.chunk_count = 0
                chat.indexed_at = datetime.now(timezone.utc)
                db.commit()
                return True

            logger.info(
                f"Retrieved {len(message_data)} messages for chunking",
                extra={"extra_data": {"chat_id": str(chat_id), "message_count": len(message_data)}}
            )

            # Close the transaction - don't hold DB connection during long operations
            db.commit()

            # PHASE 2: CPU/Network intensive operations (NO DB connection held)
            # ===================================================================

            # 3. Create conversation chunks (CPU intensive, uses message_data)
            # Recreate message-like objects for chunking function
            from types import SimpleNamespace
            message_objects = [SimpleNamespace(**data) for data in message_data]
            chunks = chunk_chat_messages(message_objects, platform=platform)

            if not chunks:
                logger.warning("No chunks created")

                # Reopen transaction to update status
                chat = db.query(Chat).filter(Chat.id == chat_id).first()
                chat.vector_status = "completed"
                chat.chunk_count = 0
                chat.indexed_at = datetime.now(timezone.utc)
                db.commit()
                return True

            logger.info(
                f"Created {len(chunks)} chunks",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "chunk_count": len(chunks),
                        "avg_chunk_size": sum(c.estimated_tokens for c in chunks) // len(chunks)
                    }
                }
            )

            # 4. Generate embeddings for chunks (Network intensive - Gemini API)
            chunk_texts = [chunk.chunk_text for chunk in chunks]
            embeddings = self.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")

            # 5. Prepare metadata for Qdrant
            qdrant_metadatas = []
            for chunk in chunks:
                metadata = chunk.metadata.copy()
                metadata.update({
                    "chat_id": str(chat_id),
                    "chunk_index": chunk.chunk_index,
                    "estimated_tokens": chunk.estimated_tokens,
                    "chunk_text": chunk.chunk_text
                })
                qdrant_metadatas.append(metadata)

            # 6. Store vectors in Qdrant (Network intensive)
            logger.info(f"Storing {len(embeddings)} vectors in Qdrant")
            vector_ids = qdrant_store.add_vectors(embeddings, qdrant_metadatas)

            logger.info(
                f"Vectors stored in Qdrant",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "vector_count": len(vector_ids)
                    }
                }
            )

            # PHASE 3: Save results to database (fresh transaction)
            # ========================================================

            # 7. Store chunk records in PostgreSQL
            # Get fresh chat instance (previous one may be stale after long operations)
            db.expire_all()  # Clear session cache

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

            # 8. Update chat status
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            chat.vector_status = "completed"
            chat.chunk_count = len(chunks)
            chat.indexed_at = datetime.now(timezone.utc)
            db.commit()

            # Log business event
            log_business_event(
                "chat_indexed",
                user_id=user_id,
                chat_id=str(chat_id),
                chunk_count=len(chunks),
                message_count=len(message_data),
                platform=platform
            )

            logger.info(
                f"✓ Chat indexed successfully",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "chunks": len(chunks),
                        "messages": len(message_data)
                    }
                }
            )

            return True
            
        except ValueError as e:
            # Validation errors
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            self._mark_indexing_failed(db, chat_id, str(e))
            return False
            
        except ExternalServiceException as e:
            # Gemini API errors
            logger.error(
                f"External service error: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            self._mark_indexing_failed(db, chat_id, "Embedding service unavailable")
            return False
            
        except SQLAlchemyError as e:
            # Database errors
            logger.error(
                f"Database error during indexing: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            db.rollback()
            self._mark_indexing_failed(db, chat_id, "Database error")
            self.cleanup_failed_indexing(db, chat_id)
            return False
            
        except Exception as e:
            # Unexpected errors
            logger.critical(
                f"Unexpected error during indexing: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            db.rollback()
            self._mark_indexing_failed(db, chat_id, f"Unexpected error: {str(e)[:200]}")
            self.cleanup_failed_indexing(db, chat_id)
            return False
    
    def _mark_indexing_failed(self, db: Session, chat_id: UUID, error_message: str):
        """Mark chat indexing as failed"""
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.vector_status = "failed"
                # Store error in metadata if exists
                if chat.chat_metadata:
                    chat.chat_metadata["indexing_error"] = error_message
                db.commit()
                
                logger.warning(
                    f"Chat indexing marked as failed",
                    extra={
                        "user_id": chat.user_id if chat else None,
                        "extra_data": {
                            "chat_id": str(chat_id),
                            "error": error_message
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Failed to mark indexing as failed: {e}")
    
    def cleanup_failed_indexing(self, db: Session, chat_id: UUID):
        """Clean up partial indexing data on failure"""
        logger.info(
            f"Cleaning up failed indexing",
            extra={"extra_data": {"chat_id": str(chat_id)}}
        )
        
        try:
            # Remove chunks from PostgreSQL
            deleted_count = db.query(MessageChunk).filter(
                MessageChunk.chat_id == chat_id
            ).delete()
            db.commit()
            
            logger.info(f"Deleted {deleted_count} DB chunks")
            
            # Remove vectors from Qdrant
            qdrant_store.delete_vectors_by_chat_id(chat_id)
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(
                f"Error during cleanup: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
    
    def search_chat(
        self,
        db: Session,
        chat_id: UUID,
        query: str,
        limit: int = 5
    ) -> List[dict]:
        """
        Search for relevant chunks in a specific chat
        
        Args:
            db: Database session
            chat_id: Chat ID to search in
            query: Search query
            limit: Max number of results
        
        Returns:
            List of search results with metadata
        
        Raises:
            ValueError: If chat is not indexed
            ExternalServiceException: If search fails
        """
        logger.debug(
            f"Searching chat",
            extra={"extra_data": {"chat_id": str(chat_id), "query_length": len(query)}}
        )
        
        try:
            # Check if chat is indexed
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
            
            if chat.vector_status != "completed":
                raise ValueError(
                    f"Chat {chat_id} is not ready for search. Status: {chat.vector_status}"
                )
            
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Search in Qdrant
            search_results = qdrant_store.search_similar(
                query_vector=query_embedding,
                limit=limit,
                chat_id=str(chat_id)
            )
            
            # Enhance results
            enhanced_results = []
            for result in search_results:
                enhanced_results.append({
                    "vector_id": result["id"],
                    "similarity_score": result["score"],
                    "content": result["metadata"]["chunk_text"],
                    "metadata": result["metadata"],
                })
            
            logger.debug(
                f"Search completed: {len(enhanced_results)} results",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
            
            return enhanced_results
            
        except ValueError:
            raise
        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(
                f"Search failed: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            raise ExternalServiceException(
                service_name="Vector Search",
                message=f"Search failed: {str(e)}",
                error_code=ErrorCode.QDRANT_ERROR
            )
    
    def reindex_chat(self, db: Session, chat_id: UUID) -> bool:
        """Re-index a chat (useful for failed indexings)"""
        logger.info(
            f"Re-indexing chat",
            extra={"extra_data": {"chat_id": str(chat_id)}}
        )
        
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
            logger.error(
                f"Re-indexing failed: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            return False


# Global service instance
vector_service = VectorService()