# src/rag/tasks.py - NEW FILE

from celery import group, chord
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import time
from typing import Dict, List
import json
import redis as redis_lib

from ..config import settings
from ..celery_app import celery_app
from ..database import SessionLocal
from .generation_service import InsightGenerationOrchestrator
from .service import generate_insight_with_context
from .models import Insight, InsightGenerationJob, InsightStatus

logger = logging.getLogger(__name__)

REDIS_URL = settings.REDIS_URL
# decode_responses=True so we get Python str from redis_client.get
_redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)

# ============================================================================
# ORCHESTRATOR TASKS (store context in Redis, pass context_key)
# ============================================================================

@celery_app.task(name="orchestrate_insight_generation", bind=True)
def orchestrate_insight_generation(self, job_id: str):
    """
    Main orchestrator task - coordinates parallel insight generation
    
    Flow:
    1. Extract shared RAG context (runs once)
    2. Launch parallel tasks for each insight
    3. Wait for all to complete
    4. Finalize job
    """
    db = SessionLocal()
    
    try:
        orchestrator = InsightGenerationOrchestrator(db)
        
        # Mark job as started
        orchestrator.start_job(job_id)
        logger.info(f"Starting insight generation job: {job_id}")
        
        # Step 1: Extract shared context (expensive operation, do once)
        logger.info(f"Extracting shared RAG context for job {job_id}")
        context = orchestrator.extract_shared_context(job_id)
        
        # Make context JSON-serializable (convert objects -> primitives).
        # Implement a small serializer for RAGChunk-like objects.
        def chunk_to_dict(chunk):
            """
            Normalize RAG chunk objects to the same shape RAGChunk expects.
            Adapt field extraction to the actual chunk object you have.
            """
            # if chunk is already a dict in expected shape, return as-is
            if isinstance(chunk, dict):
                # optional: try to normalize older key names to canonical ones
                mapping = {
                    "text": "content",
                    "id": None,  # keep id if you want but RAGChunk doesn't require it
                    "score": "similarity_score",
                    "meta": "metadata",
                }
                normalized = {}
                # copy only keys relevant to RAGChunk
                normalized["content"] = chunk.get("content") or chunk.get("text") or ""
                normalized["speakers"] = chunk.get("speakers") or chunk.get("speaker_list") or []
                normalized["message_count"] = chunk.get("message_count") or chunk.get("count") or 0
                normalized["time_span"] = chunk.get("time_span") or chunk.get("span") or ""
                normalized["similarity_score"] = chunk.get("similarity_score") or chunk.get("score") or 0.0
                normalized["metadata"] = chunk.get("metadata") or chunk.get("meta") or {}
                return normalized

            # otherwise assume it's an object with attributes
            return {
                "content": getattr(chunk, "text", None) or getattr(chunk, "content", None),
                "speakers": getattr(chunk, "speakers", None) or [],
                "message_count": getattr(chunk, "message_count", None) or 0,
                "time_span": getattr(chunk, "time_span", None) or "",
                "similarity_score": getattr(chunk, "score", None) or getattr(chunk, "similarity_score", None) or 0.0,
                "metadata": getattr(chunk, "meta", None) or getattr(chunk, "metadata", None) or {},
            }

        
        def make_serializable(obj):
            # handle common shapes: dict[str, list], list, single chunk
            if isinstance(obj, dict):
                return {k: [chunk_to_dict(c) if not isinstance(c, (dict, list, str, int, float, bool, type(None))) else c for c in v] for k, v in obj.items()}
            if isinstance(obj, list):
                return [chunk_to_dict(c) if not isinstance(c, (dict, list, str, int, float, bool, type(None))) else c for c in obj]
            # fallback: single chunk -> dict
            if not isinstance(obj, (dict, list, str, int, float, bool, type(None))):
                return chunk_to_dict(obj)
            return obj
        
        serializable_context = make_serializable(context)
        
        # store in redis with TTL (10 minutes)
        context_key = f"rag_context:{job_id}"
        try:
            _redis_client.set(context_key, json.dumps(serializable_context), ex=600)
        except Exception as e:
            logger.warning(f"Failed to write shared context to Redis (continuing): {e}")
            # fallback: keep context in-memory but we won't pass the object to Celery tasks
            context_key = None
        
        # Get job details and pending insights
        job = orchestrator._get_job(job_id)
        
        # Get all pending insights for this job
        insights = db.query(Insight).filter(
            Insight.chat_id == job.chat_id,
            Insight.status == InsightStatus.PENDING
        ).all()
        
        if not insights:
            logger.warning(f"No pending insights found for job {job_id}")
            job.status = "failed"
            job.error_message = "No pending insights to generate"
            db.commit()
            return
        
        logger.info(f"Found {len(insights)} insights to generate for job {job_id}")
        
        # Step 2: Create parallel tasks (grouped by MAX_CONCURRENT_INSIGHTS)
        # Using chord: run tasks in parallel, then call callback when all done
        # Build task signatures: pass only the context_key (or None)
        task_signatures = [
            generate_single_insight.s(
                str(insight.id),
                str(insight.chat_id),
                str(insight.insight_type_id),
                job_id,
                context_key  # PASS KEY, NOT OBJECT
            )
            for insight in insights
        ]
        
        # Execute tasks in parallel with callback
        job_tasks = chord(task_signatures)(
            finalize_generation_job.s(job_id)
        )
        
        logger.info(f"Launched {len(task_signatures)} parallel insight generation tasks")
        
    except Exception as e:
        logger.error(f"Orchestration failed for job {job_id}: {e}", exc_info=True)
        
        # Mark job as failed
        try:
            job = db.query(InsightGenerationJob).filter_by(job_id=job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)[:500]
                db.commit()
        except:
            pass
        
        raise
    
    finally:
        db.close()


