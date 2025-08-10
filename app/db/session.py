from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Use asyncpg for async PostgreSQL driver
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # To allow accessing attributes after commit
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session