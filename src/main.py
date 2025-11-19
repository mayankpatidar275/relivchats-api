# src/main.py - UPDATED VERSION

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .logging_config import setup_logging, get_logger
from .error_handlers import register_exception_handlers
from .middleware import register_middleware

# Import routers
from .users.router import router as users_router  
from .chats.router import router as chats_router
from .rag.router import router as rag_router
from .categories.router import router as category_router
from .credits.router import router as credit_router
from .insights.router import router as insights_router
from .payments.router import router as payment_router

# Initialize logger (will be configured during startup)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("="*80)
    logger.info("Starting RelivChats API")
    logger.info("="*80)
    
    # Log configuration
    logger.info(
        "Application configuration",
        extra={
            "extra_data": {
                "environment": settings.ENVIRONMENT,
                "log_level": settings.LOG_LEVEL,
                "database": settings.DATABASE_URL.split("@")[-1] if settings.DATABASE_URL else "Not configured",
                "redis": settings.REDIS_URL.split("@")[-1] if settings.REDIS_URL else "Not configured",
                "celery_broker": settings.CELERY_BROKER_URL.split("@")[-1] if settings.CELERY_BROKER_URL else "Not configured"
            }
        }
    )
    
    # Test database connection
    try:
        from .database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}", exc_info=True)
        raise
    
    # Test Redis connection
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.warning(f"⚠ Redis connection failed: {e}")
    
    # Initialize Sentry (if configured)
    # if settings.SENTRY_DSN:
    #     try:
    #         import sentry_sdk
    #         from sentry_sdk.integrations.fastapi import FastApiIntegration
    #         from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
    #         sentry_sdk.init(
    #             dsn=settings.SENTRY_DSN,
    #             environment=settings.ENVIRONMENT,
    #             traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    #             integrations=[
    #                 FastApiIntegration(),
    #                 SqlalchemyIntegration(),
    #             ],
    #         )
    #         logger.info("✓ Sentry error tracking initialized")
    #     except Exception as e:
    #         logger.warning(f"⚠ Sentry initialization failed: {e}")
    
    logger.info("="*80)
    logger.info("🚀 RelivChats API is ready to accept requests")
    logger.info("="*80)
    
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("="*80)
    logger.info("Shutting down RelivChats API")
    logger.info("="*80)


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

# Setup logging BEFORE creating the app
setup_logging()

app = FastAPI(
    title="RelivChats API",
    description="WhatsApp Chat Analysis & Insights Platform",
    version="1.0.0",
    lifespan=lifespan,
    # Disable default exception handlers - we'll use custom ones
    exception_handlers={}
)

# ============================================================================
# REGISTER MIDDLEWARE (ORDER MATTERS!)
# ============================================================================
register_middleware(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REGISTER EXCEPTION HANDLERS
# ============================================================================
register_exception_handlers(app)

# ============================================================================
# REGISTER ROUTERS
# ============================================================================

app.include_router(users_router, prefix='/api')
app.include_router(chats_router, prefix='/api')
app.include_router(insights_router, prefix='/api')
app.include_router(rag_router, prefix='/api')
app.include_router(category_router, prefix='/api')
app.include_router(credit_router, prefix='/api')
app.include_router(payment_router, prefix='/api')

logger.info("All routers registered")

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

@app.get("/health/db-pool")
async def db_pool_health():
    from .database import get_pool_status
    return get_pool_status()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RelivChats API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# # Add this endpoint for emergency bulk indexing
# @router.post("/admin/reindex-all")
# def reindex_pending_chats(db: Session = Depends(get_db)):
#     """Emergency: Index all pending chats"""
#     chats = db.query(Chat).filter(Chat.vector_status == "pending").all()
    
#     for chat in chats:
#         vector_service.create_chat_chunks(db, chat.id)
    
#     return {"reindexed": len(chats)}


## **Final API Structure**

# /api/chats
#   POST   /upload              # Upload chat file
#   GET    /                    # List user chats
#   GET    /{chat_id}           # Get chat details
#   PUT    /{chat_id}/display-name
#   GET    /{chat_id}/messages
#   GET    /{chat_id}/vector-status
#   DELETE /{chat_id}

# /api/insights                  # ← NEW
#   POST   /unlock               # Unlock insights (was in /credits)
#   GET    /jobs/{job_id}/status # Poll generation progress
#   GET    /chats/{chat_id}      # Get all insights for chat
#   POST   /{insight_id}/retry   # Retry failed insight

# /api/credits
#   GET    /balance
#   GET    /transactions
#   GET    /packages

# /api/categories
#   GET    /
#   GET    /{category_id}/insights

# /api/rag
#   POST   /query               # Conversational Q&A
#   POST   /generate            # Deprecated

# /api/users
#   POST   /store
#   DELETE /delete-account