# src/database.py
import logging
import time
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from .config import settings

# Configure logger
logger = logging.getLogger("db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------- Sync (existing) ----------
# Use the existing DATABASE_URL (postgresql://user:pass@host/db)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Detects stale connections
    pool_size=5,              # Adjust as per load
    max_overflow=10,          # Extra temporary connections
    pool_timeout=30,          # Wait before giving up on a connection
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------- Async (new) ----------
# If user doesn't have an async URL, derive one by swapping driver to asyncpg
def _make_async_url(sync_url: str) -> str:
    # common case: sync URL starts with "postgresql://"
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # if already async, return as-is
    if sync_url.startswith("postgresql+asyncpg://") or sync_url.startswith("postgresql+psycopg://"):
        return sync_url
    # otherwise, try to return original (may fail)
    return sync_url

ASYNC_DATABASE_URL = getattr(settings, "DATABASE_ASYNC_URL", None) or _make_async_url(settings.DATABASE_URL)

# create async engine - tune pools for your load
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    # async engine pool settings differ; default is usually fine, adjust as needed
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

async_session = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Base for declarative models (works for both sync & async)
Base = declarative_base()

# Import all models to ensure they're registered
# Import models to register with Base (keep existing imports)
# Keep these after Base is defined
from .users import models as users_models  # noqa: E402,F401
from .chats import models as chats_models  # noqa: E402,F401
from .vector import models as vector_models  # noqa: E402,F401
from .credits import models as credit_models  # noqa: E402,F401

# ---------- Dependencies ----------

def get_db(max_retries: int = 3) -> Generator:
    """
    Sync DB session dependency. Dependency to get a DB session with retry + safe close..
    Usage:
        def endpoint(db: Session = Depends(get_db))
    """
    for attempt in range(1, max_retries + 1):
        try:
            db = SessionLocal()
            yield db
            break
        except OperationalError as e:
            logger.error(f"Database connection error (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            time.sleep(2)  # short backoff before retry
        finally:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"Failed to close DB session cleanly: {e}")


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async DB session dependency for async endpoints.
    Usage:
        async def endpoint(db: AsyncSession = Depends(get_async_db))
    """
    # retry logic can be added if you need it
    async with async_session() as session:
        try:
            yield session
        finally:
            # async with takes care of cleanup, but explicit close if desired:
            await session.close()
