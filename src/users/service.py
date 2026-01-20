# src/users/service.py
"""
User service with production-grade error handling and async support

Key improvements:
- Async variants for all operations
- Comprehensive error handling
- Business event logging
- GDPR compliance helpers
- Proper cleanup on deletion
"""

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Optional
import httpx

from . import models, schemas
from ..chats.models import Chat
from ..rag.models import AIConversation
# from ..vector.models import MessageChunk
from ..config import settings
from ..logging_config import get_logger, log_business_event
from ..error_handlers import (
    NotFoundException,
    DatabaseException,
    ExternalServiceException,
    ErrorCode
)

logger = get_logger(__name__)



# ============================================================================
# ASYNC METHODS (New - For FastAPI endpoints)
# ============================================================================

async def store_user_on_login_async(
    db: AsyncSession,
    user: schemas.UserStore
) -> models.User:
    """
    Store or update user on login (ASYNC)

    Async variant for FastAPI endpoints
    Handles race conditions gracefully with retry logic
    """
    logger.info("Processing user login (async)", extra={"user_id": user.user_id})

    try:
        # Check for active user
        result = await db.execute(
            select(models.User).where(
                models.User.user_id == user.user_id,
                not models.User.is_deleted
            )
        )
        db_user = result.scalar_one_or_none()

        if db_user:
            logger.debug("Returning existing user", extra={"user_id": user.user_id})
            return db_user

        # Check for deleted user (reactivation)
        result = await db.execute(
            select(models.User).where(
                models.User.user_id == user.user_id,
                models.User.is_deleted
            )
        )
        deleted_user = result.scalar_one_or_none()

        if deleted_user:
            logger.info("Reactivating deleted user", extra={"user_id": user.user_id})

            deleted_user.is_deleted = False
            deleted_user.deleted_at = None
            deleted_user.email = user.email

            await db.commit()
            await db.refresh(deleted_user)

            log_business_event(
                "user_reactivated",
                user_id=user.user_id,
                email=user.email
            )

            return deleted_user

        # Create new user
        logger.info("Creating new user on first login", extra={"user_id": user.user_id})

        db_user = models.User(
            user_id=user.user_id,
            email=user.email,
            credit_balance=0
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        log_business_event(
            "user_first_login",
            user_id=user.user_id,
            email=user.email
        )

        return db_user

    except Exception as e:
        await db.rollback()

        # Handle duplicate key error gracefully (race condition from concurrent login)
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            logger.info(
                "User already exists (concurrent creation detected)",
                extra={"user_id": user.user_id}
            )
            # Retry: fetch the user that was just created
            result = await db.execute(
                select(models.User).where(
                    models.User.user_id == user.user_id
                )
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                return existing_user

        logger.error(
            f"Failed to store user: {e}",
            extra={"user_id": user.user_id},
            exc_info=True
        )
        raise DatabaseException(
            message="Failed to store user",
            original_error=e
        )


async def get_user_by_id_async(
    db: AsyncSession, 
    user_id: str
) -> Optional[models.User]:
    """Get active user by ID (ASYNC)"""
    result = await db.execute(
        select(models.User).where(
            models.User.user_id == user_id,
            models.User.is_deleted == False
        )
    )
    return result.scalar_one_or_none()


async def soft_delete_user_async(
    db: AsyncSession, 
    user_id: str
) -> Optional[models.User]:
    """
    Soft delete user and all related data (ASYNC)
    """
    logger.info(f"Soft deleting user (async)", extra={"user_id": user_id})
    
    try:
        # Get user
        user = await get_user_by_id_async(db, user_id)
        if not user:
            logger.warning(f"User not found for soft delete", extra={"user_id": user_id})
            raise NotFoundException("User", user_id)
        
        now = datetime.now(timezone.utc)
        
        # Soft delete user
        user.is_deleted = True
        user.deleted_at = now
        
        # Soft delete all user's chats
        result = await db.execute(
            select(Chat).where(
                Chat.user_id == user_id,
                Chat.is_deleted == False
            )
        )
        user_chats = result.scalars().all()
        
        for chat in user_chats:
            chat.is_deleted = True
            chat.deleted_at = now
        
        # Soft delete all user's AI conversations
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.user_id == user_id,
                AIConversation.is_deleted == False
            )
        )
        user_conversations = result.scalars().all()
        
        for conversation in user_conversations:
            conversation.is_deleted = True
            conversation.deleted_at = now
        
        await db.commit()
        await db.refresh(user)
        
        log_business_event(
            "user_soft_deleted",
            user_id=user_id,
            chats_deleted=len(user_chats),
            conversations_deleted=len(user_conversations)
        )
        
        logger.info(
            f"User soft deleted successfully",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chats": len(user_chats),
                    "conversations": len(user_conversations)
                }
            }
        )
        
        return user
        
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to soft delete user: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        await db.rollback()
        raise DatabaseException(
            message="Failed to delete user",
            original_error=e
        )


