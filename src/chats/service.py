import os
import json
from sqlalchemy import select
from uuid import UUID
import uuid
import zipfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from sqlalchemy.sql import func

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import whatstk
from fastapi import HTTPException, status

import re
from datetime import timedelta
from collections import Counter
import emoji
import pandas as pd
from nltk.corpus import stopwords
import nltk

from src.rag.models import AIConversation, AIMessage, InsightType, CategoryInsightType, Insight
from src.logging_config import get_logger
from src.error_handlers import (
    DatabaseException,
    FileProcessingException,
    ErrorCode
)
from src.monitoring import track_time, track_operation

from . import models

logger = get_logger(__name__)

# Download stopwords if not already present
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    logger.info("Downloading NLTK stopwords")
    nltk.download('stopwords', quiet=True)

# Configuration Constants
CONFIG = {
    'CONVERSATION_GAP_HOURS': 6,
    'TOP_EMOJIS_LIMIT': 30,
    'TOP_WORDS_LIMIT': 50,
    'DOUBLE_TEXT_THRESHOLD': 2,
    'MAX_RESPONSE_TIME_HOURS': 4,
    'MAX_LINKS_STORED': 1000,
    'HINDI_STOPWORDS': ['hai', 'hain', 'ka', 'ki', 'ke', 'ko', 'me', 'mein', 'se', 'ne', 'par', 
                        'aur', 'kya', 'toh', 'bhi', 'tha', 'thi', 'the', 'ho', 'hum', 'tu', 
                        'yeh', 'woh', 'is', 'us', 'ek', 'nahi', 'kyu', 'kyun', 'kaise']
}


# ============================================================================
# CORE CRUD OPERATIONS
# ============================================================================

def create_chat(db: Session, user_id: str, filename: str, category_id: Optional[str] = None):
    """Create a new chat record"""
    
    new_chat_id = str(uuid.uuid4())
    
    logger.debug(
        f"Creating new chat record",
        extra={
            "user_id": user_id,
            "extra_data": {
                "chat_id": new_chat_id,
                "filename": filename,
                "category_id": category_id
            }
        }
    )
    
    try:
        db_chat = models.Chat(
            id=new_chat_id, 
            user_id=user_id,
            title=filename,
            category_id=category_id if category_id else None,
            status="processing"
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        
        logger.info(
            f"Chat record created: {new_chat_id}",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": new_chat_id,
                    "status": "processing"
                }
            }
        )
        
        return db_chat
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Failed to create chat record: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"filename": filename}
            },
            exc_info=True
        )
        raise DatabaseException("Failed to create chat record", original_error=e)


def get_chat_by_id(db: Session, chat_id: UUID):
    """Get chat by ID with all relationships loaded"""
    
    logger.debug(f"Fetching chat by ID: {chat_id}")
    
    try:
        with track_operation("get_chat_by_id", chat_id=str(chat_id)):
            chat = db.query(models.Chat)\
                .options(
                    joinedload(models.Chat.category),
                    joinedload(models.Chat.insights).joinedload(Insight.insight_type),
                    joinedload(models.Chat.messages)
                )\
                .filter(models.Chat.id == chat_id)\
                .first()
        
        if chat:
            logger.debug(
                f"Chat found: {chat_id}",
                extra={
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "status": chat.status,
                        "message_count": len(chat.messages) if chat.messages else 0
                    }
                }
            )
        else:
            logger.debug(f"Chat not found: {chat_id}")
        
        return chat
    
    except SQLAlchemyError as e:
        logger.error(
            f"Database error fetching chat: {e}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        raise DatabaseException("Failed to fetch chat", original_error=e)


def get_user_chats(db: Session, user_id: str):
    """Return completed, non-deleted chats for a user with relationships eager-loaded"""
    
    logger.debug(
        "Fetching user chats",
        extra={"user_id": user_id}
    )
    
    try:
        with track_operation("get_user_chats", user_id=user_id):
            chats = db.query(models.Chat)\
                .options(
                    joinedload(models.Chat.category),
                    joinedload(models.Chat.insights).joinedload(Insight.insight_type),
                    joinedload(models.Chat.messages)
                )\
                .filter(
                    models.Chat.user_id == user_id,
                    models.Chat.is_deleted == False,
                    models.Chat.status == "completed"
                )\
                .all()
        
        logger.debug(
            f"Found {len(chats)} chats for user",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_count": len(chats)}
            }
        )
        
        return chats
    
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to fetch user chats: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseException("Failed to fetch user chats", original_error=e)


