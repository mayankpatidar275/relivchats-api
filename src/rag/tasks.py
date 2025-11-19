# src/rag/tasks.py
"""
Celery tasks for insight generation with proper connection management

Key improvements:
- Proper database session lifecycle management
- Redis connection pooling
- Structured logging with context
- Graceful error handling and retry logic
- No coin deduction before generation
- Charge coins only after ALL insights succeed
"""

from celery import group, chord
from sqlalchemy.orm import Session
from uuid import UUID
import time
from datetime import timezone
from typing import Dict, List, Optional
import json
import redis as redis_lib
from contextlib import contextmanager

from ..config import settings
from ..celery_app import celery_app
from ..database import SessionLocal
from .sync_generation_service import SyncInsightGenerationOrchestrator
from .service import generate_insight_with_context
from .models import Insight, InsightGenerationJob, InsightStatus
from ..logging_config import get_logger, log_business_event

logger = get_logger(__name__)

# ============================================================================
# REDIS CONNECTION POOL (Shared across workers)
# ============================================================================

REDIS_URL = settings.REDIS_URL

# Create connection pool for Redis (reused across tasks)
redis_pool = redis_lib.ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
    max_connections=10,
    socket_keepalive=True,
    socket_timeout=5,
    retry_on_timeout=True
)

logger.info(
    "Redis connection pool initialized",
    extra={"extra_data": {
        "max_connections": 10,
        "url": REDIS_URL.split('@')[-1] if '@' in REDIS_URL else "localhost"  # Hide credentials
    }}
)


@contextmanager
def get_redis_client():
    """
    Context manager for Redis client with automatic cleanup
    
    Usage:
        with get_redis_client() as redis_client:
            value = redis_client.get(key)
    """
    client = redis_lib.Redis(connection_pool=redis_pool)
    try:
        yield client
    except redis_lib.RedisError as e:
        logger.error(
            "Redis operation failed",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        raise
    finally:
        # Connection returns to pool automatically
        pass


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
            "Database session error",
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
# ORCHESTRATOR TASKS (Store context in Redis, pass context_key)
# ============================================================================

@celery_app.task(name="orchestrate_insight_generation", bind=True)
def orchestrate_insight_generation(self, job_id: str):
    """
    Main orchestrator - coordinates parallel insight generation
    
    Flow:
    1. Extract shared RAG context (runs once)
    2. Store context in Redis
    3. Launch parallel tasks for each insight
    4. Wait for all to complete (via chord callback)
    5. Charge coins if ALL succeeded, or release reservation if any failed
    """
    
    logger.info(
        "Starting insight generation orchestration",
        extra={"extra_data": {
            "job_id": job_id,
            "task_id": self.request.id
        }}
    )
    
    with get_db_session() as db:
        try:
            orchestrator = SyncInsightGenerationOrchestrator(db)
            
            # Mark job as started
            orchestrator.start_job(job_id)
            logger.info(
                "Job marked as started",
                extra={"extra_data": {"job_id": job_id}}
            )
            
            # Step 1: Extract shared context (expensive, do once)
            logger.info(
                "Extracting shared RAG context",
                extra={"extra_data": {"job_id": job_id}}
            )
            
            context_extraction_start = time.time()
            context = orchestrator.extract_shared_context(job_id)
            context_extraction_time = int((time.time() - context_extraction_start) * 1000)
            
            logger.info(
                "RAG context extracted",
                extra={"extra_data": {
                    "job_id": job_id,
                    "extraction_time_ms": context_extraction_time,
                    "keyword_groups": len(context) if isinstance(context, dict) else 0
                }}
            )
            
            # Serialize context for Redis storage
            serializable_context = _make_context_serializable(context)
            
            # Store in Redis with TTL (10 minutes)
            context_key = f"rag_context:{job_id}"
            
            try:
                with get_redis_client() as redis_client:
                    redis_client.set(
                        context_key,
                        json.dumps(serializable_context),
                        ex=600  # 10 minutes TTL
                    )
                    logger.debug(
                        "Context stored in Redis",
                        extra={"extra_data": {
                            "context_key": context_key,
                            "ttl_seconds": 600
                        }}
                    )
            except Exception as e:
                logger.error(
                    "Failed to store context in Redis",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "error": str(e)
                    }},
                    exc_info=True
                )
                # Fallback: proceed without Redis (each task will re-extract)
                context_key = None
            
            # Get job details and pending insights
            job = orchestrator._get_job(job_id)
            
            insights = db.query(Insight).filter(
                Insight.chat_id == job.chat_id,
                Insight.status == InsightStatus.PENDING
            ).all()
            
            if not insights:
                logger.warning(
                    "No pending insights found for job",
                    extra={"extra_data": {"job_id": job_id}}
                )
                
                job.status = "failed"
                job.error_message = "No pending insights to generate"
                db.commit()
                
                # Release reservation (no charge)
                _release_reservation_sync(db, job.chat_id, "No insights to generate")
                return
            
            logger.info(
                "Found insights to generate",
                extra={"extra_data": {
                    "job_id": job_id,
                    "insight_count": len(insights),
                    "chat_id": str(job.chat_id)
                }}
            )
            
            # Step 2: Create parallel tasks
            task_signatures = [
                generate_single_insight.s(
                    str(insight.id),
                    str(insight.chat_id),
                    str(insight.insight_type_id),
                    job_id,
                    context_key
                )
                for insight in insights
            ]
            
            # Execute in parallel with callback
            job_tasks = chord(task_signatures)(
                finalize_generation_job.s(job_id)
            )
            
            logger.info(
                "Parallel insight tasks launched",
                extra={"extra_data": {
                    "job_id": job_id,
                    "task_count": len(task_signatures)
                }}
            )
            
            log_business_event(
                "insight_generation_started",
                user_id=str(job.user_id),
                job_id=job_id,
                chat_id=str(job.chat_id),
                insight_count=len(insights)
            )
            
        except Exception as e:
            logger.error(
                "Orchestration failed",
                extra={"extra_data": {
                    "job_id": job_id,
                    "error": str(e)
                }},
                exc_info=True
            )
            
            # Mark job as failed
            try:
                job = db.query(InsightGenerationJob).filter_by(job_id=job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    db.commit()
                    
                    # Release reservation
                    _release_reservation_sync(db, job.chat_id, f"Orchestration failed: {str(e)}")
            except Exception as cleanup_error:
                logger.error(
                    "Failed to cleanup after orchestration error",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "error": str(cleanup_error)
                    }},
                    exc_info=True
                )
            
            raise