# ============================================================================
# CLERK INTEGRATION
# ============================================================================

async def delete_clerk_user(user_id: str) -> bool:

    
# ============================================================================
# SYNC METHODS (Keep for backward compatibility)
# ============================================================================

# def create_user(db: Session, user_id: str, email: str) -> models.User:
#     """Create a new user (SYNC)"""
#     logger.info(f"Creating new user", extra={"user_id": user_id})
    
#     try:
#         user = models.User(
#             user_id=user_id,
#             email=email,
#             credit_balance=0  # Will be set by signup bonus
#         )
#         db.add(user)
#         db.commit()
#         db.refresh(user)
        
#         log_business_event(
#             "user_created",
#             user_id=user_id,
#             email=email
#         )
        
#         return user
        
#     except Exception as e:
#         logger.error(f"Failed to create user: {e}", exc_info=True)
#         db.rollback()
#         raise


# def store_user_on_login(db: Session, user: schemas.UserStore) -> models.User:
#     """
#     Store or update user on login (SYNC)
    
#     Handles:
#     - First-time login (create new user)
#     - Returning user (return existing)
#     - Reactivate deleted user
#     """
#     logger.info(f"Processing user login", extra={"user_id": user.user_id})
    
#     try:
#         # Check for active user
#         db_user = db.query(models.User).filter(
#             models.User.user_id == user.user_id,
#             not models.User.is_deleted
#         ).first()
        
#         if db_user:
#             logger.debug(f"Returning existing user", extra={"user_id": user.user_id})
#             return db_user
        
#         # Check for deleted user (reactivation)
#         deleted_user = db.query(models.User).filter(
#             models.User.user_id == user.user_id,
#             models.User.is_deleted == True
#         ).first()
        
#         if deleted_user:
#             logger.info(f"Reactivating deleted user", extra={"user_id": user.user_id})
            
#             deleted_user.is_deleted = False
#             deleted_user.deleted_at = None
#             deleted_user.email = user.email
#             db.commit()
#             db.refresh(deleted_user)
            
#             log_business_event(
#                 "user_reactivated",
#                 user_id=user.user_id,
#                 email=user.email
#             )
            
#             return deleted_user
        
#         # Create new user
#         logger.info(f"Creating new user on first login", extra={"user_id": user.user_id})
        
#         db_user = models.User(
#             user_id=user.user_id,
#             email=user.email,
#             credit_balance=0  # Signup bonus will be added separately
#         )
#         db.add(db_user)
#         db.commit()
#         db.refresh(db_user)
        
#         log_business_event(
#             "user_first_login",
#             user_id=user.user_id,
#             email=user.email
#         )
        
#         return db_user
        
#     except Exception as e:
#         logger.error(
#             f"Failed to store user: {e}",
#             extra={"user_id": user.user_id},
#             exc_info=True
#         )
#         db.rollback()
#         raise DatabaseException(
#             message="Failed to store user",
#             original_error=e
#         )


