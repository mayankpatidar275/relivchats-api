import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..chats.service import _get_chat_by_id_sync
from ..config import settings
from ..vector.service import vector_service
from . import schemas
from .models import (
    AIConversation,
    AIMessage,
    Insight,
    InsightStatus,
    InsightType,
    MessageType,
)

logger = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_time_span(minutes: int) -> str:
    """Convert minutes to human readable format"""
    if minutes < 60:
        return f"{minutes} minutes"
    elif minutes < 1440:  # Less than 24 hours
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m" if remaining_minutes else f"{hours} hours"
    else:
        days = minutes // 1440
        remaining_hours = (minutes % 1440) // 60
        return f"{days}d {remaining_hours}h" if remaining_hours else f"{days} days"

def extract_required_metadata(
    chat_metadata: Dict[str, Any],
    required_fields: Optional[List[str]]
) -> Dict[str, Any]:
    """Extract only required metadata fields from chat metadata"""
    if not required_fields:
        # If no specific fields required, return essential stats only
        return {
            "total_messages": chat_metadata.get("total_messages"),
            "total_days": chat_metadata.get("total_days"),
            "messages_per_day_avg": chat_metadata.get("messages_per_day_avg"),
            "user_stats": chat_metadata.get("user_stats", {})
        }
    
    extracted = {}
    for field in required_fields:
        if field in chat_metadata:
            extracted[field] = chat_metadata[field]
    
    return extracted

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

# ============================================================================
# RAG & PROMPT BUILDING
# ============================================================================

def fetch_rag_chunks(
    db: Session,
    chat_id: UUID,
    rag_query_keywords: str,
    max_chunks: int = 50
) -> List[schemas.RAGChunk]:
    """Fetch relevant chunks from vector DB"""
    
    search_results = vector_service.search_chat(
        db=db,
        chat_id=str(chat_id),
        query=rag_query_keywords,
        limit=max_chunks
    )
    
    chunks = []
    for result in search_results:
        metadata = result["metadata"]
        time_span_minutes = metadata.get("time_span_minutes", 0)
        
        chunk = schemas.RAGChunk(
            content=result["content"],
            speakers=metadata.get("speakers", []),
            message_count=metadata.get("message_count", 0),
            time_span=format_time_span(time_span_minutes),
            similarity_score=result["similarity_score"],
            metadata=metadata
        )
        chunks.append(chunk)
    
    return chunks

def build_insight_prompt(
    prompt_template: str,
    context: schemas.InsightPromptContext
) -> str:
    """Build final prompt by injecting metadata and RAG chunks into template"""
    
    # Check if we have enough data
    if len(context.rag_chunks) < 2:
        return f"""
        **IMPORTANT**: Very limited data available ({len(context.rag_chunks)} conversation excerpts).
        Provide insights based on what's available, but note limitations clearly.
        Use phrases like "Based on limited data..." and "More conversation history needed for complete analysis..."
        """
    
    # Format RAG chunks as text
    chunks_text = "\n\n".join([
        f"--- Message Chunk {i+1} (Index: {i}) ---\n"
        f"Speakers: {', '.join(chunk.speakers)}\n"
        f"Time Span: {chunk.time_span}\n"
        f"Message Count: {chunk.message_count}\n\n"
        f"{chunk.content}"  # This now has timestamps from new chunking
        for i, chunk in enumerate(context.rag_chunks)
    ])
    
    # Format metadata as readable text
    metadata_text = json.dumps(context.chat_metadata, indent=2)
    
    # Inject context into template
    # Template can use placeholders: {user_name}, {partner_name}, {metadata}, {chunks}
    participants = list(context.chat_metadata.get("user_stats", {}).keys())
    participant_list = ", ".join(participants)

    final_prompt = prompt_template.format(
        participant_count=len(participants),
        participant_list=participant_list,
        chat_title=context.chat_title or "this chat",
        metadata=metadata_text,
        chunks=chunks_text,
        total_chunks=len(context.rag_chunks),
        total_messages=context.chat_metadata.get("total_messages"),
        total_days=context.chat_metadata.get("total_days"),
    )
    
    return final_prompt

