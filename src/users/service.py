from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from . import models, schemas
from src.chats.models import Chat
from src.rag.models import AIConversation, AIMessage
import logging
logger = logging.getLogger(__name__)

def store_user_on_login(db: Session, user: schemas.UserStore):
    # Check if the user already exists (excluding deleted users)
    db_user = db.query(models.User).filter(
        models.User.user_id == user.user_id,
        models.User.is_deleted == False
    ).first()

    if db_user:
        # If user exists, we can update any details
        # For now, let's just return the existing user
        return db_user
    else:
        # Check if user was previously deleted
        deleted_user = db.query(models.User).filter(
            models.User.user_id == user.user_id,
            models.User.is_deleted == True
        ).first()
        
        if deleted_user:
            # Reactivate deleted user
            deleted_user.is_deleted = False
            deleted_user.deleted_at = None
            deleted_user.email = user.email  # Update email if changed
            db.commit()
            db.refresh(deleted_user)
            return deleted_user
        
        # Create a new user record
        db_user = models.User(
            user_id=user.user_id,
            email=user.email,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    """Get active user by ID"""
    return db.query(models.User).filter(
        models.User.user_id == user_id,
        models.User.is_deleted == False
    ).first()

def soft_delete_user(db: Session, user_id: str) -> Optional[models.User]:
    """Soft delete user and all related data"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    now = func.now()
    
    # Soft delete user
    user.is_deleted = True
    user.deleted_at = now
    
    # Soft delete all user's chats
    user_chats = db.query(Chat).filter(
        Chat.user_id == user_id,
        Chat.is_deleted == False
    ).all()
    for chat in user_chats:
        chat.is_deleted = True
        chat.deleted_at = now
    
    # Soft delete all user's AI conversations  
    user_conversations = db.query(AIConversation).filter(
        AIConversation.user_id == user_id,
        AIConversation.is_deleted == False
    ).all()
    for conversation in user_conversations:
        conversation.is_deleted = True
        conversation.deleted_at = now
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Soft deleted user {user_id} and related data")
    return user

def hard_delete_user_data(db: Session, user_id: str) -> bool:
    """Permanently delete all user data (for background cleanup)"""
    try:
        # Get deleted user
        deleted_user = db.query(models.User).filter(
            models.User.user_id == user_id,
            models.User.is_deleted == True
        ).first()
        
        if not deleted_user:
            logger.warning(f"No deleted user found for permanent deletion: {user_id}")
            return False
        
        # Delete user (CASCADE will handle all related data)
        db.delete(deleted_user)
        db.commit()
        
        logger.info(f"Permanently deleted user {user_id} and all related data")
        return True
        
    except Exception as e:
        logger.error(f"Failed to permanently delete user {user_id}: {str(e)}")
        db.rollback()
        return False

# def get_all_users(db: Session, include_deleted: bool = False):
#     """Get all users, optionally including deleted ones"""
#     query = db.query(models.User)
#     if not include_deleted:
#         query = query.filter(models.User.is_deleted == False)
#     return query.all()