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