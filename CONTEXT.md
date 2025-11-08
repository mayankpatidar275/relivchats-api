# CONTEXT: RelivChats - Complete Product Documentation

## 1. PRODUCT OVERVIEW

**RelivChats** is a SaaS platform that provides AI-powered insights from exported chat conversations. Users upload chat files (WhatsApp, Instagram, Telegram), receive free statistical analysis, and can unlock AI-generated psychological insights by spending coins.

### Core Value Proposition

- **Free tier**: Upload chats → Get instant statistics (message counts, activity patterns, word clouds, emoji analysis)
- **Paid tier**: Unlock category-specific AI insights (relationship analysis, conflict patterns, communication styles)
- **Privacy-first**: End-to-end encryption, GDPR compliant, no data retention beyond user control

---

## 2. BUSINESS MODEL

### Monetization Strategy

**Credit/Point System** (NOT subscription - sporadic usage pattern)

**Free Tier:**

- 50 coins on signup
- Unlimited chat uploads
- Free statistics (generated via text processing, no AI cost)

**Pricing:**

- Basic categories (Friendship, Family): 50 coins
- Advanced categories (Romantic, Professional): 100 coins
- Point packages:
  - 200P = $2.99 (2-4 analyses)
  - 500P = $5.99 (5-10 analyses)
  - 1500P = $14.99 (best value, 15-30 analyses)

**Why This Model:**

- Users don't analyze chats frequently (not suitable for subscriptions)
- Pay-per-use aligns with sporadic usage
- Minimizes API costs (only charge for AI-generated insights)

---

## 3. USER FLOW

### 3.1 Upload Flow

```
1. User visits homepage → Selects category (optional) OR uploads directly
2. Uploads chat file (.txt for WhatsApp)
3. Backend parses file → Stores in PostgreSQL
4. Generates free stats (sync, 1-2 seconds)
5. Vector indexing: LAZY (triggered on unlock, not upload)
6. User sees dashboard with free stats + "Unlock Insights" button
```

### 3.2 Unlock Flow

```
1. User selects chat → Chooses category (if not selected earlier)
2. Clicks "Unlock Insights" → Deducts 50-100 coins
3. Backend:
   a. Check vector status (if pending → index now, 1-3 sec)
   b. Create insight generation job
   c. Launch Celery tasks (parallel generation)
4. Frontend polls job status every 2-3 seconds
5. Insights appear progressively as they complete
6. If failures: User can retry individual insights (no extra charge)
```

### 3.3 Failure Handling

```
- If >50% insights fail → Automatic refund
- Individual insight failures → Manual retry (no charge)
- Vector indexing failure → Full refund before generation starts
```

---

## 4. TECHNICAL ARCHITECTURE

### 4.1 Tech Stack

```yaml
Backend:
  - Framework: FastAPI (Python 3.11+)
  - Database: PostgreSQL 15
  - Vector DB: Qdrant (for RAG)
  - Cache: Redis 7
  - Task Queue: Celery + Redis
  - AI: Google Gemini 2.0 Flash

Infrastructure:
  - Containerization: Docker + Docker Compose
  - Deployment: Render.com / Railway / AWS ECS
  - Monitoring: Celery Flower, Sentry
  - Payments: Razorpay (India-first)

Frontend (separate repo):
  - Framework: React/Next.js (TBD)
  - State: React Query (polling)
  - Charts: Recharts
```

### 4.2 Folder Structure