# ============================================================================
# SINGLE INSIGHT GENERATION
# ============================================================================

@celery_app.task(name="generate_single_insight", bind=True, max_retries=2)
def generate_single_insight(
    self,
    insight_id: str,
    chat_id: str,
    insight_type_id: str,
    job_id: str,
    shared_context_key: Optional[str]
):
    """
    Generate a single insight using pre-extracted context
    
    This task runs in parallel (3-4 at a time based on worker concurrency)
    """
    
    logger.info(
        "Starting single insight generation",
        extra={"extra_data": {
            "task_id": self.request.id,
            "insight_id": insight_id,
            "job_id": job_id,
            "chat_id": chat_id
        }}
    )
    
    start_time = time.time()
    
    with get_db_session() as db:
        try:
            # Fetch context from Redis
            shared_context = None
            if shared_context_key:
                try:
                    with get_redis_client() as redis_client:
                        raw = redis_client.get(shared_context_key)
                        if raw:
                            shared_context = json.loads(raw)
                            logger.debug(
                                "Context loaded from Redis",
                                extra={"extra_data": {
                                    "insight_id": insight_id,
                                    "context_key": shared_context_key
                                }}
                            )
                        else:
                            logger.warning(
                                "Context key not found in Redis",
                                extra={"extra_data": {
                                    "insight_id": insight_id,
                                    "context_key": shared_context_key
                                }}
                            )
                except Exception as e:
                    logger.error(
                        "Failed to fetch context from Redis",
                        extra={"extra_data": {
                            "insight_id": insight_id,
                            "error": str(e)
                        }},
                        exc_info=True
                    )
            
            # Call generation function with shared context
            generation_start = time.time()
            
            insight = generate_insight_with_context(
                db=db,
                chat_id=UUID(chat_id),
                insight_type_id=UUID(insight_type_id),
                shared_context=shared_context
            )
            
            generation_time_ms = int((time.time() - generation_start) * 1000)
            total_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Insight generated successfully",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "tokens_used": insight.tokens_used,
                    "generation_time_ms": generation_time_ms,
                    "total_time_ms": total_time_ms
                }}
            )
            
            # Update job progress
            orchestrator = SyncInsightGenerationOrchestrator(db) 
            orchestrator.update_job_progress(
                job_id=job_id,
                insight_id=UUID(insight_id),
                status="completed",
                tokens_used=insight.tokens_used,
                generation_time_ms=generation_time_ms
            )
            
            log_business_event(
                "insight_generated",
                insight_id=insight_id,
                job_id=job_id,
                tokens_used=insight.tokens_used,
                generation_time_ms=generation_time_ms
            )
            
            return {
                "insight_id": insight_id,
                "status": "completed",
                "tokens_used": insight.tokens_used,
                "generation_time_ms": generation_time_ms
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(
                "Insight generation failed",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "job_id": job_id,
                    "error": error_message,
                    "attempt": self.request.retries + 1
                }},
                exc_info=True
            )
            
            # Mark as failed and update job
            try:
                insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
                if insight:
                    insight.status = InsightStatus.FAILED
                    insight.error_message = error_message[:500]
                    db.commit()
                
                orchestrator = SyncInsightGenerationOrchestrator(db)
                orchestrator.update_job_progress(
                    job_id=job_id,
                    insight_id=UUID(insight_id),
                    status="failed",
                    error=error_message
                )
            except Exception as update_error:
                logger.error(
                    "Failed to update insight failure status",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "error": str(update_error)
                    }},
                    exc_info=True
                )
                db.rollback()
            
            # Retry logic (Celery will auto-retry based on task config)
            if self.request.retries < self.max_retries:
                countdown = 5 * (2 ** self.request.retries)
                logger.info(
                    "Retrying insight generation",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "attempt": self.request.retries + 1,
                        "max_retries": self.max_retries,
                        "countdown_seconds": countdown
                    }}
                )
                raise self.retry(exc=e, countdown=countdown)
            
            logger.error(
                "Insight generation failed after max retries",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "max_retries": self.max_retries
                }}
            )
            
            return {
                "insight_id": insight_id,
                "status": "failed",
                "error": error_message
            }


