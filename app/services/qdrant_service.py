from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        # Initialize client but don't ensure collection exists immediately
        self.client: Optional[QdrantClient] = None
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self.collection_name = "chat_messages_vectors"
        self._initialized = False
        
        # Try to initialize connection
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Qdrant client with retry logic"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            # Test connection with a simple operation
            self.client.get_collections()
            logger.info("Successfully connected to Qdrant")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            self.client = None

    def _ensure_connection(self):
        """Ensure we have a valid connection before operations"""
        if self.client is None:
            logger.info("Attempting to reconnect to Qdrant...")
            self._initialize_client()
            
        if self.client is None:
            raise ConnectionError("Cannot connect to Qdrant. Please ensure Qdrant is running and accessible.")

    def _ensure_collection_exists(self):
        """Ensure collection exists, with lazy initialization"""
        if self._initialized:
            return
            
        self._ensure_connection()
        
        try:
            # Try to get existing collection first
            self.client.get_collection(collection_name=self.collection_name)
            logger.info(f"Qdrant collection '{self.collection_name}' already exists.")
            self._initialized = True
        except Exception as get_error:
            logger.info(f"Collection doesn't exist, creating: {get_error}")
            try:
                # Create collection if it doesn't exist
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.model.get_sentence_embedding_dimension(), 
                        distance=models.Distance.COSINE
                    ),
                )
                logger.info(f"Qdrant collection '{self.collection_name}' created.")
                self._initialized = True
            except Exception as create_error:
                logger.error(f"Failed to create Qdrant collection: {create_error}")
                raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        return self.model.encode(text).tolist()

    def index_messages(self, messages: List[Dict[str, Any]]):
        """Index messages into Qdrant with error handling"""
        self._ensure_collection_exists()
        
        if not messages:
            logger.warning("No messages provided for indexing")
            return
            
        points = []
        for msg in messages:
            try:
                # Create unique point ID
                point_id = f"chat_{msg['chat_id']}_msg_{msg['id']}"
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=self.embed_text(msg['message_text']),
                        payload={
                            "chat_id": msg['chat_id'],
                            "message_id": msg['id'],
                            "author": msg['author'],
                            "date": msg['date'].isoformat() if hasattr(msg['date'], 'isoformat') else str(msg['date']),
                            "message_text": msg['message_text'],
                            "attachment_filename": msg.get('attachment_filename'),
                            "attachment_url": msg.get('attachment_url')
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to process message {msg.get('id', 'unknown')}: {e}")
                continue
        
        if points:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    wait=True,
                    points=points
                )
                logger.info(f"Successfully indexed {len(points)} messages into Qdrant.")
            except Exception as e:
                logger.error(f"Failed to upsert points to Qdrant: {e}")
                raise
        else:
            logger.warning("No valid points to index")

    def search_messages(self, query_text: str, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Search messages with error handling"""
        self._ensure_collection_exists()
        
        try:
            query_vector = self.embed_text(query_text)
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="chat_id",
                            match=models.MatchValue(value=chat_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True
            )
            return [hit.payload for hit in search_result]
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []  # Return empty list instead of crashing

    def health_check(self) -> bool:
        """Check if Qdrant service is healthy"""
        try:
            self._ensure_connection()
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

# Lazy initialization - only create instance when first accessed
_qdrant_service_instance = None

def get_qdrant_service() -> QdrantService:
    """Get QdrantService instance with lazy initialization"""
    global _qdrant_service_instance
    if _qdrant_service_instance is None:
        _qdrant_service_instance = QdrantService()
    return _qdrant_service_instance

# For backward compatibility, but prefer using get_qdrant_service()
qdrant_service = get_qdrant_service()