```
relivchats-api/
├── src/
│   ├── auth/
│   │   └── dependencies.py              # Clerk auth, get_current_user_id()
│   ├── users/
│   │   ├── models.py                    # User, credit_balance
│   │   ├── router.py                    # POST /users/store, DELETE /users/delete-account
│   │   ├── schemas.py
│   │   └── service.py
│   ├── chats/
│   │   ├── models.py                    # Chat, Message
│   │   ├── router.py                    # POST /chats/upload, GET /chats, GET /chats/{id}
│   │   ├── schemas.py
│   │   └── service.py                   # parse_whatsapp_file(), process_whatsapp_file()
│   ├── categories/
│   │   ├── router.py                    # GET /categories, GET /categories/{id}/insights
│   │   └── schemas.py
│   ├── credits/
│   │   ├── models.py                    # CreditTransaction, CreditPackage
│   │   ├── router.py                    # GET /credits/balance, GET /credits/packages
│   │   ├── schemas.py
│   │   └── service.py                   # unlock_insights_for_category(), deduct_credits()
│   ├── insights/                        # NEW (separated from rag)
│   │   └── router.py                    # POST /insights/unlock, GET /insights/jobs/{id}/status
│   ├── rag/
│   │   ├── models.py                    # Insight, InsightType, AnalysisCategory, InsightGenerationJob
│   │   ├── router.py                    # POST /rag/query (conversational Q&A)
│   │   ├── schemas.py
│   │   ├── service.py                   # generate_insight(), fetch_rag_chunks()
│   │   ├── generation_service.py        # InsightGenerationOrchestrator
│   │   ├── rag_optimizer.py             # RAGContextCache, RAGContextExtractor
│   │   └── tasks.py                     # Celery tasks: orchestrate_insight_generation()
│   ├── vector/
│   │   ├── models.py                    # MessageChunk
│   │   ├── service.py                   # VectorService, create_chat_chunks()
│   │   ├── chunking.py                  # chunk_chat_messages() - conversation-aware
│   │   └── qdrant_client.py             # Qdrant operations
│   ├── celery_app.py                    # Celery configuration
│   ├── config.py                        # Settings (Pydantic)
│   ├── database.py                      # SQLAlchemy setup
│   └── main.py                          # FastAPI app, router registration
├── alembic/
│   └── versions/                        # Database migrations
├── seed/                                # SQL seed files
│   ├── analysis_category.sql
│   ├── insight_types.sql
│   ├── category_insight_types.sql
│   └── credit_packages.sql
├── docker-compose.yml
├── Dockerfile
└── requirements/
    ├── base.txt
    ├── dev.txt
    └── prod.txt
```

---

## 5. DATABASE SCHEMA

### 5.1 Core Tables

#### **users**

```sql
user_id VARCHAR PRIMARY KEY           -- Clerk user ID
email VARCHAR UNIQUE
credit_balance INTEGER DEFAULT 0
created_at TIMESTAMP
is_deleted BOOLEAN DEFAULT FALSE
deleted_at TIMESTAMP
```

#### **chats**

```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users.user_id)
title VARCHAR                         -- Chat name
participants TEXT                     -- JSON array
chat_metadata JSON                    -- Free stats (message counts, etc.)
partner_name VARCHAR                  -- Extracted partner name
user_display_name VARCHAR             -- User's name in chat
status VARCHAR                        -- processing, completed, failed
vector_status VARCHAR                 -- pending, indexing, completed, failed
indexed_at TIMESTAMP
chunk_count INTEGER

-- Insight generation tracking
category_id UUID FK(analysis_categories.id)
insights_unlocked_at TIMESTAMP
insights_generation_status VARCHAR    -- not_started, queued, generating, completed, partial_failure, failed
insights_generation_started_at TIMESTAMP
insights_generation_completed_at TIMESTAMP
insights_job_id VARCHAR
total_insights_requested INTEGER
total_insights_completed INTEGER
total_insights_failed INTEGER

created_at TIMESTAMP
is_deleted BOOLEAN
deleted_at TIMESTAMP
```

#### **messages**

```sql
id UUID PRIMARY KEY
chat_id UUID FK(chats.id)
sender VARCHAR
content TEXT                          -- Encrypted in production
timestamp TIMESTAMP
```

#### **analysis_categories**