def get_chat_messages(db: Session, chat_id: UUID, user_id: str):
    """Get all messages for a chat with authorization check"""
    
    logger.debug(
        "Fetching chat messages",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": str(chat_id)}
        }
    )
    
    try:
        with track_operation("get_chat_messages", chat_id=str(chat_id)):
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
            logger.warning(
                f"No messages found or unauthorized access",
                extra={
                    "user_id": user_id,
                    "extra_data": {"chat_id": str(chat_id)}
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this chat."
            )
        
        logger.debug(
            f"Retrieved {len(messages)} messages",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": str(chat_id),
                    "message_count": len(messages)
                }
            }
        )
        
        return messages
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to fetch chat messages: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat_id)}
            },
            exc_info=True
        )
        raise DatabaseException("Failed to fetch messages", original_error=e)


def update_user_display_name(db: Session, chat_id: str, user_id: str, display_name: str):
    """Update user's display name for a chat"""
    
    logger.debug(
        "Updating display name",
        extra={
            "user_id": user_id,
            "extra_data": {
                "chat_id": chat_id,
                "display_name": display_name
            }
        }
    )
    
    try:
        chat = db.query(models.Chat).filter(
            models.Chat.id == chat_id, 
            models.Chat.user_id == user_id
        ).first()
        
        if chat:
            chat.user_display_name = display_name
            db.commit()
            db.refresh(chat)
            
            logger.info(
                f"Display name updated: {chat_id}",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": chat_id,
                        "display_name": display_name
                    }
                }
            )
        else:
            logger.warning(
                f"Chat not found for display name update: {chat_id}",
                extra={"user_id": user_id}
            )
        
        return chat
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Failed to update display name: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": chat_id}
            },
            exc_info=True
        )
        raise DatabaseException("Failed to update display name", original_error=e)


def delete_chat(db: Session, chat_id: str):
    """Permanently delete chat and all related data (messages, chunks, vectors)"""
    
    logger.info(
        f"Starting permanent chat deletion: {chat_id}",
        extra={"extra_data": {"chat_id": chat_id}}
    )
    
    try:
        chat = get_chat_by_id(db, chat_id)
        if not chat:
            logger.warning(f"Chat not found for deletion: {chat_id}")
            return False
        
        # Store metadata before deletion for logging
        message_count = len(chat.messages) if chat.messages else 0
        
        # Clean up vector data first
        try:
            from ..vector.service import vector_service
            
            with track_operation("cleanup_vector_data", chat_id=chat_id):
                vector_service.cleanup_failed_indexing(db, chat_id)
            
            logger.debug(f"Vector data cleaned up: {chat_id}")
        
        except Exception as e:
            logger.warning(
                f"Failed to cleanup vector data (continuing with deletion): {e}",
                extra={"extra_data": {"chat_id": chat_id}}
            )
        
        # Delete chat (cascade will delete messages and chunks)
        db.delete(chat)
        db.commit()
        
        logger.info(
            f"Chat permanently deleted: {chat_id}",
            extra={
                "extra_data": {
                    "chat_id": chat_id,
                    "message_count": message_count
                }
            }
        )
        
        return True
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Failed to delete chat: {e}",
            extra={"extra_data": {"chat_id": chat_id}},
            exc_info=True
        )
        return False


def soft_delete_chat(db: Session, chat_id: str):
    """Soft delete chat and all related data (messages, chunks, vectors)"""
    
    logger.info(
        f"Starting soft deletion: {chat_id}",
        extra={"extra_data": {"chat_id": chat_id}}
    )
    
    try:
        chat = get_chat_by_id(db, chat_id)
        if not chat:
            logger.warning(f"Chat not found for soft deletion: {chat_id}")
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
        
        conversation_count = len(user_conversations)
        for conversation in user_conversations:
            conversation.is_deleted = True
            conversation.deleted_at = now
        
        db.commit()
        db.refresh(chat)
    
        logger.info(
            f"Chat soft deleted successfully: {chat_id}",
            extra={
                "extra_data": {
                    "chat_id": chat_id,
                    "conversations_soft_deleted": conversation_count
                }
            }
        )
        
        return True

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Failed to soft delete chat: {e}",
            extra={"extra_data": {"chat_id": chat_id}},
            exc_info=True
        )
        return False


