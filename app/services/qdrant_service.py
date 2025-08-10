from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self.collection_name = "chat_messages_vectors"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        try:
            # Recreate collection for development/testing ease.
            # In production, you'd likely `get_collection` and `create_collection` if not exists.
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=self.model.get_sentence_embedding_dimension(), distance=models.Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{self.collection_name}' recreated.")
        except Exception as e:
            logger.warning(f"Could not recreate Qdrant collection (it might already exist or be unreachable): {e}")
            try:
                # Attempt to just get the collection if recreation failed
                self.client.get_collection(collection_name=self.collection_name)
                logger.info(f"Qdrant collection '{self.collection_name}' already exists.")
            except Exception as e_check:
                logger.error(f"Failed to connect to or verify Qdrant collection: {e_check}")
                raise

    def embed_text(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

    def index_messages(self, messages: List[Dict[str, Any]]):
        points = []
        for msg in messages:
            # Qdrant expects int or string IDs. Using chat_id and message_id.
            # Make sure this ID is unique across all messages in Qdrant.
            # A good way is to use a composite key or UUID.
            # For simplicity, let's use a composite string ID for now.
            point_id = f"chat_{msg['chat_id']}_msg_{msg['id']}"
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=self.embed_text(msg['message_text']),
                    payload={
                        "chat_id": msg['chat_id'],
                        "message_id": msg['id'],
                        "author": msg['author'],
                        "date": msg['date'].isoformat(), # Store datetime as ISO string in payload
                        "message_text": msg['message_text'],
                        "attachment_filename": msg.get('attachment_filename'),
                        "attachment_url": msg.get('attachment_url')
                    }
                )
            )
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            logger.info(f"Indexed {len(points)} messages into Qdrant.")

    def search_messages(self, query_text: str, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        query_vector = self.embed_text(query_text)
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="chat_id",
                        match=models.MatchValue(value=chat_id) # Filter by exact chat_id
                    )
                ]
            ),
            limit=limit,
            with_payload=True # Ensure payload is returned
        )
        return [hit.payload for hit in search_result]

qdrant_service = QdrantService()