```sql
id UUID PRIMARY KEY
name VARCHAR UNIQUE                   -- romantic, friendship, family, professional
display_name VARCHAR                  -- "Romantic Relationship"
description TEXT
icon VARCHAR                          -- emoji or icon name
is_active BOOLEAN
created_at TIMESTAMP
```

#### **insight_types**

```sql
id UUID PRIMARY KEY
name VARCHAR UNIQUE                   -- conflict_resolution, emotional_balance
display_title VARCHAR                 -- "Conflict Resolution Patterns"
description TEXT
icon VARCHAR
prompt_template TEXT                  -- Gemini prompt with placeholders
rag_query_keywords TEXT               -- "conflict, argument, disagreement"
response_schema JSONB                 -- Gemini JSON schema
required_metadata_fields JSONB        -- ["total_messages", "user_stats"]

-- Premium & cost
is_premium BOOLEAN
credit_cost INTEGER                   -- Cost to generate this insight
estimated_tokens INTEGER
avg_generation_time_ms INTEGER

is_active BOOLEAN
created_at TIMESTAMP
```

#### **category_insight_types** (Many-to-Many)

```sql
id UUID PRIMARY KEY
category_id UUID FK(analysis_categories.id)
insight_type_id UUID FK(insight_types.id)
display_order INTEGER                 -- Order in UI
created_at TIMESTAMP

UNIQUE(category_id, insight_type_id)
```

#### **insights**

```sql
id UUID PRIMARY KEY
chat_id UUID FK(chats.id)
insight_type_id UUID FK(insight_types.id)

content JSON                          -- Structured insight data
status ENUM                           -- pending, generating, completed, failed
error_message TEXT

-- Metadata
tokens_used INTEGER
generation_time_ms INTEGER
rag_chunks_used INTEGER

created_at TIMESTAMP
updated_at TIMESTAMP

UNIQUE(chat_id, insight_type_id)     -- One insight per type per chat
```

#### **insight_generation_jobs**

```sql
id UUID PRIMARY KEY
job_id VARCHAR UNIQUE                 -- External job ID
chat_id UUID FK(chats.id)
category_id UUID FK(analysis_categories.id)
user_id VARCHAR FK(users.user_id)

status VARCHAR                        -- queued, running, completed, failed
total_insights INTEGER
completed_insights INTEGER
failed_insights INTEGER

started_at TIMESTAMP
completed_at TIMESTAMP
estimated_completion_at TIMESTAMP

total_tokens_used INTEGER
total_generation_time_ms INTEGER

error_message TEXT
failed_insight_ids JSON               -- Array of failed insight IDs

created_at TIMESTAMP
updated_at TIMESTAMP
```

#### **credit_transactions**

```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users.user_id)
transaction_type ENUM                 -- signup_bonus, purchase, insight_unlock, refund
amount INTEGER                        -- Positive for credit, negative for debit
balance_after INTEGER
description TEXT
metadata JSON                         -- {chat_id, category_id, payment_id}
created_at TIMESTAMP
```

#### **credit_packages**

```sql
id UUID PRIMARY KEY
name VARCHAR                          -- "Starter Pack"
credits INTEGER                       -- 200
price_inr DECIMAL                     -- 2.99
price_usd DECIMAL
is_active BOOLEAN
display_order INTEGER
created_at TIMESTAMP
```

#### **message_chunks** (Vector storage metadata)

```sql
id UUID PRIMARY KEY
chat_id UUID FK(chats.id)
chunk_text TEXT
chunk_metadata JSON                   -- speakers, message_count, time_span
vector_id VARCHAR                     -- Qdrant point ID
chunk_index INTEGER
token_count INTEGER
created_at TIMESTAMP
```

---

## 6. API ENDPOINTS

### 6.1 Authentication

```
Headers: Authorization: Bearer <clerk_jwt_token>
Extracted: user_id via get_current_user_id()
```

### 6.2 Users

```
POST   /api/users/store                    # Store user on first login + signup bonus
DELETE /api/users/delete-account           # GDPR compliance
```

