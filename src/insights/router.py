"""
Insights API - Handles all insight generation, retrieval, and management
Endpoints:
- POST /insights/unlock (moved from credits)
- GET /insights/jobs/{job_id}/status
- GET /insights/chats/{chat_id}
- POST /insights/{insight_id}/retry
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated, List
from uuid import UUID

from ..database import get_db
from ..auth.dependencies import get_current_user_id
from ..credits.service import CreditService
from ..rag.generation_service import InsightGenerationOrchestrator
from ..rag.tasks import retry_failed_insight
from ..rag import schemas as rag_schemas
from ..rag.models import Insight, AnalysisCategory
from ..rag.service import create_insight_response
from ..chats.models import Chat
from ..credits import schemas as credit_schemas

router = APIRouter(prefix="/insights", tags=["insights"])


# ============================================================================
# UNLOCK INSIGHTS (MOVED FROM CREDITS)
# ============================================================================

@router.post("/unlock", response_model=credit_schemas.UnlockInsightsResponse)
def unlock_chat_insights(
    request: credit_schemas.UnlockInsightsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """
    Unlock all insights for a chat category
    - Deducts credits
    - Creates insight records
    - Launches background generation
    
    Returns job_id for status polling
    """
    service = CreditService(db)
    
    try:
        result = service.unlock_insights_for_category(
            user_id=user_id,
            chat_id=request.chat_id,
            category_id=request.category_id
        )
        
        return credit_schemas.UnlockInsightsResponse(**result)
        
    except HTTPException:
        raise


# ============================================================================
# JOB STATUS POLLING
# ============================================================================

@router.get("/jobs/{job_id}/status", response_model=rag_schemas.JobStatusResponse)
def get_generation_job_status(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """
    Poll job status for real-time updates
    Frontend should call this every 2-3 seconds while generating
    
    Returns:
    - status: queued, running, completed, failed, partial_failure
    - progress_percentage: 0-100
    - completed_insights, failed_insights
    """
    from ..rag.models import InsightGenerationJob
    
    orchestrator = InsightGenerationOrchestrator(db)
    
    # Verify job belongs to user
    job = db.query(InsightGenerationJob).filter(
        InsightGenerationJob.job_id == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        status = orchestrator.get_job_status(job_id)
        return rag_schemas.JobStatusResponse(**status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# GET CHAT INSIGHTS
# ============================================================================

@router.get("/chats/{chat_id}", response_model=rag_schemas.ChatInsightsResponse)
def get_chat_insights(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """
    Get all insights for a chat (completed, failed, generating)
    
    Returns:
    - Generation status (not_started, queued, generating, completed, etc.)
    - List of insights with content
    - Progress counters
    """
    # Verify chat belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == user_id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get category info if insights unlocked
    category = None
    if chat.category_id:
        category = db.query(AnalysisCategory).filter(
            AnalysisCategory.id == chat.category_id
        ).first()
    
    # Get all insights
    insights = db.query(Insight).filter(
        Insight.chat_id == chat_id
    ).all()
    
    return rag_schemas.ChatInsightsResponse(
        chat_id=chat_id,
        category=rag_schemas.CategoryBasicResponse(
            id=category.id,
            name=category.name,
            display_name=category.display_name,
            icon=category.icon
        ) if category else None,
        generation_status=chat.insights_generation_status or "not_started",
        unlocked_at=chat.insights_unlocked_at,
        total_requested=chat.total_insights_requested or 0,
        total_completed=chat.total_insights_completed or 0,
        total_failed=chat.total_insights_failed or 0,
        insights=[create_insight_response(db, i) for i in insights]
    )


# ============================================================================
# RETRY FAILED INSIGHT
# ============================================================================

@router.post("/{insight_id}/retry")
def retry_failed_insight_endpoint(
    insight_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """
    Retry a failed insight (manual trigger)
    Useful when individual insights fail due to temporary issues
    """
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Verify ownership
    chat = db.query(Chat).filter(
        Chat.id == insight.chat_id,
        Chat.user_id == user_id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not chat.insights_job_id:
        raise HTTPException(status_code=400, detail="No job found for this chat")
    
    # Trigger retry task
    retry_failed_insight.delay(
        insight_id=str(insight_id),
        job_id=chat.insights_job_id
    )
    
    return {
        "success": True,
        "message": "Retry queued",
        "insight_id": str(insight_id)
    }