# ============================================================================
# FINALIZATION (CRITICAL: Charge coins here)
# ============================================================================

@celery_app.task(name="finalize_generation_job")
def finalize_generation_job(results: List[Dict], job_id: str):
    """
    Callback after all insights complete
    
    CRITICAL: This is where we charge coins (only if all succeeded)
    """
    
    logger.info(
        "Finalizing insight generation job",
        extra={"extra_data": {
            "job_id": job_id,
            "result_count": len(results)
        }}
    )
    
    with get_db_session() as db:
        try:
            orchestrator = SyncInsightGenerationOrchestrator(db)
            
            # Mark job as completed (this triggers coin charging logic)
            orchestrator.mark_job_completed(job_id)
            
            job_status = orchestrator.get_job_status(job_id)
            
            completed = job_status['completed_insights']
            failed = job_status['failed_insights']
            total = job_status['total_insights']
            
            logger.info(
                "Job finalized",
                extra={"extra_data": {
                    "job_id": job_id,
                    "completed_insights": completed,
                    "failed_insights": failed,
                    "total_insights": total,
                    "success_rate": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
                }}
            )
            
            log_business_event(
                "insight_generation_completed",
                job_id=job_id,
                completed_insights=completed,
                failed_insights=failed,
                total_insights=total
            )
            
        except Exception as e:
            logger.error(
                "Error finalizing job",
                extra={"extra_data": {
                    "job_id": job_id,
                    "error": str(e)
                }},
                exc_info=True
            )


# ============================================================================
# PAYMENT RETRY TASKS
# ============================================================================

