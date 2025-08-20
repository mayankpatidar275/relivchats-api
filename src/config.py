from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    CLERK_SECRET_KEY: str
    MAX_UPLOAD_SIZE_MB: int = 25 # Maximum file size in MB
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()