def get_chat_ai_conversation(db: Session, chat_id: UUID, user_id: str) -> Optional[AIConversation]:
    """Get AI conversation for a specific chat and user"""
    
    logger.debug(
        "Fetching AI conversation",
        extra={
            "user_id": user_id,
            "extra_data": {"chat_id": str(chat_id)}
        }
    )
    
    try:
        conversation = db.query(AIConversation).options(
            joinedload(AIConversation.messages)
        ).filter(
            AIConversation.chat_id == chat_id,
            AIConversation.user_id == user_id
        ).first()
        
        if conversation:
            logger.debug(
                f"AI conversation found with {len(conversation.messages)} messages",
                extra={
                    "user_id": user_id,
                    "extra_data": {
                        "chat_id": str(chat_id),
                        "message_count": len(conversation.messages)
                    }
                }
            )
        
        return conversation
    
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to fetch AI conversation: {e}",
            extra={
                "user_id": user_id,
                "extra_data": {"chat_id": str(chat_id)}
            },
            exc_info=True
        )
        raise DatabaseException("Failed to fetch AI conversation", original_error=e)


# ============================================================================
# FILE PROCESSING
# ============================================================================

def extract_txt_from_zip(zip_path: str) -> Optional[str]:
    """Extract .txt file from zip and return path to extracted file"""
    
    logger.debug(f"Extracting txt from zip: {zip_path}")
    
    try:
        with track_operation("extract_zip", zip_path=zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find .txt files in the zip
                txt_files = [f for f in zip_ref.namelist() if f.endswith('.txt')]
                
                if not txt_files:
                    logger.error(f"No .txt file found in zip: {zip_path}")
                    raise FileProcessingException(
                        "No .txt file found in zip archive",
                        error_code=ErrorCode.INVALID_FILE_FORMAT
                    )
                
                # Extract the first .txt file
                txt_filename = txt_files[0]
                extract_path = Path(zip_path).parent / f"extracted_{uuid.uuid4().hex}.txt"
                
                with zip_ref.open(txt_filename) as source, open(extract_path, 'wb') as target:
                    target.write(source.read())
                
                logger.debug(f"Extracted txt file to: {extract_path}")
                
                return str(extract_path)
    
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid zip file: {e}", exc_info=True)
        raise FileProcessingException(
            "Invalid zip file format",
            error_code=ErrorCode.INVALID_FILE_FORMAT
        )
    except Exception as e:
        logger.error(f"Failed to extract txt from zip: {e}", exc_info=True)
        raise FileProcessingException(
            f"Failed to extract file: {str(e)}",
            error_code=ErrorCode.CHAT_PROCESSING_FAILED
        )


@track_time("save_messages_to_db")
def save_messages_to_db(db: Session, chat_id: UUID, whatstk_chat) -> int:
    """Save parsed messages to database and return count"""
    
    logger.debug(
        f"Saving messages to database",
        extra={"extra_data": {"chat_id": str(chat_id)}}
    )
    
    try:
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
        with track_operation("bulk_insert_messages", message_count=len(messages)):
            db.bulk_save_objects(messages)
            db.commit()
        
        logger.info(
            f"Saved {len(messages)} messages to database",
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "message_count": len(messages)
                }
            }
        )
        
        return len(messages)
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Failed to save messages: {e}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        raise DatabaseException("Failed to save messages", original_error=e)



# ============================================================================
# WHATSAPP FILE PROCESSING
# ============================================================================

