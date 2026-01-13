# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**RelivChats API** is a FastAPI-based SaaS platform that analyzes WhatsApp chat conversations and generates AI-powered psychological insights. Users upload chats (free), receive instant statistics, then pay credits to unlock category-specific insights (6 insights per category) via Google Gemini 2.0.

**Key characteristics:**
- Credit-based monetization (no subscriptions)
- Asynchronous insight generation with Celery workers
- RAG pipeline with Qdrant vector database for semantic search
- PostgreSQL with Alembic migrations
- Multi-provider payment system (Razorpay + Stripe)
- Clerk-based JWT authentication

---

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15
- Redis 7
- Docker & Docker Compose

### Quick Start

```bash
# Clone and setup
git clone <repo>
cd relivchats-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (DATABASE_URL, GEMINI_API_KEY, CLERK_SECRET_KEY, etc.)

# Start services (PostgreSQL, Redis, Qdrant)
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
alembic upgrade head

# Seed database (analysis categories, insight types, credit packages)
# Optional - seed data may already exist

# Start Celery worker (in separate terminal)
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info --concurrency=1

# Start API server
uvicorn src.main:app --reload --port 8000

# Access API docs
http://localhost:8000/docs
```

---

## Common Development Commands

### Running the API
```bash
# Development with auto-reload
uvicorn src.main:app --reload --port 8000

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Running Celery Workers
```bash
# Start worker (note: CELERY_WORKER=true env var is important - disables connection pooling)
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info --concurrency=1

# Monitor tasks with Flower
celery -A src.celery_app flower --port 5555
# Access: http://localhost:5555
```

### Database Migrations
```bash
# Create new migration (auto-detects changes)
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current migration
alembic current
```

### Testing & Linting
```bash
# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/chats/test_parser.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Linting (format + check)
black src/
isort src/
flake8 src/
```

### Docker
```bash
# Build Docker image
docker build -t relivchats-api .

# Run full stack with compose
docker-compose -f docker-compose.dev.yml up -d

# Stop services
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f app
docker-compose -f docker-compose.dev.yml logs -f celery_worker
```

---

## Architecture Overview

### Codebase Structure

```
src/
├── main.py                  # FastAPI app setup, lifespan events, routers
├── config.py                # Pydantic settings management
├── database.py              # SQLAlchemy engine & session factory
├── celery_app.py            # Celery configuration & signal handlers
├── error_handlers.py        # Custom exception handlers
├── logging_config.py        # Structured logging setup
├── middleware.py            # Request/response middleware
├── monitoring.py            # Performance monitoring utilities
│
├── auth/                    # Clerk JWT authentication
│   └── dependencies.py      # get_current_user dependency
│
├── users/                   # User management & credit balance
│   ├── models.py            # User ORM model
│   ├── router.py            # /api/users endpoints
│   ├── schemas.py           # Pydantic schemas
│   └── service.py           # Business logic
│
├── chats/                   # Chat upload, parsing, storage
│   ├── models.py            # Chat, Message ORM models
│   ├── router.py            # /api/chats endpoints (upload, list, get, delete)
│   ├── schemas.py           # Pydantic schemas
│   └── service.py           # WhatsApp parser (whatstk library)
│
├── categories/              # Analysis categories (Romantic, Friendship, etc.)
│   ├── router.py            # /api/categories endpoints
│   └── schemas.py
│
├── credits/                 # Credit system & transactions
│   ├── models.py            # CreditTransaction, CreditPackage, CoinReservation
│   ├── router.py            # /api/credits endpoints
│   ├── schemas.py
│   └── service.py           # unlock_insights_for_category(), refund logic
│
├── insights/                # Insight management (NEW)
│   ├── router.py            # /api/insights endpoints (unlock, status, get)
│   └── schemas.py
│
├── rag/                     # RAG pipeline & insight generation
│   ├── models.py            # Insight, InsightType, InsightGenerationJob ORM
│   ├── router.py            # /api/rag/query endpoint
│   ├── schemas.py
│   ├── service.py           # generate_insight() - core AI logic
│   ├── generation_service.py # InsightGenerationOrchestrator - task orchestration
│   ├── rag_optimizer.py     # RAG context caching
│   ├── sync_generation_service.py # Sync version of orchestrator
│   └── tasks.py             # Celery tasks (task_generate_insight_group)
│
├── vector/                  # Vector DB operations (Qdrant)
│   ├── models.py            # MessageChunk ORM model
│   ├── service.py           # VectorService - chunk creation, deletion
│   ├── chunking.py          # Conversation-aware chunking logic
│   └── qdrant_client.py     # Qdrant client wrapper
│
├── payments/                # Payment processing
│   ├── base.py              # PaymentProvider base class
│   ├── factory.py           # Factory pattern to select provider
│   ├── providers/
│   │   ├── razorpay_provider.py
│   │   └── stripe_provider.py
│   ├── router.py            # Webhook endpoints
│   ├── models.py            # PaymentOrder, PaymentRefund ORM
│   ├── schemas.py
│   └── service.py           # Payment orchestration
│
└── seed/                    # SQL seed files for initial data
    ├── analysis_category.sql
    ├── insight_types.sql
    ├── category_insight_types.sql
    └── credit_packages.sql
