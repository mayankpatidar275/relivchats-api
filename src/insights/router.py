# src/insights/router.py
"""
Insights API - Handles all insight generation, retrieval, and management
Endpoints:
- POST /insights/unlock (async, production-ready)
- GET /insights/jobs/{job_id}/status
- GET /insights/chats/{chat_id}
- POST /insights/{insight_id}/retry
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Annotated
from uuid import UUID

from ..database import get_async_db
from ..auth.dependencies import get_current_user_id
from ..credits.service import CreditService
from ..rag.generation_service import InsightGenerationOrchestrator
from ..rag import schemas as rag_schemas
from ..rag.models import Insight, AnalysisCategory, InsightGenerationJob
from ..chats.models import Chat
from ..credits import schemas as credit_schemas
from ..logging_config import get_logger
from ..config import settings
from ..error_handlers import NotFoundException
from ..rate_limit import limiter, INSIGHT_UNLOCK_LIMIT, INSIGHT_UNLOCK_BURST, INSIGHT_READ_LIMIT

router = APIRouter(prefix="/insights", tags=["insights"])
logger = get_logger(__name__)


# ============================================================================
# UNLOCK INSIGHTS (ASYNC - PRODUCTION READY)
# ============================================================================

@router.post("/unlock", response_model=credit_schemas.UnlockInsightsResponse)
@limiter.limit(INSIGHT_UNLOCK_LIMIT)  # 10/hour - prevents abuse
@limiter.limit(INSIGHT_UNLOCK_BURST)  # 3/minute - prevents rapid unlocks
async def unlock_chat_insights(
    http_request: Request,  # Required for rate limiting
    request: credit_schemas.UnlockInsightsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Unlock all insights for a chat category (ASYNC + Production Ready)
    
    This endpoint:
    1. Verifies chat ownership
    2. Checks if already unlocked (idempotency)
    3. Ensures chat is indexed
    4. Deducts credits atomically (with row-level lock)
    5. Creates insight records
    6. Launches background generation
    
    Returns job_id for status polling
    
    Errors:
    - 404: Chat not found
    - 400: Already unlocked or indexing failed
    - 402: Insufficient credits
    - 409: Currently indexing
    """
    logger.info(
        "Unlock insights endpoint called",
        extra={
            "user_id": user_id,
            "extra_data": {
                "chat_id": str(request.chat_id),
                "category_id": str(request.category_id)
            }
        }
    )
    
    try:
        result = await CreditService.unlock_insights_for_category(
            db=db,
            user_id=user_id,
            chat_id=request.chat_id,
            category_id=request.category_id
        )
        
        return credit_schemas.UnlockInsightsResponse(**result)
        
    except (NotFoundException, HTTPException) as e:
        logger.warning(
            f"Unlock failed: {str(e)}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(request.chat_id),
                    "error": str(e)
                }
            }
        )
        raise


# ============================================================================
# JOB STATUS POLLING
# ============================================================================

