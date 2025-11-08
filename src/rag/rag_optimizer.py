# src/rag/rag_optimizer.py - NEW FILE

from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import json
import hashlib
from datetime import datetime, timedelta
from redis import Redis

from ..config import settings
from ..vector.service import vector_service
from .schemas import RAGChunk

class RAGContextCache:
    """
    Caches RAG chunks per chat to avoid redundant Qdrant queries
    Key: chat_id:category_id
    """
    
    def __init__(self):
        self.redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    
    def _generate_cache_key(self, chat_id: UUID, category_id: UUID) -> str:
        return f"rag_context:{chat_id}:{category_id}"
    
    def get_cached_context(
        self, 
        chat_id: UUID, 
        category_id: UUID
    ) -> Optional[Dict[str, List[RAGChunk]]]:
        """Retrieve cached RAG context"""
        cache_key = self._generate_cache_key(chat_id, category_id)
        cached = self.redis_client.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            # Convert back to RAGChunk objects
            return {
                keyword_group: [
                    RAGChunk(**chunk) for chunk in chunks
                ]
                for keyword_group, chunks in data.items()
            }
        return None
    
    def cache_context(
        self,
        chat_id: UUID,
        category_id: UUID,
        context: Dict[str, List[RAGChunk]],
        ttl: int = None
    ):
        """Cache RAG context"""
        cache_key = self._generate_cache_key(chat_id, category_id)
        ttl = ttl or settings.RAG_CHUNK_CACHE_TTL
        
        # Convert RAGChunk objects to dicts for JSON serialization
        serializable = {
            keyword_group: [
                chunk.dict() for chunk in chunks
            ]
            for keyword_group, chunks in context.items()
        }
        
        self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(serializable)
        )
    
    def invalidate(self, chat_id: UUID, category_id: UUID):
        """Invalidate cache for a chat"""
        cache_key = self._generate_cache_key(chat_id, category_id)
        self.redis_client.delete(cache_key)


class RAGContextExtractor:
    """
    Extracts and organizes RAG chunks for all insight types in a category
    Runs ONCE per chat unlock instead of per-insight
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = RAGContextCache()
    
    def extract_category_context(
        self,
        chat_id: UUID,
        category_id: UUID,
        insight_types: List[Dict]  # List of {id, rag_query_keywords}
    ) -> Dict[str, List[RAGChunk]]:
        """
        Extract all relevant chunks for a category's insight types
        
        Returns:
            {
                "conflict_keywords": [RAGChunk, ...],
                "affection_keywords": [RAGChunk, ...],
                ...
            }
        """
        
        # Check cache first
        cached = self.cache.get_cached_context(chat_id, category_id)
        if cached:
            return cached
        
        context = {}
        
        # Group insight types by similar keywords to reduce queries
        keyword_groups = self._group_by_keywords(insight_types)
        
        for group_key, keywords in keyword_groups.items():
            chunks = self._fetch_chunks(chat_id, keywords)
            context[group_key] = chunks
        
        # Cache for future use
        self.cache.cache_context(chat_id, category_id, context)
        
        return context
    
    def _group_by_keywords(
        self, 
        insight_types: List[Dict]
    ) -> Dict[str, str]:
        """
        Group insight types with similar keywords
        Example: conflict_analysis + red_flags → "conflict, argument, fight, red flag"
        """
        # For now, keep each insight type separate
        # TODO: Implement smart grouping based on keyword overlap
        return {
            f"insight_{it['id']}": it['rag_query_keywords']
            for it in insight_types
            if it.get('rag_query_keywords')
        }
    
    def _fetch_chunks(
        self,
        chat_id: UUID,
        keywords: str,
        max_chunks: int = 50
    ) -> List[RAGChunk]:
        """Fetch chunks from Qdrant"""
        from .service import fetch_rag_chunks  # Import here to avoid circular
        
        return fetch_rag_chunks(
            db=self.db,
            chat_id=chat_id,
            rag_query_keywords=keywords,
            max_chunks=max_chunks
        )


# Singleton instance
rag_cache = RAGContextCache()