### 6.3 Chats

```
POST   /api/chats/upload                   # Upload chat file
GET    /api/chats                          # List user chats
GET    /api/chats/{chat_id}                # Get chat details + free stats
PUT    /api/chats/{chat_id}/display-name   # Update user's display name
GET    /api/chats/{chat_id}/messages       # Get all messages
GET    /api/chats/{chat_id}/vector-status  # Check if ready for insights
DELETE /api/chats/{chat_id}                # Soft delete
```

### 6.4 Categories

```
GET    /api/categories                     # List all categories
GET    /api/categories/{id}/insights       # Get insight types for category
```

### 6.5 Credits

```
GET    /api/credits/balance                # Get user balance
GET    /api/credits/transactions           # Transaction history
GET    /api/credits/packages               # Available packages (public)
```

### 6.6 Insights (NEW - separated from rag)

```
POST   /api/insights/unlock                # Unlock insights (deduct coins, start job)
GET    /api/insights/jobs/{job_id}/status  # Poll job progress
GET    /api/insights/chats/{chat_id}       # Get all insights for chat
POST   /api/insights/{insight_id}/retry    # Retry failed insight
```

### 6.7 RAG (Internal)

```
POST   /api/rag/query                      # Conversational Q&A about chat
POST   /api/rag/generate                   # (Deprecated) Single insight generation
```

---

## 7. INSIGHT GENERATION FLOW (DETAILED)

### 7.1 Unlock Request

```python
POST /api/insights/unlock
Body: {
  "chat_id": "uuid",
  "category_id": "uuid"
}

# Backend (credits/service.py):
1. Verify chat ownership
2. Check if already unlocked → reject if yes
3. Check vector_status:
   - If "pending" → trigger indexing NOW (sync, 1-3 sec)
   - If "indexing" → reject (409 conflict)
   - If "failed" → reject (400 bad request)
   - If "completed" → proceed
4. Get insight types for category (e.g., 7 insights for romantic)
5. Calculate cost (7 × credit_cost)
6. Deduct credits (create RESERVED transaction)
7. Create insight records (status=PENDING)
8. Create InsightGenerationJob record
9. Launch Celery: orchestrate_insight_generation.delay(job_id)
10. Return job_id to frontend

Response: {
  "success": true,
  "job_id": "abc-123",
  "coins_deducted": 100,
  "remaining_balance": 150,
  "total_insights": 7,
  "poll_url": "/api/insights/jobs/abc-123/status"
}
```

### 7.2 Background Generation (Celery)

```python
# Task: orchestrate_insight_generation(job_id)
1. Mark job as "running"
2. Extract shared RAG context (ONE Qdrant query for all insights)
   - Cache in Redis (key: rag_context:{chat_id}:{category_id})
3. Get all pending insights
4. Launch parallel tasks (3-4 concurrent):
   - generate_single_insight(insight_id, chat_id, insight_type_id, job_id, shared_context)
5. Each task:
   a. Update insight.status = GENERATING
   b. Get relevant chunks from shared_context
   c. Build prompt with metadata + chunks
   d. Call Gemini with JSON schema
   e. Parse response → insight.content
   f. Update insight.status = COMPLETED
   g. Update job progress
6. When all complete:
   - Finalize job (status=completed/partial_failure/failed)
   - Update chat counters
   - If >50% failed → Auto-refund credits
```

### 7.3 Frontend Polling

```javascript
// Poll every 2 seconds
GET /api/insights/jobs/{job_id}/status

Response: {
  "job_id": "abc-123",
  "status": "running",
  "progress_percentage": 42.8,
  "total_insights": 7,
  "completed_insights": 3,
  "failed_insights": 0,
  "estimated_completion_at": "2025-11-08T12:35:00Z"
}

// When status = "completed", fetch insights:
GET /api/insights/chats/{chat_id}
```

---

## 8. AI PROMPT STRUCTURE