@track_time("process_whatsapp_file")
def process_whatsapp_file(
    chat_id: UUID,
    file_path: str,
    db: Session
) -> models.Chat:
    """
    Process WhatsApp chat file and store in database
    NOTE: Does NOT trigger vector indexing (lazy loading)
    """
    
    chat = None
    error_message = ""
    
    logger.info(
        f"Starting WhatsApp file processing",
        extra={"extra_data": {"chat_id": str(chat_id), "file_path": file_path}}
    )
    
    try:
        # Get the chat record
        chat = get_chat_by_id(db, chat_id)
        if not chat:
            error_message = f"Chat with ID {chat_id} not found"
            logger.error(error_message)
            raise ValueError(error_message)
        
        # Parse the WhatsApp file
        with track_operation("parse_whatsapp_file", chat_id=str(chat_id)):
            whatstk_chat, participants, title, metadata = parse_whatsapp_file(file_path)
        
        logger.info(
            f"File parsed successfully",
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "participant_count": len(participants),
                    "message_count": len(whatstk_chat.df)
                }
            }
        )
        
        # Save messages to database
        message_count = save_messages_to_db(db, chat_id, whatstk_chat)
        
        # Update chat with parsed information
        chat.title = title
        chat.participants = json.dumps(participants)
        chat.is_group_chat = len(participants) > 2
        chat.participant_count = len(participants)
        chat.chat_metadata = metadata
        chat.status = "completed"
        chat.error_log = None  # Clear any previous errors
        
        db.commit()
        db.refresh(chat)
        
        logger.info(
            f"Chat processing completed successfully",
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "message_count": message_count,
                    "participant_count": len(participants),
                    "is_group_chat": chat.is_group_chat,
                    "status": "completed"
                }
            }
        )
        
        return chat
        
    except FileProcessingException:
        # Re-raise our custom exceptions (already logged)
        raise
    
    except Exception as e:
        error_message = f"Failed to process WhatsApp file: {str(e)}"
        
        logger.error(
            error_message,
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "file_path": file_path,
                    "error_type": type(e).__name__
                }
            },
            exc_info=True
        )
        
        # On any error, mark chat as failed and log error
        if chat:
            try:
                chat.error_log = error_message
                chat.status = "failed"
                chat.chat_metadata = None
                db.commit()
                
                logger.info(
                    f"Chat marked as failed: {chat_id}",
                    extra={"extra_data": {"chat_id": str(chat_id)}}
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update chat status: {update_error}",
                    extra={"extra_data": {"chat_id": str(chat_id)}},
                    exc_info=True
                )
        
        # Delete the failed chat completely
        try:
            delete_chat(db, chat_id)
            logger.info(
                f"Failed chat deleted: {chat_id}",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
        except Exception as delete_error:
            logger.error(
                f"Failed to delete failed chat: {delete_error}",
                extra={"extra_data": {"chat_id": str(chat_id)}},
                exc_info=True
            )
        
        # Raise as FileProcessingException for proper error handling
        raise FileProcessingException(
            error_message,
            error_code=ErrorCode.CHAT_PROCESSING_FAILED
        )
   
    finally:
        # Always clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Uploaded file cleaned up: {file_path}")
        except Exception as cleanup_error:
            logger.warning(
                f"Failed to clean up uploaded file: {cleanup_error}",
                extra={"extra_data": {"file_path": file_path}}
            )


@track_time("parse_whatsapp_file")
def parse_whatsapp_file(file_path: str) -> Tuple[whatstk.WhatsAppChat, List[str], str, Dict[str, Any]]:
    """Parse WhatsApp file and return (whatstk_chat, participants_list, title, metadata)"""
    
    logger.debug(f"Parsing WhatsApp file: {file_path}")
    
    extracted_path = None
    
    try:
        # Handle zip files
        if file_path.endswith('.zip'):
            logger.debug("Zip file detected, extracting...")
            extracted_path = extract_txt_from_zip(file_path)
            parse_path = extracted_path
        else:
            parse_path = file_path
        
        # Parse with whatstk
        logger.debug(f"Parsing with whatstk: {parse_path}")
        
        with track_operation("whatstk_parse"):
            try:
                chat = whatstk.WhatsAppChat.from_source(parse_path)
            except Exception as e:
                logger.error(f"whatstk parsing failed: {e}", exc_info=True)
                raise FileProcessingException(
                    f"Failed to parse WhatsApp file. Please ensure it's a valid WhatsApp export: {str(e)}",
                    error_code=ErrorCode.INVALID_FILE_FORMAT
                )
        
        # Extract participants
        participants = list(chat.df['username'].unique())
        participants = [p for p in participants if p is not None]  # Remove None values
        
        if not participants:
            logger.error("No participants found in chat")
            raise FileProcessingException(
                "No participants found in the WhatsApp chat file",
                error_code=ErrorCode.INVALID_FILE_FORMAT
            )
        
        # Generate title
        if len(participants) == 2:
            title = f"{', '.join(participants)}"
        else:
            title = f"Group chat ({len(participants)} participants)"
        
        logger.debug(
            f"Chat parsed: {len(participants)} participants, {len(chat.df)} messages",
            extra={
                "extra_data": {
                    "participant_count": len(participants),
                    "message_count": len(chat.df),
                    "title": title
                }
            }
        )
        
        # Compute metadata
        with track_operation("compute_metadata"):
            metadata = compute_chat_metadata(chat, participants)
        
        logger.debug(f"Metadata computed successfully")
        
        return chat, participants, title, metadata
        
    except FileProcessingException:
        raise
    
    except Exception as e:
        logger.error(
            f"Failed to parse WhatsApp file: {e}",
            extra={"extra_data": {"file_path": file_path}},
            exc_info=True
        )
        raise FileProcessingException(
            f"Failed to parse WhatsApp file: {str(e)}",
            error_code=ErrorCode.CHAT_PROCESSING_FAILED
        )
    
    finally:
        # Clean up extracted file if it exists
        if extracted_path and os.path.exists(extracted_path):
            try:
                os.remove(extracted_path)
                logger.debug(f"Extracted file cleaned up: {extracted_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up extracted file: {e}",
                    extra={"extra_data": {"extracted_path": extracted_path}}
                )


# ============================================================================
# METADATA COMPUTATION HELPERS
# ============================================================================

def get_stopwords() -> set:
    """Get combined English and Hindi stopwords"""
    try:
        english_stopwords = set(stopwords.words('english'))
    except:
        logger.warning("Failed to load English stopwords")
        english_stopwords = set()
    
    hindi_stopwords = set(CONFIG['HINDI_STOPWORDS'])
    return english_stopwords.union(hindi_stopwords)


def extract_emojis(text: str) -> List[str]:
    """Extract all emojis from text"""
    if pd.isna(text):
        return []
    return [c for c in text if c in emoji.EMOJI_DATA]


def extract_links(text: str) -> List[str]:
    """Extract URLs from text"""
    if pd.isna(text):
        return []
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)


