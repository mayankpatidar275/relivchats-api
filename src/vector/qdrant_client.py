# src/vector/qdrant_client.py
"""
Qdrant vector store with production-grade error handling and timeout management

Key improvements:
- Configurable timeouts for large batches
- Retry logic for transient failures
- Batch size optimization
- Comprehensive error handling
"""

import uuid
from uuid import UUID
from typing import List, Dict, Any, Optional
import time

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import ResponseHandlingException

from ..config import settings
from ..logging_config import get_logger
from ..error_handlers import ExternalServiceException, ErrorCode

logger = get_logger(__name__)


class QdrantVectorStore:
    """Qdrant vector store with timeout and retry handling"""
    
    # Configuration constants
    DEFAULT_TIMEOUT = 60  # 60 seconds for normal operations
    BATCH_TIMEOUT = 300   # 5 minutes for large batch operations
    MAX_BATCH_SIZE = 100  # Split large batches to avoid timeouts
    MAX_RETRIES = 3       # Number of retry attempts
    
    def __init__(self):
        try:
            # Initialize client with increased timeout
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=self.BATCH_TIMEOUT,  # CRITICAL: Set timeout for large operations
            )
            
            self.collection_name = settings.QDRANT_COLLECTION_NAME
            self._ensure_collection_exists()
            
            logger.info(
                "Qdrant client initialized",
                extra={
                    "extra_data": {
                        "collection": self.collection_name,
                        "timeout": self.BATCH_TIMEOUT,
                        "max_batch_size": self.MAX_BATCH_SIZE
                    }
                }
            )
            
        except Exception as e:
            logger.critical(
                f"Failed to initialize Qdrant client: {str(e)}",
                exc_info=True
            )
            raise

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                
                # Create index for chat_id (faster filtering)
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="chat_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                
                logger.info(f"✓ Qdrant collection created: {self.collection_name}")
            else:
                logger.debug(f"Qdrant collection exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(
                f"Failed to ensure collection exists: {str(e)}",
                exc_info=True
            )
            raise ExternalServiceException(
                service_name="Qdrant",
                message=f"Collection setup failed: {str(e)}",
                error_code=ErrorCode.QDRANT_ERROR
            )

    def add_vectors(
        self, 
        vectors: List[List[float]], 
        metadatas: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add vectors with metadata to Qdrant with batching and retry logic
        
        Args:
            vectors: List of embedding vectors
            metadatas: List of metadata dicts
        
        Returns:
            List of vector IDs
        
        Raises:
            ExternalServiceException: If all retry attempts fail
        """
        if len(vectors) != len(metadatas):
            raise ValueError("Vectors and metadatas must have the same length")
        
        total_vectors = len(vectors)
        
        logger.info(
            f"Adding {total_vectors} vectors to Qdrant",
            extra={"extra_data": {"vector_count": total_vectors}}
        )
        
        # If batch is small, add directly
        if total_vectors <= self.MAX_BATCH_SIZE:
            return self._add_vectors_batch(vectors, metadatas)
        
        # Split large batches to avoid timeout
        logger.info(
            f"Splitting large batch into smaller chunks",
            extra={
                "extra_data": {
                    "total": total_vectors,
                    "batch_size": self.MAX_BATCH_SIZE
                }
            }
        )
        
        all_vector_ids = []
        
        for i in range(0, total_vectors, self.MAX_BATCH_SIZE):
            batch_vectors = vectors[i:i + self.MAX_BATCH_SIZE]
            batch_metadatas = metadatas[i:i + self.MAX_BATCH_SIZE]
            
            logger.debug(
                f"Processing batch {i // self.MAX_BATCH_SIZE + 1}",
                extra={
                    "extra_data": {
                        "start": i,
                        "end": i + len(batch_vectors),
                        "batch_size": len(batch_vectors)
                    }
                }
            )
            
            batch_ids = self._add_vectors_batch(batch_vectors, batch_metadatas)
            all_vector_ids.extend(batch_ids)
        
        logger.info(
            f"✓ Added {len(all_vector_ids)} vectors in {(total_vectors + self.MAX_BATCH_SIZE - 1) // self.MAX_BATCH_SIZE} batches"
        )
        
        return all_vector_ids
    
    def _add_vectors_batch(
        self,
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]],
        retry_count: int = 0
    ) -> List[str]:
        """
        Add a single batch of vectors with retry logic
        
        Args:
            vectors: Batch of vectors
            metadatas: Batch of metadata
            retry_count: Current retry attempt
        
        Returns:
            List of vector IDs
        """
        try:
            points = []
            vector_ids = []
            
            for vector, metadata in zip(vectors, metadatas):
                vector_id = str(uuid.uuid4())
                vector_ids.append(vector_id)
                
                points.append(
                    PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload={**metadata, "chat_id": metadata.get("chat_id")}
                    )
                )
            
            # Batch insert points
            start_time = time.time()
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True  # Wait for operation to complete
            )
            
            duration = time.time() - start_time
            
            logger.debug(
                f"Batch upsert completed in {duration:.2f}s",
                extra={
                    "extra_data": {
                        "vector_count": len(vectors),
                        "duration_seconds": round(duration, 2)
                    }
                }
            )
            
            return vector_ids
            
        except ResponseHandlingException as e:
            error_msg = str(e)
            
            # Check if it's a timeout error
            is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
            
            if is_timeout and retry_count < self.MAX_RETRIES:
                # Retry with exponential backoff
                wait_time = 2 ** retry_count  # 1s, 2s, 4s
                
                logger.warning(
                    f"Qdrant timeout, retrying in {wait_time}s (attempt {retry_count + 1}/{self.MAX_RETRIES})",
                    extra={
                        "extra_data": {
                            "vector_count": len(vectors),
                            "retry_attempt": retry_count + 1,
                            "wait_seconds": wait_time
                        }
                    }
                )
                
                time.sleep(wait_time)
                
                # Retry
                return self._add_vectors_batch(vectors, metadatas, retry_count + 1)
            
            # Max retries reached or non-timeout error
            logger.error(
                f"Failed to add vectors after {retry_count} retries: {error_msg}",
                extra={"extra_data": {"vector_count": len(vectors)}},
                exc_info=True
            )
            
            raise ExternalServiceException(
                service_name="Qdrant",
                message=f"Failed to add vectors: {error_msg}",
                error_code=ErrorCode.QDRANT_ERROR
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected error adding vectors: {str(e)}",
                extra={"extra_data": {"vector_count": len(vectors)}},
                exc_info=True
            )
            
            raise ExternalServiceException(
                service_name="Qdrant",
                message=f"Failed to add vectors: {str(e)}",
                error_code=ErrorCode.QDRANT_ERROR
            )

    def search_similar(
        self, 
        query_vector: List[float], 
        limit: int = 5,
        chat_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors with optional chat filtering
        
        Args:
            query_vector: Query embedding
            limit: Max results
            chat_id: Optional chat ID filter
        
        Returns:
            List of search results
        """
        try:
            search_filter = None
            if chat_id:
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="chat_id",
                            match=models.MatchValue(value=chat_id)
                        )
                    ]
                )
            
            logger.debug(
                f"Searching Qdrant",
                extra={
                    "extra_data": {
                        "limit": limit,
                        "chat_id": chat_id,
                        "has_filter": bool(search_filter)
                    }
                }
            )
            
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=limit,
            )
            
            results = []
            for result in search_results.points:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "metadata": result.payload,
                })
            
            logger.debug(
                f"Found {len(results)} results",
                extra={"extra_data": {"result_count": len(results)}}
            )
            
            return results
            
        except ResponseHandlingException as e:
            logger.error(
                f"Search failed: {str(e)}",
                extra={"extra_data": {"chat_id": chat_id}},
                exc_info=True
            )
            raise ExternalServiceException(
                service_name="Qdrant",
                message=f"Search failed: {str(e)}",
                error_code=ErrorCode.QDRANT_ERROR
            )
        except Exception as e:
            logger.error(
                f"Unexpected search error: {str(e)}",
                extra={"extra_data": {"chat_id": chat_id}},
                exc_info=True
            )
            raise ExternalServiceException(
                service_name="Qdrant",
                message=f"Search failed: {str(e)}",
                error_code=ErrorCode.QDRANT_ERROR
            )

    def delete_vectors_by_chat_id(self, chat_id: UUID):
        """
        Delete all vectors for a specific chat
        
        Args:
            chat_id: Chat ID
        """
        try:
            logger.info(
                f"Deleting vectors for chat",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="chat_id",
                                match=models.MatchValue(value=str(chat_id))
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"✓ Deleted vectors for chat {chat_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to delete vectors: {str(e)}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
            # Don't raise - cleanup is best-effort
            # Log the error but continue


# Global instance
qdrant_store = QdrantVectorStore()