# src/rag/generation_service.py - NEW FILE

from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
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

logger = logging.getLogger(__name__)


class InsightGenerationOrchestrator:
    """
    Orchestrates parallel insight generation for a chat category
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.rag_extractor = RAGContextExtractor(db)
    
    def create_generation_job(
        self,
        job_id: str,
        chat_id: UUID,
        category_id: UUID,
        user_id: str,
        insight_types: List[CategoryInsightType]
    ) -> InsightGenerationJob:
        """
        Create a generation job record
        Called by unlock_insights_for_category in credits/service.py
        """
        
        # Calculate estimated completion time
        # Assume 30s per insight, with 3 parallel workers
        total_insights = len(insight_types)
        estimated_seconds = (total_insights / settings.MAX_CONCURRENT_INSIGHTS) * 30
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)
        
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
            chat.insights_unlocked_at = datetime.utcnow()
            chat.total_insights_requested = total_insights
            self.db.commit()
        
        return job
    
    def start_job(self, job_id: str):
        """Mark job as started"""
        job = self._get_job(job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        # Update chat
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        if chat:
            chat.insights_generation_status = "generating"
            chat.insights_generation_started_at = datetime.utcnow()
            self.db.commit()
    
    def extract_shared_context(
        self,
        job_id: str
    ) -> Dict[str, List]:
        """
        Extract RAG context once for all insights
        Returns cached context that tasks can use
        """
        job = self._get_job(job_id)
        
        # Get all insight types for this job
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
        
        # Extract context (will cache automatically)
        context = self.rag_extractor.extract_category_context(
            chat_id=job.chat_id,
            category_id=job.category_id,
            insight_types=insight_type_configs
        )
        
        logger.info(f"Extracted RAG context for job {job_id}: {len(context)} keyword groups")
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
                job.total_tokens_used += tokens_used
            if generation_time_ms:
                job.total_generation_time_ms += generation_time_ms
        
        elif status == "failed":
            job.failed_insights += 1
            if not job.failed_insight_ids:
                job.failed_insight_ids = []
            job.failed_insight_ids.append(str(insight_id))
            if error and not job.error_message:
                job.error_message = f"First failure: {error}"
        
        # Check if job is complete
        total_processed = job.completed_insights + job.failed_insights
        
        if total_processed == job.total_insights:
            self._finalize_job(job)
        
        self.db.commit()
        
        # Update chat counters
        self._update_chat_progress(job.chat_id)
    
    def _finalize_job(self, job: InsightGenerationJob):
        """Mark job as complete and determine final status"""
        job.completed_at = datetime.utcnow()
        
        if job.failed_insights == 0:
            job.status = "completed"
            final_status = "completed"
        elif job.completed_insights == 0:
            job.status = "failed"
            final_status = "failed"
        else:
            job.status = "partial_failure"
            final_status = "partial_failure"
        
        # Update chat
        chat = self.db.query(Chat).filter(Chat.id == job.chat_id).first()
        if chat:
            chat.insights_generation_status = final_status
            chat.insights_generation_completed_at = datetime.utcnow()
        
        logger.info(
            f"Job {job.job_id} finalized: {job.completed_insights}/{job.total_insights} completed, "
            f"{job.failed_insights} failed, {job.total_tokens_used} tokens, "
            f"{job.total_generation_time_ms}ms total"
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
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get current job status for polling"""
        job = self._get_job(job_id)
        
        progress_percentage = 0
        if job.total_insights > 0:
            progress_percentage = (
                (job.completed_insights + job.failed_insights) / job.total_insights
            ) * 100
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress_percentage": round(progress_percentage, 1),
            "total_insights": job.total_insights,
            "completed_insights": job.completed_insights,
            "failed_insights": job.failed_insights,
            "started_at": job.started_at,
            "estimated_completion_at": job.estimated_completion_at,
            "completed_at": job.completed_at,
        }