@router.get("/jobs/{job_id}/status", response_model=rag_schemas.JobStatusResponse)
async def get_generation_job_status(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Poll job status for real-time updates
    
    Frontend should call this every 2-3 seconds while generating.
    
    Returns:
    - status: queued, running, completed, failed, partial_failure
    - progress_percentage: 0-100
    - completed_insights, failed_insights
    - insights: List of insight responses
    
    Errors:
    - 404: Job not found
    - 403: Access denied (job belongs to different user)
    """
    logger.debug(
        f"Job status check: {job_id}",
        extra={"user_id": user_id}
    )
    
    try:
        # Verify job belongs to user
        result = await db.execute(
            select(InsightGenerationJob).where(
                InsightGenerationJob.job_id == job_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise NotFoundException("Job", job_id)
        
        if job.user_id != user_id:
            logger.warning(
                "Unauthorized job access attempt",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "job_id": job_id,
                        "owner_id": job.user_id
                    }
                }
            )
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get job status (this is async now)
        orchestrator = InsightGenerationOrchestrator(db)
        status = await orchestrator.get_job_status_async(job_id)
        
        return rag_schemas.JobStatusResponse(**status)
        
    except NotFoundException:
        raise HTTPException(status_code=404, detail="Job not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# GET CHAT INSIGHTS
# ============================================================================

@router.get("/chats/{chat_id}", response_model=rag_schemas.ChatInsightsResponse)
async def get_chat_insights(
    chat_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all insights for a chat (completed, failed, generating)
    
    Returns:
    - Generation status (not_started, queued, generating, completed, etc.)
    - List of insights with content
    - Progress counters
    
    Errors:
    - 404: Chat not found
    - 403: Access denied
    """
    logger.debug(
        f"Getting insights for chat {chat_id}",
        extra={"user_id": user_id}
    )
    
    try:
        # Verify chat belongs to user
        result = await db.execute(
            select(Chat).where(
                and_(
                    Chat.id == chat_id,
                    Chat.user_id == user_id,
                    Chat.is_deleted == False
                )
            )
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise NotFoundException("Chat", str(chat_id))
        
        # Get category info if insights unlocked
        category = None
        if chat.category_id:
            result = await db.execute(
                select(AnalysisCategory).where(
                    AnalysisCategory.id == chat.category_id
                )
            )
            category = result.scalar_one_or_none()
        
        # Get all insights
        result = await db.execute(
            select(Insight)
            .where(Insight.chat_id == chat_id)
        )
        insights = result.scalars().all()
        
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
            insights=[await create_insight_response_async(db, i) for i in insights]
        )
        
    except NotFoundException:
        raise HTTPException(status_code=404, detail="Chat not found")

# ============================================================================
# HELPER FUNCTIONS (ASYNC)
# ============================================================================

async def create_insight_response_async(
    db: AsyncSession,
    insight: Insight
) -> rag_schemas.InsightResponse:
    """Create insight response (async variant)"""
    # Get insight type details
    from ..rag.models import InsightType
    
    result = await db.execute(
        select(InsightType).where(InsightType.id == insight.insight_type_id)
    )
    insight_type = result.scalar_one()
    
    return rag_schemas.InsightResponse(
        id=insight.id,
        chat_id=insight.chat_id,
        insight_type_id=insight.insight_type_id,
        insight_type_name=insight_type.name,
        display_title=insight_type.display_title,
        description=insight_type.description,
        icon=insight_type.icon,
        content=insight.content,
        status=insight.status,
        is_premium=insight_type.is_premium if insight_type else False,
        generation_metadata=rag_schemas.InsightGenerationMetadata(
            tokens_used=insight.tokens_used or 0,
            generation_time_ms=insight.generation_time_ms or 0,
            rag_chunks_used=insight.rag_chunks_used or 0,
            model_used=settings.GEMINI_LLM_MODEL
        ),
        # confidence_score= None,
        error_message=insight.error_message,
        tokens_used=insight.tokens_used,
        generation_time_ms=insight.generation_time_ms,
        created_at=insight.created_at,
        updated_at=insight.updated_at
    )



# ============================================================================
# RETRY FAILED INSIGHT
# ============================================================================

# @router.post("/{insight_id}/retry")
# async def retry_failed_insight_endpoint(
#     insight_id: UUID,
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: AsyncSession = Depends(get_async_db)
# ):
#     """
#     Retry a failed insight (manual trigger)
    
#     Useful when individual insights fail due to temporary issues.
    
#     Errors:
#     - 404: Insight not found
#     - 403: Access denied
#     - 400: No job found for this chat
#     """
#     logger.info(
#         f"Retry insight requested: {insight_id}",
#         extra={"user_id": user_id}
#     )
    
#     try:
#         result = await db.execute(
#             select(Insight).where(Insight.id == insight_id)
#         )
#         insight = result.scalar_one_or_none()
        
#         if not insight:
#             raise NotFoundException("Insight", str(insight_id))
        
#         # Verify ownership
#         result = await db.execute(
#             select(Chat).where(
#                 and_(
#                     Chat.id == insight.chat_id,
#                     Chat.user_id == user_id,
#                     Chat.is_deleted == False
#                 )
#             )
#         )
#         chat = result.scalar_one_or_none()
        
#         if not chat:
#             raise HTTPException(status_code=403, detail="Access denied")
        
#         if not chat.insights_job_id:
#             raise HTTPException(
#                 status_code=400,
#                 detail="No job found for this chat"
#             )
        
#         # Trigger retry task
#         retry_failed_insight.delay(
#             insight_id=str(insight_id),
#             job_id=chat.insights_job_id
#         )
        
#         logger.info(
#             f"Retry queued for insight {insight_id}",
#             extra={"user_id": user_id}
#         )
        
#         return {
#             "success": True,
#             "message": "Retry queued",
#             "insight_id": str(insight_id)
#         }
        
#     except (NotFoundException, HTTPException):
#         raise