# def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
#     """Get active user by ID (SYNC)"""
#     return db.query(models.User).filter(
#         models.User.user_id == user_id,
#         models.User.is_deleted == False
#     ).first()


# def soft_delete_user(db: Session, user_id: str) -> Optional[models.User]:
#     """
#     Soft delete user and all related data (SYNC)
    
#     Marks as deleted but doesn't remove from DB (GDPR compliance)
#     """
#     logger.info(f"Soft deleting user", extra={"user_id": user_id})
    
#     try:
#         user = get_user_by_id(db, user_id)
#         if not user:
#             logger.warning(f"User not found for soft delete", extra={"user_id": user_id})
#             raise NotFoundException("User", user_id)
        
#         now = func.now()
        
#         # Soft delete user
#         user.is_deleted = True
#         user.deleted_at = now
        
#         # Soft delete all user's chats
#         user_chats = db.query(Chat).filter(
#             Chat.user_id == user_id,
#             Chat.is_deleted == False
#         ).all()
        
#         for chat in user_chats:
#             chat.is_deleted = True
#             chat.deleted_at = now
        
#         # Soft delete all user's AI conversations
#         user_conversations = db.query(AIConversation).filter(
#             AIConversation.user_id == user_id,
#             AIConversation.is_deleted == False
#         ).all()
        
#         for conversation in user_conversations:
#             conversation.is_deleted = True
#             conversation.deleted_at = now
        
#         db.commit()
#         db.refresh(user)
        
#         log_business_event(
#             "user_soft_deleted",
#             user_id=user_id,
#             chats_deleted=len(user_chats),
#             conversations_deleted=len(user_conversations)
#         )
        
#         logger.info(
#             f"User soft deleted successfully",
#             extra={
#                 "user_id": user_id,
#                 "extra_data": {
#                     "chats": len(user_chats),
#                     "conversations": len(user_conversations)
#                 }
#             }
#         )
        
#         return user
        
#     except NotFoundException:
#         raise
#     except Exception as e:
#         logger.error(
#             f"Failed to soft delete user: {e}",
#             extra={"user_id": user_id},
#             exc_info=True
#         )
#         db.rollback()
#         raise DatabaseException(
#             message="Failed to delete user",
#             original_error=e
#         )


# def hard_delete_user_data(db: Session, user_id: str) -> bool:
#     """
#     Permanently delete all user data (GDPR compliance)
    
#     This should only be called after retention period (30 days).
#     Use with caution - this is irreversible!
#     """
#     logger.warning(
#         f"HARD DELETE: Permanently removing user data",
#         extra={"user_id": user_id}
#     )
    
#     try:
#         # Get all chat IDs first
#         chat_ids = [
#             chat.id for chat in db.query(Chat).filter(
#                 Chat.user_id == user_id
#             ).all()
#         ]
        
#         # Delete messages for each chat
#         for chat_id in chat_ids:
#             message_count = db.query(Message).filter(
#                 Message.chat_id == chat_id
#             ).delete()
            
#             insight_count = db.query(Insight).filter(
#                 Insight.chat_id == chat_id
#             ).delete()
            
#             chunk_count = db.query(MessageChunk).filter(
#                 MessageChunk.chat_id == chat_id
#             ).delete()
            
#             logger.debug(
#                 f"Deleted chat data",
#                 extra={
#                     "user_id": user_id,
#                     "extra_data": {
#                         "chat_id": str(chat_id),
#                         "messages": message_count,
#                         "insights": insight_count,
#                         "chunks": chunk_count
#                     }
#                 }
#             )
        
#         # Delete chats
#         chat_count = db.query(Chat).filter(
#             Chat.user_id == user_id
#         ).delete()
        
#         # Get all conversation IDs
#         conversation_ids = [
#             conv.id for conv in db.query(AIConversation).filter(
#                 AIConversation.user_id == user_id
#             ).all()
#         ]
        
