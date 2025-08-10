import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    QDRANT_URL: str
    QDRANT_API_KEY: str

    # S3 Configuration (placeholders - replace with your actual values in .env)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "your_aws_access_key_id")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "your_aws_secret_access_key")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "relivchats-media")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

    # Embedding model configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2" # A good balance of size and performance

    # Chat limits
    MAX_UPLOAD_FILE_SIZE_MB: int = 5
    MAX_CHATS_PER_USER: int = 3


settings = Settings()