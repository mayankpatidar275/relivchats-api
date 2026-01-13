# src/config.py 

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str
    CLERK_SECRET_KEY: str
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Redis & Celery - CHANGED: Use environment variable
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default_factory=lambda: settings.REDIS_URL if 'settings' in globals() else "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default_factory=lambda: settings.REDIS_URL if 'settings' in globals() else "redis://localhost:6379/0")

    # Generation settings
    MAX_CONCURRENT_INSIGHTS: int = 3  # Generate 3 insights in parallel
    # INSIGHT_GENERATION_TIMEOUT: int = 600  # 10 minutes per insight (hard timeout)
    # Increased from 120s to handle Gemini API slowness/unavailability
    # Soft timeout (task_soft_time_limit) will be TIMEOUT - 10 seconds
    # This gives tasks time to cleanup before hard kill
    INSIGHT_GENERATION_TIMEOUT: int = 600  # 10 minutes per insight
    RAG_CHUNK_CACHE_TTL: int = 3600  # Cache RAG chunks for 1 hour
    
    # Vector Database Settings
    # QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    # QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "chat_messages"
    # QDRANT_VECTOR_SIZE: int = 768  # Gemini embedding dimension
    QDRANT_VECTOR_SIZE: int = 3072  # Gemini embedding dimension

    # Qdrant settings
    QDRANT_TIMEOUT: int = 300  # 5 minutes
    QDRANT_BATCH_SIZE: int = 100
    QDRANT_MAX_RETRIESint: int = 3
    
    # Gemini API Settings
    GEMINI_API_KEY: str
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_BATCH_SIZE: int = 100  # Number of texts per embedding API call
    
    # Chunking Settings
    MAX_CHUNK_SIZE: int = 1000  # Maximum tokens per chunk
    MIN_CHUNK_SIZE: int = 800   # Minimum tokens per chunk
    CHUNK_OVERLAP: int = 50     # Token overlap between chunks
    TIME_WINDOW_MINUTES: int = 10  # Max time gap for conversation grouping

    # # Razorpay Configuration
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str
    
    # # Stripe Configuration
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # ========================================================================
    # LOGGING CONFIGURATION
    # ========================================================================
    
    # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = "INFO"
    
    # Log format: "json" for structured logging, "human" for readable console output
    LOG_FORMAT: str = "json"  # Use "human" for local development
    
    # Enable file logging (logs written to logs/ directory)
    ENABLE_FILE_LOGGING: bool = True
    
    # Environment: development, staging, production
    ENVIRONMENT: str = "development"
    
    # Sentry DSN for error tracking (optional)
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # Sample 10% of transactions

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",  # Local development
            "http://localhost:3001",  # Alternative local port
        ]
    )
    # In production .env, set: CORS_ORIGINS=["https://relivchats.com","https://www.relivchats.com","https://app.relivchats.com","https://relivchats.mkpatidar.in","https://www.relivchats.mkpatidar.in","https://app.relivchats.in"]

    # Performance monitoring thresholds
    SLOW_REQUEST_THRESHOLD_SECONDS: float = 2.0
    SLOW_DATABASE_QUERY_THRESHOLD_MS: int = 1000

    # ========================================================================
    # DATABASE PERFORMANCE SETTINGS
    # ========================================================================

    # Connection pooling - optimized for Neon serverless
    DB_POOL_SIZE: int = 15                  # Persistent connections in pool
    DB_MAX_OVERFLOW: int = 5                # Additional overflow connections
    DB_POOL_TIMEOUT: int = 10              # Timeout waiting for a connection
    DB_POOL_RECYCLE: int = 3600            # Recycle connections every hour

    # Query optimization
    DB_ECHO_ENABLED: bool = False          # Disable SQL logging in production
    DB_STATEMENT_CACHE_SIZE: int = 20      # Cache compiled statements
    DB_PREPARED_STMT_CACHE_SIZE: int = 10  # Cache prepared statements
    
    # ========================================================================
    # ERROR HANDLING
    # ========================================================================
    
    # Whether to expose detailed error messages (disable in production)
    EXPOSE_ERROR_DETAILS: bool = True
    
    # Support contact for error messages
    SUPPORT_EMAIL: str = "mayankpatidar275@gmail.com"
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="ignore"  # 👈 allows extra env vars without raising errors
)

# Create settings instance
settings = Settings()

# Fix CELERY URLs after settings is created
settings.CELERY_BROKER_URL = settings.REDIS_URL
settings.CELERY_RESULT_BACKEND = settings.REDIS_URL