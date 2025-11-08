import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY")
    MAX_UPLOAD_SIZE_MB: int = 25 # Maximum file size in MB
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Generation settings
    MAX_CONCURRENT_INSIGHTS: int = 3  # Generate 3 insights in parallel
    INSIGHT_GENERATION_TIMEOUT: int = 120  # 2 minutes per insight
    RAG_CHUNK_CACHE_TTL: int = 3600  # Cache RAG chunks for 1 hour
    
    # Vector Database Settings
    # QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    # QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "chat_messages"
    # QDRANT_VECTOR_SIZE: int = 768  # Gemini embedding dimension
    QDRANT_VECTOR_SIZE: int = 3072  # Gemini embedding dimension
    
    # Gemini API Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_LLM_MODEL: str = "gemini-2.5-flash"
    
    # Chunking Settings
    MAX_CHUNK_SIZE: int = 1000  # Maximum tokens per chunk
    MIN_CHUNK_SIZE: int = 800   # Minimum tokens per chunk
    CHUNK_OVERLAP: int = 50     # Token overlap between chunks
    TIME_WINDOW_MINUTES: int = 10  # Max time gap for conversation grouping

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()