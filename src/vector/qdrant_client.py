import uuid
from uuid import UUID
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from ..config import settings

class QdrantVectorStore:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            # port=6333,
            # host=settings.QDRANT_HOST,
            # port=settings.QDRANT_PORT,
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                # 🔑 add index for chat_id
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="chat_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                print(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            print(f"Error ensuring collection exists: {e}")
            raise

    def add_vectors(self, vectors: List[List[float]], metadatas: List[Dict[str, Any]]) -> List[str]:
        """Add vectors with metadata to Qdrant"""
        if len(vectors) != len(metadatas):
            raise ValueError("Vectors and metadatas must have the same length")
        
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
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return vector_ids

    def search_similar(
        self, 
        query_vector: List[float], 
        limit: int = 5,
        chat_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
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
        
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit,
        )
        
        results = []
        for result in search_results:
            results.append({
                "id": result.id,
                "score": result.score,
                "metadata": result.payload,
            })
        
        return results

    def delete_vectors_by_chat_id(self, chat_id: UUID):
        """Delete all vectors for a specific chat"""
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

# Global instance
qdrant_store = QdrantVectorStore()