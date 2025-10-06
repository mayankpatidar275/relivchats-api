import os
import json
from sqlalchemy import select
from uuid import UUID
import uuid
import zipfile
from pathlib import Path
from typing import Optional
from sqlalchemy.sql import func

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import whatstk
from fastapi import HTTPException, status
import logging

from src.rag.models import AIConversation, AIMessage, InsightType, CategoryInsightType, Insight
logger = logging.getLogger(__name__)

from . import models

def create_chat(db: Session, user_id: str, analysis_category_id: str):
    new_chat_id = str(uuid.uuid4())
    db_chat = models.Chat(id=new_chat_id, user_id=user_id, category_id=analysis_category_id, status="processing")
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_chat_by_id(db: Session, chat_id: UUID):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def get_user_chats(db: Session, user_id: str):
    return db.query(models.Chat).filter(models.Chat.user_id == user_id, models.Chat.is_deleted == False, models.Chat.vector_status == "completed", models.Chat.status == "completed", models.Chat.user_display_name != None).all()

def get_chat_messages(db: Session, chat_id: UUID, user_id: str):
    messages = (
        db.query(models.Message)
        .join(models.Chat)
        .filter(
            models.Message.chat_id == chat_id,
            models.Chat.user_id == user_id
        )
        .all()
    )
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this chat."
        )
    return messages

def update_user_display_name(db: Session, chat_id: str, user_id: str, display_name: str):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id, 
        models.Chat.user_id == user_id
    ).first()
    if chat:
        chat.user_display_name = display_name
        db.commit()
        db.refresh(chat)
    return chat

