from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Annotated
from ..auth.dependencies import get_current_user_id
from datetime import datetime
from ..credits.service import CreditService 

from ..database import get_db
from . import schemas, service

router = APIRouter(
    prefix="/users",
    tags=["users"],
)
