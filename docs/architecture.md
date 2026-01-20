# Architecture

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI 0.104+ | REST API framework |
| **Database** | PostgreSQL 15 | Relational data |
| **Vector DB** | Qdrant | RAG (semantic search) |
| **Cache** | Redis 7 | Session cache, Celery broker |
| **Queue** | Celery 5.4 | Background jobs |
| **AI** | Google Gemini 2.0 | LLM & embeddings |
| **Auth** | Clerk | User authentication |
| **Payments** | Razorpay | Payment processing |
| **ORM** | SQLAlchemy 2.0 | Database ORM |
| **Migrations** | Alembic | Schema versioning |

## System Architecture

```
┌─────────────┐
│   Frontend  │
│  (Next.js)  │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌──────────────────────────────────────┐
│         FastAPI Backend              │
├──────────────────────────────────────┤
│  Routers: /chats /insights /credits  │
│  Services: Credit, Vector, RAG       │
│  Auth: Clerk JWT validation          │
└───┬──────────────┬──────────┬────────┘
    │              │          │
    ↓              ↓          ↓
┌─────────┐  ┌─────────┐  ┌─────────┐
│PostgreSQL│  │  Redis  │  │ Qdrant  │
│ (Chats,  │  │ (Cache, │  │(Vectors)│
│ Users)   │  │ Celery) │  │         │
└─────────┘  └────┬────┘  └─────────┘
                  │
            ┌─────▼─────┐
            │   Celery  │
            │  Workers  │
            │ (Insights)│
            └───────────┘
```

## Folder Structure

```
src/
├── auth/                    # Clerk JWT authentication
│   └── dependencies.py      # get_current_user_id()
├── users/                   # User management, credit balance
│   ├── models.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── chats/                   # Chat upload, parsing, storage
│   ├── models.py            # Chat, Message
│   ├── router.py            # /chats endpoints
│   ├── schemas.py
│   └── service.py           # WhatsApp parser
├── categories/              # Analysis categories
│   ├── router.py
│   └── schemas.py
├── credits/                 # Credit system
│   ├── models.py            # CreditTransaction, CreditPackage
│   ├── router.py
│   ├── schemas.py
│   └── service.py           # unlock_insights_for_category()
├── insights/                # Insight management
│   └── router.py            # /insights endpoints
├── rag/                     # AI generation
│   ├── models.py            # Insight, InsightType, InsightGenerationJob
│   ├── router.py
│   ├── schemas.py
│   ├── service.py           # generate_insight()
│   ├── generation_service.py # Async orchestrator
│   ├── sync_generation_service.py # Sync orchestrator (Celery)
│   ├── rag_optimizer.py     # Context caching
│   └── tasks.py             # Celery tasks
├── vector/                  # Vector operations
│   ├── models.py            # MessageChunk
│   ├── service.py           # VectorService
│   ├── chunking.py          # Conversation-aware chunking
│   └── qdrant_client.py     # Qdrant client
├── payments/                # Payment processing
│   ├── base.py
│   ├── factory.py
│   ├── providers/
│   │   ├── razorpay_provider.py
│   │   └── stripe_provider.py
│   ├── router.py            # Webhooks
│   ├── models.py
│   ├── schemas.py
│   └── service.py
├── celery_app.py            # Celery configuration
├── config.py                # Pydantic settings
├── database.py              # SQLAlchemy setup
├── error_handlers.py        # Custom exceptions
├── logging_config.py        # Structured logging
├── middleware.py            # Request/response middleware
├── monitoring.py            # Performance tracking
└── main.py                  # FastAPI app
```

## Request Flow: Unlock Insights