# ============================================================================
# GEMINI INTERACTION
# ============================================================================

def call_gemini_structured(
    prompt: str,
    response_schema: Dict[str, Any],
    temperature: float = 0.7
) -> tuple[Dict[str, Any], int]:
    """
    Call Gemini with structured output mode
    Returns: (parsed_json, tokens_used)
    """
    
    try:
        # Initialize client (configure API key in settings)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Prepare generation config
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema, 
            automatic_function_calling={"disable": True}
        )
        
        # Generate content
        response = client.models.generate_content(
            model=settings.GEMINI_LLM_MODEL,  # e.g., "gemini-2.0-flash-exp"
            contents=prompt,
            config=generation_config
        )
        
        # Parse JSON response
        result = json.loads(response.text)
        
        # Get token usage if available
        tokens_used = None
        if hasattr(response, 'usage_metadata'):
            tokens_used = (
                response.usage_metadata.prompt_token_count + 
                response.usage_metadata.candidates_token_count
            )
        
        return result, tokens_used
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")

# ============================================================================
# INSIGHT RETRIEVAL & REGENERATION
# ============================================================================

def get_insight(
    db: Session,
    chat_id: UUID,
    insight_type_id: UUID
) -> Optional[Insight]:
    """Get existing insight if it exists"""
    return db.query(Insight).filter(
        Insight.chat_id == chat_id,
        Insight.insight_type_id == insight_type_id
    ).first()

def get_chat_insights_summary(
    db: Session,
    chat_id: UUID,
    category_id: UUID
) -> schemas.ChatInsightsSummary:
    """Get summary of all insights for a chat"""
    
    # Get all available insight types for this category
    # (You'll need to implement category-insight relationship query)
    # For now, just get all active insights
    available_types = db.query(InsightType).filter(
        InsightType.is_active == True
    ).all()
    
    # Get generated insights
    generated = db.query(Insight).filter(
        Insight.chat_id == chat_id
    ).all()
    
    # Calculate stats
    completed = sum(1 for i in generated if i.status == InsightStatus.COMPLETED)
    failed = sum(1 for i in generated if i.status == InsightStatus.FAILED)
    generating = sum(1 for i in generated if i.status == InsightStatus.GENERATING)
    
    return schemas.ChatInsightsSummary(
        chat_id=chat_id,
        total_insights=len(generated),
        completed_insights=completed,
        failed_insights=failed,
        generating_insights=generating,
        available_insight_types=[
            schemas.InsightTypeResponse.from_orm(it) for it in available_types
        ],
        generated_insights=[
            create_insight_response(db, insight) for insight in generated
        ]
    )

def create_insight_response(db: Session, insight: Insight) -> schemas.InsightResponse:
    """Convert Insight model to response schema"""
    
    # Add this line to ensure relationship is loaded:
    db.refresh(insight)  # <-- ADD THIS LINE

    insight_type = insight.insight_type
    
    generation_metadata = None
    if insight.status == InsightStatus.COMPLETED:
        generation_metadata = schemas.InsightGenerationMetadata(
            rag_chunks_used=insight.rag_chunks_used or 0,
            tokens_used=insight.tokens_used,
            generation_time_ms=insight.generation_time_ms or 0,
            model_used=settings.GEMINI_LLM_MODEL
        )
    
    return schemas.InsightResponse(
        id=insight.id,
        chat_id=insight.chat_id,
        insight_type_id=insight.insight_type_id,
        insight_type_name=insight_type.name,
        display_title=insight_type.display_title,
        description=insight_type.description,
        icon=insight_type.icon,
        is_premium=insight_type.is_premium if insight_type else False,
        content=insight.content,
        status=insight.status,
        error_message=insight.error_message,
        generation_metadata=generation_metadata,
        # confidence_score= None,
        tokens_used=insight.tokens_used,
        generation_time_ms=insight.generation_time_ms,
        created_at=insight.created_at,
        updated_at=insight.updated_at
    )

