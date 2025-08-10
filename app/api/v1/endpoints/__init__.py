from fastapi import APIRouter
from app.api.v1.endpoints import chats, ai, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(chats.router, prefix="", tags=["Chats"]) # Base path for chats
api_router.include_router(ai.router, prefix="", tags=["AI"]) # Base path for AI