def is_deleted_message(text: str) -> bool:
    """Check if message was deleted"""
    if pd.isna(text):
        return False
    pattern = r'(this message was deleted|you deleted this message)'
    return bool(re.search(pattern, str(text).lower()))


def is_media_message(text: str) -> bool:
    """Check if message is media"""
    if pd.isna(text):
        return False
    return '<Media omitted>' in str(text) or '<attached:' in str(text).lower()


def extract_words(text: str, stopwords_set: set) -> List[str]:
    """Extract words from text, filtering stopwords"""
    if pd.isna(text) or is_deleted_message(text) or is_media_message(text):
        return []
    
    # Remove URLs, emojis, and special characters
    text = re.sub(r'http[s]?://\S+', '', text)
    text = ''.join(c for c in text if c not in emoji.EMOJI_DATA)
    
    # Extract words (alphanumeric only)
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter stopwords and short words
    return [w for w in words if w not in stopwords_set and len(w) > 2]


def calculate_response_times(df: pd.DataFrame, user: str, max_hours: float = 4) -> List[float]:
    """Calculate response times for a user (in seconds)"""
    response_times = []
    max_seconds = max_hours * 3600
    
    df_sorted = df.sort_values('date').reset_index(drop=True)
    
    for i in range(1, len(df_sorted)):
        current_msg = df_sorted.iloc[i]
        previous_msg = df_sorted.iloc[i-1]
        
        # Check if current user is responding to different user
        if current_msg['username'] == user and previous_msg['username'] != user:
            time_diff = (current_msg['date'] - previous_msg['date']).total_seconds()
            
            # Only count if within reasonable time window
            if 0 < time_diff < max_seconds:
                response_times.append(time_diff)
    
    return response_times


def detect_conversation_initiations(df: pd.DataFrame, gap_hours: float = 6) -> Dict[str, int]:
    """Count conversation initiations per user"""
    initiations = {user: 0 for user in df['username'].unique() if pd.notna(user)}
    
    df_sorted = df.sort_values('date').reset_index(drop=True)
    gap_threshold = timedelta(hours=gap_hours)
    
    # First message is an initiation
    if len(df_sorted) > 0:
        first_user = df_sorted.iloc[0]['username']
        if pd.notna(first_user):
            initiations[first_user] += 1
    
    for i in range(1, len(df_sorted)):
        current_msg = df_sorted.iloc[i]
        previous_msg = df_sorted.iloc[i-1]
        
        time_gap = current_msg['date'] - previous_msg['date']
        
        if time_gap >= gap_threshold:
            current_user = current_msg['username']
            if pd.notna(current_user):
                initiations[current_user] += 1
    
    return initiations


