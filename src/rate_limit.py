"""
Rate Limiting Configuration for RelivChats API

Uses SlowAPI with Redis backend for distributed rate limiting.
Prevents API abuse and controls costs (especially Gemini API usage).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


def get_user_id_or_ip(request: Request) -> str:
    """
    Rate limit key function - uses user_id if authenticated, otherwise IP address.

    This ensures:
    - Authenticated users are rate limited per account (prevents multi-IP abuse)
    - Anonymous users are rate limited per IP (prevents signup spam)
    """
    # Check if user is authenticated (user_id set by auth middleware)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


# Initialize rate limiter with Redis backend
limiter = Limiter(
    key_func=get_user_id_or_ip,
    storage_uri=settings.REDIS_URL,
    default_limits=[],  # No default limits - we'll set per-endpoint
    enabled=True,  # Can be disabled in testing
    headers_enabled=True,  # Return X-RateLimit-* headers
)


# ============================================================================
# RATE LIMIT DEFINITIONS (Production-Grade)
# ============================================================================

# Global limits (applies to all endpoints unless overridden)
GLOBAL_LIMIT = "1000/hour"  # Prevent spam from any single source

# Authentication endpoints (prevent brute force)
AUTH_LIMIT = "10/minute"  # Reasonable for login/signup flows

# Chat upload (expensive operation - WhatsApp parsing + metadata generation)
UPLOAD_LIMIT = "20/hour"  # ~1 upload every 3 minutes

# Insight unlock (MOST EXPENSIVE - Gemini API costs)
# This is the critical limit that protects your revenue model
INSIGHT_UNLOCK_LIMIT = "10/hour"  # Max 10 categories per hour per user
INSIGHT_UNLOCK_BURST = "3/minute"  # Prevent rapid unlocks (abuse pattern)

# Insight retrieval (read-only, cheap)
INSIGHT_READ_LIMIT = "100/minute"  # Allow frequent polling

# Payment endpoints
PAYMENT_CREATE_LIMIT = "10/minute"  # Prevent payment spam
PAYMENT_WEBHOOK_LIMIT = "100/minute"  # Razorpay/Stripe webhooks can burst

# Credit/balance checks (read-only)
BALANCE_CHECK_LIMIT = "60/minute"  # 1 per second

# Chat list/read (read-only)
CHAT_READ_LIMIT = "100/minute"

# RAG query endpoint (uses Gemini API)
RAG_QUERY_LIMIT = "20/minute"  # Expensive - semantic search + LLM call

# Health check (exempt from rate limiting)
# No limit - used by load balancers


# ============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ============================================================================

if settings.ENVIRONMENT == "development":
    # More relaxed limits for development
    INSIGHT_UNLOCK_LIMIT = "100/hour"
    UPLOAD_LIMIT = "100/hour"
    RAG_QUERY_LIMIT = "100/minute"
    logger.info("Rate limiting: DEVELOPMENT mode (relaxed limits)")

elif settings.ENVIRONMENT == "staging":
    # Same as production but with logging
    logger.info("Rate limiting: STAGING mode (production limits with verbose logging)")

else:  # production
    logger.info("Rate limiting: PRODUCTION mode (strict limits enabled)")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_rate_limit_message(endpoint: str, limit: str) -> dict:
    """
    Returns user-friendly error message when rate limit is exceeded.

    Used in exception handlers to provide actionable feedback.
    """
    return {
        "error": "rate_limit_exceeded",
        "message": f"Too many requests to {endpoint}. Please try again later.",
        "limit": limit,
        "retry_after": "Check X-RateLimit-Reset header",
    }


def exempt_from_rate_limit(request: Request) -> bool:
    """
    Exempt certain paths from rate limiting.

    Use case: Health checks, internal webhooks, admin endpoints (if you add auth).
    """
    exempt_paths = [
        "/health",
        "/health/db-pool",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    return request.url.path in exempt_paths


# ============================================================================
# RATE LIMIT DECORATORS (for easy use in routers)
# ============================================================================

# Export commonly used limits as ready-to-use decorators
strict_limit = limiter.limit(INSIGHT_UNLOCK_LIMIT)
upload_limit = limiter.limit(UPLOAD_LIMIT)
read_limit = limiter.limit(CHAT_READ_LIMIT)
payment_limit = limiter.limit(PAYMENT_CREATE_LIMIT)
webhook_limit = limiter.limit(PAYMENT_WEBHOOK_LIMIT)
auth_limit = limiter.limit(AUTH_LIMIT)


# ============================================================================
# MONITORING & ALERTS
# ============================================================================

def log_rate_limit_hit(request: Request, limit: str):
    """
    Log when rate limits are hit - useful for detecting abuse patterns.

    In production, you could:
    - Send alerts to Slack/PagerDuty if >100 hits/minute
    - Auto-ban IPs with excessive violations
    - Analyze patterns to adjust limits
    """
    logger.warning(
        "Rate limit exceeded",
        extra={
            "extra_data": {
                "path": request.url.path,
                "limit": limit,
                "key": get_user_id_or_ip(request),
                "user_agent": request.headers.get("user-agent"),
            }
        }
    )


# ============================================================================
# USAGE EXAMPLE (for reference)
# ============================================================================

# In your routers, use like this:
#
# from src.rate_limit import limiter, INSIGHT_UNLOCK_LIMIT
#
# @router.post("/insights/unlock")
# @limiter.limit(INSIGHT_UNLOCK_LIMIT)
# async def unlock_insights(request: Request, ...):
#     ...
#
# Or use the pre-made decorators:
#
# from src.rate_limit import strict_limit
#
# @router.post("/insights/unlock")
# @strict_limit
# async def unlock_insights(request: Request, ...):
#     ...
