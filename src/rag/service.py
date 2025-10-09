import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from uuid import UUID
import time
import uuid

import google.generativeai as genai
from sqlalchemy.orm import Session

from ..vector.service import vector_service
from ..chats.service import get_chat_by_id
from .models import AIConversation, AIMessage, MessageType, Insight, InsightType, InsightStatus
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

def create_insight_rag_prompt(question: str, context_chunks: List[Dict], chat_title: str = None) -> str:
    """Create a prompt for insight for the LLM"""
    
    title_info = f" titled '{chat_title}'" if chat_title else ""
    
    context_text = "\n\n".join([
        f"**Context {i+1}** (from {chunk['metadata'].get('speakers', ['Unknown'])}): \n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    # Add conversation history section
    conversation_text = ""
    
    prompt = f"""You are helping a user understand their WhatsApp chat{title_info}. 
Answer their question based ONLY on the provided chat context. Be helpful.

**User Question:** {question}

**Relevant Chat Context:**
{context_text}
{conversation_text}
**Instructions:**
- Answer based only on the provided context
- Be conversational and natural
- If the context doesn't contain enough information, say so honestly
- Reference specific people or timeframes when relevant
- Don't make up information not in the context
- Consider the conversation flow and previous questions

**Answer:**"""

    return prompt

def query_chat_for_insight_with_rag(
    db: Session,
    chat_id: str,
    question: str,
    rag_query_keywords: str,
    max_chunks: int = 5
) -> schemas.RAGQueryResponse:
    """Perform RAG query on a chat with for insight"""
    
    start_time = time.time()
    
    # Get chat info
    chat = get_chat_by_id(db, chat_id)
    chat_title = chat.title if chat else None
    
    # Search for relevant chunks
    search_results = vector_service.search_chat(db, chat_id, rag_query_keywords, max_chunks)
    
    if not search_results:
        # No relevant context found
        answer = "I couldn't find any relevant information in this chat to answer your question. Try rephrasing your question or asking about something else from the conversation."
        confidence = "low"
        sources = []
    else:
        # Create prompt with context and conversation history
        prompt = create_insight_rag_prompt(question, search_results, chat_title)
        
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
        chat_id=str(chat_id),
        chat_title=chat_title,
        sources_used=sources,
        confidence=confidence,
        response_time_ms=response_time_ms,
        created_at=datetime.utcnow()
    )

def get_insight(db: Session, chat_id: UUID, insight_type_id: UUID):
    """Get existing insight if it exists"""
    try: 
        insight = db.query(Insight).filter(
            Insight.chat_id == chat_id,
            Insight.insight_type_id == insight_type_id
        ).first()
        return insight

    except Exception as e:
        print("Get insight error:", str(e))

def generate_insight(db: Session, chat_id: UUID, insight_type_id: UUID):
    """Generate a new insight using RAG"""
    start_time = time.time()
    # Get insight type with prompt template
    insight_type = db.query(InsightType).filter(InsightType.id == insight_type_id).first()
    if not insight_type:
        raise ValueError("Insight type not found")
    
    # Create insight record with "generating" status
    existing = db.query(Insight).filter_by(chat_id=chat_id, insight_type_id=insight_type_id).first()
    if existing:
        insight = existing
        insight.status = InsightStatus.GENERATING
        insight.error_message = None
    else:
        insight = Insight(chat_id=chat_id, insight_type_id=insight_type_id, status=InsightStatus.GENERATING)

    try:
        db.add(insight)
        db.commit()
        db.refresh(insight)

    except Exception as e:
        db.rollback()
        print("Commit Error:", str(e))

    try:
        # Use RAG to generate insight
        rag_response = query_chat_for_insight_with_rag(
            db=db,
            chat_id=chat_id,
            question=insight_type.prompt_template,
            rag_query_keywords=insight_type.rag_query_keywords,
            # user_id=None,  # System generated
            max_chunks=50  # Adjust based on insight type
        )
        
        # Parse and structure the content
        content = {
            "analysis": rag_response.answer,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Update insight with results
        insight.content = content
        insight.status = InsightStatus.COMPLETED
        # insight.tokens_used = rag_response.tokens_used if hasattr(rag_response, 'tokens_used') else None
        insight.tokens_used = None
        insight.generation_time_ms = int((time.time() - start_time) * 1000)
        # insight.rag_chunks_used = len(rag_response.chunks) if hasattr(rag_response, 'chunks') else None
        insight.rag_chunks_used = None
        db.commit()
        db.refresh(insight)
        return insight
        
    except Exception as e:
        # Mark as failed
        insight.status = InsightStatus.FAILED
        insight.error_message = str(e)
        db.commit()
        raise

def regenerate_insight(db: Session, insight_id: UUID):
    """Retry generating a failed insight"""
    try: 
        insight = db.query(Insight).filter(Insight.id == insight_id).first()
        if not insight:
            raise ValueError("Insight not found")
        # Reset and regenerate
        insight.status = InsightStatus.GENERATING
        insight.error_message = None
        db.commit()
        generated_insight =  generate_insight(db, insight.chat_id, insight.insight_type_id)
        return generated_insight

    except Exception as e: 
        insight.status = InsightStatus.FAILED
        insight.error_message = str(e)
        db.commit()
        print("Error generating insight: ", e)


# Not used for now

def create_rag_prompt(question: str, context_chunks: List[Dict], chat_title: str = None, conversation_history: List[Dict] = None) -> str:
    """Create a prompt for the LLM with context and conversation history"""
    
    title_info = f" titled '{chat_title}'" if chat_title else ""
    
    context_text = "\n\n".join([
        f"**Context {i+1}** (from {chunk['metadata'].get('speakers', ['Unknown'])}): \n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    # Add conversation history section
    conversation_text = ""
    if conversation_history:
        conversation_text = "\n\n**Previous Conversation:**\n"
        for msg in conversation_history:
            role = "You" if msg["type"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"
        conversation_text += "\n"
    
    prompt = f"""You are helping a user understand their WhatsApp chat{title_info}. 
Answer their question based ONLY on the provided chat context and previous conversation. Be conversational and helpful.

**User Question:** {question}

**Relevant Chat Context:**
{context_text}
{conversation_text}
**Instructions:**
- Answer based only on the provided context and conversation history
- Be conversational and natural
- If the context doesn't contain enough information, say so honestly
- Reference specific people or timeframes when relevant
- Don't make up information not in the context
- Consider the conversation flow and previous questions

**Answer:**"""

    return prompt


def get_or_create_conversation(db: Session, chat_id: str, user_id: str) -> AIConversation:
    """Get existing conversation or create a new one for given chat and user"""
    try:
        conversation = (
            db.query(AIConversation)
            .filter(
                AIConversation.chat_id == chat_id,
                AIConversation.user_id == user_id
            )
            .first()
        )

        if not conversation:
            conversation = AIConversation(
                chat_id=chat_id,
                user_id=user_id
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        return conversation

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while creating conversation: {str(e)}"
        )

def get_conversation_history(db: Session, conversation_id: str, token_limit: int = 3000) -> List[Dict]:
    """Get conversation history within token limit"""
    messages = db.query(AIMessage).filter(
        AIMessage.conversation_id == conversation_id
    ).order_by(AIMessage.created_at.desc()).limit(10).all()  # Get last 10 messages
    
    # Reverse to get chronological order
    messages = messages[::-1]
    
    # Simple token estimation (4 chars ≈ 1 token)
    history = []
    total_tokens = 0
    
    for msg in messages:
        estimated_tokens = len(msg.content) // 4
        if total_tokens + estimated_tokens > token_limit:
            break
        history.append({
            "type": msg.message_type.value,
            "content": msg.content,
            "created_at": msg.created_at
        })
        total_tokens += estimated_tokens
    
    return history


def store_conversation_messages(db: Session, conversation_id: str, question: str, answer: str):
    """Store user question and AI answer in conversation"""
    # Store user message
    user_message = AIMessage(
        conversation_id=conversation_id,
        message_type=MessageType.USER,
        content=question
    )
    
    # Store assistant message
    assistant_message = AIMessage(
        conversation_id=conversation_id,
        message_type=MessageType.ASSISTANT,
        content=answer
    )
    
    db.add(user_message)
    db.add(assistant_message)
    db.commit()


def query_chat_with_rag(
    db: Session,
    chat_id: str,
    question: str,
    user_id: str,
    max_chunks: int = 5
) -> schemas.RAGQueryResponse:
    """Perform RAG query on a chat with conversation context"""
    
    start_time = time.time()
    # Get or create conversation
    conversation = get_or_create_conversation(db, chat_id, user_id)
    
    # Get conversation history
    conversation_history = get_conversation_history(db, str(conversation.id))
    
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
        # Create prompt with context and conversation history
        prompt = create_rag_prompt(question, search_results, chat_title, conversation_history)
        
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
    
    # Store conversation messages BEFORE returning
    store_conversation_messages(db, str(conversation.id), question, answer)
    
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
