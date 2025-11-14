# src/monitoring.py
"""
Performance monitoring utilities, decorators for tracking
execution time, database queries, and external API calls.
"""

import time
import functools
from typing import Callable, Any
from contextlib import contextmanager

from .logging_config import get_logger, log_business_event
from .config import settings

logger = get_logger(__name__)


# ============================================================================
# PERFORMANCE MONITORING DECORATORS
# ============================================================================

def track_time(operation_name: str = None):
    """
    Decorator to track execution time of functions
    
    Usage:
        @track_time("parse_whatsapp_file")
        def parse_whatsapp_file(file_path):
            # ... function code
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000  # ms
                
                logger.info(
                    f"Operation completed: {op_name}",
                    extra={
                        "extra_data": {
                            "operation": op_name,
                            "execution_time_ms": int(execution_time),
                            "status": "success"
                        }
                    }
                )
                
                # Warn on slow operations
                if execution_time > 2000:  # 2 seconds
                    logger.warning(
                        f"Slow operation detected: {op_name}",
                        extra={
                            "extra_data": {
                                "operation": op_name,
                                "execution_time_ms": int(execution_time),
                                "threshold_exceeded": True
                            }
                        }
                    )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation failed: {op_name}",
                    extra={
                        "extra_data": {
                            "operation": op_name,
                            "execution_time_ms": int(execution_time),
                            "status": "failed",
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def track_async_time(operation_name: str = None):
    """
    Async version of track_time decorator
    
    Usage:
        @track_async_time("process_payment")
        async def process_payment(order_id):
            # ... async function code
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or func.__name__
            
            try:
                result = await func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Async operation completed: {op_name}",
                    extra={
                        "extra_data": {
                            "operation": op_name,
                            "execution_time_ms": int(execution_time),
                            "status": "success"
                        }
                    }
                )
                
                if execution_time > 2000:
                    logger.warning(
                        f"Slow async operation: {op_name}",
                        extra={
                            "extra_data": {
                                "operation": op_name,
                                "execution_time_ms": int(execution_time)
                            }
                        }
                    )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(
                    f"Async operation failed: {op_name}",
                    extra={
                        "extra_data": {
                            "operation": op_name,
                            "execution_time_ms": int(execution_time),
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    exponential_backoff: bool = True
):
    """
    Decorator to retry function on failure with exponential backoff
    
    Usage:
        @retry_on_failure(max_attempts=3, delay_seconds=1.0)
        def call_external_api():
            # ... code that might fail
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        if exponential_backoff:
                            current_delay = delay_seconds * (2 ** attempt)
                        else:
                            current_delay = delay_seconds
                        
                        logger.warning(
                            f"Function {func.__name__} failed, retrying in {current_delay}s (attempt {attempt + 1}/{max_attempts})",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "attempt": attempt + 1,
                                    "max_attempts": max_attempts,
                                    "delay": current_delay,
                                    "error": str(e)
                                }
                            }
                        )
                        
                        time.sleep(current_delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            extra={
                                "extra_data": {
                                    "function": func.__name__,
                                    "max_attempts": max_attempts,
                                    "final_error": str(e)
                                }
                            },
                            exc_info=True
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# CONTEXT MANAGERS FOR TRACKING
# ============================================================================

@contextmanager
def track_operation(operation_name: str, **context_data):
    """
    Context manager to track operations with custom metadata
    
    Usage:
        with track_operation("database_query", query_type="select", table="chats"):
            result = db.query(Chat).all()
    """
    start_time = time.time()
    
    logger.info(
        f"Starting operation: {operation_name}",
        extra={"extra_data": {"operation": operation_name, **context_data}}
    )
    
    try:
        yield
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Operation completed: {operation_name}",
            extra={
                "extra_data": {
                    "operation": operation_name,
                    "execution_time_ms": int(execution_time),
                    "status": "success",
                    **context_data
                }
            }
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Operation failed: {operation_name}",
            extra={
                "extra_data": {
                    "operation": operation_name,
                    "execution_time_ms": int(execution_time),
                    "status": "failed",
                    "error": str(e),
                    **context_data
                }
            },
            exc_info=True
        )
        raise


@contextmanager
def track_database_query(query_description: str):
    """
    Context manager specifically for tracking database queries
    
    Usage:
        with track_database_query("fetch user chats"):
            chats = db.query(Chat).filter(Chat.user_id == user_id).all()
    """
    start_time = time.time()
    
    try:
        yield
        
        execution_time = (time.time() - start_time) * 1000
        
        # Warn on slow queries
        if execution_time > settings.SLOW_DATABASE_QUERY_THRESHOLD_MS:
            logger.warning(
                f"Slow database query: {query_description}",
                extra={
                    "extra_data": {
                        "query": query_description,
                        "execution_time_ms": int(execution_time),
                        "threshold": settings.SLOW_DATABASE_QUERY_THRESHOLD_MS
                    }
                }
            )
        else:
            logger.debug(
                f"Database query: {query_description}",
                extra={
                    "extra_data": {
                        "query": query_description,
                        "execution_time_ms": int(execution_time)
                    }
                }
            )
            
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Database query failed: {query_description}",
            extra={
                "extra_data": {
                    "query": query_description,
                    "execution_time_ms": int(execution_time),
                    "error": str(e)
                }
            },
            exc_info=True
        )
        raise


@contextmanager
def track_external_api_call(service_name: str, operation: str, **metadata):
    """
    Context manager for tracking external API calls
    
    Usage:
        with track_external_api_call("Gemini", "generate_content", model="gemini-2.0"):
            response = client.generate_content(prompt)
    """
    start_time = time.time()
    
    logger.info(
        f"External API call: {service_name}.{operation}",
        extra={
            "extra_data": {
                "service": service_name,
                "operation": operation,
                **metadata
            }
        }
    )
    
    try:
        yield
        
        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"External API call succeeded: {service_name}.{operation}",
            extra={
                "extra_data": {
                    "service": service_name,
                    "operation": operation,
                    "execution_time_ms": int(execution_time),
                    "status": "success",
                    **metadata
                }
            }
        )
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"External API call failed: {service_name}.{operation}",
            extra={
                "extra_data": {
                    "service": service_name,
                    "operation": operation,
                    "execution_time_ms": int(execution_time),
                    "status": "failed",
                    "error": str(e),
                    **metadata
                }
            },
            exc_info=True
        )
        raise


# ============================================================================
# METRICS COLLECTION (for Prometheus/Grafana integration)
# ============================================================================

class MetricsCollector:
    """
    Collect application metrics for monitoring dashboards
    Can be extended to export to Prometheus, Datadog, etc.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.metrics = {
                "requests_total": 0,
                "requests_failed": 0,
                "chats_uploaded": 0,
                "insights_generated": 0,
                "payments_processed": 0,
                "average_response_time_ms": 0,
            }
        return cls._instance
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a metric counter"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
    
    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge metric value"""
        self.metrics[metric_name] = value
    
    def get_metrics(self) -> dict:
        """Get all current metrics"""
        return self.metrics.copy()
    
    def reset(self):
        """Reset all metrics (useful for testing)"""
        for key in self.metrics:
            self.metrics[key] = 0


# Singleton instance
metrics = MetricsCollector()


# ============================================================================
# EXAMPLE USAGE IN SERVICES
# ============================================================================

# In chats/service.py:
"""
@track_time("parse_whatsapp_file")
def parse_whatsapp_file(file_path: str):
    with track_operation("extract_zip", file_path=file_path):
        if file_path.endswith('.zip'):
            extracted_path = extract_txt_from_zip(file_path)
    
    with track_operation("whatstk_parse"):
        chat = whatstk.WhatsAppChat.from_source(parse_path)
    
    return chat, participants, title, metadata
"""

# In rag/service.py:
"""
def call_gemini_structured(prompt: str, response_schema: dict):
    with track_external_api_call(
        "Gemini",
        "generate_content",
        model=settings.GEMINI_LLM_MODEL,
        prompt_length=len(prompt)
    ):
        response = client.models.generate_content(...)
    
    return result, tokens_used
"""

# In vector/service.py:
"""
@retry_on_failure(max_attempts=3, delay_seconds=2.0)
def index_chunks_to_qdrant(chat_id: str, chunks: list):
    with track_external_api_call("Qdrant", "upsert", chunk_count=len(chunks)):
        qdrant_client.upsert(
            collection_name="chats",
            points=points
        )
"""