```
1. Frontend: POST /api/insights/unlock
   ↓
2. insights/router.py:unlock_insights()
   - Authenticates user (Clerk JWT)
   - Validates coin balance
   ↓
3. credits/service.py:unlock_insights_for_category()
   - Checks balance
   - Deducts 400 coins
   - Updates chat status
   ↓
4. generation_service.py:create_generation_job_async()
   - Creates InsightGenerationJob
   - Creates 6 Insight records (status=pending)
   ↓
5. Celery: orchestrate_insight_generation (tasks.py)
   - Launches orchestration task
   ↓
6. sync_generation_service.py:
   - start_job() - Mark running
   - extract_shared_context() - RAG once
   - Store in Redis (20 min TTL)
   ↓
7. Celery Chord: generate_single_insight × 6 (parallel)
   - Fetch context from Redis
   - Call Gemini with JSON schema
   - Store in Insight.content
   - Update job progress
   ↓
8. finalize_generation_job (chord callback)
   - All complete: Keep coins deducted
   - Any failed: Refund coins
   ↓
9. Frontend: Polls /api/insights/jobs/{job_id}/status
   - Returns progress, completed count, ETA
   ↓
10. GET /api/insights/chats/{chat_id}
    - Returns all 6 completed insights
```

## Database Schema (Core Tables)

### users
```sql
user_id VARCHAR PRIMARY KEY           -- Clerk ID
email VARCHAR UNIQUE
credit_balance INTEGER DEFAULT 50
created_at TIMESTAMP
```

### chats
```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users)
title VARCHAR
chat_metadata JSON                    -- Free stats
vector_status VARCHAR                 -- pending/completed
category_id UUID FK(analysis_categories)
insights_generation_status VARCHAR    -- queued/generating/completed
insights_job_id VARCHAR
```

### insights
```sql
id UUID PRIMARY KEY
chat_id UUID FK(chats)
insight_type_id UUID FK(insight_types)
content JSON                          -- Structured data
status ENUM                           -- pending/generating/completed/failed
tokens_used INTEGER
UNIQUE(chat_id, insight_type_id)
```

### credit_transactions
```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users)
transaction_type ENUM                 -- signup_bonus/purchase/insight_unlock/refund
amount INTEGER                        -- Positive or negative
balance_after INTEGER
metadata JSON                         -- {chat_id, category_id}
```

## Connection Management

**Critical**: Different connection pooling strategies

**API (FastAPI)**:
- Uses `QueuePool`
- `pool_size=2, max_overflow=0`
- Handles HTTP requests

**Celery Workers**:
- Uses `NullPool` (no pooling)
- Set `CELERY_WORKER=true` env var
- Each task gets fresh connection, closes immediately
- Prevents connection exhaustion

## Key Design Patterns

### 1. Insight Generation Pipeline
- **Orchestrator Pattern**: Coordinates parallel task execution
- **Chord Pattern** (Celery): All tasks complete before callback
- **RAG Pattern**: Semantic search + LLM for context-aware insights

### 2. Credit System
- **Immediate Deduction**: Deduct coins before generation starts
- **Refund Logic**: Auto-refund if any insights fail
- **Transaction Ledger**: All changes in credit_transactions table

### 3. Error Handling
- **Custom Exceptions**: AppError, ValidationError, InsufficientCreditsException
- **Structured Logging**: JSON logs with context
- **Graceful Degradation**: Non-critical failures don't block requests

### 4. Vector Indexing
- **Lazy Indexing**: Created on unlock, not upload (saves 95% of embedding costs)
- **Conversation-Aware Chunking**: Groups messages into context windows
- **Caching**: RAG context cached in Redis (20 min TTL)

## Performance Characteristics

### Upload (5.4MB, 2-year chat)
- Parse + DB insert: ~1:35 min
- Vector indexing: Triggered on unlock

### Insight Generation
- 6 insights parallel: ~8 min total
- Context extraction (once): ~2-3 sec
- Single insight generation: ~60-90 sec
- Gemini API: 2-3K tokens/insight

### Scalability
- Celery: Increase worker concurrency
- Database: Index on (chat_id, user_id)
- Qdrant: Scales to 10K+ chats easily
- Redis: Cache hit rate >80%