### 8.1 Prompt Template Example (Conflict Resolution)

```python
prompt_template = """
You are analyzing a {category} chat conversation between {user_name} and {partner_name}.

CHAT METADATA:
{metadata}

RELEVANT CONVERSATIONS (showing conflicts, arguments, disagreements):
{chunks}

Analyze conflict resolution patterns and return JSON matching this schema:
{response_schema}

Focus on:
1. How conflicts typically start (triggers)
2. Escalation patterns (do they escalate quickly or slowly?)
3. Resolution strategies (who apologizes first? compromise or avoidance?)
4. Apology styles (direct vs indirect)
5. Time to resolution (hours? days?)
6. Healthy vs unhealthy patterns

Be specific and cite examples from the chat.
"""
```

### 8.2 Response Schema Example

```json
{
  "type": "object",
  "properties": {
    "overall_score": {
      "type": "number",
      "description": "1-10 score for conflict resolution health"
    },
    "conflict_triggers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "trigger": { "type": "string" },
          "frequency": {
            "type": "string",
            "enum": ["rare", "occasional", "frequent"]
          },
          "example": { "type": "string" }
        }
      }
    },
    "resolution_patterns": {
      "type": "object",
      "properties": {
        "primary_resolver": { "type": "string" },
        "typical_resolution_time": { "type": "string" },
        "apology_style": { "type": "string" }
      }
    },
    "red_flags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "strengths": {
      "type": "array",
      "items": { "type": "string" }
    },
    "recommendations": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["overall_score", "conflict_triggers", "resolution_patterns"]
}
```

---

## 9. SECURITY & ENCRYPTION

### 9.1 Encryption at Rest (Phase 4)

```python
# Encrypt message content before DB insert
from cryptography.fernet import Fernet

encryption_key = settings.ENCRYPTION_KEY  # Stored in AWS KMS
cipher = Fernet(encryption_key)

# Before insert:
message.content = cipher.encrypt(message.content.encode()).decode()

# Before insight generation:
decrypted = cipher.decrypt(message.content.encode()).decode()
```

### 9.2 Data Retention

- **Active chats**: Retained while user account active
- **Soft deleted**: 30-day grace period (can restore)
- **Hard deleted**: Permanent deletion after 30 days
- **Vectors**: Deleted immediately on chat deletion (Qdrant)

### 9.3 GDPR Compliance

- User data export: `GET /api/users/export-data`
- Account deletion: `DELETE /api/users/delete-account`
- Consent: Terms checkbox on upload
- Logging: No PII in logs (hash user IDs)

---

## 10. CATEGORIES & INSIGHTS (FINALIZED)

### 10.1 Romantic Relationship (100 coins)

1. **Emotional Balance Score** - Who invests more emotionally?
2. **Conflict Resolution Patterns** - How do you handle fights?
3. **Affection & Appreciation Levels** - Love language analysis
4. **Response Time Dynamics** - Communication eagerness
5. **Future Planning & Commitment Signals** - Long-term viability
6. **Special Moments Timeline** - Key relationship milestones
7. **Communication Style Compatibility** - Do you speak the same language?

### 10.2 Friendship (50 coins)

1. **Friendship Depth Score** - Surface-level or deep?
2. **Support Balance Analysis** - Who supports whom?
3. **Shared Interest Map** - Common ground
4. **Banter vs Deep Talk Ratio** - Friendship style
5. **Effort Symmetry Check** - Who initiates more?
6. **Inside Jokes & Memory Bank** - Friendship culture

### 10.3 Family (50 coins)

1. **Emotional Closeness Index** - Family bond strength
2. **Support Exchange Patterns** - Who helps whom?
3. **Generational Communication Gaps** - Bridging differences
4. **Shared Responsibility Balance** - Fair distribution?
5. **Nostalgia & Memory Sharing** - Family history

### 10.4 Professional (100 coins)

