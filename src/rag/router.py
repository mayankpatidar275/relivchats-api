"""
RAG API - Internal RAG operations and queries
Endpoints:
- POST /rag/query (conversational Q&A)
- POST /rag/generate (legacy single insight generation - consider deprecating)
"""

import asyncio
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_async_db
from ..chats.models import Chat
from ..auth.dependencies import get_current_user_id
from ..chats.service import get_chat_by_id  # Async version for router
from . import schemas, service
from .models import InsightStatus

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=schemas.RAGQueryResponse)
async def query_chat(
    request: schemas.RAGQueryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db)
):
    """
    Ask a question about a specific chat using RAG
    This is for conversational Q&A, not insight generation
    """
    # Verify user owns the chat using async query
    result = await db.execute(
        select(Chat).where(Chat.id == request.chat_id)
    )
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")

    # Check if chat is ready for search
    if chat.vector_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Chat is not ready for search. Current status: {chat.vector_status}"
        )

    try:
        # Perform RAG query (run in executor since service is sync)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            service.query_chat_with_rag,
            db,
            request.chat_id,
            request.question,
            user_id,
            request.max_chunks
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# DEPRECATED: Use POST /insights/unlock instead
@router.post("/generate", response_model=schemas.InsightResponse, deprecated=True)
async def generate_insight(
    request: schemas.GenerateInsightRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db),
    # background_tasks: BackgroundTasks = None
):
    """
    DEPRECATED: Generate single insight asynchronously
    Use POST /insights/unlock for batch generation

    This endpoint is kept for backward compatibility
    """
    # Verify user owns the chat using async query
    result = await db.execute(
        select(Chat).where(Chat.id == UUID(request.chat_id))
    )
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")

    # Check if chat is ready
    if chat.vector_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Chat is not ready. Current status: {chat.vector_status}"
        )
    
    try:
        # Check if insight already exists (run in executor)
        loop = asyncio.get_event_loop()
        existing_insight = await loop.run_in_executor(
            None,
            service.get_insight,
            db,
            UUID(request.chat_id),
            UUID(request.insight_type_id)
        )

        if existing_insight:
            # If completed, return immediately
            if existing_insight.status == InsightStatus.COMPLETED:
                response = await loop.run_in_executor(
                    None,
                    service.create_insight_response,
                    db,
                    existing_insight
                )
                return response

            # If already generating, return status
            if existing_insight.status == InsightStatus.GENERATING:
                raise HTTPException(
                    status_code=409,
                    detail="Insight is already being generated. Please wait."
                )

            # If failed, retry
            if existing_insight.status == InsightStatus.FAILED:
                insight = await loop.run_in_executor(
                    None,
                    service.regenerate_insight,
                    db,
                    existing_insight.id
                )
                response = await loop.run_in_executor(
                    None,
                    service.create_insight_response,
                    db,
                    insight
                )
                return response

        # Generate new insight
        insight = await loop.run_in_executor(
            None,
            service.generate_insight,
            db,
            UUID(request.chat_id),
            UUID(request.insight_type_id)
        )

        response = await loop.run_in_executor(
            None,
            service.create_insight_response,
            db,
            insight
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insight: {str(e)}")

# @router.get("/search/{chat_id}", response_model=List[schemas.SearchResultResponse])
# def search_chat_chunks(
#     chat_id: str,
#     q: str,  # Query parameter
#     limit: int = 5,
#     user_id: Annotated[str, Depends(get_current_user_id)],
#     db: Session = Depends(get_db)
# ):
#     """Search for relevant chunks in a chat without LLM response"""
    
#     # Verify user owns the chat
#     chat = get_chat_by_id(db, chat_id)
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
    
#     if chat.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
#     # Check if chat is ready for search
#     if chat.vector_status != "completed":
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Chat is not ready for search. Current status: {chat.vector_status}"
#         )
    
#     try:
#         # Perform vector search only
#         results = service.search_chat_chunks(
#             db=db,
#             chat_id=chat_id,
#             query=q,
#             limit=limit
#         )
        
#         return results
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")