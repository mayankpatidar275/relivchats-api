from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.session import get_db
from app.models.chat import AIChatConversation, AIMessage, Message, Chat
from app.schemas.ai import AIChatRequest, AIMessageResponse, AIChatConversationResponse
from app.services.qdrant_service import qdrant_service
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Placeholder for LLM interaction.
# In a real scenario, you'd use a library like google-generativeai or OpenAI client.
async def call_llm(prompt_messages: List[Dict[str, str]]) -> str:
    """
    Simulates a call to a Large Language Model (LLM).
    In a real application, this would integrate with Gemini API or similar.
    """
    # This is a very basic mock LLM response based on the last user message.
    # In a real setup, you'd send `prompt_messages` to the LLM.
    user_prompt = prompt_messages[-1]['content'].lower() # Get the last user message

    if "good mornings" in user_prompt:
        return "You both shared many 'good mornings'! It seems like a common and cheerful way you greeted each other."
    elif "love" in user_prompt:
        return "Ah, the topic of love. This chat clearly holds moments of deep affection and connection."
    elif "memories" in user_prompt or "nostalgia" in user_prompt:
        return "Reflecting on your memories can be a powerful experience. I'm here to help you explore them further."
    elif "breakup" in user_prompt or "end of relationship" in user_prompt:
        return "Navigating the end of a relationship is challenging. I'm here to provide a safe space for reflection and understanding."
    else:
        return f"That's an insightful question about your chat. Based on the history, I'm finding relevant information on '{user_prompt}'."

