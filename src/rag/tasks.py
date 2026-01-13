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

from celery import chord
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm import Session
from uuid import UUID
import time
from datetime import timezone, datetime
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
from src.chats.models import Chat
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

            # Step 0: Wait for vector indexing to complete (if needed)
            # This is the NEW step that handles background indexing
            job = orchestrator._get_job(job_id)
            chat = db.query(Chat).filter(Chat.id == job.chat_id).first()

            if chat.vector_status != "completed":
                logger.info(
                    "Waiting for chat vector indexing to complete",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "chat_id": str(chat.id),
                        "current_status": chat.vector_status
                    }}
                )

                # Poll chat.vector_status until completed (with timeout)
                indexing_wait_start = time.time()
                max_wait_seconds = 600  # 10 minutes timeout for indexing
                poll_interval_seconds = 10  # Check every 10 seconds

                while chat.vector_status != "completed":
                    # Check timeout
                    elapsed = time.time() - indexing_wait_start
                    if elapsed > max_wait_seconds:
                        logger.error(
                            "Indexing timeout exceeded",
                            extra={"extra_data": {
                                "job_id": job_id,
                                "chat_id": str(chat.id),
                                "elapsed_seconds": int(elapsed),
                                "timeout_seconds": max_wait_seconds,
                                "final_status": chat.vector_status
                            }}
                        )

                        job.status = "failed"
                        job.error_message = f"Chat indexing timeout after {int(elapsed)}s (status: {chat.vector_status})"
                        db.commit()

                        raise Exception(f"Chat indexing timeout after {int(elapsed)} seconds")

                    # Check if indexing failed
                    if chat.vector_status == "failed":
                        logger.error(
                            "Chat indexing failed",
                            extra={"extra_data": {
                                "job_id": job_id,
                                "chat_id": str(chat.id)
                            }}
                        )

                        job.status = "failed"
                        job.error_message = "Chat vector indexing failed"
                        db.commit()

                        raise Exception("Chat vector indexing failed")

                    # Still indexing - wait and poll again
                    logger.debug(
                        f"Chat still indexing, waiting {poll_interval_seconds}s...",
                        extra={"extra_data": {
                            "job_id": job_id,
                            "chat_id": str(chat.id),
                            "elapsed_seconds": int(elapsed),
                            "current_status": chat.vector_status
                        }}
                    )

                    time.sleep(poll_interval_seconds)

                    # Refresh chat status from database
                    db.refresh(chat)

                # Indexing completed!
                indexing_wait_duration = time.time() - indexing_wait_start
                logger.info(
                    "✓ Chat indexing completed, proceeding with insight generation",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "chat_id": str(chat.id),
                        "wait_duration_seconds": round(indexing_wait_duration, 2),
                        "chunk_count": chat.chunk_count
                    }}
                )

            else:
                # Already indexed
                logger.info(
                    "Chat already indexed, proceeding directly to insight generation",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "chat_id": str(chat.id),
                        "chunk_count": chat.chunk_count
                    }}
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
            
            # Store in Redis with TTL (20 minutes)
            context_key = f"rag_context:{job_id}"
            
            try:
                with get_redis_client() as redis_client:
                    redis_client.set(
                        context_key,
                        json.dumps(serializable_context),
                        ex=1200  # 20 minutes TTL
                    )
                    logger.debug(
                        "Context stored in Redis",
                        extra={"extra_data": {
                            "context_key": context_key,
                            "ttl_seconds": 1200
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

                # Update chat status
                chat = db.query(Chat).filter(Chat.id == job.chat_id).first()
                if chat:
                    chat.insights_generation_status = "failed"

                db.commit()

                # Note: Coins already deducted, will be auto-refunded via finalization
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

            # Mark job as failed and REFUND coins immediately
            try:
                job = db.query(InsightGenerationJob).filter_by(job_id=job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)[:500]
                    job.completed_at = datetime.now(timezone.utc)

                    # Update chat status
                    chat = db.query(Chat).filter(Chat.id == job.chat_id).first()
                    if chat:
                        chat.insights_generation_status = "failed"

                    db.commit()

                    # CRITICAL: Refund coins immediately (orchestration failed before generation)
                    logger.warning(
                        "Orchestration failed - refunding coins",
                        extra={"extra_data": {
                            "job_id": job_id,
                            "chat_id": str(job.chat_id)
                        }}
                    )

                    from ..credits.service import CreditService
                    credit_service = CreditService(db)
                    try:
                        credit_service.refund_transaction(
                            chat_id=job.chat_id,
                            reason=f"Insight generation orchestration failed: {str(e)[:100]}"
                        )
                        logger.info("✓ Coins refunded after orchestration failure")
                    except Exception as refund_error:
                        logger.critical(
                            "CRITICAL: Failed to refund coins after orchestration failure",
                            extra={"extra_data": {
                                "job_id": job_id,
                                "chat_id": str(job.chat_id),
                                "error": str(refund_error)
                            }},
                            exc_info=True
                        )
                        # Don't raise - log for manual intervention

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
            "chat_id": chat_id,
            "retry_attempt": self.request.retries
        }}
    )

    start_time = time.time()

    with get_db_session() as db:
        try:
            # CRITICAL: Mark insight as GENERATING when task starts
            # This ensures frontend shows correct status during generation
            insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
            if insight and insight.status in [InsightStatus.PENDING, InsightStatus.FAILED]:
                insight.status = InsightStatus.GENERATING
                insight.error_message = None  # Clear previous errors on retry
                db.commit()
                logger.info(
                    "Insight status updated to GENERATING",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "previous_status": "pending" if self.request.retries == 0 else "failed (retry)"
                    }}
                )

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

        except SoftTimeLimitExceeded:
            # Handle soft timeout gracefully - mark as failed without retry
            # Timeout usually indicates Gemini API is down/slow - retries won't help
            error_message = f"Task exceeded soft time limit ({settings.INSIGHT_GENERATION_TIMEOUT - 10}s) - Gemini API may be unavailable"
            logger.error(
                "Insight generation hit soft timeout",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "job_id": job_id,
                    "timeout_seconds": settings.INSIGHT_GENERATION_TIMEOUT - 10
                }}
            )

            # Mark as failed without retry (timeout indicates systemic issue)
            try:
                insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
                if insight:
                    insight.status = InsightStatus.FAILED
                    insight.error_message = error_message
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
                    "Failed to update insight timeout status",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "error": str(update_error)
                    }},
                    exc_info=True
                )
                db.rollback()

            # Return failure without retry
            return {
                "insight_id": insight_id,
                "status": "failed",
                "error": error_message
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

            # Check if we should retry
            will_retry = self.request.retries < self.max_retries

            # Update insight status
            try:
                insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
                if insight:
                    if will_retry:
                        # Keep as GENERATING during retry (user sees "in progress")
                        insight.status = InsightStatus.GENERATING
                        insight.error_message = f"Retrying... (attempt {self.request.retries + 1}/{self.max_retries}): {error_message[:200]}"
                    else:
                        # Final failure - mark as FAILED
                        insight.status = InsightStatus.FAILED
                        insight.error_message = error_message[:500]
                    db.commit()
            except Exception as update_error:
                logger.error(
                    "Failed to update insight status",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "error": str(update_error)
                    }},
                    exc_info=True
                )
                db.rollback()

            # Retry logic with adaptive backoff
            if will_retry:
                # Check if error is 503 (Service Unavailable) - needs longer backoff
                is_503_error = "503" in error_message or "UNAVAILABLE" in error_message or "overloaded" in error_message.lower()

                if is_503_error:
                    # Longer backoff for 503: 15s, 45s, 135s
                    countdown = 15 * (3 ** self.request.retries)
                    logger.info(
                        "Gemini API overloaded (503), using extended backoff",
                        extra={"extra_data": {
                            "insight_id": insight_id,
                            "attempt": self.request.retries + 1,
                            "countdown_seconds": countdown
                        }}
                    )
                else:
                    # Standard exponential backoff: 5s, 10s, 20s
                    countdown = 5 * (2 ** self.request.retries)

                logger.info(
                    "Retrying insight generation",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "attempt": self.request.retries + 1,
                        "max_retries": self.max_retries,
                        "countdown_seconds": countdown,
                        "is_503_error": is_503_error
                    }}
                )
                # Don't update job progress yet - wait for retry result
                raise self.retry(exc=e, countdown=countdown)

            # Final failure - update job progress
            logger.error(
                "Insight generation failed after max retries",
                extra={"extra_data": {
                    "insight_id": insight_id,
                    "max_retries": self.max_retries
                }}
            )

            try:
                orchestrator = SyncInsightGenerationOrchestrator(db)
                orchestrator.update_job_progress(
                    job_id=job_id,
                    insight_id=UUID(insight_id),
                    status="failed",
                    error=error_message
                )
            except Exception as job_update_error:
                logger.error(
                    "Failed to update job progress after final failure",
                    extra={"extra_data": {
                        "insight_id": insight_id,
                        "error": str(job_update_error)
                    }},
                    exc_info=True
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

    CRITICAL: This is where coin charging/refunding happens
    Safety net: If finalization fails, we MUST ensure refund happens
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

            # Mark job as completed (this triggers coin charging/refund logic)
            orchestrator.mark_job_completed(job_id)

            job_status = orchestrator.get_job_status(job_id)

            completed = job_status['completed_insights']
            failed = job_status['failed_insights']
            total = job_status['total_insights']

            logger.info(
                "Job finalized successfully",
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

            # CRITICAL SAFETY NET: If finalization fails, ensure refund happens
            # This prevents money being charged when insights aren't delivered
            try:
                job = db.query(InsightGenerationJob).filter_by(job_id=job_id).first()
                if job:
                    # Mark as failed
                    job.status = "failed"
                    job.error_message = f"Finalization failed: {str(e)[:200]}"
                    job.completed_at = datetime.now(timezone.utc)

                    # Update chat
                    chat = db.query(Chat).filter(Chat.id == job.chat_id).first()
                    if chat:
                        chat.insights_generation_status = "failed"

                    db.commit()

                    # REFUND coins as safety measure
                    logger.warning(
                        "Finalization failed - refunding coins as safety measure",
                        extra={"extra_data": {
                            "job_id": job_id,
                            "chat_id": str(job.chat_id)
                        }}
                    )

                    from ..credits.service import CreditService
                    credit_service = CreditService(db)
                    try:
                        credit_service.refund_transaction(
                            chat_id=job.chat_id,
                            reason=f"Finalization failed - safety refund: {str(e)[:100]}"
                        )
                        logger.info("✓ Safety refund completed after finalization failure")
                    except Exception as refund_error:
                        logger.critical(
                            "CRITICAL: Failed to refund after finalization failure - MANUAL INTERVENTION REQUIRED",
                            extra={"extra_data": {
                                "job_id": job_id,
                                "chat_id": str(job.chat_id),
                                "original_error": str(e),
                                "refund_error": str(refund_error)
                            }},
                            exc_info=True
                        )

            except Exception as safety_error:
                logger.critical(
                    "CRITICAL: Safety net also failed - MANUAL INTERVENTION REQUIRED",
                    extra={"extra_data": {
                        "job_id": job_id,
                        "original_error": str(e),
                        "safety_error": str(safety_error)
                    }},
                    exc_info=True
                )



# ============================================================================
# CLEANUP TASKS
# ============================================================================

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


# ============================================================================
# CELERY BEAT SCHEDULE (Empty - no periodic tasks needed)
# ============================================================================

celery_app.conf.beat_schedule = {}

logger.info(
    "Celery tasks module initialized",
    extra={"extra_data": {
        "scheduled_tasks": list(celery_app.conf.beat_schedule.keys())
    }}
)