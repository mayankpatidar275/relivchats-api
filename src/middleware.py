# src/middleware.py
"""
Custom middleware for request/response logging, monitoring,
and performance tracking.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import get_logger
from .config import settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and outgoing responses
    Adds request_id for tracing and tracks response times
    """
    
    # Paths to exclude from logging (health checks, etc.)
    EXCLUDED_PATHS = ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)
        
        # Record start time
        start_time = time.time()
        
        # Should we log this request?
        should_log = not any(
            request.url.path.startswith(path) for path in self.EXCLUDED_PATHS
        )
        
        if should_log:
            logger.info(
                f"Incoming request: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": dict(request.query_params),
                        "client_host": request.client.host if request.client else None,
                        "user_agent": request.headers.get("user-agent"),
                    }
                }
            )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            process_time_ms = int(process_time * 1000)
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time_ms)
            
            if should_log:
                # Determine log level based on status code
                if response.status_code >= 500:
                    log_level = logger.error
                elif response.status_code >= 400:
                    log_level = logger.warning
                else:
                    log_level = logger.info
                
                log_level(
                    f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "request_id": request_id,
                        "user_id": user_id,
                        "extra_data": {
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                            "process_time_ms": process_time_ms,
                        }
                    }
                )
            
            # Track slow requests
            if process_time > 2.0:  # Requests taking > 2 seconds
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path}",
                    extra={
                        "request_id": request_id,
                        "user_id": user_id,
                        "extra_data": {
                            "process_time_ms": process_time_ms,
                            "threshold_exceeded": True
                        }
                    }
                )
            
            return response
            
        except Exception as exc:
            # Log exception but let it propagate to exception handlers
            process_time = time.time() - start_time
            
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "process_time_ms": int(process_time * 1000),
                        "exception": str(exc)
                    }
                },
                exc_info=True
            )
            raise


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and attach user context to requests
    Makes user_id available in request.state for logging
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user ID from auth token (Clerk or your auth system)
        # This is a simplified example - adjust based on your auth setup
        
        auth_header = request.headers.get("authorization", "")
        
        # You would decode JWT or validate session here
        # For now, we'll just set it to None
        user_id = None
        
        # If you have a get_current_user_id dependency, you could call it here
        # Or extract from JWT claims
        
        request.state.user_id = user_id
        
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def register_middleware(app):
    """
    Register all middleware with FastAPI app
    Order matters: first registered = outermost layer
    """
    # Security headers (outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # User context extraction
    app.add_middleware(UserContextMiddleware)
    
    logger.info("Middleware registered successfully")