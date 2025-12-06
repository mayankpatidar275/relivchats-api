# src/database.py
import time
import os
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from .config import settings
from .logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# ============================================================================
# DETECT EXECUTION CONTEXT
# ============================================================================

# Determine if running in Celery worker context
IS_CELERY_WORKER = os.environ.get('CELERY_WORKER', 'false').lower() == 'true'

# ============================================================================
# SYNC ENGINE CONFIGURATION
# ============================================================================

if IS_CELERY_WORKER:
    # CELERY WORKERS: Use NullPool (no connection pooling)
    # Each task gets a fresh connection and closes it immediately
    # Prevents connection leaks and pool exhaustion
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,  # No pooling for Celery workers
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
    )
    logger.info(
        "Database engine configured for Celery worker",
        extra={"extra_data": {"pool_type": "NullPool", "pooling": False}}
    )
else:
    # API/WEB: Use QueuePool (connection pooling for FastAPI)
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=10,               # Increased from 2
        max_overflow=5,             # Allow overflow connections
        pool_timeout=10,            # Fail faster if no connections available
        pool_recycle=3600,          # Increased from 280 - recycle hourly
        echo=False,                # Set to True for SQL debugging
        echo_pool=True,          # Uncomment to debug pool behavior
    )
    logger.info(
        "Database engine configured for API",
        extra={"extra_data": {
            "pool_type": "QueuePool",
            "pool_size": 10,
            "max_overflow": 5,
            "total_max_connections": 15,
            "pool_recycle_seconds": 3600
        }}
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================================================
# CONNECTION POOL MONITORING (Optional - for debugging)
# ============================================================================

@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new database connection is opened"""
    logger.debug("Database connection opened")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    if not IS_CELERY_WORKER and settings.LOG_LEVEL == "DEBUG":
        pool = engine.pool
        logger.debug(
            "Connection checked out from pool",
            extra={"extra_data": {
                "checked_out": pool.checkedout(),
                "pool_size": pool.size(),
                "overflow": pool.overflow()
            }}
        )

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when a connection is returned to the pool"""
    if not IS_CELERY_WORKER and settings.LOG_LEVEL == "DEBUG":
        pool = engine.pool
        logger.debug(
            "Connection checked in to pool",
            extra={"extra_data": {
                "checked_out": pool.checkedout(),
                "pool_size": pool.size()
            }}
        )

@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log when a database connection is closed"""
    logger.debug("Database connection closed")

# ============================================================================
# ASYNC ENGINE CONFIGURATION
# ============================================================================

def _make_async_url(sync_url: str) -> str:
    """Convert sync PostgreSQL URL to async (asyncpg driver)"""
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql+asyncpg://") or sync_url.startswith("postgresql+psycopg://"):
        return sync_url
    return sync_url

ASYNC_DATABASE_URL = getattr(settings, "DATABASE_ASYNC_URL", None) or _make_async_url(settings.DATABASE_URL)

# ============================================================================
# ASYNC ENGINE CONFIGURATION (FastAPI ONLY)
# ============================================================================
# IMPORTANT: This engine is ONLY for FastAPI endpoints (async/await)
# Celery workers use the sync engine above with NullPool
# Keeping them separate prevents connection pool conflicts across
# different execution contexts (async event loop vs. worker processes)
#
# Migration Strategy:
# - FastAPI endpoints should use get_async_db() → async_engine
# - Celery workers use get_db() → engine (sync) with NullPool
# - CPU-intensive work in FastAPI uses ThreadPoolExecutor
#
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,               # Match sync engine pool_size for consistency
    max_overflow=5,             # Match sync engine max_overflow
    pool_timeout=10,            # Match sync engine pool_timeout
    pool_recycle=3600,          # Match sync engine pool_recycle
    echo=False,                 # Set to True for SQL debugging
    connect_args={
        "statement_cache_size": 20,      # Enable statement caching
        "prepared_statement_cache_size": 10,  # Enable prepared statements
        "command_timeout": 60,
        "server_settings": {
            "jit": "off",
            "default_transaction_isolation": "repeatable read"  # Prevent phantom reads
        }
    }
)

async_session = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

logger.info(
    "Async database engine configured (for FastAPI endpoints)",
    extra={"extra_data": {
        "pool_type": "AsyncQueuePool",
        "pool_size": 10,
        "max_overflow": 5,
        "pool_timeout": 10,
        "context": "FastAPI only - use get_async_db() dependency"
    }}
)

# ============================================================================
# BASE MODEL
# ============================================================================

Base = declarative_base()

# Import all models to ensure they're registered with Base
from .users import models as users_models  # noqa: E402,F401
from .chats import models as chats_models  # noqa: E402,F401
from .vector import models as vector_models  # noqa: E402,F401
from .credits import models as credit_models  # noqa: E402,F401

# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_db(max_retries: int = 3) -> Generator[Session, None, None]:
    """
    Sync DB session dependency for FastAPI endpoints.
    
    Automatically handles:
    - Connection retries on failure
    - Session cleanup (close)
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = None
    for attempt in range(1, max_retries + 1):
        try:
            db = SessionLocal()
            yield db
            break  # Success - exit retry loop
            
        except OperationalError as e:
            logger.error(
                f"Database connection error (attempt {attempt}/{max_retries})",
                extra={"extra_data": {
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "error": str(e)
                }},
                exc_info=True
            )
            
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.warning(
                        "Failed to close database session after error",
                        extra={"extra_data": {"error": str(close_error)}}
                    )
            
            if attempt == max_retries:
                raise  # Re-raise after max retries
            
            time.sleep(2)  # Backoff before retry
            
        except Exception as e:
            logger.error(
                "Unexpected error in database session",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            
            if db:
                try:
                    db.rollback()  # Rollback on unexpected errors
                except Exception as rollback_error:
                    logger.warning(
                        "Failed to rollback database session",
                        extra={"extra_data": {"error": str(rollback_error)}}
                    )
            raise
            
        finally:
            # Always close session (unless yielded successfully)
            if db and attempt < max_retries:
                try:
                    db.close()
                except Exception as e:
                    logger.warning(
                        "Failed to close database session cleanly",
                        extra={"extra_data": {"error": str(e)}}
                    )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async DB session dependency for async FastAPI endpoints.

    Automatically handles:
    - Transaction rollback on exceptions
    - Session cleanup

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(
                "Error in async database session",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_transaction():
    """
    Async context manager for explicit transaction control.

    Automatically commits on success, rolls back on exception.
    Use when you need explicit transaction boundaries.

    Usage:
        async with get_async_db_transaction() as db:
            # Perform database operations
            db.add(record)
            # Auto-commits on success
            # Auto-rolls back on exception

    Returns:
        AsyncSession: Database session with transaction management
    """
    async with async_session() as db:
        try:
            yield db
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(
                "Transaction rolled back due to exception",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            raise
        finally:
            await db.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pool_status() -> dict:
    """
    Get current connection pool status (for monitoring/debugging)
    
    Returns:
        dict: Pool statistics including size, checked out, overflow
    """
    if IS_CELERY_WORKER:
        return {
            "pool_type": "NullPool",
            "pooling_enabled": False,
            "message": "No pooling in Celery workers"
        }
    
    try:
        pool = engine.pool
        status = {
            "pool_type": "QueuePool",
            "pooling_enabled": True,
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "total_connections": pool.size() + pool.overflow(),
            "available": pool.size() - pool.checkedout(),
            "status": "healthy" if pool.checkedout() < pool.size() else "warning"
        }
        return status
    except Exception as e:
        logger.error(
            "Failed to get pool status",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        return {
            "error": "Failed to retrieve pool status",
            "message": str(e)
        }


def close_all_sessions():
    """
    Close all active database connections (for cleanup/shutdown)
    Use with caution - typically only needed during application shutdown
    """
    try:
        engine.dispose()
        logger.info("All database connections closed successfully")
    except Exception as e:
        logger.error(
            "Error closing database connections",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )


# Log initial configuration
logger.info(
    "Database module initialized",
    extra={"extra_data": {
        "context": "Celery Worker" if IS_CELERY_WORKER else "FastAPI API",
        "pool_type": "NullPool" if IS_CELERY_WORKER else "QueuePool",
        "environment": settings.ENVIRONMENT
    }}
)