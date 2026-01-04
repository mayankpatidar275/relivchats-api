# src/main.py - UPDATED VERSION

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import asyncio

from .config import settings
from .logging_config import setup_logging, get_logger
from .error_handlers import register_exception_handlers
from .middleware import register_middleware
from .rate_limit import limiter, SlowAPIMiddleware, log_rate_limit_hit
from slowapi.errors import RateLimitExceeded

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

# Background task state
_app_state = {"keepalive_task": None}


def _scrub_sensitive_data(event: dict, hint: dict = None) -> dict:
    """
    Scrub sensitive data from Sentry events before sending.

    Prevents leaking: API keys, passwords, credit card info, chat content, user PII.
    """
    # Scrub request data
    if "request" in event:
        request_data = event["request"]

        # Scrub headers (Authorization, API keys, etc.)
        if "headers" in request_data:
            sensitive_headers = ["authorization", "cookie", "x-api-key", "razorpay", "stripe"]
            for header in list(request_data["headers"].keys()):
                if any(s in header.lower() for s in sensitive_headers):
                    request_data["headers"][header] = "[REDACTED]"

        # Scrub query params
        if "query_string" in request_data:
            request_data["query_string"] = "[REDACTED]"

        # Scrub form data
        if "data" in request_data:
            sensitive_keys = ["password", "api_key", "secret", "token", "credit_card", "cvv"]
            if isinstance(request_data["data"], dict):
                for key in list(request_data["data"].keys()):
                    if any(s in key.lower() for s in sensitive_keys):
                        request_data["data"][key] = "[REDACTED]"

    # Scrub extra context
    if "extra" in event:
        if "chat_content" in event["extra"]:
            event["extra"]["chat_content"] = "[REDACTED - CHAT DATA]"
        if "message_text" in event["extra"]:
            event["extra"]["message_text"] = "[REDACTED - MESSAGE]"

    return event


async def _neon_keepalive():
    """
    Background task to keep Neon compute from suspending.

    Neon's Scale-to-Zero suspends compute after 5 minutes of inactivity.
    This task runs a lightweight health check every 4 minutes in production.
    """
    if settings.ENVIRONMENT != "production":
        return

    try:
        from .database import async_session
        from sqlalchemy import text

        while True:
            try:
                await asyncio.sleep(240)  # Run every 4 minutes
                async with async_session() as session:
                    await session.execute(text("SELECT 1"))
                logger.debug("Neon keepalive: connection refreshed")
            except Exception as e:
                logger.warning(f"Neon keepalive error: {e}")
    except Exception as e:
        logger.error(f"Failed to start Neon keepalive task: {e}")


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
        start = time.time()
        db.execute(text("SELECT 1"))
        logger.info(f"select(1) took {(time.time()-start)*1000:.1f}ms")
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

    # Start Neon keepalive task (prevents Scale-to-Zero suspension in production)
    _app_state["keepalive_task"] = asyncio.create_task(_neon_keepalive())
    if settings.ENVIRONMENT == "production":
        logger.info("✓ Neon keepalive task started (prevents Scale-to-Zero suspension)")

    # Initialize Sentry (if configured)
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,

                # Enable sending request data (headers, IP) for better debugging
                send_default_pii=True,

                # Enable automatic log forwarding to Sentry
                enable_logs=True,

                # Performance monitoring (traces)
                # Production: 10% sampling to reduce costs
                # Development: 100% sampling for full visibility
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,

                # Profiling (CPU/memory performance)
                # Production: 10% of traces
                # Development: 100% of traces
                profiles_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                profile_lifecycle="trace",  # Profile during active transactions

                # Scrub sensitive data before sending to Sentry
                before_send=lambda event, hint: _scrub_sensitive_data(event),
            )

            logger.info(
                "✓ Sentry initialized",
                extra={"extra_data": {
                    "environment": settings.ENVIRONMENT,
                    "traces_sample_rate": settings.SENTRY_TRACES_SAMPLE_RATE,
                    "logs_enabled": True,
                    "pii_enabled": True,
                }}
            )
        except Exception as e:
            logger.warning(f"⚠ Sentry initialization failed: {e}")
    else:
        logger.info("⚠ Sentry DSN not configured - error tracking disabled")
    
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

    # Cancel keepalive task
    if _app_state["keepalive_task"]:
        _app_state["keepalive_task"].cancel()
        try:
            await _app_state["keepalive_task"]
        except asyncio.CancelledError:
            logger.debug("Neon keepalive task cancelled")


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

# Rate limiting middleware (MUST be before CORS)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS middleware (Production: Whitelist specific domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Now required in config
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# ============================================================================
# REGISTER EXCEPTION HANDLERS
# ============================================================================
register_exception_handlers(app)

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors with user-friendly message"""
    log_rate_limit_hit(request, str(exc.detail))

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "detail": str(exc.detail),
        },
        headers={
            "Retry-After": "60",  # Suggest retry after 60 seconds
        }
    )

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

@app.get("/sentry-debug")
async def trigger_sentry_error():
    """
    Sentry verification endpoint - triggers a test error

    IMPORTANT: Disable this in production or add authentication!
    Visit https://api.relivchats.mkpatidar.in/sentry-debug to test Sentry
    """
    logger.info("Sentry debug endpoint called - triggering test error")
    division_by_zero = 1 / 0  # This will trigger a ZeroDivisionError
    return {"status": "This should never be reached"}

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