@celery_app.task(name="retry_payment_deduction", bind=True, max_retries=288)  # 24 hours
def retry_payment_deduction(self, chat_id: str):
    """
    Retry charging coins if user's balance was insufficient
    
    Runs every 5 minutes for up to 24 hours (288 retries).
    After max retries, mark as permanently failed.
    """
    
    logger.info(
        "Retrying payment deduction",
        extra={"extra_data": {
            "chat_id": chat_id,
            "attempt": self.request.retries + 1,
            "max_retries": self.max_retries
        }}
    )
    
    import asyncio
    from ..database import async_session
    from ..credits.service import CreditService
    
    async def attempt_charge():
        async with async_session() as async_db:
            await CreditService.charge_reserved_coins(
                db=async_db,
                chat_id=UUID(chat_id)
            )
    
    try:
        asyncio.run(attempt_charge())
        
        logger.info(
            "Payment retry succeeded",
            extra={"extra_data": {"chat_id": chat_id}}
        )
        
        log_business_event(
            "payment_retry_succeeded",
            chat_id=chat_id,
            attempt=self.request.retries + 1
        )
        
    except Exception as e:
        from ..error_handlers import InsufficientCreditsException
        
        if isinstance(e, InsufficientCreditsException):
            # Still insufficient, retry later
            logger.warning(
                "Payment retry failed - insufficient balance",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "attempt": self.request.retries + 1
                }}
            )
            
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=300)  # 5 minutes
            else:
                # Max retries reached (24 hours)
                logger.critical(
                    "Payment permanently failed after 24 hours",
                    extra={"extra_data": {
                        "chat_id": chat_id,
                        "max_retries": self.max_retries
                    }}
                )
                
                log_business_event(
                    "payment_permanently_failed",
                    chat_id=chat_id,
                    reason="Insufficient balance after 24 hours"
                )
        else:
            logger.error(
                "Payment retry error",
                extra={"extra_data": {
                    "chat_id": chat_id,
                    "error": str(e)
                }},
                exc_info=True
            )
            raise self.retry(exc=e, countdown=300)


# ============================================================================
# CLEANUP TASKS
# ============================================================================