def calculate_double_texting(df: pd.DataFrame, threshold: int = 2) -> Dict[str, float]:
    """Calculate double texting rate per user"""
    double_text_counts = {user: 0 for user in df['username'].unique() if pd.notna(user)}
    total_sequences = {user: 0 for user in df['username'].unique() if pd.notna(user)}
    
    df_sorted = df.sort_values('date').reset_index(drop=True)
    
    i = 0
    while i < len(df_sorted):
        current_user = df_sorted.iloc[i]['username']
        if pd.isna(current_user):
            i += 1
            continue
        
        # Count consecutive messages from same user
        consecutive_count = 1
        j = i + 1
        while j < len(df_sorted) and df_sorted.iloc[j]['username'] == current_user:
            consecutive_count += 1
            j += 1
        
        total_sequences[current_user] += 1
        if consecutive_count >= threshold:
            double_text_counts[current_user] += 1
        
        i = j
    
    # Calculate percentages
    rates = {}
    for user in double_text_counts:
        if total_sequences[user] > 0:
            rates[user] = (double_text_counts[user] / total_sequences[user]) * 100
        else:
            rates[user] = 0.0
    
    return rates


def get_hourly_distribution(df: pd.DataFrame, user: str = None) -> List[int]:
    """Get message count by hour (0-23)"""
    if user:
        user_df = df[df['username'] == user]
    else:
        user_df = df
    
    hours = user_df['date'].dt.hour
    distribution = [0] * 24
    
    for hour in range(24):
        distribution[hour] = (hours == hour).sum()
    
    return distribution


def get_daily_distribution(df: pd.DataFrame, user: str = None) -> Dict[str, int]:
    """Get message count by day of week"""
    if user:
        user_df = df[df['username'] == user]
    else:
        user_df = df
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts = user_df['date'].dt.dayofweek.value_counts().to_dict()
    
    return {days[i]: day_counts.get(i, 0) for i in range(7)}


# ============================================================================
# COMPREHENSIVE METADATA COMPUTATION
# ============================================================================