```

### Request Flow: Unlock Insights (Key User Flow)

```
1. Frontend: User clicks "Unlock Romantic Insights (400 coins)"
   ↓
2. POST /api/insights/unlock
   {
     "chat_id": "uuid",
     "category_id": "romantic"
   }
   ↓
3. insights/router.py:unlock_insights()
   - Authenticates user (Clerk JWT)
   - Validates coin balance
   - Calls credits/service.py:unlock_insights_for_category()
   ↓
4. credits/service.py:unlock_insights_for_category()
   - Checks coins available
   - Creates CoinReservation (temporary hold)
   - Updates Chat.insights_generation_status = "queued"
   - Calls rag/generation_service.py:InsightGenerationOrchestrator.start_insight_generation()
   ↓
5. InsightGenerationOrchestrator.start_insight_generation()
   - Creates InsightGenerationJob (tracks overall progress)
   - Chunks chat vectors (if not already indexed)
   - Creates 6 Insight records with status="pending"
   - Uses Celery chord to run tasks in parallel
   - Launches task_generate_insight_group Celery task
   ↓
6. Celery Worker: task_generate_insight_group (parallel x6)
   - Fetches context from Qdrant (RAG)
   - Calls Gemini API with insight-specific prompt
   - Stores result in Insight.content JSON
   - Sets Insight.status = "completed"
   ↓
7. Chord callback (all 6 complete or fail)
   - If ALL succeeded: Deduct coins, create CreditTransaction
   - If ANY failed (>50%): Refund coins
   - Update InsightGenerationJob.status = "completed"
   ↓
8. Frontend: Polls /api/insights/jobs/{job_id}/status
   - Returns: progress_percentage, completed_insights, estimated_completion_at
   ↓
9. When complete: Frontend calls GET /api/insights/chats/{chat_id}
   - Returns all 6 completed insights with content
```

### Database Connection Management

**Critical detail**: The codebase uses different connection pooling strategies:

- **API/Web (FastAPI)**: `QueuePool` with `pool_size=2, max_overflow=0` (src/database.py)
  - Connection pooling for HTTP requests
  - Set via environment detection (not Celery worker)

- **Celery Workers**: `NullPool` (no pooling)
  - Each task gets fresh connection, closes immediately
  - Triggered by `CELERY_WORKER=true` environment variable
  - Prevents connection exhaustion in worker processes

**Important**: Always set `CELERY_WORKER=true` when starting Celery workers, or connection pooling will exhaust database.

---

## Key Design Patterns

### 1. Insight Generation Pipeline
- **Orchestrator Pattern** (InsightGenerationOrchestrator): Coordinates parallel task execution
- **Chord Pattern** (Celery): All subtasks complete before callback
- **RAG Pattern**: Semantic search + LLM for context-aware generation

### 2. Credit System
- **Reservation Pattern**: Hold coins before generation, deduct after success
- **Refund Logic**: If >50% insights fail, automatically refund coins
- **Transaction Ledger**: All credit changes recorded in CreditTransaction table

### 3. Error Handling
- **Custom Exception Classes** (error_handlers.py): AppError, ValidationError, etc.
- **Structured Logging**: JSON logs with context data for debugging
- **Graceful Degradation**: Non-critical failures don't block main requests

### 4. Vector Indexing
- **Lazy Indexing**: Chat vectors created on-demand (during insight unlock), not on upload
- **Conversation-Aware Chunking** (chunking.py): Groups messages into context windows, not random splits
- **Caching** (RAG Optimizer): Caches extracted context to avoid repeated vector queries

---

## Important Implementation Details

### Gemini API Integration (src/rag/service.py)

```python
# Using google-genai library (new, not google-generativeai)
from google import genai
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Structured output with response schemas
response = client.models.generate_content(
    model=settings.GEMINI_LLM_MODEL,  # "gemini-2.5-flash"
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=insight_type.response_schema  # JSONB from DB
    )
)
```

### Qdrant Vector Database (src/vector/)

```python
# Collection: "chat_messages" (3072-dim vectors from Gemini embeddings)
# Operations: Create chunks on unlock, semantic search during generation
from qdrant_client import QdrantClient
client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

