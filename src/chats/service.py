import os
import json
import uuid
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import whatstk

from . import models
from . import schemas


def create_chat(db: Session, user_id: str):
    new_chat_id = str(uuid.uuid4())
    db_chat = models.Chat(id=new_chat_id, user_id=user_id, status="processing")
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

def get_chat_by_id(db: Session, chat_id: str):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def get_user_chats(db: Session, user_id: str):
    return db.query(models.Chat).filter(models.Chat.user_id == user_id).all()

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

def delete_chat_completely(db: Session, chat_id: str):
    """Delete chat and all related messages"""
    try:
        chat = get_chat_by_id(db, chat_id)
        if chat:
            db.delete(chat)  # Cascade will delete messages
            db.commit()
            return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error deleting chat {chat_id}: {e}")
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
            title = f"Chat with {', '.join(participants)}"
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

def save_messages_to_db(db: Session, chat_id: str, whatstk_chat) -> int:
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

def process_whatsapp_file(chat_id: str, file_path: str, db: Session):
    """Process uploaded WhatsApp file"""
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
        delete_chat_completely(db, chat_id)
        raise Exception(error_message)  # Re-raise so endpoint can handle it
        
    finally:
        # Always clean up the uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            print(f"Warning: Failed to clean up file {file_path}: {cleanup_error}")