@track_time("compute_chat_metadata")
def compute_chat_metadata(chat: whatstk.WhatsAppChat, participants: List[str]) -> Dict[str, Any]:
    """Compute comprehensive metadata from parsed chat"""
    
    logger.debug(
        f"Computing metadata for {len(participants)} participants, {len(chat.df)} messages"
    )
    
    try:
        df = chat.df
        stopwords_set = get_stopwords()
        
        # Global stats
        total_messages = len(df)
        date_range = {
            'start': df['date'].min().isoformat(),
            'end': df['date'].max().isoformat()
        }
        total_days = (df['date'].max() - df['date'].min()).days + 1
        messages_per_day_avg = total_messages / total_days if total_days > 0 else 0
        
        logger.debug(
            f"Basic stats: {total_messages} messages over {total_days} days"
        )
        
        # Deleted messages
        deleted_messages_count = df['message'].apply(is_deleted_message).sum()
        
        # Media and links
        all_links = []
        for idx, row in df.iterrows():
            links = extract_links(row['message'])
            for link in links:
                all_links.append({
                    'url': link,
                    'user': row['username'],
                    'timestamp': row['date'].isoformat()
                })
        
        # Limit links if too many
        if len(all_links) > CONFIG['MAX_LINKS_STORED']:
            logger.debug(
                f"Truncating links from {len(all_links)} to {CONFIG['MAX_LINKS_STORED']}"
            )
            all_links = all_links[:CONFIG['MAX_LINKS_STORED']]
        
        links_shared_count = len(all_links)
        media_shared_count = df['message'].apply(is_media_message).sum()
        
        # Global word and emoji analysis
        logger.debug("Analyzing words and emojis")
        
        all_words = []
        all_emojis = []
        
        for msg in df['message']:
            all_words.extend(extract_words(msg, stopwords_set))
            all_emojis.extend(extract_emojis(msg))
        
        total_words = len(all_words)
        word_counter = Counter(all_words)
        emoji_counter = Counter(all_emojis)
        
        top_words = [{'word': word, 'count': count} 
                     for word, count in word_counter.most_common(CONFIG['TOP_WORDS_LIMIT'])]
        top_emojis = [{'emoji': emoji, 'count': count} 
                      for emoji, count in emoji_counter.most_common(CONFIG['TOP_EMOJIS_LIMIT'])]
        
        # Temporal patterns
        hourly_dist = get_hourly_distribution(df)
        daily_dist = get_daily_distribution(df)
        
        busiest_hour = hourly_dist.index(max(hourly_dist)) if hourly_dist else 0
        busiest_day = max(daily_dist, key=daily_dist.get) if daily_dist else 'Monday'
        
        # Conversation initiations
        logger.debug("Computing conversation patterns")
        initiations = detect_conversation_initiations(df, CONFIG['CONVERSATION_GAP_HOURS'])
        
        # Double texting rates
        double_text_rates = calculate_double_texting(df, CONFIG['DOUBLE_TEXT_THRESHOLD'])
        
        # Per-user stats
        logger.debug(f"Computing per-user stats for {len(participants)} participants")
        
        user_stats = {}
        
        for user in participants:
            if pd.isna(user):
                continue
            
            user_df = df[df['username'] == user]
            
            # Basic counts
            message_count = len(user_df)
            
            # Words
            user_words = []
            for msg in user_df['message']:
                user_words.extend(extract_words(msg, stopwords_set))
            
            word_count = len(user_words)
            avg_words_per_message = word_count / message_count if message_count > 0 else 0
            
            # Character count (excluding deleted/media)
            valid_messages = user_df[
                ~user_df['message'].apply(is_deleted_message) & 
                ~user_df['message'].apply(is_media_message)
            ]
            total_chars = valid_messages['message'].str.len().sum()
            avg_message_length_chars = total_chars / len(valid_messages) if len(valid_messages) > 0 else 0
            
            # Deleted and media
            user_deleted = user_df['message'].apply(is_deleted_message).sum()
            user_media = user_df['message'].apply(is_media_message).sum()
            
            # Links
            user_links = 0
            for msg in user_df['message']:
                user_links += len(extract_links(msg))
            
            # Questions
            questions_asked = user_df['message'].str.contains('?', na=False, regex=False).sum()
            
            # Response times
            response_times = calculate_response_times(df, user, CONFIG['MAX_RESPONSE_TIME_HOURS'])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Top words and emojis for user
            user_word_counter = Counter(user_words)
            user_top_words = [{'word': word, 'count': count} 
                              for word, count in user_word_counter.most_common(CONFIG['TOP_WORDS_LIMIT'])]
            
            user_emojis = []
            for msg in user_df['message']:
                user_emojis.extend(extract_emojis(msg))
            
            user_emoji_counter = Counter(user_emojis)
            user_top_emojis = [{'emoji': emoji, 'count': count} 
                               for emoji, count in user_emoji_counter.most_common(CONFIG['TOP_EMOJIS_LIMIT'])]
            
            # Temporal patterns
            user_hourly = get_hourly_distribution(df, user)
            user_busiest_hour = user_hourly.index(max(user_hourly)) if user_hourly else 0
            
            # Longest message
            longest_msg_idx = valid_messages['message'].str.len().idxmax() if len(valid_messages) > 0 else None
            if longest_msg_idx is not None:
                longest_msg = valid_messages.loc[longest_msg_idx]
                longest_words = len(extract_words(longest_msg['message'], set()))  # Count all words
                longest_message = {
                    'word_count': longest_words,
                    'char_count': len(longest_msg['message']),
                    'timestamp': longest_msg['date'].isoformat()
                }
            else:
                longest_message = {'word_count': 0, 'char_count': 0, 'timestamp': None}
            
            user_stats[user] = {
                'message_count': int(message_count),
                'word_count': int(word_count),
                'avg_words_per_message': round(avg_words_per_message, 2),
                'avg_message_length_chars': round(avg_message_length_chars, 2),
                'deleted_messages': int(user_deleted),
                'media_shared': int(user_media),
                'links_shared': int(user_links),
                'conversation_initiations': int(initiations.get(user, 0)),
                'double_texting_rate': round(double_text_rates.get(user, 0), 2),
                'questions_asked': int(questions_asked),
                'avg_response_time_seconds': round(avg_response_time, 2),
                'top_words': user_top_words,
                'top_emojis': user_top_emojis,
                'busiest_hour': int(user_busiest_hour),
                'hourly_distribution': user_hourly,
                'longest_message': longest_message
            }
        
        # Compile metadata
        metadata = {
            'total_messages': int(total_messages),
            'total_words': int(total_words),
            'date_range': date_range,
            'total_days': int(total_days),
            'messages_per_day_avg': round(messages_per_day_avg, 2),
            'deleted_messages_count': int(deleted_messages_count),
            'media_shared_count': int(media_shared_count),
            'links_shared_count': int(links_shared_count),
            'links': all_links,
            'busiest_hour': int(busiest_hour),
            'busiest_day': busiest_day,
            'hourly_distribution': hourly_dist,
            'daily_distribution': daily_dist,
            'top_words': top_words,
            'top_emojis': top_emojis,
            'user_stats': user_stats
        }
        
        logger.debug(
            "Metadata computation complete",
            extra={
                "extra_data": {
                    "total_messages": total_messages,
                    "total_words": total_words,
                    "participant_count": len(user_stats)
                }
            }
        )
        
        # Forces conversion to ensure all values are JSON serializable
        return json.loads(json.dumps(metadata, default=int))
    
    except Exception as e:
        logger.error(
            f"Failed to compute metadata: {e}",
            extra={
                "extra_data": {
                    "participant_count": len(participants),
                    "message_count": len(chat.df)
                }
            },
            exc_info=True
        )
        raise FileProcessingException(
            f"Failed to compute chat metadata: {str(e)}",
            error_code=ErrorCode.CHAT_PROCESSING_FAILED
        )


