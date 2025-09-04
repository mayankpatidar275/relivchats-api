from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.dependencies import get_current_user_id
from ..chats.service import get_chat_by_id
from . import schemas, service

router = APIRouter(
    prefix="/rag",
    tags=["rag"],
)

@router.post("/query", response_model=schemas.RAGQueryResponse)
def query_chat(
    request: schemas.RAGQueryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db)
):
    """Ask a question about a specific chat using RAG"""
    # Verify user owns the chat
    chat = get_chat_by_id(db, request.chat_id)
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
        # Perform RAG query
        response = service.query_chat_with_rag(
            db=db,
            chat_id=request.chat_id,
            question=request.question,
            user_id=user_id,
            max_chunks=request.max_chunks
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

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