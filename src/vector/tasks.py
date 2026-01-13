# src/vector/tasks.py
"""
Celery tasks for vector indexing with proper connection management

Key features:
- Background vector indexing (non-blocking)
- Proper database session lifecycle
- Structured logging with context
- Graceful error handling and retry logic
- Updates chat.vector_status atomically
"""

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session
from uuid import UUID
import time
from datetime import timezone, datetime
from contextlib import contextmanager

from ..config import settings
from ..celery_app import celery_app
from ..database import SessionLocal
from ..chats.models import Chat
from ..logging_config import get_logger, log_business_event
from ..error_handlers import ExternalServiceException, ErrorCode

logger = get_logger(__name__)


# ============================================================================
# DATABASE SESSION CONTEXT MANAGER (Reused from rag/tasks.py pattern)
# ============================================================================

@contextmanager
def get_db_session():
    """
    Context manager for database session with automatic cleanup

    Usage:
        with get_db_session() as db:
            result = db.query(Model).first()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(
            "Database session error in vector task",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        db.rollback()
        raise
    finally:
        try:
            db.close()
            logger.debug("Database session closed successfully")
        except Exception as e:
            logger.warning(
                "Failed to close database session",
                extra={"extra_data": {"error": str(e)}}
            )


# ============================================================================
# VECTOR INDEXING TASK
# ============================================================================

@celery_app.task(name="index_chat_vectors", bind=True, max_retries=2, time_limit=600)
def index_chat_vectors(self, chat_id: str, user_id: str):
    """
    Background task to index chat vectors (embeddings + Qdrant upload)

    This task:
    1. Updates chat.vector_status = "indexing"
    2. Calls vector_service.create_chat_chunks() (5-7 minutes)
    3. Updates chat.vector_status = "completed" or "failed"
    4. Allows frontend to poll Chat model for progress

    Args:
        chat_id: UUID of chat to index
        user_id: User who triggered indexing (for logging)

    Raises:
        ExternalServiceException: If indexing fails after retries

    Time Limit: 600 seconds (10 minutes) - kills task if exceeded
    Retries: 2 attempts with exponential backoff
    """

    logger.info(
        "Starting vector indexing task",
        extra={"extra_data": {
            "task_id": self.request.id,
            "chat_id": chat_id,
            "user_id": user_id,
            "retry_attempt": self.request.retries
        }}
    )

    start_time = time.time()

    with get_db_session() as db:
        try:
            # 1. Get chat and validate
            chat = db.query(Chat).filter(Chat.id == UUID(chat_id)).first()

            if not chat:
                logger.error(
                    "Chat not found for vector indexing",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "user_id": user_id
                    }}
                )
                raise ValueError(f"Chat {chat_id} not found")

            # Verify ownership
            if chat.user_id != user_id:
                logger.error(
                    "User does not own chat for indexing",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "actual_owner": chat.user_id
                    }}
                )
                raise ValueError(f"User {user_id} does not own chat {chat_id}")

            # 2. Update status to "indexing" (idempotency check)
            if chat.vector_status == "completed":
                logger.info(
                    "Chat already indexed, skipping",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "indexed_at": str(chat.indexed_at)
                    }}
                )
                return {
                    "success": True,
                    "chat_id": chat_id,
                    "already_indexed": True,
                    "indexed_at": str(chat.indexed_at)
                }

            # Mark as indexing (prevents duplicate indexing jobs)
            previous_status = chat.vector_status
            chat.vector_status = "indexing"
            db.commit()

            logger.info(
                "Chat status updated to 'indexing'",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "previous_status": previous_status,
                    "user_id": user_id
                }}
            )

            # Log business event (for analytics)
            log_business_event(
                "vector_indexing_started",
                user_id=user_id,
                extra_data={
                    "chat_id": chat_id,
                    "platform": chat.platform,
                    "retry_attempt": self.request.retries
                }
            )

            # 3. Import vector service and perform indexing
            # Import here to avoid circular dependencies
            from .service import vector_service

            indexing_start = time.time()

            logger.info(
                "Starting vector service indexing",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "user_id": user_id
                }}
            )

            # CRITICAL: This is the long-running operation (5-7 minutes)
            # - Fetches messages from DB (6 seconds with cursor pagination)
            # - Chunks messages (10 seconds)
            # - Generates embeddings via Gemini (3-4 minutes with quota retries)
            # - Uploads to Qdrant (11 seconds)
            success = vector_service.create_chat_chunks(db, UUID(chat_id))

            indexing_duration = time.time() - indexing_start

            # 4. Update chat based on result
            if success:
                chat.vector_status = "completed"
                chat.indexed_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(
                    "✓ Vector indexing completed successfully",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "chunk_count": chat.chunk_count,
                        "indexing_duration_seconds": round(indexing_duration, 2),
                        "total_task_duration_seconds": round(time.time() - start_time, 2)
                    }}
                )

                # Log business event (for analytics)
                log_business_event(
                    "vector_indexing_completed",
                    user_id=user_id,
                    extra_data={
                        "chat_id": chat_id,
                        "chunk_count": chat.chunk_count,
                        "duration_seconds": round(indexing_duration, 2),
                        "success": True
                    }
                )

                return {
                    "success": True,
                    "chat_id": chat_id,
                    "chunk_count": chat.chunk_count,
                    "indexed_at": str(chat.indexed_at),
                    "duration_seconds": round(indexing_duration, 2)
                }

            else:
                # Indexing failed (returned False)
                chat.vector_status = "failed"
                db.commit()

                logger.error(
                    "Vector indexing failed (returned False)",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "indexing_duration_seconds": round(indexing_duration, 2)
                    }}
                )

                raise ExternalServiceException(
                    service_name="Vector Indexing",
                    message="Failed to create chat chunks",
                    error_code=ErrorCode.VECTOR_INDEXING_FAILED
                )

        except SoftTimeLimitExceeded:
            # Task exceeded time limit (600 seconds / 10 minutes)
            logger.error(
                "Vector indexing task exceeded time limit",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "time_limit_seconds": 600,
                    "elapsed_seconds": round(time.time() - start_time, 2)
                }}
            )

            # Mark as failed
            chat = db.query(Chat).filter(Chat.id == UUID(chat_id)).first()
            if chat:
                chat.vector_status = "failed"
                db.commit()

            raise ExternalServiceException(
                service_name="Vector Indexing",
                message="Indexing task exceeded 10 minute time limit",
                error_code=ErrorCode.VECTOR_INDEXING_FAILED
            )

        except Exception as e:
            # Any other exception (network errors, Gemini quota, Qdrant errors, etc.)
            logger.error(
                "Vector indexing task failed with exception",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retry_attempt": self.request.retries,
                    "will_retry": self.request.retries < self.max_retries
                }},
                exc_info=True
            )

            # Mark as failed
            chat = db.query(Chat).filter(Chat.id == UUID(chat_id)).first()
            if chat:
                chat.vector_status = "failed"
                db.commit()

            # Retry with exponential backoff if not max retries
            if self.request.retries < self.max_retries:
                # Exponential backoff: 30s, 90s
                retry_delay = 30 * (3 ** self.request.retries)

                logger.info(
                    f"Retrying vector indexing in {retry_delay}s",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "retry_attempt": self.request.retries + 1,
                        "max_retries": self.max_retries,
                        "retry_delay_seconds": retry_delay
                    }}
                )

                raise self.retry(exc=e, countdown=retry_delay)

            # Max retries exhausted
            logger.error(
                "Vector indexing failed after max retries",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "max_retries": self.max_retries,
                    "final_error": str(e)
                }}
            )

            # Log business event (for monitoring)
            log_business_event(
                "vector_indexing_failed",
                user_id=user_id,
                extra_data={
                    "chat_id": chat_id,
                    "error": str(e),
                    "retries_exhausted": True
                }
            )

            raise


# ============================================================================
# TASK REGISTRATION
# ============================================================================

# Task is automatically registered by @celery_app.task decorator
# Can be invoked via:
#   from src.vector.tasks import index_chat_vectors
#   index_chat_vectors.delay(chat_id, user_id)

logger.info("Vector indexing Celery tasks module initialized")
