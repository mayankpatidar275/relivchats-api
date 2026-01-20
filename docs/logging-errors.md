# Logging and Error Handling Documentation

## Overview

This document covers the production-grade logging and error handling system implemented for RelivChats API. The system is designed to be:

- **Scalable**: Handles high-volume logging without performance impact
- **Structured**: JSON logs for easy parsing by log aggregation tools
- **Comprehensive**: Captures all errors, performance metrics, and business events
- **Maintainable**: Centralized configuration and consistent patterns

## Table of Contents

1. [Architecture](#architecture)
2. [Setup and Configuration](#setup-and-configuration)
3. [Usage Examples](#usage-examples)
4. [Error Handling](#error-handling)
5. [Performance Monitoring](#performance-monitoring)
6. [Best Practices](#best-practices)
7. [Integration with Monitoring Tools](#integration-with-monitoring-tools)

---

## Architecture

### Components

```
src/
├── logging_config.py        # Centralized logging setup
├── error_handlers.py         # Custom exceptions and handlers
├── middleware.py             # Request/response logging
├── monitoring.py             # Performance tracking utilities
└── main.py                   # Application initialization
```

### Log Flow

```
Request → Middleware (log start) → Router → Service → Database/External API
                                     ↓          ↓            ↓
                                   Logs     Logs        Logs
                                     ↓          ↓            ↓
                              Structured Logger (JSON)
                                     ↓
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
                 Console        File (app.log)   File (errors.log)
                    ↓                               ↓
            Development View              Aggregation Service
                                         (ELK, Datadog, etc.)
```

---

## Setup and Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                   # json or human
ENABLE_FILE_LOGGING=true          # Enable writing to log files
ENVIRONMENT=production            # development, staging, production

# Performance Thresholds
SLOW_REQUEST_THRESHOLD_SECONDS=2.0
SLOW_DATABASE_QUERY_THRESHOLD_MS=1000

# Optional: Error Tracking Services
SENTRY_DSN=https://your-sentry-dsn@sentry.io/123456
SENTRY_TRACES_SAMPLE_RATE=0.1

# Support Contact
SUPPORT_EMAIL=support@relivchats.com
```

### 2. Development vs Production

**Development:**

```bash
LOG_LEVEL=DEBUG
LOG_FORMAT=human
ENVIRONMENT=development
EXPOSE_ERROR_DETAILS=true
```

**Production:**

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=production
EXPOSE_ERROR_DETAILS=false
SENTRY_DSN=your-real-dsn
```

### 3. Log Files

Logs are automatically rotated and stored in `logs/` directory:

- `app.log` - General application logs (max 10MB, 5 backups)
- `errors.log` - Error logs only (daily rotation, 30 days retention)
- `business.log` - Business events tracking (max 10MB, 10 backups)

---

## Usage Examples

### 1. Basic Logging in Routes

```python
from src.logging_config import get_logger

logger = get_logger(__name__)

@router.post("/chats/upload")
def upload_chat(file: UploadFile, user_id: str = Depends(get_current_user_id)):
    logger.info(
        "Chat upload started",
        extra={
            "user_id": user_id,
            "extra_data": {
                "filename": file.filename,
                "file_size": file.size
            }
        }
    )

    try:
        # Process file
        result = process_file(file)

        logger.info(
            "Chat upload completed",
            extra={
                "user_id": user_id,
                "extra_data": {
                    "chat_id": result.id,
                    "message_count": result.message_count
                }
            }
        )

        return result

    except Exception as e:
        logger.error(
            f"Chat upload failed: {e}",
            extra={"user_id": user_id},
            exc_info=True  # Includes full stack trace
        )
        raise
```

### 2. Structured Logging

All logs are automatically structured in JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "src.chats.router",
  "message": "Chat upload started",
  "module": "router",
  "function": "upload_chat",
  "line": 42,
  "user_id": "user_abc123",
  "request_id": "req_xyz789",
  "extra": {
    "filename": "chat.txt",
    "file_size": 1024000
  }
}
```

### 3. Business Event Logging

Track important business events for analytics:

```python
from src.logging_config import log_business_event

# After successful payment
log_business_event(
    event_type="payment_completed",
    user_id=user_id,
    order_id=str(order.id),
    amount=order.amount,
    currency=order.currency,
    payment_method="razorpay"
)

# After insight generation
log_business_event(
    event_type="insight_generated",
    user_id=user_id,
    chat_id=str(chat_id),
    insight_type=insight_type.name,
    tokens_used=tokens,
    generation_time_ms=time_ms
)
```

### 4. Using Custom Exceptions

```python
from src.error_handlers import (
    NotFoundException,
    InsufficientCreditsException,
    FileProcessingException,
    ErrorCode
)

# In service layer
def get_chat(db: Session, chat_id: UUID, user_id: str):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()

    if not chat:
        raise NotFoundException("Chat", str(chat_id))

    if chat.user_id != user_id:
        raise ForbiddenException("Access denied to this chat")

    return chat

# For credit checks
if user.credit_balance < required_credits:
    raise InsufficientCreditsException(
        required=required_credits,
        available=user.credit_balance
    )

# For file processing errors
if not is_valid_format(file):
    raise FileProcessingException(
        "Invalid WhatsApp chat format",
        error_code=ErrorCode.INVALID_FILE_FORMAT
    )
```

### 5. Performance Tracking

```python
from src.monitoring import track_time, track_operation, track_external_api_call

# Track function execution time
@track_time("parse_whatsapp_file")
def parse_whatsapp_file(file_path: str):
    # ... parsing logic
    return chat

# Track specific operations
def process_chat(chat_id: UUID):
    with track_operation("chunk_messages", chat_id=str(chat_id)):
        chunks = create_chunks(messages)

    with track_operation("embed_chunks", chunk_count=len(chunks)):
        embeddings = generate_embeddings(chunks)

# Track external API calls
def generate_insight(prompt: str):
    with track_external_api_call(
        "Gemini",
        "generate_content",
        model="gemini-2.0-flash",
        prompt_length=len(prompt)
    ):
        response = client.generate_content(prompt)

    return response
```

### 6. Database Query Tracking

```python
from src.monitoring import track_database_query

def get_user_chats(db: Session, user_id: str):
    with track_database_query("fetch user chats with category"):
        chats = db.query(Chat)\
            .options(joinedload(Chat.category))\
            .filter(Chat.user_id == user_id)\
            .all()

    return chats
```

### 7. Retry Logic with Logging

```python
from src.monitoring import retry_on_failure

@retry_on_failure(max_attempts=3, delay_seconds=1.0, exponential_backoff=True)
def call_payment_gateway(order_id: str):
    # This will automatically retry on failure with:
    # Attempt 1: immediate
    # Attempt 2: after 1s
    # Attempt 3: after 2s
    # All attempts are logged

    response = razorpay_client.create_order(...)
    return response
```

---

## Error Handling

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "ERR_3000",
    "message": "Insufficient credits. Required: 50, Available: 20",
    "timestamp": "2024-01-15T10:30:00.123Z",
    "request_id": "req_xyz789",
    "details": {
      "required": 50,
      "available": 20,
      "deficit": 30
    },
    "support": "Contact support@relivchats.com"
  }
}
```

### Error Codes Reference

| Code     | Type                  | Description                  |
| -------- | --------------------- | ---------------------------- |
| ERR_1000 | Internal Server Error | Unexpected server error      |
| ERR_1001 | Validation Error      | Request validation failed    |
| ERR_1002 | Not Found             | Resource not found           |
| ERR_1003 | Unauthorized          | Authentication required      |
| ERR_1004 | Forbidden             | Access denied                |
| ERR_1005 | Rate Limit            | Too many requests            |
| ERR_2000 | Database Error        | Database operation failed    |
| ERR_2001 | Integrity Error       | Database constraint violated |
| ERR_3000 | Insufficient Credits  | Not enough credits           |
| ERR_3002 | Processing Failed     | Chat processing failed       |
| ERR_3003 | Invalid File          | Invalid file format          |
| ERR_3004 | File Too Large        | File exceeds size limit      |
| ERR_3005 | Indexing Failed       | Vector indexing failed       |
| ERR_3006 | Insight Failed        | Insight generation failed    |
| ERR_4000 | Gemini Error          | Gemini API error             |
| ERR_4001 | Qdrant Error          | Vector DB error              |
| ERR_4004 | Payment Gateway       | Payment provider error       |

### Creating Custom Exceptions

```python
# In your service
from src.error_handlers import AppException, ErrorCode

class ChatLimitExceededException(AppException):
    def __init__(self, current: int, max_allowed: int):
        super().__init__(
            message=f"Chat limit exceeded. You have {current}/{max_allowed} chats.",
            error_code="ERR_3010",
            status_code=403,
            details={
                "current_count": current,
                "max_allowed": max_allowed
            }
        )
```

---

## Performance Monitoring

### Slow Request Detection

Requests taking longer than `SLOW_REQUEST_THRESHOLD_SECONDS` (default: 2s) are automatically flagged:

```json
{
  "level": "WARNING",
  "message": "Slow request detected: POST /chats/upload",
  "extra": {
    "process_time_ms": 3456,
    "threshold_exceeded": true
  }
}
```

### Slow Database Query Detection

Queries exceeding `SLOW_DATABASE_QUERY_THRESHOLD_MS` (default: 1000ms) are logged:

```json
{
  "level": "WARNING",
  "message": "Slow database query: fetch user chats with category",
  "extra": {
    "query": "fetch user chats with category",
    "execution_time_ms": 1234,
    "threshold": 1000
  }
}
```

### Metrics Collection

```python
from src.monitoring import metrics

# Metrics are automatically collected
# Access them via endpoint:
@router.get("/metrics")
def get_metrics():
    return metrics.get_metrics()

# Returns:
{
  "requests_total": 15234,
  "requests_failed": 42,
  "chats_uploaded": 1523,
  "insights_generated": 8945,
  "payments_processed": 234,
  "average_response_time_ms": 245
}
```

---

## Best Practices

### 1. Always Include User Context

```python
# ✅ Good
logger.info(
    "Operation performed",
    extra={
        "user_id": user_id,  # Always include user_id
        "extra_data": {...}
    }
)

# ❌ Bad
logger.info("Operation performed")
```

### 2. Log at Appropriate Levels

```python
# DEBUG: Detailed diagnostic info
logger.debug(f"Processing chunk {i}/{total}", extra={"user_id": user_id})

# INFO: General informational messages
logger.info("Chat uploaded successfully", extra={"user_id": user_id})

# WARNING: Potential issues that don't stop execution
logger.warning("Slow database query detected", extra={"user_id": user_id})

# ERROR: Errors that need attention
logger.error("Payment processing failed", extra={"user_id": user_id}, exc_info=True)

# CRITICAL: Severe errors requiring immediate action
logger.critical("Database connection lost", exc_info=True)
```

### 3. Include Relevant Context

```python
# ✅ Good - Rich context
logger.error(
    "Insight generation failed",
    extra={
        "user_id": user_id,
        "extra_data": {
            "insight_id": str(insight_id),
            "insight_type": insight_type.name,
            "chat_id": str(chat_id),
            "tokens_attempted": tokens,
            "error_type": type(e).__name__
        }
    },
    exc_info=True
)

# ❌ Bad - Insufficient context
logger.error(f"Error: {e}")
```

### 4. Use Business Event Logging

```python
# Track important business metrics
log_business_event(
    "insight_unlocked",
    user_id=user_id,
    chat_id=str(chat_id),
    category=category.name,
    credits_spent=total_cost,
    insight_count=len(insights)
)
```

### 5. Don't Log Sensitive Data

```python
# ❌ BAD - Logging passwords, tokens, personal data
logger.info(f"User logged in: {user.email}, password: {password}")

# ✅ GOOD - Log only non-sensitive identifiers
logger.info(
    "User logged in",
    extra={
        "user_id": user.id,
        "login_method": "password"
    }
)
```

---

## Integration with Monitoring Tools

### 1. Sentry (Error Tracking)

Already integrated in `main.py`. Just set `SENTRY_DSN` in `.env`:

```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1  # Sample 10% of transactions
```

### 2. ELK Stack (Elasticsearch + Logstash + Kibana)

Configure Filebeat to ship logs:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /path/to/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

### 3. Datadog

Install the Datadog agent and configure log collection:

```yaml
# datadog.yaml
logs_enabled: true
logs_config:
  container_collect_all: true
```

### 4. CloudWatch (AWS)

Use CloudWatch Logs agent:

```bash
# Install CloudWatch agent
sudo apt-get install amazon-cloudwatch-agent

# Configure to collect logs from logs/ directory
```

### 5. Grafana + Loki

Configure Promtail to scrape logs:

```yaml
# promtail-config.yaml
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: relivchats
    static_configs:
      - targets:
          - localhost
        labels:
          job: relivchats
          __path__: /path/to/logs/*.log
```

---

## Testing

### 1. Test Logging in Development

```python
# tests/test_logging.py
from src.logging_config import get_logger

logger = get_logger(__name__)

def test_logging():
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Check logs/ directory for output
```

### 2. Test Error Handling

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_not_found_error():
    response = client.get("/chats/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ERR_1002"

def test_validation_error():
    response = client.post("/chats/upload", files={})
    assert response.status_code == 422
    assert "validation_errors" in response.json()["error"]["details"]
```

---

## Troubleshooting

### Logs not appearing?

1. Check `ENABLE_FILE_LOGGING=true` in `.env`
2. Ensure `logs/` directory exists and is writable
3. Verify `LOG_LEVEL` is not set too high (use `DEBUG` for troubleshooting)

### Too many logs?

1. Increase `LOG_LEVEL` to `WARNING` or `ERROR`
2. Add paths to `RequestLoggingMiddleware.EXCLUDED_PATHS`
3. Adjust third-party library log levels in `logging_config.py`

### Performance impact?

1. Use `LOG_FORMAT=json` in production (faster than human-readable)
2. Disable console logging in production (log to files only)
3. Use asynchronous log handlers if needed

---

## Quick Migration Guide

### 1. Update existing code

Replace all `print()` statements:

```python
# Before
print(f"Processing chat {chat_id}")

# After
logger.info("Processing chat", extra={"extra_data": {"chat_id": str(chat_id)}})
```

### 2. Replace generic exceptions

```python
# Before
raise HTTPException(status_code=404, detail="Chat not found")

# After
raise NotFoundException("Chat", str(chat_id))
```

### 3. Add tracking to slow operations

```python
# Before
def expensive_operation():
    result = do_work()
    return result

# After
@track_time("expensive_operation")
def expensive_operation():
    result = do_work()
    return result
```

---

## Summary Checklist

- [ ] Update `.env` with logging configuration
- [ ] Add logging to all routers and services
- [ ] Replace `HTTPException` with custom exceptions
- [ ] Add performance tracking to critical paths
- [ ] Test error responses in development
- [ ] Configure log aggregation service (optional)
- [ ] Set up Sentry for production error tracking (optional)
- [ ] Review logs regularly and adjust thresholds
- [ ] Document team logging conventions

---

For questions or issues, contact the backend team or file an issue in the repository.