# Vector operations are async-safe (uses httpx internally)
```

### Celery Task Execution (src/rag/tasks.py)

```python
# Insight generation launches as Celery chord:
from celery import chord

callback = chord(
    [task_generate_single_insight.s(...) for each insight],
    callback_fn.s()
).apply_async()

# Tasks timeout after INSIGHT_GENERATION_TIMEOUT (120 sec by default)
# Retries up to 2 times on failure with 5s delay
```

### Migrations & Schema Changes

- Use Alembic for ALL schema changes (never raw SQL)
- Migrations tracked in `alembic/versions/`
- Common issues: Timezone handling (use `datetime.timezone.utc`), foreign key constraints
- **Always create reversible migrations** (`upgrade()` and `downgrade()` functions)

---

## Common Gotchas & Debugging

### 1. Celery Tasks Not Running
```bash
# Check if worker is listening
celery -A src.celery_app inspect active

# Check Redis connection
redis-cli ping

# Restart worker
pkill -f celery
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info
```

### 2. Vector Indexing Fails
```bash
# Check Qdrant health
curl http://localhost:6333/health

# Restart Qdrant
docker-compose -f docker-compose.dev.yml restart qdrant
```

### 3. Database Connection Errors
- Always check `CELERY_WORKER=true` env var when starting workers
- FastAPI using `QueuePool`, workers using `NullPool`
- Check connection pool status: `GET /health/db-pool`

### 4. Insight Generation Hangs
- Check Gemini API rate limits (quota issues)
- Verify RAG context not too large (max 10K tokens)
- Check logs: `logs/app.log` for structured JSON error details

### 5. Credit Deduction Issues
- Coins only deducted AFTER all insights complete
- Check `CoinReservation` table for stuck reservations (timeout after 30 min)
- Manual refund: `POST /api/insights/{insight_id}/refund`

---

## Code Style & Conventions

### File Organization
- One main class/service per file (e.g., `VectorService` in `vector/service.py`)
- Router file = endpoint definitions only (logic in service)
- Models = ORM definitions; Schemas = Pydantic request/response

### Naming Conventions
- Database models: PascalCase (e.g., `InsightType`, `CreditTransaction`)
- Database tables: snake_case (auto-generated by SQLAlchemy)
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE

### Type Hints
- All function signatures should include return type
- Use `Optional[X]` instead of `X | None` for backwards compatibility
- Pydantic models for all request/response bodies

### Logging
```python
from .logging_config import get_logger

logger = get_logger(__name__)

# Structured logging with context
logger.info(
    "User unlocked insights",
    extra={"extra_data": {
        "user_id": user_id,
        "chat_id": chat_id,
        "coin_cost": 400
    }}
)
```

---

## Database Notes

### Key Tables

**Users** (from Clerk)
- `user_id` (VARCHAR): Clerk user ID (primary key)
- `credit_balance` (INTEGER): Current coin balance
- `created_at` (TIMESTAMP WITH TZ)

**Chats** (user-uploaded conversations)
- `id` (UUID): Primary key
- `user_id` (VARCHAR): Foreign key to users
- `category_id` (UUID): Analysis category (romantic, friendship, etc.)
- `vector_status` (VARCHAR): pending → indexing → completed
- `insights_generation_status` (VARCHAR): not_started → queued → generating → completed
- `chat_metadata` (JSON): Free statistics (message counts, word clouds, etc.)

**Insights** (generated AI insights)
- `id` (UUID): Primary key
- `chat_id` (UUID): Foreign key to chats
- `insight_type_id` (UUID): Type of insight (e.g., "communication_basics")
- `content` (JSON): Structured insight data
- `status` (ENUM): pending → generating → completed/failed
- `tokens_used` (INTEGER): Gemini API token count
- UNIQUE constraint: (chat_id, insight_type_id)

**CreditTransaction** (all credit movements)
- `id` (UUID): Primary key
- `user_id` (VARCHAR): Foreign key to users
- `transaction_type` (ENUM): signup_bonus, purchase, insight_unlock, refund
- `amount` (INTEGER): Positive or negative
- `balance_after` (INTEGER): User balance after transaction
- `metadata` (JSON): {chat_id, category_id, payment_id}

**CoinReservation** (temporary hold during generation)
- `id` (UUID): Primary key
- `user_id` (VARCHAR): Foreign key to users
- `coins_reserved` (INTEGER): Hold amount
- `expires_at` (TIMESTAMP WITH TZ): Auto-cleanup after 30 minutes

### Useful Queries
```sql
-- Check user balance
SELECT credit_balance FROM users WHERE user_id = 'clerk_user_123';

