# CONTEXT: RelivChats - Complete Product Documentation

## 1. PRODUCT OVERVIEW

**RelivChats** is a SaaS platform that provides AI-powered insights from exported chat conversations. Users upload chat files (only WhatsApp for now), receive free statistical analysis, and can unlock AI-generated psychological insights by spending coins.

### Core Value Proposition

- **Free tier**: Upload chats → Get instant statistics (message counts, activity patterns, word clouds, emoji analysis)
- **Paid tier**: Unlock category-specific AI insights (relationship analysis, conflict patterns, communication styles)

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

# YOUR ROLE

You are an expert product strategist, pricing consultant, and SaaS business advisor with deep experience in:

- Consumer AI products and their economics
- Freemium conversion optimization
- Credit/point system psychology
- Competitive positioning against free alternatives
- API cost management for AI products

When I ask questions, provide:

- Data-driven reasoning (reference similar products when relevant)
- Brutally honest analysis (don't sugarcoat or be biased toward making me feel good)
- Specific, actionable recommendations
- Short, concise answers unless I ask for detail
- Trade-off analysis when multiple options exist

Challenge my assumptions when needed. I want the BEST strategy, not the nicest answer.

---

# INSTRUCTION

I will now ask you questions about Reliv Chats. Use all the context above to provide informed, expert-level guidance.

Question:

I want to improve the chunking system. Here is my current chunking.py:

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from ..config import settings
from uuid import UUID

@dataclass
class ChunkMessage:
message_id: UUID
sender: str
content: str
timestamp: datetime

@dataclass
class ConversationChunk:
chunk_index: int
messages: List[ChunkMessage]
chunk_text: str
metadata: Dict[str, Any]
estimated_tokens: int

class ConversationChunker:
def **init**(
self,
max_chunk_size: int = settings.MAX_CHUNK_SIZE,
min_chunk_size: int = settings.MIN_CHUNK_SIZE,
time_window_minutes: int = settings.TIME_WINDOW_MINUTES
):
self.max_chunk_size = max_chunk_size
self.min_chunk_size = min_chunk_size
self.time_window = timedelta(minutes=time_window_minutes)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    def should_break_chunk(
        self,
        current_chunk: List[ChunkMessage],
        new_message: ChunkMessage
    ) -> bool:
        """Determine if we should start a new chunk"""
        if not current_chunk:
            return False

        # Get current chunk text
        current_text = self._format_messages_to_text(current_chunk)
        new_text = f"{current_text}\n{new_message.sender}: {new_message.content}"

        # Check token limit
        if self.estimate_tokens(new_text) > self.max_chunk_size:
            return True

        # Check time gap
        last_message = current_chunk[-1]
        time_diff = new_message.timestamp - last_message.timestamp
        if time_diff > self.time_window:
            return True

        # Check speaker transition after significant gap (more than 1 hour)
        if (time_diff > timedelta(hours=1) and
            new_message.sender != last_message.sender):
            return True

        return False

    def _format_messages_to_text(self, messages: List[ChunkMessage]) -> str:
        """Convert messages to formatted text"""
        lines = []
        current_speaker = None
        speaker_messages = []

        for msg in messages:
            if msg.sender != current_speaker:
                # Flush previous speaker's messages
                if speaker_messages:
                    content = " ".join(speaker_messages)
                    lines.append(f"{current_speaker}: {content}")
                    speaker_messages = []
                current_speaker = msg.sender

            speaker_messages.append(msg.content)

        # Flush last speaker's messages
        if speaker_messages:
            content = " ".join(speaker_messages)
            lines.append(f"{current_speaker}: {content}")

        return "\n".join(lines)

    def _create_chunk_metadata(self, messages: List[ChunkMessage]) -> Dict[str, Any]:
        """Create metadata for a chunk"""
        if not messages:
            return {}

        start_time = messages[0].timestamp
        end_time = messages[-1].timestamp
        speakers = list(set(msg.sender for msg in messages if msg.sender))
        message_ids = [str(msg.message_id) for msg in messages]

        return {
            "start_timestamp": start_time.isoformat(),
            "end_timestamp": end_time.isoformat(),
            "speakers": speakers,
            "message_count": len(messages),
            "message_ids": message_ids,
            "time_span_minutes": int((end_time - start_time).total_seconds() / 60),
        }

    def chunk_messages(self, messages: List[ChunkMessage]) -> List[ConversationChunk]:
        """Main chunking function"""
        if not messages:
            return []

        # Sort messages by timestamp
        messages.sort(key=lambda x: x.timestamp)

        chunks = []
        current_chunk = []
        chunk_index = 0

        for message in messages:
            # Check if we should start a new chunk
            if self.should_break_chunk(current_chunk, message):
                # Finalize current chunk if it exists
                if current_chunk:
                    chunk_text = self._format_messages_to_text(current_chunk)
                    chunk_tokens = self.estimate_tokens(chunk_text)

                    if chunk_tokens >= self.min_chunk_size:
                        # Chunk is big enough, save it and start fresh
                        chunks.append(ConversationChunk(
                            chunk_index=chunk_index,
                            messages=current_chunk.copy(),
                            chunk_text=chunk_text,
                            metadata=self._create_chunk_metadata(current_chunk),
                            estimated_tokens=chunk_tokens
                        ))
                        chunk_index += 1
                        # Start new chunk with current message
                        current_chunk = [message]
                    else:
                        # Chunk is too small - merge with next chunk instead of discarding
                        # Keep all messages from small chunk and add new message
                        current_chunk.append(message)
                        # Don't increment chunk_index - we're continuing to build the same logical chunk
                else:
                    # No current chunk, start fresh
                    current_chunk = [message]
            else:
                # Continue building current chunk
                current_chunk.append(message)

        # Handle final chunk - always include it regardless of size
        if current_chunk:
            chunk_text = self._format_messages_to_text(current_chunk)
            chunks.append(ConversationChunk(
                chunk_index=chunk_index,
                messages=current_chunk,
                chunk_text=chunk_text,
                metadata=self._create_chunk_metadata(current_chunk),
                estimated_tokens=self.estimate_tokens(chunk_text)
            ))

        return chunks

def chunk_chat_messages(db_messages) -> List[ConversationChunk]:
"""Convert database messages to chunks""" # Convert DB messages to ChunkMessage objects
chunk_messages = []
for msg in db_messages:
chunk_messages.append(ChunkMessage(
message_id=msg.id,
sender=msg.sender or "Unknown",
content=msg.content,
timestamp=msg.timestamp
)) # Create chunker and process
chunker = ConversationChunker()
return chunker.chunk_messages(chunk_messages)

Please tell me in very short that why should i even store the chat messages in a table? give very short answer.