def delete_chat(db: Session, chat_id: str):
    """Delete chat and all related data (messages, chunks, vectors)"""
    try:
        chat = get_chat_by_id(db, chat_id)
        if chat:
            # Import here to avoid circular imports
            from ..vector.service import vector_service
            
            # Clean up vector data first
            try:
                vector_service.cleanup_failed_indexing(db, chat_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup vector data for chat {chat_id}: {e}")
            
            # Delete chat (cascade will delete messages and chunks)
            db.delete(chat)
            db.commit()
            return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error deleting chat {chat_id}: {e}")
    return False

def soft_delete_chat(db: Session, chat_id: str):
    """Soft Delete chat and all related data (messages, chunks, vectors)"""
    try:
        chat = get_chat_by_id(db, chat_id)
        if not chat:
            return None
        
        now = func.now()
    
        # Soft delete chat
        chat.is_deleted = True
        chat.deleted_at = now
    
        # Soft delete all user's AI conversations  
        user_conversations = db.query(AIConversation).filter(
            AIConversation.chat_id == chat_id,
            AIConversation.is_deleted == False
        ).all()
        for conversation in user_conversations:
            conversation.is_deleted = True
            conversation.deleted_at = now
        
        db.commit()
        db.refresh(chat)
    
        logger.info(f"Soft deleted chat {chat_id} and related data")
        return True

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error soft deleting chat {chat_id}: {e}")
    return False

def extract_txt_from_zip(zip_path: str) -> Optional[str]:
    """Extract .txt file from zip and return path to extracted file"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find .txt files in the zip
            txt_files = [f for f in zip_ref.namelist() if f.endswith('.txt')]
            if not txt_files:
                raise ValueError("No .txt file found in zip archive")
            
            # Extract the first .txt file
            txt_filename = txt_files[0]
            extract_path = Path(zip_path).parent / f"extracted_{uuid.uuid4().hex}.txt"
            
            with zip_ref.open(txt_filename) as source, open(extract_path, 'wb') as target:
                target.write(source.read())
            
            return str(extract_path)
    except Exception as e:
        raise ValueError(f"Failed to extract txt from zip: {e}")

def parse_whatsapp_file(file_path: str) -> tuple:
    """Parse WhatsApp file and return (whatstk_chat, participants_list, title)"""
    try:
        # Handle zip files
        extracted_path = None
        if file_path.endswith('.zip'):
            extracted_path = extract_txt_from_zip(file_path)
            parse_path = extracted_path
        else:
            parse_path = file_path
        
        # Parse with whatstk
        chat = whatstk.WhatsAppChat.from_source(parse_path)
        
        # Extract participants
        participants = list(chat.df['username'].unique())
        participants = [p for p in participants if p is not None]  # Remove None values
        
        # Generate title (you can customize this logic)
        if len(participants) == 2:
            # title = f"Chat with {', '.join(participants)}"
            title = f"{', '.join(participants)}"
        else:
            title = f"Group chat ({len(participants)} participants)"
        
        # Clean up extracted file if it exists
        if extracted_path and os.path.exists(extracted_path):
            os.remove(extracted_path)
        
        return chat, participants, title
        
    except Exception as e:
        # Clean up extracted file if it exists
        if 'extracted_path' in locals() and extracted_path and os.path.exists(extracted_path):
            os.remove(extracted_path)
        raise e

def save_messages_to_db(db: Session, chat_id: UUID, whatstk_chat) -> int:
    """Save parsed messages to database and return count"""
    messages = []
    
    for _, row in whatstk_chat.df.iterrows():
        message = models.Message(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            sender=row['username'],
            content=row['message'],
            timestamp=row['date']
        )
        messages.append(message)
    
    # Bulk insert
    db.bulk_save_objects(messages)
    db.commit()
    
    return len(messages)

def process_whatsapp_file(chat_id: UUID, file_path: str, db: Session):
    """Process WhatsApp file synchronously and trigger vector indexing"""
    chat = None
    error_message = ""
    
    try:
        # Get the chat record
        chat = get_chat_by_id(db, chat_id)
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found")
        
        # Parse the WhatsApp file
        whatstk_chat, participants, title = parse_whatsapp_file(file_path)
        
        # Save messages to database
        message_count = save_messages_to_db(db, chat_id, whatstk_chat)
        
        # Update chat with parsed information
        chat.title = title
        chat.participants = json.dumps(participants)
        chat.status = "completed"
        chat.error_log = None  # Clear any previous errors
        
        db.commit()
        print(f"Successfully processed chat {chat_id}: {message_count} messages saved")
        
        # **NEW: Trigger vector indexing asynchronously**
        trigger_vector_indexing(db, chat_id)
        
        return chat
        
    except Exception as e:
        error_message = f"Failed to process WhatsApp file: {str(e)}"
        print(f"Error processing chat {chat_id}: {error_message}")
        
        # On any error, delete the chat completely
        if chat:
            # Log the error first
            try:
                chat.error_log = error_message
                chat.status = "failed"
                db.commit()
            except:
                pass  # If we can't even save the error, we'll just delete
        
        # Delete the chat completely
        delete_chat(db, chat_id)
        raise Exception(error_message)  # Re-raise so endpoint can handle it
   
    finally:
        # Always clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            print(f"Warning: Failed to clean up file {file_path}: {cleanup_error}")
            
def trigger_vector_indexing(db: Session, chat_id: UUID):
    """Trigger vector indexing for a completed chat"""
    try:
        # Import here to avoid circular imports
        from ..vector.service import vector_service
        
        print(f"Starting vector indexing for chat {chat_id}")
        success = vector_service.create_chat_chunks(db, chat_id)
        
        if success:
            print(f"Vector indexing completed successfully for chat {chat_id}")
        else:
            print(f"Vector indexing failed for chat {chat_id}")
            
    except Exception as e:
        print(f"Error triggering vector indexing for chat {chat_id}: {e}")
        # TODO
        # Don't raise the error - chat parsing was successful
        # Vector indexing can be retried later
                # Delete the chat completely
        delete_chat(db, chat_id)

def get_chat_ai_conversation(db: Session, chat_id: UUID, user_id: str) -> Optional[AIConversation]:
    """Get AI conversation for a specific chat and user"""
    conversation = db.query(AIConversation).options(
        joinedload(AIConversation.messages)
    ).filter(
        AIConversation.chat_id == chat_id,
        AIConversation.user_id == user_id
    ).first()
    
    return conversation

def get_chat_insights_with_types(db: Session, chat_id: UUID):
    """Get all insight types for a chat's category with generation status"""
    # Get chat with category
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat or not chat.category_id:
        return []
    
    # Get insight types for this category
    stmt = (
        select(InsightType, Insight)
        .join(CategoryInsightType, CategoryInsightType.insight_type_id == InsightType.id)
        .outerjoin(
            Insight,
            (Insight.insight_type_id == InsightType.id) & (Insight.chat_id == chat_id)
        )
        .where(CategoryInsightType.category_id == chat.category_id)
        .where(InsightType.is_active == True)
        .order_by(CategoryInsightType.display_order)
    )
    
    results = db.execute(stmt).all()
    
    # Format response
    insights = []
    for insight_type, insight in results:
        insights.append({
            "insight_type": insight_type,
            "status": insight.status if insight else "pending",
            "insight_id": insight.id if insight else None,
            "has_content": bool(insight and insight.content)
        })
    
    return insights
