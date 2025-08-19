from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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

# response_model=schemas.UserOut ensures that any data returned by the function is automatically validated against the UserOut Pydantic schema and formatted into a JSON response.

# user: schemas.UserStore: FastAPI automatically reads the JSON data from the request body. It then uses Pydantic to validate that data against the UserStore schema. 

# db: Session = Depends(get_db): This is FastAPI's dependency injection system.
# Depends(get_db) means that before store_user is called, FastAPI will first call the get_db() function (from src/database.py).
# get_db() yields a SQLAlchemy Session object.
# FastAPI then passes this Session object as the db argument to your store_user function. This is a common pattern for managing database connections per request.