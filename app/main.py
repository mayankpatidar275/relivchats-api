from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

from app.api.v1.endpoints import api_router # Use the combined router
from app.db.session import engine
from app.models.base import Base

# Import all models to ensure Base.metadata discovers them for Alembic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Initialization (using the modern lifespan event handler) ---
# --- Database Initialization (for local development/testing without Alembic) ---
# In a production environment, you'd solely rely on Alembic migrations.
# This part is for convenience to create tables if they don't exist.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    """
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        # THIS SHOULD BE REMOVED OR PROTECTED IN PRODUCTION, USE ALEMBIC!
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured (via create_all). For production, use Alembic migrations.")
    yield
    # No shutdown logic is needed for this example, but it would go here.

app = FastAPI(
    title="Reliv Chats API",
    description="Backend API for Reliv Chats mobile app. Empathetic AI insights on WhatsApp chats.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware (adjust origins as needed for your frontend)
# In production, specify exact origins: allow_origins=["https://yourfrontend.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development, CHANGE THIS IN PRODUCTION
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods
    allow_headers=["*"], # Allow all headers
)

# --- API Routers ---
app.include_router(api_router, prefix="/api/v1")

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during request to {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."}
    )