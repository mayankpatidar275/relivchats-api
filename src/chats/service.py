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
import logging

import re
from datetime import timedelta
from collections import Counter
import emoji
import pandas as pd
from nltk.corpus import stopwords
import nltk

from src.rag.models import AIConversation, AIMessage, InsightType, CategoryInsightType, Insight
logger = logging.getLogger(__name__)

from . import models

# Download stopwords if not already present
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
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

def create_chat(db: Session, user_id: str, filename: str, category_id: Optional[str] = None):
    """Create a new chat record"""
    new_chat_id = str(uuid.uuid4())
    db_chat = models.Chat(
        id=new_chat_id, 
        user_id=user_id,
        title=filename,  # Use filename as initial title
        category_id=category_id if category_id else None,
        status="processing"
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_chat_by_id(db: Session, chat_id: UUID):
    try:
        return db.query(models.Chat)\
            .options(
                joinedload(models.Chat.category),
                joinedload(models.Chat.insights).joinedload(Insight.insight_type)
            )\
            .filter(models.Chat.id == chat_id)\
            .first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get chat by id failed: {str(e)}")
    
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

# def parse_whatsapp_file(file_path: str) -> tuple:
#     """Parse WhatsApp file and return (whatstk_chat, participants_list, title)"""
#     try:
#         # Handle zip files
#         extracted_path = None
#         if file_path.endswith('.zip'):
#             extracted_path = extract_txt_from_zip(file_path)
#             parse_path = extracted_path
#         else:
#             parse_path = file_path
        
#         # Parse with whatstk
#         chat = whatstk.WhatsAppChat.from_source(parse_path)
        
#         # Extract participants
#         participants = list(chat.df['username'].unique())
#         participants = [p for p in participants if p is not None]  # Remove None values
        
#         # Generate title (you can customize this logic)
#         if len(participants) == 2:
#             # title = f"Chat with {', '.join(participants)}"
#             title = f"{', '.join(participants)}"
#         else:
#             title = f"Group chat ({len(participants)} participants)"
        
#         # Clean up extracted file if it exists
#         if extracted_path and os.path.exists(extracted_path):
#             os.remove(extracted_path)
        
#         return chat, participants, title
        
#     except Exception as e:
#         # Clean up extracted file if it exists
#         if 'extracted_path' in locals() and extracted_path and os.path.exists(extracted_path):
#             os.remove(extracted_path)
#         raise e

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
        whatstk_chat, participants, title, metadata = parse_whatsapp_file(file_path)
        
        # Save messages to database
        message_count = save_messages_to_db(db, chat_id, whatstk_chat)
        
        # Update chat with parsed information
        chat.title = title
        chat.participants = json.dumps(participants)
        chat.chat_metadata = metadata
        chat.status = "completed"
        chat.error_log = None  # Clear any previous errors
        
        db.commit()
        print(f"Successfully processed chat {chat_id}: {message_count} messages saved")
        
        # **NEW: Trigger vector indexing asynchronously**
        # trigger_vector_indexing(db, chat_id)
        
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
                chat.chat_metadata = None
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


# Chat Parsing and Metadata

def get_stopwords() -> set:
    """Get combined English and Hindi stopwords"""
    try:
        english_stopwords = set(stopwords.words('english'))
    except:
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

def compute_chat_metadata(chat: whatstk.WhatsAppChat, participants: List[str]) -> Dict[str, Any]:
    """Compute comprehensive metadata from parsed chat"""
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
        all_links = all_links[:CONFIG['MAX_LINKS_STORED']]
    
    links_shared_count = len(all_links)
    media_shared_count = df['message'].apply(is_media_message).sum()
    
    # Global word and emoji analysis
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
    initiations = detect_conversation_initiations(df, CONFIG['CONVERSATION_GAP_HOURS'])
    
    # Double texting rates
    double_text_rates = calculate_double_texting(df, CONFIG['DOUBLE_TEXT_THRESHOLD'])
    
    # Per-user stats
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
    
    return json.loads(json.dumps(metadata, default=int))  # Forces conversionRetry 

def parse_whatsapp_file(file_path: str) -> Tuple[whatstk.WhatsAppChat, List[str], str, Dict[str, Any]]:
    """Parse WhatsApp file and return (whatstk_chat, participants_list, title, metadata)"""
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
        
        # Generate title
        if len(participants) == 2:
            title = f"{', '.join(participants)}"
        else:
            title = f"Group chat ({len(participants)} participants)"
        
        # Compute metadata
        metadata = compute_chat_metadata(chat, participants)
        
        # Clean up extracted file if it exists
        if extracted_path and os.path.exists(extracted_path):
            os.remove(extracted_path)
        
        return chat, participants, title, metadata
        
    except Exception as e:
        # Clean up extracted file if it exists
        if 'extracted_path' in locals() and extracted_path and os.path.exists(extracted_path):
            os.remove(extracted_path)
        raise e


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