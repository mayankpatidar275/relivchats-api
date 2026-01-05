# src/error_handlers.py
"""
Centralized error handling with custom exception classes,
error codes, and FastAPI exception handlers.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
from typing import Any, Dict, Optional
import traceback
from datetime import timezone

from .logging_config import get_logger
from .config import settings

logger = get_logger(__name__)


# ============================================================================
# ERROR CODES - For client-side error handling
# ============================================================================

class ErrorCode:
    """Centralized error codes for consistent client-side handling"""
    
    # General errors (1xxx)
    INTERNAL_SERVER_ERROR = "ERR_1000"
    VALIDATION_ERROR = "ERR_1001"
    NOT_FOUND = "ERR_1002"
    UNAUTHORIZED = "ERR_1003"
    FORBIDDEN = "ERR_1004"
    RATE_LIMIT_EXCEEDED = "ERR_1005"
    
    # Database errors (2xxx)
    DATABASE_ERROR = "ERR_2000"
    INTEGRITY_ERROR = "ERR_2001"
    CONNECTION_ERROR = "ERR_2002"
    
    # Business logic errors (3xxx)
    INSUFFICIENT_CREDITS = "ERR_3000"
    CHAT_ALREADY_EXISTS = "ERR_3001"
    CHAT_PROCESSING_FAILED = "ERR_3002"
    INVALID_FILE_FORMAT = "ERR_3003"
    FILE_TOO_LARGE = "ERR_3004"
    VECTOR_INDEXING_FAILED = "ERR_3005"
    INSIGHT_GENERATION_FAILED = "ERR_3006"
    PAYMENT_FAILED = "ERR_3007"
    REFUND_FAILED = "ERR_3008"
    
    # External service errors (4xxx)
    GEMINI_API_ERROR = "ERR_4000"
    QDRANT_ERROR = "ERR_4001"
    REDIS_ERROR = "ERR_4002"
    CLERK_ERROR = "ERR_4003"
    PAYMENT_GATEWAY_ERROR = "ERR_4004"


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class AppException(Exception):
    """Base exception for all application errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundException(AppException):
    """Raised when a resource is not found"""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class UnauthorizedException(AppException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(AppException):
    """Raised when user doesn't have permission"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN
        )


class InsufficientCreditsException(AppException):
    """Raised when user doesn't have enough credits"""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            message=f"Insufficient credits. Required: {required}, Available: {available}",
            error_code=ErrorCode.INSUFFICIENT_CREDITS,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details={
                "required": required,
                "available": available,
                "deficit": required - available
            }
        )


class DatabaseException(AppException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"original_error": str(original_error)} if original_error else {}
        )


class ExternalServiceException(AppException):
    """Raised when external service calls fail"""
    
    def __init__(
        self,
        service_name: str,
        message: str,
        error_code: str = ErrorCode.INTERNAL_SERVER_ERROR
    ):
        super().__init__(
            message=f"{service_name} error: {message}",
            error_code=error_code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service_name}
        )


class FileProcessingException(AppException):
    """Raised when file processing fails"""

    def __init__(self, message: str, error_code: str = ErrorCode.CHAT_PROCESSING_FAILED):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class LockTimeoutException(AppException):
    """Raised when database row lock cannot be acquired (async migrations)"""

    def __init__(self, resource: str, message: str = "Resource is currently locked"):
        super().__init__(
            message=f"{resource}: {message}",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # Temporary unavailability
            details={"resource": resource, "cause": "lock_timeout"}
        )


class AsyncDatabaseException(AppException):
    """Raised when async database operations fail (connection, timeout, etc.)"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"original_error": str(original_error)} if original_error else {}
        )


# ============================================================================
# ERROR RESPONSE FORMATTER
# ============================================================================

def format_error_response(
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format error response in a consistent structure
    
    Returns:
        {
            "error": {
                "code": "ERR_1000",
                "message": "Something went wrong",
                "details": {...},
                "request_id": "abc123",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    """
    from datetime import datetime
    
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    if request_id:
        response["error"]["request_id"] = request_id
    
    # Add support link in production
    if settings.ENVIRONMENT == "production":
        response["error"]["support"] = "Contact support@relivchats.com"
    
    return response