1. **Professionalism Score** - Boundary maintenance
2. **Decision-Making Patterns** - Leadership dynamics
3. **Project Coordination Efficiency** - Collaboration quality
4. **Work-Life Boundary Analysis** - Balance check
5. **Communication Clarity Index** - Effective communication

---

## 11. COST BREAKDOWN

### 11.1 Per-Insight Cost

```
Gemini Embedding: ~$0.0001 per 50 chunks = $0.005
Gemini Generation: ~$0.01 per insight (2000 tokens avg)
Total per insight: ~$0.015
Total per romantic unlock (7 insights): ~$0.105

Revenue per romantic unlock: $2 (100 coins @ $2.99/200 coins)
Gross margin: 95% ($1.90 profit)
```

### 11.2 Monthly Cost Estimate (100 unlocks/month)

```
Gemini API: $10.50
Qdrant Cloud: $20 (1GB storage)
PostgreSQL: $0 (free tier Render/Supabase)
Redis: $0 (free tier Render)
Hosting: $7 (Render Starter)
Total: ~$37.50

Revenue (100 unlocks @ $2): $200
Net profit: $162.50/month
```

---

## 12. COMPETITIVE ANALYSIS

| Product           | Free Features  | Paid Features           | Price                 |
| ----------------- | -------------- | ----------------------- | --------------------- |
| **ChatBump.ai**   | 50 points free | 100 points per analysis | Similar to RelivChats |
| **ChatAnalytics** | 100% free      | None                    | Free                  |
| **ConvoAnalyzer** | 100% free      | None                    | Free                  |
| **RelivChats**    | Stats only     | AI insights             | $2-3 per analysis     |

**Differentiation:**

- Category-specific insights (competitors do generic analysis)
- Psychological depth (competitors show surface metrics)
- Privacy-first (E2E encryption planned)
- Multi-platform support (competitors WhatsApp-only)

---

## 13. FUTURE ROADMAP

### Phase 1: Core (4 weeks)

- ✅ Categories & prompts finalization
- 🔄 Payment integration (Razorpay)
- 🔄 Credit safety (refunds, idempotency)
- 🔄 Frontend polling

### Phase 2: Expansion (4 weeks)

- Instagram + Telegram parsers
- Family + Professional categories
- PDF export
- Referral program

### Phase 3: Enterprise (8 weeks)

- Encryption at rest
- GDPR compliance
- Analytics dashboard
- Subscription model (optional)

### Phase 4: Advanced AI (4 weeks)

- Dynamic prompt generation (premium)
- Multi-language support
- Sentiment analysis timeline
- Relationship health score

---

## 14. ENVIRONMENT VARIABLES

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/relivchats
REDIS_URL=redis://localhost:6379/0

# AI
GEMINI_API_KEY=your_key_here
GEMINI_LLM_MODEL=gemini-2.0-flash-exp
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_key_here
QDRANT_COLLECTION_NAME=relivchats_messages

# Auth
CLERK_SECRET_KEY=your_clerk_secret

# Encryption (Production)
ENCRYPTION_KEY=your_fernet_key_base64