@celery_app.task(name="generate_single_insight", bind=True, max_retries=2)
def generate_single_insight(
    self,
    insight_id: str,
    chat_id: str,
    insight_type_id: str,
    job_id: str,
    shared_context_key: str | None
):
    """
    Generate a single insight using pre-extracted context
    
    This task runs in parallel (3-4 at a time based on worker concurrency)
    """
    db = SessionLocal()
    start_time = time.time()
    
    # local redis client (safe to construct per-worker)
    redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    
    try:
        logger.info(f"Generating insight {insight_id} for job {job_id}")
        
        # fetch context from redis if key provided
        shared_context = None
        if shared_context_key:
            try:
                raw = redis_client.get(shared_context_key)
                if raw:
                    shared_context = json.loads(raw)
                else:
                    logger.warning(f"Context key {shared_context_key} not found in Redis; continuing with None")
            except Exception as e:
                logger.warning(f"Failed to fetch context from Redis ({e}); continuing with None")
        
        # Call generation function with shared context
        # If shared_context is None, your generator can re-extract or handle fallback.
        insight = generate_insight_with_context(
            db=db,
            chat_id=UUID(chat_id),
            insight_type_id=UUID(insight_type_id),
            shared_context=shared_context
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        # Update job progress
        orchestrator = InsightGenerationOrchestrator(db)
        orchestrator.update_job_progress(
            job_id=job_id,
            insight_id=UUID(insight_id),
            status="completed",
            tokens_used=insight.tokens_used,
            generation_time_ms=generation_time_ms
        )
        
        logger.info(
            f"✓ Insight {insight_id} completed in {generation_time_ms}ms "
            f"({insight.tokens_used} tokens)"
        )
        
        return {
            "insight_id": insight_id,
            "status": "completed",
            "tokens_used": insight.tokens_used,
            "generation_time_ms": generation_time_ms
        }
        
    except Exception as e:
        logger.error(f"✗ Insight {insight_id} failed: {e}", exc_info=True)
        
        # Mark insight as failed
        try:
            insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
            if insight:
                insight.status = InsightStatus.FAILED
                insight.error_message = str(e)[:500]
                db.commit()
            
            # Update job progress
            orchestrator = InsightGenerationOrchestrator(db)
            orchestrator.update_job_progress(
                job_id=job_id,
                insight_id=UUID(insight_id),
                status="failed",
                error=str(e)
            )
        except Exception as update_error:
            logger.error(f"Failed to update failure status: {update_error}")
        
        # Retry logic (Celery will auto-retry based on task config)
        if self.request.retries < self.max_retries:
            # Exponential backoff: 5s, 10s
            countdown = 5 * (2 ** self.request.retries)
            logger.info(f"Retrying insight {insight_id} in {countdown}s (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=countdown)
        
        return {
            "insight_id": insight_id,
            "status": "failed",
            "error": str(e)
        }
    
    finally:
        db.close()


@celery_app.task(name="finalize_generation_job")
def finalize_generation_job(results: List[Dict], job_id: str):
    """
    Callback task that runs after all parallel insights complete
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Finalizing job {job_id}. Results: {len(results)} tasks completed")
        
        # Job finalization is already handled in update_job_progress
        # This is just for final logging and cleanup
        
        orchestrator = InsightGenerationOrchestrator(db)
        job_status = orchestrator.get_job_status(job_id)
        
        logger.info(
            f"Job {job_id} finalized: {job_status['completed_insights']}/{job_status['total_insights']} "
            f"completed, {job_status['failed_insights']} failed"
        )
        
        # Optional: Send webhook/notification to user
        # send_completion_notification(job_id, job_status)
        
    except Exception as e:
        logger.error(f"Error finalizing job {job_id}: {e}", exc_info=True)
    
    finally:
        db.close()


# ============================================================================
# UTILITY TASKS
# ============================================================================

@celery_app.task(name="retry_failed_insight")
def retry_failed_insight(insight_id: str, job_id: str):
    """
    Retry a single failed insight (can be triggered manually)
    """
    db = SessionLocal()
    
    try:
        insight = db.query(Insight).filter(Insight.id == UUID(insight_id)).first()
        
        if not insight:
            logger.error(f"Insight {insight_id} not found")
            return {"error": "Insight not found"}
        
        if insight.status != InsightStatus.FAILED:
            logger.warning(f"Insight {insight_id} is not in FAILED state (current: {insight.status})")
            return {"error": "Insight is not failed"}
        
        # Reset status
        insight.status = InsightStatus.PENDING
        insight.error_message = None
        db.commit()
        
        # Re-extract context and generate
        orchestrator = InsightGenerationOrchestrator(db)
        job = orchestrator._get_job(job_id)
        context = orchestrator.extract_shared_context(job_id)
        
        # Call generation
        generate_single_insight.delay(
            insight_id=str(insight.id),
            chat_id=str(insight.chat_id),
            insight_type_id=str(insight.insight_type_id),
            job_id=job_id,
            shared_context=context
        )
        
        logger.info(f"Retrying insight {insight_id}")
        return {"status": "retry_queued"}
        
    except Exception as e:
        logger.error(f"Failed to retry insight {insight_id}: {e}", exc_info=True)
        return {"error": str(e)}
    
    finally:
        db.close()