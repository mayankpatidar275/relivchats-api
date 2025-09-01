import time
from datetime import datetime
from typing import List, Dict, Any

import google.generativeai as genai
from sqlalchemy.orm import Session

from ..vector.service import vector_service
from ..chats.service import get_chat_by_id
from . import schemas
from ..config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

def format_time_span(minutes: int) -> str:
    """Convert minutes to human readable format"""
    if minutes < 60:
        return f"{minutes} minutes"
    elif minutes < 1440:  # Less than 24 hours
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hours"
        return f"{hours}h {remaining_minutes}m"
    else:
        days = minutes // 1440
        remaining_hours = (minutes % 1440) // 60
        if remaining_hours == 0:
            return f"{days} days"
        return f"{days}d {remaining_hours}h"

def search_chat_chunks(
    db: Session, 
    chat_id: str, 
    query: str, 
    limit: int = 5
) -> List[schemas.SearchResultResponse]:
    """Search for relevant chunks without LLM response"""
    
    # Use vector service to search
    search_results = vector_service.search_chat(db, chat_id, query, limit)
    
    # Convert to response format
    formatted_results = []
    for result in search_results:
        metadata = result["metadata"]
        
        # Calculate time span
        time_span_minutes = metadata.get("time_span_minutes", 0)
        time_span_str = format_time_span(time_span_minutes)
        
        formatted_result = schemas.SearchResultResponse(
            vector_id=result["vector_id"],
            content=result["content"],
            similarity_score=result["similarity_score"],
            metadata=metadata,
            chunk_index=metadata.get("chunk_index", 0),
            speakers=metadata.get("speakers", []),
            message_count=metadata.get("message_count", 0),
            time_span=time_span_str
        )
        formatted_results.append(formatted_result)
    
    return formatted_results

def determine_confidence(similarity_scores: List[float]) -> str:
    """Determine confidence level based on similarity scores"""
    if not similarity_scores:
        return "low"
    
    avg_score = sum(similarity_scores) / len(similarity_scores)
    max_score = max(similarity_scores)
    
    if max_score > 0.8 and avg_score > 0.7:
        return "high"
    elif max_score > 0.6 and avg_score > 0.5:
        return "medium"
    else:
        return "low"

def create_rag_prompt(question: str, context_chunks: List[Dict], chat_title: str = None) -> str:
    """Create a prompt for the LLM with context"""
    
    title_info = f" titled '{chat_title}'" if chat_title else ""
    
    context_text = "\n\n".join([
        f"**Context {i+1}** (from {chunk['metadata'].get('speakers', ['Unknown'])}): \n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    prompt = f"""You are helping a user understand their WhatsApp chat{title_info}. 
Answer their question based ONLY on the provided chat context. Be conversational and helpful.

**User Question:** {question}

**Relevant Chat Context:**
{context_text}

**Instructions:**
- Answer based only on the provided context
- Be conversational and natural
- If the context doesn't contain enough information, say so honestly
- Reference specific people or timeframes when relevant
- Don't make up information not in the context

**Answer:**"""

    return prompt

def query_chat_with_rag(
    db: Session,
    chat_id: str,
    question: str,
    max_chunks: int = 5
) -> schemas.RAGQueryResponse:
    """Perform RAG query on a chat"""
    
    start_time = time.time()
    
    # Get chat info
    chat = get_chat_by_id(db, chat_id)
    chat_title = chat.title if chat else None
    
    # Search for relevant chunks
    search_results = vector_service.search_chat(db, chat_id, question, max_chunks)
    
    if not search_results:
        # No relevant context found
        answer = "I couldn't find any relevant information in this chat to answer your question. Try rephrasing your question or asking about something else from the conversation."
        confidence = "low"
        sources = []
    else:
        # Create prompt with context
        prompt = create_rag_prompt(question, search_results, chat_title)
        
        # Get LLM response
        try:
            model = genai.GenerativeModel(settings.GEMINI_LLM_MODEL)
            response = model.generate_content(prompt)
            answer = response.text.strip()
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            answer = "I'm sorry, I encountered an error while generating a response. Please try again."
        
        # Determine confidence
        similarity_scores = [r["similarity_score"] for r in search_results]
        confidence = determine_confidence(similarity_scores)
        
        # Format sources
        sources = []
        for result in search_results:
            metadata = result["metadata"]
            time_span_minutes = metadata.get("time_span_minutes", 0)
            
            source = schemas.SearchResultResponse(
                vector_id=result["vector_id"],
                content=result["content"],
                similarity_score=result["similarity_score"],
                metadata=metadata,
                chunk_index=metadata.get("chunk_index", 0),
                speakers=metadata.get("speakers", []),
                message_count=metadata.get("message_count", 0),
                time_span=format_time_span(time_span_minutes)
            )
            sources.append(source)
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    return schemas.RAGQueryResponse(
        question=question,
        answer=answer,
        chat_id=chat_id,
        chat_title=chat_title,
        sources_used=sources,
        confidence=confidence,
        response_time_ms=response_time_ms,
        created_at=datetime.utcnow()
    )