@celery_app.task(name="cleanup_expired_reservations")
def cleanup_expired_reservations():
    """
    Release reservations that expired (generation took >10 minutes)
    Run every 5 minutes via Celery Beat
    """
    from ..chats.models import Chat
    from datetime import datetime
    
    logger.info("Starting cleanup of expired reservations")
    
    with get_db_session() as db:
        try:
            expired_chats = db.query(Chat).filter(
                Chat.reserved_coins > 0,
                Chat.reservation_expires_at < datetime.now(timezone.utc)
            ).all()
            
            if not expired_chats:
                logger.debug("No expired reservations found")
                return
            
            for chat in expired_chats:
                logger.warning(
                    "Releasing expired reservation",
                    extra={"extra_data": {
                        "chat_id": str(chat.id),
                        "user_id": str(chat.user_id),
                        "reserved_coins": chat.reserved_coins,
                        "expired_at": chat.reservation_expires_at.isoformat()
                    }}
                )
                
                log_business_event(
                    "reservation_expired",
                    user_id=str(chat.user_id),
                    chat_id=str(chat.id),
                    reserved_coins=chat.reserved_coins
                )
                
                chat.reserved_coins = 0
                chat.reservation_expires_at = None
                chat.insights_generation_status = "timeout"
            
            db.commit()
            
            logger.info(
                "Expired reservations cleaned up",
                extra={"extra_data": {"count": len(expired_chats)}}
            )
        
        except Exception as e:
            logger.error(
                "Failed to cleanup expired reservations",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            db.rollback()


@celery_app.task(name="retry_failed_insight")
def retry_failed_insight(insight_id: str, job_id: str):
    """
    Retry a single failed insight (manual trigger)
    """
    
    logger.info(
        "Manually retrying failed insight",
        extra={"extra_data": {
            "insight_id": insight_id,
            "job_id": job_id
        }}
    )
    
    with get_db_session() as db:
        try:
            insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
            
            if not insight:
                logger.error(
                    "Insight not found for retry",
                    extra={"extra_data": {"insight_id": insight_id}}
                )
                return {"error": "Insight not found"}
            
            if insight.status != InsightStatus.FAILED:
                logger.warning(
                    "Insight is not in failed state",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "current_status": insight.status.value
                    }}
                )
                return {"error": f"Insight is not failed (current: {insight.status})"}
            
            # Reset status
            insight.status = InsightStatus.PENDING
            insight.error_message = None
            db.commit()
            
            # Re-extract context and generate
            orchestrator = SyncInsightGenerationOrchestrator(db)
            context = orchestrator.extract_shared_context(job_id)
            
            # Serialize and store context
            serializable_context = _make_context_serializable(context)
            context_key = f"rag_context:retry:{insight_id}"
            
            with get_redis_client() as redis_client:
                redis_client.set(context_key, json.dumps(serializable_context), ex=600)
            
            # Queue generation
            generate_single_insight.delay(
                insight_id=str(insight.id),
                chat_id=str(insight.chat_id),
                insight_type_id=str(insight.insight_type_id),
                job_id=job_id,
                shared_context_key=context_key
            )
            
            logger.info(
                "Insight retry queued",
                extra={"extra_data": {"insight_id": insight_id}}
            )
            
            log_business_event(
                "insight_retry_queued",
                insight_id=insight_id,
                job_id=job_id
            )
            
            return {"status": "retry_queued"}
            
        except Exception as e:
            logger.error(
                "Failed to retry insight",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "error": str(e)
                }},
                exc_info=True
            )
            return {"error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _make_context_serializable(context) -> dict:
    """
    Convert RAG context objects to JSON-serializable dictionaries
    
    Args:
        context: RAG context (dict of lists or single list)
    
    Returns:
        Serializable dictionary
    """
    
    def chunk_to_dict(chunk):
        """Normalize RAG chunk objects to dictionary format"""
        if isinstance(chunk, dict):
            # Already a dict - normalize keys
            return {
                "content": chunk.get("content") or chunk.get("text") or "",
                "speakers": chunk.get("speakers") or chunk.get("speaker_list") or [],
                "message_count": chunk.get("message_count") or chunk.get("count") or 0,
                "time_span": chunk.get("time_span") or chunk.get("span") or "",
                "similarity_score": chunk.get("similarity_score") or chunk.get("score") or 0.0,
                "metadata": chunk.get("metadata") or chunk.get("meta") or {},
            }
        
        # Object with attributes
        return {
            "content": getattr(chunk, "content", None) or getattr(chunk, "text", None) or "",
            "speakers": getattr(chunk, "speakers", None) or [],
            "message_count": getattr(chunk, "message_count", None) or 0,
            "time_span": getattr(chunk, "time_span", None) or "",
            "similarity_score": getattr(chunk, "similarity_score", None) or getattr(chunk, "score", None) or 0.0,
            "metadata": getattr(chunk, "metadata", None) or getattr(chunk, "meta", None) or {},
        }
    
    def make_serializable(obj):
        if isinstance(obj, dict):
            # Dict of lists - process each list
            return {
                k: [chunk_to_dict(c) for c in v] 
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            # Single list - process each item
            return [chunk_to_dict(c) for c in obj]
        else:
            # Single chunk
            return chunk_to_dict(obj)
    
    try:
        return make_serializable(context)
    except Exception as e:
        logger.error(
            "Failed to serialize context",
            extra={"extra_data": {"error": str(e)}},
            exc_info=True
        )
        return {}


def _release_reservation_sync(db: Session, chat_id: UUID, reason: str):
    """Synchronous helper to release coin reservation"""
    from ..chats.models import Chat
    
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat or chat.reserved_coins == 0:
            logger.debug(
                "No reservation to release",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
            return
        
        reserved_amount = chat.reserved_coins
        
        chat.reserved_coins = 0
        chat.reservation_expires_at = None
        chat.insights_generation_status = "failed"
        
        db.commit()
        
        log_business_event(
            "reservation_released",
            user_id=str(chat.user_id),
            chat_id=str(chat_id),
            amount=reserved_amount,
            reason=reason
        )
        
        logger.info(
            "Reservation released",
            extra={"extra_data": {
                "chat_id": str(chat_id),
                "user_id": str(chat.user_id),
                "amount": reserved_amount,
                "reason": reason
            }}
        )
    except Exception as e:
        logger.error(
            "Failed to release reservation",
            extra={"extra_data": {
                "chat_id": str(chat_id),
                "error": str(e)
            }},
            exc_info=True
        )
        db.rollback()


# ============================================================================
# CELERY BEAT SCHEDULE
# ============================================================================

celery_app.conf.beat_schedule = {
    'cleanup-expired-reservations': {
        'task': 'cleanup_expired_reservations',
        'schedule': 300.0,  # Every 5 minutes
    },
}

logger.info(
    "Celery tasks module initialized",
    extra={"extra_data": {
        "scheduled_tasks": list(celery_app.conf.beat_schedule.keys())
    }}
)