# ============================================================================
# FASTAPI EXCEPTION HANDLERS
# ============================================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for custom AppException errors"""

    request_id = getattr(request.state, "request_id", None)

    # Send 5xx errors to Sentry (500-599 status codes indicate server errors)
    # if exc.status_code >= 500:
    #     try:
    #         import sentry_sdk
    #         sentry_sdk.capture_exception(exc)
    #     except Exception:
    #         pass

    # Log the error
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method,
                "details": exc.details
            }
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request_id
        )
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler for Pydantic validation errors"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "extra_data": {
                "path": str(request.url),
                "method": request.method,
                "errors": errors
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors},
            request_id=request_id
        )
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """Handler for SQLAlchemy database errors"""

    request_id = getattr(request.state, "request_id", None)

    # Send to Sentry (database errors are critical!)
    # try:
    #     import sentry_sdk
    #     sentry_sdk.capture_exception(exc)
    # except Exception:
    #     pass  # Don't crash if Sentry fails

    # Determine error type
    if isinstance(exc, IntegrityError):
        error_code = ErrorCode.INTEGRITY_ERROR
        message = "Database integrity constraint violated"
        status_code = status.HTTP_409_CONFLICT
    else:
        error_code = ErrorCode.DATABASE_ERROR
        message = "Database operation failed"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Log with full details
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "error_type": type(exc).__name__,
                "path": str(request.url),
                "method": request.method
            }
        },
        exc_info=True
    )
    
    # Don't expose internal DB details in production
    if settings.ENVIRONMENT == "production":
        details = None
    else:
        details = {"database_error": str(exc)}
    
    return JSONResponse(
        status_code=status_code,
        content=format_error_response(
            error_code=error_code,
            message=message,
            status_code=status_code,
            details=details,
            request_id=request_id
        )
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Catch-all handler for unexpected errors"""

    request_id = getattr(request.state, "request_id", None)

    # ⚠️ CRITICAL: Send to Sentry BEFORE logging/returning response
    # Without this, Sentry never sees the exception!
    # try:
    #     import sentry_sdk
    #     sentry_sdk.capture_exception(exc)
    # except Exception as sentry_error:
    #     # If Sentry fails, don't crash the error handler
    #     logger.debug(f"Failed to send exception to Sentry: {sentry_error}")

    # Log the full error with stack trace
    logger.critical(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "exception_type": type(exc).__name__,
                "path": str(request.url),
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        },
        exc_info=True
    )
    
    # Generic error message for production
    if settings.ENVIRONMENT == "production":
        message = "An unexpected error occurred. Our team has been notified."
        details = None
    else:
        message = str(exc)
        details = {"traceback": traceback.format_exc().split("\n")}
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            request_id=request_id
        )
    )


async def lock_timeout_exception_handler(
    request: Request,
    exc: LockTimeoutException
) -> JSONResponse:
    """Handler for database lock timeout errors (async migrations)"""

    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        f"Lock timeout: {exc.message}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "resource": exc.details.get("resource"),
                "path": str(request.url),
                "method": request.method
            }
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request_id
        )
    )


async def async_database_exception_handler(
    request: Request,
    exc: AsyncDatabaseException
) -> JSONResponse:
    """Handler for async database operation errors"""

    request_id = getattr(request.state, "request_id", None)

    logger.error(
        f"Async database error: {exc.message}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "path": str(request.url),
                "method": request.method,
                "original_error": exc.details.get("original_error")
            }
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details if settings.ENVIRONMENT != "production" else None,
            request_id=request_id
        )
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app
    Call this in main.py during app initialization

    Handlers are registered in order of specificity:
    1. Custom app exceptions (most specific)
    2. Validation errors
    3. SQLAlchemy errors
    4. Generic exceptions (least specific)
    """
    app.add_exception_handler(LockTimeoutException, lock_timeout_exception_handler)
    app.add_exception_handler(AsyncDatabaseException, async_database_exception_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)