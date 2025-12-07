# src/rag/sync_generation_service.py
"""
Synchronous InsightGenerationOrchestrator for Celery tasks
"""

from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging

from .models import (
    InsightGenerationJob, 
    Insight, 
    InsightType,
    InsightStatus,
    CategoryInsightType
)
from ..chats.models import Chat
from .rag_optimizer import RAGContextExtractor
from ..config import settings
from ..logging_config import get_logger, log_business_event
from ..error_handlers import InsufficientCreditsException

logger = get_logger(__name__)


class SyncInsightGenerationOrchestrator:
    """Synchronous orchestrator for Celery tasks"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rag_extractor = RAGContextExtractor(db)
    
    # ========================================================================
    # JOB CREATION (Sync)
    # ========================================================================
    
    def create_generation_job(
        self,
        job_id: str,
        chat_id: UUID,
        category_id: UUID,
        user_id: str,
        insight_types: List[CategoryInsightType]
    ) -> InsightGenerationJob:
        """Create generation job record"""
        
        total_insights = len(insight_types)
        estimated_seconds = (total_insights / settings.MAX_CONCURRENT_INSIGHTS) * 7
        estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=estimated_seconds)
        
        job = InsightGenerationJob(
            job_id=job_id,
            chat_id=chat_id,
            category_id=category_id,
            user_id=user_id,
            status="queued",
            total_insights=total_insights,
            estimated_completion_at=estimated_completion
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Update chat status
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if chat:
            chat.insights_generation_status = "queued"
            chat.insights_job_id = job_id
            chat.insights_unlocked_at = datetime.now(timezone.utc)
            chat.total_insights_requested = total_insights
            self.db.commit()
        
        logger.info(
            f"Generation job created: {job_id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "total_insights": total_insights,
                    "estimated_seconds": int(estimated_seconds)
                }
            }
        )
        
        return job
    
    # ========================================================================
    # JOB LIFECYCLE (Sync)
    # ========================================================================
    
    def start_job(self, job_id: str):
        """Mark job as running"""
        job = self._get_job(job_id)
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Update chat
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        if chat:
            chat.insights_generation_status = "generating"
            chat.insights_generation_started_at = datetime.now(timezone.utc)
            self.db.commit()
        
        logger.info(f"Job started: {job_id}")
    
    def extract_shared_context(self, job_id: str) -> Dict[str, List]:
        """Extract RAG context once for all insights"""
        job = self._get_job(job_id)
        
        # Get insight types for this category
        insight_types = self.db.query(CategoryInsightType).filter(
            CategoryInsightType.category_id == job.category_id
        ).join(InsightType).filter(
            InsightType.is_active == True
        ).all()
        
        insight_type_configs = [
            {
                "id": cit.insight_type_id,
                "rag_query_keywords": cit.insight_type.rag_query_keywords
            }
            for cit in insight_types
        ]
        
        # Extract context
        context = self.rag_extractor.extract_category_context(
            chat_id=job.chat_id,
            category_id=job.category_id,
            insight_types=insight_type_configs
        )
        
        logger.info(
            f"Extracted RAG context: {len(context)} keyword groups",
            extra={
                "user_id": job.user_id,
                "extra_data": {"job_id": job_id}
            }
        )
        
        return context
    
    def update_job_progress(
        self,
        job_id: str,
        insight_id: UUID,
        status: str,
        tokens_used: Optional[int] = None,
        generation_time_ms: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Update job progress when an insight completes/fails"""
        job = self._get_job(job_id)
        
        if status == "completed":
            job.completed_insights += 1
            if tokens_used:
                job.total_tokens_used = (job.total_tokens_used or 0) + tokens_used
            if generation_time_ms:
                job.total_generation_time_ms = (job.total_generation_time_ms or 0) + generation_time_ms
        
        elif status == "failed":
            job.failed_insights += 1
            if not job.failed_insight_ids:
                job.failed_insight_ids = []
            job.failed_insight_ids.append(str(insight_id))
            if error and not job.error_message:
                job.error_message = f"First failure: {error[:200]}"
        
        # Check if job is complete
        total_processed = job.completed_insights + job.failed_insights
        
        if total_processed == job.total_insights:
            self._finalize_job(job)
        
        self.db.commit()
        
        # Update chat counters
        self._update_chat_progress(job.chat_id)
    
    def _finalize_job(self, job: InsightGenerationJob):
        """Mark job as complete and refund if failed"""
        job.completed_at = datetime.now(timezone.utc)

        # Determine final status
        if job.failed_insights == 0:
            job.status = "completed"
        elif job.completed_insights == 0:
            job.status = "failed"
        else:
            job.status = "partial_failure"

        # Get chat
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        if not chat:
            logger.error(f"Chat not found for job {job.job_id}")
            return

        # Update chat status
        if job.failed_insights == 0:
            chat.insights_generation_status = "completed"
        else:
            chat.insights_generation_status = "failed"

        self.db.commit()

        logger.info(
            f"Job finalized: {job.job_id}",
            extra={
                "user_id": job.user_id,
                "extra_data": {
                    "status": job.status,
                    "completed": job.completed_insights,
                    "failed": job.failed_insights,
                    "total": job.total_insights
                }
            }
        )

        # Refund coins if ANY insights failed (immediate deduction pattern)
        if job.failed_insights > 0:
            self._refund_coins_after_failure(job, chat)
    
    def _refund_coins_after_failure(self, job: InsightGenerationJob, chat: Chat):
        """Refund coins when generation fails (immediate deduction pattern)"""
        logger.info(
            f"{job.failed_insights} insights failed, refunding coins",
            extra={
                "user_id": job.user_id,
                "extra_data": {
                    "job_id": job.job_id,
                    "chat_id": str(job.chat_id),
                    "failed": job.failed_insights,
                    "total": job.total_insights
                }
            }
        )

        try:
            # Refund the transaction using async-compatible approach
            import asyncio
            from ..credits.service import CreditService
            from ..database import get_async_db_transaction

            async def do_refund():
                async with get_async_db_transaction() as async_db:
                    await CreditService.refund_transaction_async(
                        db=async_db,
                        chat_id=job.chat_id,
                        reason=f"{job.failed_insights}/{job.total_insights} insights failed"
                    )

            # Run async refund in event loop
            asyncio.run(do_refund())

            logger.info("✓ Coins refunded successfully")

        except Exception as e:
            logger.error(
                f"Failed to refund coins: {e}",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {
                        "job_id": job.job_id,
                        "chat_id": str(job.chat_id)
                    }
                },
                exc_info=True
            )
    
    def _update_chat_progress(self, chat_id: UUID):
        """Update chat's insight counters"""
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return
        
        insights = self.db.query(Insight).filter(Insight.chat_id == chat_id).all()
        
        chat.total_insights_completed = sum(
            1 for i in insights if i.status == InsightStatus.COMPLETED
        )
        chat.total_insights_failed = sum(
            1 for i in insights if i.status == InsightStatus.FAILED
        )
        
        self.db.commit()
    
    def _get_job(self, job_id: str) -> InsightGenerationJob:
        """Get job or raise error"""
        job = self.db.query(InsightGenerationJob).filter(
            InsightGenerationJob.job_id == job_id
        ).first()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        return job
    
    def mark_job_completed(self, job_id: str):
        """
        Mark job as completed and refund if any failed
        """
        job = self._get_job(job_id)

        # Determine final status
        if job.failed_insights == 0:
            job.status = "completed"
        elif job.failed_insights == job.total_insights:
            job.status = "failed"
        else:
            job.status = "partial_failure"

        job.completed_at = datetime.now(timezone.utc)

        # Update chat status
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        if not chat:
            return

        # Update chat generation status
        if job.failed_insights == 0:
            chat.insights_generation_status = "completed"
            logger.info(f"All insights succeeded, keeping coins deducted")
        else:
            chat.insights_generation_status = "failed"
            logger.info(f"{job.failed_insights} insights failed, refunding coins")

        self.db.commit()

        # Refund coins if any failed
        if job.failed_insights > 0:
            self._refund_coins_after_failure(job, chat)
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get current job status for API polling"""
        job = self._get_job(job_id)
        
        if job.total_insights > 0:
            progress_percentage = int(
                (job.completed_insights + job.failed_insights) / job.total_insights * 100
            )
        else:
            progress_percentage = 0
        
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress_percentage": progress_percentage,
            "total_insights": job.total_insights,
            "completed_insights": job.completed_insights,
            "failed_insights": job.failed_insights,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "estimated_completion_at": job.estimated_completion_at
        }