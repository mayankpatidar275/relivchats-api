# src/rag/generation_service.py
"""
Async Insight generation orchestrator

Insight generation orchestrator with deduct-after-generation logic

KEY CHANGE: mark_job_completed() now charges coins only if ALL succeeded
"""

from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from .models import (
    InsightGenerationJob, 
    Insight, 
    InsightType,
    InsightStatus,
    CategoryInsightType
)
from ..error_handlers import (
    InsufficientCreditsException
)
from ..chats.models import Chat
from .rag_optimizer import RAGContextExtractor
from ..config import settings
from ..logging_config import get_logger, log_business_event

logger = get_logger(__name__)


class InsightGenerationOrchestrator:
    """Async orchestrator for parallel insight generation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_extractor = RAGContextExtractor(db)
    
    # ========================================================================
    # ASYNC JOB CREATION
    # ========================================================================
    
    async def create_generation_job(
        self,
        job_id: str,
        chat_id: UUID,
        category_id: UUID,
        user_id: str,
        insight_types: List[CategoryInsightType]
    ) -> InsightGenerationJob:
        """Create generation job record"""
        
        # Estimate completion time (7s per insight avg)
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
        await self.db.commit()
        await self.db.refresh(job)
        
        # Update chat status
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.insights_generation_status = "queued"
            chat.insights_job_id = job_id
            chat.insights_unlocked_at = datetime.now(timezone.utc)
            chat.total_insights_requested = total_insights
            await self.db.commit()
        
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
    
    async def create_generation_job_async(
        self,
        job_id: str,
        chat_id: UUID,
        category_id: UUID,
        user_id: str,
        insight_types: List[CategoryInsightType]
    ) -> InsightGenerationJob:
        """Alias for async method"""
        return await self.create_generation_job(
            job_id, chat_id, category_id, user_id, insight_types
        )
    
    # ========================================================================
    # ASYNC JOB LIFECYCLE
    # ========================================================================
    
    async def start_job(self, job_id: str):
        """Mark job as running"""
        job = await self._get_job(job_id)
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        # Update chat
        result = await self.db.execute(
            select(Chat).where(Chat.id == job.chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.insights_generation_status = "generating"
            chat.insights_generation_started_at = datetime.now(timezone.utc)
            await self.db.commit()
        
        logger.info(f"Job started: {job_id}")
    
    async def extract_shared_context(self, job_id: str) -> Dict[str, List]:
        """Extract RAG context once for all insights"""
        job = await self._get_job(job_id)
        
        # Get insight types for this category
        result = await self.db.execute(
            select(CategoryInsightType)
            .where(CategoryInsightType.category_id == job.category_id)
            .join(InsightType)
            .where(InsightType.is_active == True)
        )
        insight_types = result.scalars().all()
        
        insight_type_configs = [
            {
                "id": cit.insight_type_id,
                "rag_query_keywords": cit.insight_type.rag_query_keywords
            }
            for cit in insight_types
        ]
        
        # Extract context (cached in Redis)
        context = await self.rag_extractor.extract_category_context(
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
    
    async def update_job_progress(
        self,
        job_id: str,
        insight_id: UUID,
        status: str,
        tokens_used: Optional[int] = None,
        generation_time_ms: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Update job progress when an insight completes/fails"""
        job = await self._get_job(job_id)
        
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
            await self._finalize_job(job)
        
        await self.db.commit()
        
        # Update chat counters
        await self._update_chat_progress(job.chat_id)
    
    async def _finalize_job(self, job: InsightGenerationJob):
        """Mark job as complete and CHARGE COINS if successful
        CRITICAL: This is where coins are deducted (only if all succeeded)
        """
        job.completed_at = datetime.now(timezone.utc)
        
        # Determine final status
        if job.failed_insights == 0:
            job.status = "completed"
            final_status = "completed"
        elif job.completed_insights == 0:
            job.status = "failed"
            final_status = "failed"
        else:
            job.status = "partial_failure"
            final_status = "partial_failure"
        
        # Get chat
        result = await self.db.execute(
            select(Chat).where(Chat.id == job.chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            logger.error(f"Chat not found for job {job.job_id}")
            return
        
        await self.db.commit()
        
        logger.info(
            f"Job finalized: {job.job_id}",
            extra={
                "user_id": job.user_id,
                "extra_data": {
                    "status": job.status,
                    "completed": job.completed_insights,
                    "failed": job.failed_insights,
                    "total": job.total_insights,
                    "tokens_used": job.total_tokens_used,
                    "generation_time_ms": job.total_generation_time_ms
                }
            }
        )
        
        # Charge coins or release reservation
        if job.failed_insights == 0:
            # ALL INSIGHTS SUCCEEDED → CHARGE COINS
            await self._charge_coins_after_success(job, chat)
        else:
            # SOME/ALL FAILED → RELEASE RESERVATION (NO CHARGE)
            await self._release_reservation_after_failure(job, chat)
    
    async def _charge_coins_after_success(self, job: InsightGenerationJob, chat: Chat):
        """Charge reserved coins after successful generation"""
        logger.info(
            f"All insights succeeded, charging {chat.reserved_coins} coins",
            extra={
                "user_id": job.user_id,
                "extra_data": {
                    "job_id": job.job_id,
                    "chat_id": str(job.chat_id),
                    "reserved_coins": chat.reserved_coins
                }
            }
        )
        
        from ..credits.service import CreditService
        from ..error_handlers import InsufficientCreditsException
        
        try:
            transaction = await CreditService.charge_reserved_coins(
                db=self.db,
                chat_id=job.chat_id
            )
            
            logger.info(
                f"✓ Coins charged: {transaction.amount}",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {
                        "transaction_id": str(transaction.id),
                        "new_balance": transaction.balance_after
                    }
                }
            )
            
        except InsufficientCreditsException as e:
            # User spent coins during generation
            logger.critical(
                "PAYMENT FAILED: User spent coins during generation",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {
                        "chat_id": str(job.chat_id),
                        "required": e.details["required"],
                        "available": e.details["available"]
                    }
                }
            )
            
            # Queue retry task
            from .tasks import retry_payment_deduction
            retry_payment_deduction.apply_async(
                args=[str(job.chat_id)],
                countdown=300  # Retry after 5 minutes
            )
            
        except Exception as e:
            logger.critical(
                f"CRITICAL: Failed to charge coins after success: {str(e)}",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {"chat_id": str(job.chat_id)}
                },
                exc_info=True
            )
            
            # Queue retry
            from .tasks import retry_payment_deduction
            retry_payment_deduction.apply_async(
                args=[str(job.chat_id)],
                countdown=60  # Retry after 1 minute
            )
    
    async def _release_reservation_after_failure(self, job: InsightGenerationJob, chat: Chat):
        """Release coin reservation when generation fails"""
        logger.info(
            f"{job.failed_insights} insights failed, releasing reservation",
            extra={
                "user_id": job.user_id,
                "extra_data": {
                    "job_id": job.job_id,
                    "chat_id": str(job.chat_id),
                    "reserved_coins": chat.reserved_coins,
                    "failed": job.failed_insights,
                    "total": job.total_insights
                }
            }
        )
        
        from ..credits.service import CreditService
        
        await CreditService.release_reservation(
            db=self.db,
            chat_id=job.chat_id,
            reason=f"{job.failed_insights}/{job.total_insights} insights failed"
        )
        
        logger.info("✓ Reservation released (no charge)")
        
        log_business_event(
            "generation_failed_no_charge",
            user_id=job.user_id,
            job_id=job.job_id,
            chat_id=str(job.chat_id),
            failed_insights=job.failed_insights,
            total_insights=job.total_insights
        )
    
    async def _update_chat_progress(self, chat_id: UUID):
        """Update chat's insight counters"""
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return
        
        result = await self.db.execute(
            select(Insight).where(Insight.chat_id == chat_id)
        )
        insights = result.scalars().all()
        
        chat.total_insights_completed = sum(
            1 for i in insights if i.status == InsightStatus.COMPLETED
        )
        chat.total_insights_failed = sum(
            1 for i in insights if i.status == InsightStatus.FAILED
        )
        
        await self.db.commit()
    
    async def _get_job(self, job_id: str) -> InsightGenerationJob:
        """Get job or raise error"""
        result = await self.db.execute(
            select(InsightGenerationJob).where(InsightGenerationJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        return job
    
    # ========================================================================
    # ASYNC JOB STATUS (For polling)
    # ========================================================================
    
    async def get_job_status(self, job_id: str) -> Dict:
        """Get current job status for API polling"""
        job = await self._get_job(job_id)
        
        # Calculate progress
        if job.total_insights > 0:
            progress_percentage = int(
                (job.completed_insights + job.failed_insights) / job.total_insights * 100
            )
        else:
            progress_percentage = 0
        
        # Get chat for payment status
        result = await self.db.execute(
            select(Chat).where(Chat.id == job.chat_id)
        )
        chat = result.scalar_one_or_none()
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress_percentage": progress_percentage,
            "total_insights": job.total_insights,
            "completed_insights": job.completed_insights,
            "failed_insights": job.failed_insights,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "estimated_completion_at": job.estimated_completion_at,
            "payment_status": await self._get_payment_status(chat),
            "coins_charged": 0 if chat.reserved_coins > 0 else chat.reserved_coins
        }
    
    async def _get_payment_status(self, chat: Chat) -> str:
        """Determine payment status for frontend"""
        if not chat:
            return "unknown"
        
        status = chat.insights_generation_status
        
        if status == "completed" and chat.reserved_coins == 0:
            return "charged"
        elif status == "pending_payment" or (status == "completed" and chat.reserved_coins > 0):
            return "pending"
        elif status == "payment_failed":
            return "insufficient_balance"
        elif status in ["failed", "timeout"]:
            return "not_charged"
        else:
            return "pending"
    
    async def get_job_status_async(self, job_id: str) -> Dict:
        """Alias for async method"""
        return await self.get_job_status(job_id)
    
    async def mark_job_completed(self, job_id: str):
        """
        Mark job as completed and charge coins if all succeeded
        """
        job = await self._get_job(job_id)
        
        # Determine final status
        if job.failed_insights == 0:
            job.status = "completed"
            final_status = "completed"
        elif job.failed_insights == job.total_insights:
            job.status = "failed"
            final_status = "failed"
        else:
            job.status = "partial_failure"
            final_status = "partial_failure"
        
        job.completed_at = datetime.now(timezone.utc)
        
        # Update chat status
        result = await self.db.execute(
            select(Chat).where(Chat.id == job.chat_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return
        
        await self.db.commit()
        
        # CRITICAL: Charge coins if all succeeded
        if job.failed_insights == 0:
            # ALL insights succeeded → Charge reserved coins
            logger.info(
                f"All insights succeeded, charging {chat.reserved_coins} coins",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {
                        "job_id": job_id,
                        "chat_id": str(job.chat_id)
                    }
                }
            )
            
            from ..credits.service import CreditService
            from ..error_handlers import InsufficientCreditsException
            
            try:
                await CreditService.charge_reserved_coins(
                    db=self.db,
                    chat_id=job.chat_id
                )
                logger.info(f"✓ Successfully charged coins for job {job_id}")
                
            except InsufficientCreditsException:
                # User spent coins during generation
                logger.critical(
                    "Payment failed: User spent coins during generation",
                    extra={
                        "user_id": job.user_id,
                        "extra_data": {"chat_id": str(job.chat_id)}
                    }
                )
                # Insights will be hidden by charge_reserved_coins
                
            except Exception as e:
                logger.critical(
                    f"Failed to charge coins after success: {str(e)}",
                    extra={
                        "user_id": job.user_id,
                        "extra_data": {"chat_id": str(job.chat_id)}
                    },
                    exc_info=True
                )
        
        else:
            # Some/all insights failed → Release reservation (don't charge)
            logger.info(
                f"{job.failed_insights} insights failed, releasing reservation",
                extra={
                    "user_id": job.user_id,
                    "extra_data": {
                        "job_id": job_id,
                        "chat_id": str(job.chat_id)
                    }
                }
            )
            
            from ..credits.service import CreditService
            
            await CreditService.release_reservation(
                db=self.db,
                chat_id=job.chat_id,
                reason=f"{job.failed_insights}/{job.total_insights} insights failed"
            )
            logger.info("✓ Reservation released (no charge)")
        
        log_business_event(
            "insight_generation_finalized",
            user_id=job.user_id,
            job_id=job_id,
            chat_id=str(job.chat_id),
            status=job.status.value,
            completed=job.completed_insights,
            failed=job.failed_insights,
            coins_charged=chat.reserved_coins if job.failed_insights == 0 else 0
        )