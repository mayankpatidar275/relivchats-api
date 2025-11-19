# src/logging_config.py
"""
Production-grade logging configuration with structured logging,
multiple handlers, and integration with external monitoring services.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback

from .config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON-structured logs for easy parsing
    by log aggregation services (ELK, Datadog, CloudWatch, etc.)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields passed via extra={} in log calls
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        # Add user context if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and not record.exc_info:
            log_data["stack_trace"] = traceback.format_stack()
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output during development
    """
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        levelname = record.levelname
        if settings.ENVIRONMENT == "development":
            color = self.COLORS.get(levelname, self.RESET)
            colored_levelname = f"{color}{levelname:8s}{self.RESET}"
        else:
            colored_levelname = f"{levelname:8s}"
        
        # Build the message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"{timestamp} | {colored_levelname} | {record.name:25s} | {record.getMessage()}"
        
        # Add extra context
        if hasattr(record, "user_id"):
            message += f" [user={record.user_id}]"
        
        if hasattr(record, "request_id"):
            message += f" [req={record.request_id[:8]}]"
        
        # Add exception if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


def setup_logging():
    """
    Configure logging for the entire application
    Should be called once during application startup
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # ========================================================================
    # CONSOLE HANDLER (stdout)
    # ========================================================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO)
    
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter())
    
    root_logger.addHandler(console_handler)
    
    # ========================================================================
    # FILE HANDLER (rotating by size) - General logs
    # ========================================================================
    if settings.ENABLE_FILE_LOGGING:
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # ========================================================================
    # ERROR FILE HANDLER (rotating by time) - Errors only
    # ========================================================================
    if settings.ENABLE_FILE_LOGGING:
        error_handler = TimedRotatingFileHandler(
            log_dir / "errors.log",
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days of error logs
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
    
    # ========================================================================
    # BUSINESS LOGIC HANDLER - Track important business events
    # ========================================================================
    if settings.ENABLE_FILE_LOGGING:
        business_handler = RotatingFileHandler(
            log_dir / "business.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        business_handler.setLevel(logging.INFO)
        business_handler.setFormatter(StructuredFormatter())
        
        # Only add this to specific loggers
        business_logger = logging.getLogger("business")
        business_logger.addHandler(business_handler)
        business_logger.propagate = False  # Don't duplicate to root logger
    
    # ========================================================================
    # THIRD-PARTY LIBRARY LOGGING LEVELS
    # ========================================================================
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # ========================================================================
    # STARTUP LOG
    # ========================================================================
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "extra_data": {
                "environment": settings.ENVIRONMENT,
                "log_level": settings.LOG_LEVEL,
                "log_format": settings.LOG_FORMAT,
                "file_logging": settings.ENABLE_FILE_LOGGING
            }
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Usage:
        from src.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)


# Business event logger for tracking critical business operations
business_logger = logging.getLogger("business")


def log_business_event(
    event_type: str,
    user_id: str = None,
    **kwargs: Any
):
    """
    Log important business events for analytics and auditing
    
    Examples:
        - User signup
        - Chat uploaded
        - Payment successful
        - Credits deducted
        - Insight generated
    
    Usage:
        log_business_event(
            "chat_uploaded",
            user_id="user123",
            chat_id="chat456",
            message_count=1234,
            file_size_mb=2.5
        )
    """
    business_logger.info(
        f"Business Event: {event_type}",
        extra={
            "user_id": user_id,
            "extra_data": {
                "event_type": event_type,
                **kwargs
            }
        }
    )