#         # Delete AI messages for each conversation
#         for conv_id in conversation_ids:
#             db.query(AIMessage).filter(
#                 AIMessage.conversation_id == conv_id
#             ).delete()
        
#         # Delete AI conversations
#         conversation_count = db.query(AIConversation).filter(
#             AIConversation.user_id == user_id
#         ).delete()
        
#         # Finally, delete user
#         db.query(models.User).filter(
#             models.User.user_id == user_id
#         ).delete()
        
#         db.commit()
        
#         log_business_event(
#             "user_hard_deleted",
#             user_id=user_id,
#             chats_deleted=chat_count,
#             conversations_deleted=conversation_count
#         )
        
#         logger.warning(
#             f"✓ User data permanently deleted",
#             extra={
#                 "user_id": user_id,
#                 "extra_data": {
#                     "chats": chat_count,
#                     "conversations": conversation_count
#                 }
#             }
#         )
        
#         return True
        
#     except Exception as e:
#         logger.critical(
#             f"Failed to permanently delete user: {e}",
#             extra={"user_id": user_id},
#             exc_info=True
#         )
#         db.rollback()
#         return False


# def schedule_hard_delete(db: Session, user_id: str):
#     """
#     Schedule permanent data deletion after retention period
    
#     In production, this should queue a job to run after 30 days.
#     For now, it's a placeholder.
#     """
#     logger.info(
#         f"Scheduling hard delete after retention period",
#         extra={"user_id": user_id}
#     )
    
#     log_business_event(
#         "hard_delete_scheduled",
#         user_id=user_id,
#         scheduled_days=30
#     )
    
#     # TODO: Add to job queue for deletion after 30 days
#     # Example with Celery:
#     # from ..rag.tasks import hard_delete_user_task
#     # hard_delete_user_task.apply_async(
#     #     args=[user_id],
#     #     countdown=30 * 24 * 60 * 60  # 30 days in seconds
#     # )


    """
    Delete user from Clerk authentication service
    
    This should be called after soft delete in our DB.
    Required for GDPR compliance.
    """
    logger.info(f"Deleting user from Clerk", extra={"user_id": user_id})
    
    clerk_secret_key = settings.CLERK_SECRET_KEY
    
    if not clerk_secret_key:
        logger.error("CLERK_SECRET_KEY not configured")
        raise ExternalServiceException(
            service_name="Clerk",
            message="Clerk API key not configured",
            error_code=ErrorCode.CLERK_ERROR
        )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {clerk_secret_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code not in [200, 204]:
                logger.error(
                    f"Clerk deletion failed: {response.status_code}",
                    extra={
                        "user_id": user_id,
                        "extra_data": {
                            "status_code": response.status_code,
                            "response": response.text[:200]
                        }
                    }
                )
                raise ExternalServiceException(
                    service_name="Clerk",
                    message=f"Deletion failed: {response.text[:100]}",
                    error_code=ErrorCode.CLERK_ERROR
                )
            
            logger.info(f"✓ User deleted from Clerk", extra={"user_id": user_id})
            
            log_business_event(
                "clerk_user_deleted",
                user_id=user_id
            )
            
            return True
            
    except httpx.TimeoutException as e:
        logger.error(
            f"Clerk API timeout: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise ExternalServiceException(
            service_name="Clerk",
            message="Request timeout",
            error_code=ErrorCode.CLERK_ERROR
        )
    except httpx.HTTPError as e:
        logger.error(
            f"Clerk API HTTP error: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise ExternalServiceException(
            service_name="Clerk",
            message=f"HTTP error: {str(e)}",
            error_code=ErrorCode.CLERK_ERROR
        )
    except ExternalServiceException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error deleting from Clerk: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise ExternalServiceException(
            service_name="Clerk",
            message=f"Unexpected error: {str(e)}",
            error_code=ErrorCode.CLERK_ERROR
        )