class AIService:
    async def create_conversation(
        self, db: AsyncSession, chat_id: int, user_id: str, title: str
    ) -> AIChatConversation:
        """Creates a new AI chat conversation thread."""
        new_conversation = AIChatConversation(
            chat_id=chat_id,
            user_id=user_id,
            title=title
        )
        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)
        return new_conversation

    async def get_conversations(self, db: AsyncSession, chat_id: int, user_id: str) -> List[AIChatConversation]:
        """Retrieves all AI conversations for a specific chat and user."""
        # Ensure user owns the parent chat
        chat_check = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        if not chat_check.scalar_one_or_none():
            raise ValueError("Chat not found or you do not have access to it.")

        result = await db.execute(
            select(AIChatConversation)
            .where(and_(AIChatConversation.chat_id == chat_id, AIChatConversation.user_id == user_id))
            .order_by(AIChatConversation.created_at.desc())
        )
        return result.scalars().all()

    async def get_messages_in_conversation(self, db: AsyncSession, conversation_id: int, user_id: str) -> List[AIMessageResponse]:
        """Retrieves all AI messages within a specific conversation, ensuring user ownership."""
        # First, verify conversation belongs to user
        conversation_check = await db.execute(
            select(AIChatConversation).where(and_(AIChatConversation.id == conversation_id, AIChatConversation.user_id == user_id))
        )
        conversation = conversation_check.scalar_one_or_none()
        if not conversation:
            raise ValueError("Conversation not found or you do not have access.")

        result = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at)
        )
        messages = result.scalars().all()
        return [AIMessageResponse.model_validate(msg) for msg in messages]

    async def ask_ai(
        self, db: AsyncSession, chat_id: int, user_id: str, ai_request: AIChatRequest
    ) -> AIMessageResponse:
        """
        Processes a user's AI query, fetches relevant context, calls LLM, and saves conversation.
        """
        # Ensure the user owns the parent chat first
        chat_check = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        chat = chat_check.scalar_one_or_none()
        if not chat:
            raise ValueError("Chat not found or you do not have access to it.")

        conversation: Optional[AIChatConversation] = None
        if ai_request.conversation_id:
            # Continue existing conversation
            conv_check = await db.execute(
                select(AIChatConversation).where(and_(
                    AIChatConversation.id == ai_request.conversation_id,
                    AIChatConversation.chat_id == chat_id,
                    AIChatConversation.user_id == user_id
                ))
            )
            conversation = conv_check.scalar_one_or_none()
            if not conversation:
                raise ValueError("Conversation not found or does not belong to this chat/user.")
        else:
            # Create a new conversation thread for the AI query
            conversation = await self.create_conversation(
                db, chat_id, user_id, title=f"AI Chat for '{chat.name}'" # Use chat name for title
            )
        
        if not conversation:
            raise ValueError("Failed to establish AI conversation.")

        # Save user's message
        user_ai_message = AIMessage(
            conversation_id=conversation.id,
            sender='user',
            text=ai_request.prompt
        )
        db.add(user_ai_message)
        await db.flush() # Flush to get message ID for context if needed immediately

        # --- Context Retrieval (RAG - Retrieval Augmented Generation) ---
        # 1. Fetch relevant chat messages using Qdrant (semantic search)
        relevant_chat_messages = []
        try:
            qdrant_results = qdrant_service.search_messages(ai_request.prompt, chat_id, limit=20)
            if qdrant_results:
                # Extract message_ids from Qdrant results. Qdrant payload already contains the message_text and other details.
                # No need to fetch from PostgreSQL again if Qdrant payload is sufficient.
                # However, for full context and consistent object structure, fetching from DB is safer.
                message_ids_from_qdrant = [res['message_id'] for res in qdrant_results]
                db_messages_result = await db.execute(
                    select(Message).where(and_(Message.chat_id == chat_id, Message.id.in_(message_ids_from_qdrant)))
                )
                # Sort them by date for better context flow to the LLM
                relevant_chat_messages = sorted(db_messages_result.scalars().all(), key=lambda msg: msg.date)
        except Exception as e:
            logger.error(f"Error during Qdrant search for chat {chat_id}: {e}", exc_info=True)
            # Continue without Qdrant context if it fails

        # 2. Fetch recent AI conversation history for context
        ai_history_query = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id)
            .order_by(AIMessage.created_at.desc()) # Get most recent first
            .limit(10) # Limit history to keep prompt short for LLM context window
        )
        ai_history_messages = ai_history_query.scalars().all()
        ai_history_messages.reverse() # Oldest first for chronological order in prompt

        # Construct prompt for LLM
        prompt_messages = []
        # System message to guide the LLM's persona and objective
        prompt_messages.append({
            "role": "system",
            "content": (
                f"You are Reliv, an empathetic and emotionally intelligent AI assistant. "
                f"Your goal is to provide calm, private, and insightful answers about WhatsApp chat history. "
                f"The chat is between participants {chat.participants} and the user identifies as '{chat.me_identifier}'. "
                f"Focus on emotional nuances, relationship trends, and key milestones. "
                f"Keep your responses soft, supportive, and reflective. Avoid being overly analytical unless explicitly asked. "
                f"Refer to the provided chat context for factual accuracy."
            )
        })
        
        # Add relevant chat message context
        if relevant_chat_messages:
            chat_context_str = "\n".join([
                f"{msg.author} ({msg.date.strftime('%Y-%m-%d %H:%M')}): {msg.message_text}"
                for msg in relevant_chat_messages
            ])
            prompt_messages.append({
                "role": "system",
                "content": "Here is some relevant context from the chat history:\n" + chat_context_str
            })
        
        # Add AI conversation history (for multi-turn conversations)
        for msg in ai_history_messages:
            prompt_messages.append({"role": msg.sender, "content": msg.text})

        # Add current user prompt
        prompt_messages.append({"role": "user", "content": ai_request.prompt})

        # Call LLM
        ai_response_text = await call_llm(prompt_messages) # Your actual LLM integration here

        # Save AI's response
        ai_response_message = AIMessage(
            conversation_id=conversation.id,
            sender='ai',
            text=ai_response_text,
            model_response_metadata={"model": "gemini-2.5-flash-preview-05-20"} # Example metadata
        )
        db.add(ai_response_message)
        
        # Update conversation's last updated time
        conversation.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(ai_response_message)

        return AIMessageResponse.model_validate(ai_response_message)

    async def get_chat_summary_insights(self, db: AsyncSession, chat_id: int, user_id: str) -> List[InsightResponse]:
        """
        Placeholder for generating/retrieving specific insights like 'good mornings' count.
        These would ideally be pre-computed and stored in the `insights` table.
        For demonstration, we'll fetch existing insights.
        """
        # Ensure the user owns the parent chat
        chat_check = await db.execute(
            select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == user_id))
        )
        if not chat_check.scalar_one_or_none():
            raise ValueError("Chat not found or you do not have access to it.")

        # In a real scenario, if an insight type doesn't exist, you'd trigger its computation.
        # For now, just fetch what's available.
        result = await db.execute(
            select(Insight)
            .where(Insight.chat_id == chat_id)
            .order_by(Insight.generated_at.desc())
        )
        insights = result.scalars().all()
        return [InsightResponse.model_validate(insight) for insight in insights]

ai_service = AIService()