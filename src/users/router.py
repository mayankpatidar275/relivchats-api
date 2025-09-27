from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Annotated
from ..auth.dependencies import get_current_user_id
from datetime import datetime

from ..database import get_db
from . import schemas, service

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.post("/store", response_model=schemas.UserOut)
def store_user(user: schemas.UserStore, db: Session = Depends(get_db)):
    db_user = service.store_user_on_login(db=db, user=user)
    return db_user

@router.delete("/delete-account", response_model=schemas.UserDeleteResponse)
def delete_account(
    user_id: Annotated[str, Depends(get_current_user_id)],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Soft delete user account and schedule permanent cleanup
    """

    # Check if user exists
    user = service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="User not found"
        )
    
    # Soft delete user and related data
    deleted_user = service.soft_delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(
            status_code=500, 
            detail="Failed to delete user account"
        )
    
    # Schedule permanent cleanup in background
    background_tasks.add_task(
        service.hard_delete_user_data, 
        db, 
        user_id
    )
    
    return schemas.UserDeleteResponse(
        success=True,
        message="Account successfully deleted",
        deleted_at=deleted_user.deleted_at,
        user_id=user_id
    )


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