from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ..auth.dependencies import get_current_user_id
from ..database import get_async_db
from . import schemas, service
from ..credits.service import CreditService
from ..logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/store", response_model=schemas.UserOut)
async def store_user(
    user: schemas.UserStore,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_async_db)
):
    """Store user on first login and grant signup bonus"""
    
    logger.info(f"Storing user on login", extra={"user_id": user_id})
    
    try:
        # Store/update user (make this async)
        db_user = await service.store_user_on_login_async(db=db, user=user)
        
        # Give signup bonus (50 coins) - ASYNC
        await CreditService.add_signup_bonus_async(db, user_id, bonus_amount=50)
        
        logger.info("User stored and signup bonus granted", extra={"user_id": user_id})
        
        return db_user
        
    except Exception as e:
        logger.error(f"Failed to store user: {str(e)}", extra={"user_id": user_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store user")

@router.delete("/delete-account", response_model=schemas.UserDeleteResponse)
async def delete_account(
    user_id: Annotated[str, Depends(get_current_user_id)],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete user account (GDPR compliance)
    
    Process:
    1. Soft delete in our DB (immediate)
    2. Delete from Clerk (immediate)
    3. Schedule hard delete (background, after 30 days)
    """
    
    logger.info(f"Account deletion requested", extra={"user_id": user_id})
    
    try:
        # Check if user exists (make async)
        user = await service.get_user_by_id_async(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 1. Soft delete in our DB
        deleted_user = await service.soft_delete_user_async(db, user_id)
        if not deleted_user:
            raise HTTPException(status_code=500, detail="Failed to delete user")
        
        # 2. Delete from Clerk
        try:
            await service.delete_clerk_user(user_id)
            logger.info(f"User deleted from Clerk", extra={"user_id": user_id})
        except Exception as e:
            logger.error(
                f"Failed to delete from Clerk: {str(e)}",
                extra={"user_id": user_id},
                exc_info=True
            )
            # Don't fail request - user is soft-deleted
        
        # 3. Schedule permanent cleanup (30 days)
        background_tasks.add_task(
            service.schedule_hard_delete,
            user_id
        )
        
        logger.info(
            "Account deletion completed",
            extra={"user_id": user_id}
        )
        
        return schemas.UserDeleteResponse(
            success=True,
            message="Account deleted successfully",
            deleted_at=deleted_user.deleted_at,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Account deletion failed: {str(e)}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Deletion failed")

# @router.post("/clerk-webhook")
# async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
#     """Handle Clerk webhook events"""
#     try:
#         event_data = await request.json()
#         event_type = event_data.get("type")
        
#         if event_type == "user.created":
#             user_data = event_data.get("data")
#             user_id = user_data.get("id")
#             email = user_data.get("email_addresses", [{}])[0].get("email_address")
            
#             # Create user
#             new_user = service.create_user(db, user_id, email)
            
#             # Give signup bonus (50 coins) - NEW
#             credit_service = CreditService(db)
#             credit_service.add_signup_bonus(user_id, bonus_amount=50)
            
#             return {"status": "success", "user_id": user_id, "bonus_coins": 50}
            
#         return {"status": "ignored"}
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/{user_id}", response_model=schemas.UserOut)
# def get_user(user_id: str, db: Session = Depends(get_db)):
#     """Get active user by ID"""
#     user = service.get_user_by_id(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user

# response_model=schemas.UserOut ensures that any data returned by the function is automatically validated against the UserOut Pydantic schema and formatted into a JSON response.

# user: schemas.UserStore: FastAPI automatically reads the JSON data from the request body. It then uses Pydantic to validate that data against the UserStore schema. 

# db: Session = Depends(get_db): This is FastAPI's dependency injection system.
# Depends(get_db) means that before store_user is called, FastAPI will first call the get_db() function (from src/database.py).
# get_db() yields a SQLAlchemy Session object.
# FastAPI then passes this Session object as the db argument to your store_user function. This is a common pattern for managing database connections per request.