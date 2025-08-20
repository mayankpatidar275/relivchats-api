from sqlalchemy.orm import Session
from .. import models
from . import schemas
import uuid

def create_chat(db: Session, user_id: str):
    new_chat_id = str(uuid.uuid4())
    db_chat = models.Chat(id=new_chat_id, user_id=user_id, status="processing")
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat
    
def get_chat_by_id(db: Session, chat_id: str):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def process_whatsapp_file_background(chat_id: str, file_path: str, db: Session):
    # This is a placeholder for the parsing logic.
    # We will implement this after getting the file upload working.
    #
    # Example:
    # try:
    #     parsed_messages = parse_whatsapp_chat(file_path)
    #     chat = get_chat_by_id(db, chat_id)
    #     if chat:
    #         chat.status = "completed"
    #         # Save parsed messages to the database
    #         db.commit()
    # except Exception as e:
    #     chat = get_chat_by_id(db, chat_id)
    #     if chat:
    #         chat.status = "failed"
    #         db.commit()
    # finally:
    #     # Clean up the file
    #     os.remove(file_path)
    pass