-- Get all insights for a chat
SELECT * FROM insights WHERE chat_id = 'chat_uuid' ORDER BY created_at;

-- Get credit transactions for audit
SELECT * FROM credit_transactions WHERE user_id = 'clerk_user_123' ORDER BY created_at DESC;

-- Check job progress
SELECT * FROM insight_generation_jobs WHERE job_id = 'job_uuid';
```

---

## Deployment Notes

### Environment Variables (Production)
Ensure these are set in production:
- `DATABASE_URL` - NeonDB or AWS RDS PostgreSQL
- `REDIS_URL` - Redis cloud (e.g., Redis Labs)
- `QDRANT_URL` + `QDRANT_API_KEY` - Qdrant cloud
- `GEMINI_API_KEY` - Google Cloud
- `CLERK_SECRET_KEY` - Clerk dashboard
- `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` - Razorpay dashboard
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` - Stripe dashboard
- `ENVIRONMENT=production`
- `LOG_FORMAT=json` (for structured logging)
- `EXPOSE_ERROR_DETAILS=false` (don't leak errors)

### Monitoring
- **API Health**: `GET /health` (returns status + version)
- **DB Pool Status**: `GET /health/db-pool` (connection stats)
- **Celery Tasks**: Flower dashboard at port 5555
- **Logs**: Structured JSON logs in `logs/` directory

### Scaling Considerations
- **Celery**: Increase `worker_concurrency` (currently 1 for long-running tasks)
- **Database**: Monitor connection pool with `max_overflow=0` (no spikes)
- **Qdrant**: Batch size capped at 100 (see `QDRANT_BATCH_SIZE`)
- **Gemini**: Rate limits ~300 req/min (handle with retry backoff)

---

## Testing Notes

- Tests located in `tests/` directory (mirrors src structure)
- Use `pytest` with fixtures for database/Redis mocking
- Integration tests use real database (in-memory SQLite option available)
- Celery tasks testable via `celery.current_app.task()` in tests

---

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/
- **Alembic**: https://alembic.sqlalchemy.org/
- **Celery**: https://docs.celeryq.dev/
- **Qdrant**: https://qdrant.tech/documentation/
- **Google Gemini API**: https://ai.google.dev/
- **Clerk Auth**: https://clerk.com/docs

---

## Quick Troubleshooting Checklist

| Issue | Check |
|-------|-------|
| API won't start | Database URL, Redis connection, Gemini API key |
| Celery tasks not running | `CELERY_WORKER=true` env var, Redis connection, worker logs |
| Insights generation hangs | Qdrant health, Gemini rate limits, task timeout settings |
| Connection pool errors | Is this a Celery worker? Must set `CELERY_WORKER=true` |
| Vector indexing fails | Qdrant running? Collection exists? Embedding model available? |
| Coins not deducting | Check insight status = "completed", check CoinReservation timeout |
| Payment webhook not working | Webhook URL registered? Secret key correct? HTTPS required |

---

## Production Monitoring & Debugging

For production monitoring, debugging, and incident response, see:

### 📚 [PRODUCTION_MONITORING.md](./PRODUCTION_MONITORING.md)
Comprehensive guide covering:
- Docker service management & log viewing
- Database monitoring queries
- Celery worker inspection
- Redis & Qdrant health checks
- Performance monitoring
- Troubleshooting common issues

### ⚡ [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
One-page cheat sheet with copy-paste commands:
- Emergency commands (restart, health checks)
- Daily health check routine (30 seconds)
- Common log searches
- Troubleshooting specific issues

**Most common production commands:**
```bash
# Follow API logs in real-time
docker-compose logs -f relivchats-api

# Check last 100 errors
docker-compose logs relivchats-api | grep ERROR | tail -100

# Health check
curl http://localhost:8000/health | jq .

# Restart services
docker-compose restart relivchats-api
docker-compose restart celery_worker

# Check Celery worker status
docker exec celery_worker celery -A src.celery_app inspect active
```

---

**Last Updated**: January 2026
**Key Tech**: FastAPI, PostgreSQL, Celery, Qdrant, Google Gemini, Clerk
**Status**: Active Development (V1)