def generate_insight_with_context(
    db: Session,
    chat_id: UUID,
    insight_type_id: UUID,
    shared_context: Optional[Dict[str, List]] = None
) -> Insight:
    """
    Generate insight using pre-extracted shared RAG context
    This is called by Celery tasks with cached context
    
    Key difference from generate_insight():
    - Does NOT query Qdrant (uses provided context)
    - Faster and more efficient
    """
    
    start_time = time.time()
    
    # 1. Get insight type configuration
    insight_type = db.query(InsightType).filter(
        InsightType.id == insight_type_id
    ).first()
    
    if not insight_type:
        raise ValueError(f"Insight type {insight_type_id} not found")
    
    if not insight_type.is_active:
        raise ValueError(f"Insight type {insight_type.name} is not active")
    
    # 2. Get chat and metadata
    chat = _get_chat_by_id_sync(db, chat_id)
    if not chat:
        raise ValueError(f"Chat {chat_id} not found")
    
    if not chat.chat_metadata:
        raise ValueError(f"Chat {chat_id} has no metadata. Process chat first.")
    
    # After fetching insight_type and chat:
    if chat.is_group_chat and not insight_type.supports_group_chats:
        raise ValueError(f"Insight '{insight_type.display_title}' doesn't support group chats")

    if insight_type.max_participants and chat.participant_count > insight_type.max_participants:
        raise ValueError(f"This insight supports max {insight_type.max_participants} participants")
    
    # 3. Get or create insight record
    insight = db.query(Insight).filter_by(
        chat_id=chat_id,
        insight_type_id=insight_type_id
    ).first()
    
    if insight:
        insight.status = InsightStatus.GENERATING
        insight.error_message = None
        insight.updated_at = datetime.now(timezone.utc)
    else:
        insight = Insight(
            chat_id=chat_id,
            insight_type_id=insight_type_id,
            status=InsightStatus.GENERATING
        )
        db.add(insight)
    
    db.commit()
    db.refresh(insight)
    
    try:
        # 4. Handle shared context (FIXED)
        rag_chunks = []
        context_key = f"insight_{insight_type_id}"
        
        if shared_context is not None:
            # Use shared context if available
            rag_chunks = shared_context.get(context_key, [])
            logger.info(f"Using shared context for {context_key}: {len(rag_chunks)} chunks")
            
            # Convert dict chunks back to RAGChunk objects if needed
            if rag_chunks and isinstance(rag_chunks[0], dict):
                rag_chunks = [schemas.RAGChunk(**chunk) for chunk in rag_chunks]
        else:
            logger.warning(f"No shared context provided for {context_key}")
        
        # Fallback: If no pre-cached chunks, fetch them from Qdrant
        if not rag_chunks:
            logger.info(f"Fetching fresh chunks from Qdrant for {context_key}")
            rag_chunks = fetch_rag_chunks(
                db=db,
                chat_id=chat_id,
                rag_query_keywords=insight_type.rag_query_keywords,
                max_chunks=50
            )
        
        if not rag_chunks:
            raise ValueError("No relevant message chunks found for this insight")
        
        logger.info(f"Using {len(rag_chunks)} RAG chunks for insight generation")
        
        
        # 5. Extract required metadata
        filtered_metadata = extract_required_metadata(
            chat_metadata=chat.chat_metadata,
            required_fields=insight_type.required_metadata_fields
        )
        # 6. Build prompt context
        prompt_context = schemas.InsightPromptContext(
            user_display_name=chat.user_display_name or "User",
            partner_name=chat.partner_name,
            chat_metadata=filtered_metadata,
            rag_chunks=rag_chunks,
            chat_title=chat.title
        )
        # 7. Build final prompt
        final_prompt = build_insight_prompt(
            prompt_template=insight_type.prompt_template,
            context=prompt_context
        )
        
        # 8. Call Gemini with structured output
        structured_content, tokens_used = call_gemini_structured(
            prompt=final_prompt,
            response_schema=insight_type.response_schema,
            temperature=0.7
        )
        
        # 9. Update insight with results
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        insight.content = structured_content
        insight.status = InsightStatus.COMPLETED
        insight.tokens_used = tokens_used
        insight.generation_time_ms = generation_time_ms
        insight.rag_chunks_used = len(rag_chunks)
        insight.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(insight)
        
        return insight
        
    except Exception as e:
        # Mark as failed
        insight.status = InsightStatus.FAILED
        insight.error_message = str(e)[:500]
        insight.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise









# Not used for now

# ============================================================================
# MAIN INSIGHT GENERATION
# ============================================================================

def generate_insight(
    db: Session,
    chat_id: UUID,
    insight_type_id: UUID
) -> Insight:
    """
    Generate a new insight using RAG + Gemini structured output
    
    Flow:
    1. Load InsightType config from DB
    2. Get chat metadata and partner info
    3. Fetch relevant chunks via RAG
    4. Build prompt with injected context
    5. Call Gemini with response schema
    6. Store structured result
    """
    
    start_time = time.time()
    
    # 1. Get insight type configuration
    insight_type = db.query(InsightType).filter(
        InsightType.id == insight_type_id
    ).first()
    
    if not insight_type:
        raise ValueError(f"Insight type {insight_type_id} not found")
    
    if not insight_type.is_active:
        raise ValueError(f"Insight type {insight_type.name} is not active")
    
    # 2. Get chat and metadata
    chat = _get_chat_by_id_sync(db, chat_id)
    if not chat:
        raise ValueError(f"Chat {chat_id} not found")
    
    if not chat.chat_metadata:
        raise ValueError(f"Chat {chat_id} has no metadata. Process chat first.")
    
    # 3. Create or update insight record
    insight = db.query(Insight).filter_by(
        chat_id=chat_id,
        insight_type_id=insight_type_id
    ).first()
    
    if insight:
        insight.status = InsightStatus.GENERATING
        insight.error_message = None
        insight.updated_at = datetime.now(timezone.utc)
    else:
        insight = Insight(
            chat_id=chat_id,
            insight_type_id=insight_type_id,
            status=InsightStatus.GENERATING
        )
        db.add(insight)
    
    db.commit()
    db.refresh(insight)
    
    try:
        # 4. Fetch RAG chunks
        rag_chunks = fetch_rag_chunks(
            db=db,
            chat_id=chat_id,
            rag_query_keywords=insight_type.rag_query_keywords,
            max_chunks=50
        )
        
        if not rag_chunks:
            raise ValueError("No relevant message chunks found for this insight")
        
        # 5. Extract required metadata
        filtered_metadata = extract_required_metadata(
            chat_metadata=chat.chat_metadata,
            required_fields=insight_type.required_metadata_fields
        )
        
        # 6. Build prompt context
        prompt_context = schemas.InsightPromptContext(
            user_display_name=chat.user_display_name or "User",
            partner_name=chat.partner_name,
            chat_metadata=filtered_metadata,
            rag_chunks=rag_chunks,
            chat_title=chat.title
        )
        
        # 7. Build final prompt
        final_prompt = build_insight_prompt(
            prompt_template=insight_type.prompt_template,
            context=prompt_context
        )
        
        # 8. Call Gemini with structured output
        structured_content, tokens_used = call_gemini_structured(
            prompt=final_prompt,
            response_schema=insight_type.response_schema,
            temperature=0.7
        )
        
        # 9. Update insight with results
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        insight.content = structured_content
        insight.status = InsightStatus.COMPLETED
        insight.tokens_used = tokens_used
        insight.generation_time_ms = generation_time_ms
        insight.rag_chunks_used = len(rag_chunks)
        insight.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(insight)
        
        return insight
        
    except Exception as e:
        # Mark as failed
        insight.status = InsightStatus.FAILED
        insight.error_message = str(e)[:500]  # Limit error message length
        insight.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise

def regenerate_insight(
    db: Session,
    insight_id: UUID
) -> Insight:
    """Retry generating a failed insight"""
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    
    if not insight:
        raise ValueError(f"Insight {insight_id} not found")
    
    # Simply call generate_insight again
    return generate_insight(
        db=db,
        chat_id=insight.chat_id,
        insight_type_id=insight.insight_type_id
    )


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
    chat = _get_chat_by_id_sync(db, chat_id)
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
        created_at=datetime.now(timezone.utc)
    )