# ============================================================================
# INSIGHT RELATED FUNCTIONS
# ============================================================================

def get_chat_insights_with_types(db: Session, chat_id: UUID):
    """Get all insight types for a chat's category with generation status"""
    
    logger.debug(
        "Fetching insight types for chat",
        extra={"extra_data": {"chat_id": str(chat_id)}}
    )
    
    try:
        # Get chat with category
        chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not chat or not chat.category_id:
            logger.debug(f"No category found for chat: {chat_id}")
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
        
        logger.debug(
            f"Found {len(insights)} insight types for chat",
            extra={
                "extra_data": {
                    "chat_id": str(chat_id),
                    "insight_count": len(insights)
                }
            }
        )
        
        return insights
    
    except SQLAlchemyError as e:
        logger.error(
            f"Failed to fetch insight types: {e}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        raise DatabaseException("Failed to fetch insight types", original_error=e)


# ============================================================================
# DEPRECATED FUNCTIONS (KEPT FOR BACKWARD COMPATIBILITY)
# ============================================================================

def trigger_vector_indexing(db: Session, chat_id: UUID):
    """
    DEPRECATED: Trigger vector indexing for a completed chat
    
    This function is deprecated. Vector indexing is now done on-demand
    when insights are unlocked. Kept for backward compatibility.
    """
    logger.warning(
        "DEPRECATED: trigger_vector_indexing called - vector indexing is now on-demand",
        extra={"extra_data": {"chat_id": str(chat_id)}}
    )
    
    try:
        from ..vector.service import vector_service
        
        logger.info(
            f"Starting on-demand vector indexing for chat: {chat_id}",
            extra={"extra_data": {"chat_id": str(chat_id)}}
        )
        
        success = vector_service.create_chat_chunks(db, chat_id)
        
        if success:
            logger.info(
                f"Vector indexing completed for chat: {chat_id}",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
        else:
            logger.error(
                f"Vector indexing failed for chat: {chat_id}",
                extra={"extra_data": {"chat_id": str(chat_id)}}
            )
            
    except Exception as e:
        logger.error(
            f"Error during vector indexing: {e}",
            extra={"extra_data": {"chat_id": str(chat_id)}},
            exc_info=True
        )
        # Delete the chat completely on indexing failure
        delete_chat(db, chat_id)
        raise


# Note: You need to implement extract_txt_from_zip() function
# def extract_txt_from_zip(zip_path: str) -> str:
#     """Extract .txt file from zip archive"""
#     import zipfile
#     import tempfile
    
#     with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#         # Find .txt file in zip
#         txt_files = [f for f in zip_ref.namelist() if f.endswith('.txt')]
#         if not txt_files:
#             raise ValueError("No .txt file found in zip archive")
        
#         # Extract to temp location
#         temp_dir = tempfile.gettempdir()
#         extracted_file = zip_ref.extract(txt_files[0], temp_dir)
        
#         return extracted_file