# Payments
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# App
MAX_UPLOAD_SIZE_MB=10
RAG_CHUNK_CACHE_TTL=3600
MAX_CONCURRENT_INSIGHTS=3
INSIGHT_GENERATION_TIMEOUT=120
```

---

## 15. KEY DESIGN DECISIONS

### Why Lazy Vector Indexing?

- **Cost**: 95% of uploads never unlock → wasting embedding costs
- **Speed**: Faster upload experience
- **Failure handling**: Can refund if indexing fails before generating insights

### Why Celery over BackgroundTasks?

- **Reliability**: Survives server restarts
- **Retries**: Automatic retry on failure
- **Scalability**: Horizontal scaling (multiple workers)
- **Monitoring**: Flower dashboard

### Why Credit System over Subscription?

- **Usage pattern**: Sporadic (not daily/weekly)
- **Conversion**: Lower barrier to entry ($3 vs $10/month)
- **Flexibility**: Pay only for what you use

### Why Separate Insights from RAG?

- **Domain clarity**: Insights = paid feature, RAG = internal tool
- **API design**: Clear separation of concerns
- **Billing**: Easier to track credit usage

---

## 16. TESTING CHECKLIST

### Unit Tests

- [ ] Chat parsing (WhatsApp format edge cases)
- [ ] Credit deduction (idempotency, refunds)
- [ ] Prompt template rendering
- [ ] Insight validation (schema compliance)

### Integration Tests

- [ ] Upload → Parse → Index → Generate flow
- [ ] Payment webhook → Credit addition
- [ ] Job orchestration (parallel generation)
- [ ] Failure scenarios (refunds, retries)

### Load Tests

- [ ] 100 concurrent uploads
- [ ] 50 concurrent insight generations
- [ ] Qdrant query performance (>1000 chats)
- [ ] Redis cache hit rate

---

## 17. MONITORING & ALERTS

### Key Metrics

```python
# Track in Mixpanel/PostHog:
- upload_count
- unlock_count
- conversion_rate (uploads → unlocks)
- revenue_per_user
- insight_generation_failures
- avg_generation_time
- credit_refund_rate

# Alert if:
- Insight failure rate >10%
- Avg generation time >60s
- Credit refund rate >5%
- Qdrant query latency >500ms
```

### Error Monitoring

- **Sentry**: Exception tracking
- **Celery Flower**: Task monitoring (http://localhost:5555)
- **Slack webhooks**: Critical errors

---

## 18. DEVELOPER NOTES

### Running Locally

```bash
# Start services
docker-compose up redis postgres qdrant

# Run migrations
alembic upgrade head

# Seed database
psql $DATABASE_URL < seed/analysis_category.sql
psql $DATABASE_URL < seed/insight_types.sql
psql $DATABASE_URL < seed/category_insight_types.sql

# Start Celery worker
celery -A src.celery_app worker --loglevel=info --concurrency=3

# Start API
uvicorn src.main:app --reload

# Monitor tasks
celery -A src.celery_app flower
```

### Common Issues

1. **Vector indexing fails**: Check Qdrant connection, increase timeout
2. **Insights timeout**: Reduce max_chunks from 50 to 30
3. **Redis connection error**: Check REDIS_URL, restart Redis
4. **Gemini rate limits**: Add exponential backoff in service.py

---

## 19. SUPPORT & DOCUMENTATION

### For Frontend Developers

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Polling flow**: See section 7.3
- **Error codes**: 402 (insufficient credits), 409 (already generating)

### For Data Scientists

- **Prompt templates**: `src/rag/models.py` → InsightType.prompt_template
- **Response schemas**: `src/rag/models.py` → InsightType.response_schema
- **RAG config**: `src/vector/chunking.py` → MAX_CHUNK_SIZE, OVERLAP

### For DevOps

- **Scaling**: Add more Celery workers (increase concurrency)
- **Database**: Index on (chat_id, user_id), (insight_type_id)
- **Qdrant**: Increase RAM if >10k chats

---

## 20. LEGAL & COMPLIANCE

### Terms of Service (TOS)

- Users own their data
- We process data only for insight generation
- Data deleted on request (GDPR Article 17)
- No data sharing with third parties

### Privacy Policy

- Encryption in transit (HTTPS) and at rest (Fernet)
- Data retention: 90 days max (configurable)
- GDPR rights: Access, deletion, export
- Cookie policy (if web app)

### Payment Terms

- Non-refundable credits (except system failures)
- Auto-refund if >50% insights fail
- Credits never expire
- Pricing subject to change (30-day notice)

---

**END OF CONTEXT**

Use this document to:

1. Ask AI assistants detailed questions about the product
2. Onboard new developers
3. Plan features and architecture decisions
4. Debug issues by referencing exact table/column names
5. Estimate costs and timelines
