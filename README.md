# RelivChats API

> AI-powered chat analysis platform that transforms exported conversations into actionable psychological insights.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/relivchats-api.git
cd relivchats-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Run migrations
alembic upgrade head

# Seed database
psql $DATABASE_URL < seed/analysis_category.sql
psql $DATABASE_URL < seed/insight_types.sql
psql $DATABASE_URL < seed/category_insight_types.sql
psql $DATABASE_URL < seed/credit_packages.sql

# Start Celery worker
celery -A src.celery_app worker --loglevel=info --concurrency=3 &

# Start API server
uvicorn src.main:app --reload

# API docs: http://localhost:8000/docs
# Task monitoring: http://localhost:5555
```

---

## 📖 Overview

RelivChats analyzes exported chat conversations (WhatsApp, Instagram, Telegram) to provide:

- **Free Statistics**: Message counts, activity patterns, word clouds, emoji analysis
- **AI Insights**: Category- specific psychological analysis (relationship dynamics, conflict patterns, communication styles)

### Key Features

- 🧠 **AI-Powered Analysis**: Google Gemini 2.0 for structured insights
- 🔒 **Privacy First**: End-to-end encryption, GDPR compliant
- ⚡ **Real-time Generation**: Parallel processing with Celery
- 💰 **Credit System**: Pay-per-use (no subscriptions)
- 📊 **Rich Statistics**: 20+ free metrics per chat
- 🎯 **Category-Specific**: Romantic, Friendship, Family, Professional

---

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │
│  (React/    │
│   Next.js)  │
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

---

## 🗄️ Database Schema

### Core Tables

```sql
-- User Management
users (user_id, email, credit_balance, created_at)

-- Chat Storage
chats (id, user_id, title, chat_metadata, vector_status,
       insights_generation_status, category_id)
messages (id, chat_id, sender, content, timestamp)

-- Insight System
analysis_categories (id, name, display_name, icon)
insight_types (id, name, prompt_template, response_schema, credit_cost)
category_insight_types (category_id, insight_type_id, display_order)
insights (id, chat_id, insight_type_id, content, status, tokens_used)

-- Job Tracking
insight_generation_jobs (job_id, chat_id, status, completed_insights,
                          total_insights, total_tokens_used)

-- Payments
credit_transactions (id, user_id, transaction_type, amount, metadata)
credit_packages (id, name, credits, price_inr, price_usd)

-- Vector Store Metadata
message_chunks (id, chat_id, chunk_text, vector_id, chunk_index)
```

See [CONTEXT.md](CONTEXT.md) for complete schema.

---

## 🔄 User Flow

### 1. Upload Chat

```http
POST /api/chats/upload
Content-Type: multipart/form-data

file: chat.txt
category_id: romantic (optional)
```

**Response:**

```json
{
  "id": "uuid",
  "title": "Chat with Alice",
  "chat_metadata": {
    "total_messages": 657,
    "total_words": 3145,
    "busiest_hour": 20,
    "top_emojis": ["😂", "❤️"],
    "user_stats": { ... }
  },
  "vector_status": "pending"
}
```

### 2. Unlock Insights

```http
POST /api/insights/unlock
Content-Type: application/json
Authorization: Bearer <token>

{
  "chat_id": "uuid",
  "category_id": "romantic"
}
```

**Response:**

```json
{
  "success": true,
  "job_id": "abc-123",
  "coins_deducted": 100,
  "remaining_balance": 150,
  "total_insights": 7,
  "poll_url": "/api/insights/jobs/abc-123/status"
}
```

### 3. Poll Job Status

```http
GET /api/insights/jobs/abc-123/status
Authorization: Bearer <token>
```

**Response:**

```json
{
  "job_id": "abc-123",
  "status": "running",
  "progress_percentage": 42.8,
  "total_insights": 7,
  "completed_insights": 3,
  "failed_insights": 0,
  "estimated_completion_at": "2025-11-08T12:35:00Z"
}
```

### 4. Get Insights

```http
GET /api/insights/chats/{chat_id}
Authorization: Bearer <token>
```

**Response:**

```json
{
  "chat_id": "uuid",
  "generation_status": "completed",
  "insights": [
    {
      "insight_type_name": "conflict_resolution",
      "display_title": "Conflict Resolution Patterns",
      "status": "completed",
      "content": {
        "overall_score": 7.5,
        "conflict_triggers": [...],
        "resolution_patterns": {...},
        "recommendations": [...]
      },
      "generation_metadata": {
        "tokens_used": 2500,
        "generation_time_ms": 3200
      }
    }
  ]
}
```

---

## 📁 Project Structure

```
relivchats-api/
├── src/
│   ├── auth/                    # Clerk authentication
│   │   └── dependencies.py
│   ├── users/                   # User management
│   │   ├── models.py            # User table
│   │   ├── router.py            # /users endpoints
│   │   ├── schemas.py
│   │   └── service.py
│   ├── chats/                   # Chat upload & parsing
│   │   ├── models.py            # Chat, Message tables
│   │   ├── router.py            # /chats endpoints
│   │   ├── schemas.py
│   │   └── service.py           # WhatsApp parser
│   ├── categories/              # Insight categories
│   │   ├── router.py            # /categories endpoints
│   │   └── schemas.py
│   ├── credits/                 # Payment & credits
│   │   ├── models.py            # CreditTransaction, CreditPackage
│   │   ├── router.py            # /credits endpoints
│   │   ├── schemas.py
│   │   └── service.py           # unlock_insights_for_category()
│   ├── insights/                # Insight management
│   │   └── router.py            # /insights endpoints (NEW)
│   ├── rag/                     # AI & insight generation
│   │   ├── models.py            # Insight, InsightType, InsightGenerationJob
│   │   ├── router.py            # /rag/query endpoint
│   │   ├── schemas.py
│   │   ├── service.py           # generate_insight()
│   │   ├── generation_service.py # InsightGenerationOrchestrator
│   │   ├── rag_optimizer.py     # RAG context caching
│   │   └── tasks.py             # Celery tasks
│   ├── vector/                  # Vector storage
│   │   ├── models.py            # MessageChunk
│   │   ├── service.py           # VectorService
│   │   ├── chunking.py          # Conversation-aware chunking
│   │   └── qdrant_client.py     # Qdrant operations
│   ├── celery_app.py            # Celery configuration
│   ├── config.py                # Settings (Pydantic)
│   ├── database.py              # SQLAlchemy setup
│   └── main.py                  # FastAPI app
├── alembic/                     # Database migrations
│   └── versions/
├── seed/                        # Initial data
│   ├── analysis_category.sql
│   ├── insight_types.sql
│   ├── category_insight_types.sql
│   └── credit_packages.sql
├── tests/                       # Unit & integration tests
├── docker-compose.yml           # Local development services
├── Dockerfile                   # Production container
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer          | Technology        | Purpose                      |
| -------------- | ----------------- | ---------------------------- |
| **API**        | FastAPI 0.104+    | REST API framework           |
| **Database**   | PostgreSQL 15     | Relational data              |
| **Vector DB**  | Qdrant            | RAG (semantic search)        |
| **Cache**      | Redis 7           | Session cache, Celery broker |
| **Task Queue** | Celery 5.4        | Background job processing    |
| **AI**         | Google Gemini 2.0 | LLM & embeddings             |
| **Auth**       | Clerk             | User authentication          |
| **Payments**   | Razorpay          | Payment processing (India)   |
| **Monitoring** | Celery Flower     | Task monitoring UI           |
| **ORM**        | SQLAlchemy 2.0    | Database ORM                 |
| **Migrations** | Alembic           | Schema versioning            |

---

## 🔐 Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/relivchats

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI
GEMINI_API_KEY=your_gemini_api_key
GEMINI_LLM_MODEL=gemini-2.0-flash-exp
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION_NAME=relivchats_messages

# Auth
CLERK_SECRET_KEY=your_clerk_secret_key

# Payments (Production)
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# App Config
MAX_UPLOAD_SIZE_MB=10
MAX_CONCURRENT_INSIGHTS=3
INSIGHT_GENERATION_TIMEOUT=120
RAG_CHUNK_CACHE_TTL=3600

# Security (Production)
ENCRYPTION_KEY=your_fernet_key_base64
```

---

## 📊 Insight Categories

### Romantic Relationship (100 coins)

1. Emotional Balance Score
2. Conflict Resolution Patterns
3. Affection & Appreciation Levels
4. Response Time Dynamics
5. Future Planning & Commitment Signals
6. Special Moments Timeline
7. Communication Style Compatibility

### Friendship (50 coins)

1. Friendship Depth Score
2. Support Balance Analysis
3. Shared Interest Map
4. Banter vs Deep Talk Ratio
5. Effort Symmetry Check
6. Inside Jokes & Memory Bank

### Family (50 coins)

1. Emotional Closeness Index
2. Support Exchange Patterns
3. Generational Communication Gaps
4. Shared Responsibility Balance
5. Nostalgia & Memory Sharing

### Professional (100 coins)

1. Professionalism Score
2. Decision-Making Patterns
3. Project Coordination Efficiency
4. Work-Life Boundary Analysis
5. Communication Clarity Index

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/chats/test_parser.py

# Run integration tests
pytest tests/integration/ -v

# Load testing
locust -f tests/load/locustfile.py
```

---

## 🚀 Deployment

### Docker (Production)

```bash
# Build image
docker build -t relivchats-api .

# Run container
docker run -d \
  --name relivchats-api \
  -p 8000:8000 \
  --env-file .env \
  relivchats-api

# Check logs
docker logs -f relivchats-api
```

---

## 📈 Monitoring

### Celery Flower Dashboard

```bash
# Start Flower
celery -A src.celery_app flower --port=5555

# Access at http://localhost:5555
```

### Key Metrics to Track

- Upload success rate
- Unlock conversion rate (uploads → unlocks)
- Insight generation success rate (target: >95%)
- Average generation time per insight (target: <30s)
- Credit refund rate (target: <5%)
- API response times (p95, p99)

### Error Monitoring

```python
# Install Sentry
pip install sentry-sdk[fastapi]

# Add to main.py
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

---

## 🐛 Troubleshooting

### Vector Indexing Fails

```bash
# Check Qdrant connection
curl http://localhost:6333/health

# Restart Qdrant
docker-compose restart qdrant

# Reindex chat manually
curl -X POST http://localhost:8000/api/chats/{chat_id}/reindex
```

### Celery Tasks Not Running

```bash
# Check Celery worker status
celery -A src.celery_app inspect active

# Check Redis connection
redis-cli ping

# Restart worker
pkill -f celery
celery -A src.celery_app worker --loglevel=info --concurrency=3
```

### Gemini Rate Limits

```python
# Add exponential backoff in service.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini_structured(...):
    # Your code
```

### Database Migrations

```bash
# Check current migration
alembic current

# Upgrade to latest
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "description"
```

---

## 💰 Pricing & Economics

### Credit Packages

| Package    | Credits | Price (INR) | Price (USD) | Value          |
| ---------- | ------- | ----------- | ----------- | -------------- |
| Starter    | 200     | ₹249        | $2.99       | 2-4 analyses   |
| Popular    | 500     | ₹499        | $5.99       | 5-10 analyses  |
| Best Value | 1500    | ₹1249       | $14.99      | 15-30 analyses |

### Cost Analysis (per unlock)

```
Revenue: ₹200 (100 coins @ ₹2.49/coin)
Costs:
  - Gemini API: ₹8 ($0.10)
  - Infrastructure: ₹1
  - Payment gateway: ₹6 (3%)
Total cost: ₹15
Gross profit: ₹185 (92.5% margin)
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Fork repository
git clone https://github.com/yourusername/relivchats-api.git

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes
# Write tests
# Run linting
black src/
isort src/
flake8 src/

# Commit
git commit -m "Add amazing feature"

# Push
git push origin feature/amazing-feature

# Create Pull Request
```

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Google Gemini](https://ai.google.dev/) - AI model
- [Qdrant](https://qdrant.tech/) - Vector database
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [Clerk](https://clerk.com/) - Authentication

---

## 📞 Support

- **Documentation**: [docs.relivchats.com](https://docs.relivchats.com)
- **Email**: support@relivchats.com
- **Discord**: [Join our community](https://discord.gg/relivchats)
- **Issues**: [GitHub Issues](https://github.com/yourusername/relivchats-api/issues)

---

## 🗺️ Roadmap

### Q1 2025

- [x] Core API with WhatsApp support
- [x] Romantic & Friendship categories
- [ ] Payment integration (Razorpay)
- [ ] Frontend polling implementation

### Q2 2025

- [ ] Instagram & Telegram support
- [ ] Family & Professional categories
- [ ] PDF export feature
- [ ] Referral program

### Q3 2025

- [ ] End-to-end encryption
- [ ] GDPR compliance tools
- [ ] Mobile app (React Native)
- [ ] Multi-language support

### Q4 2025

- [ ] Dynamic AI prompt generation
- [ ] Subscription model (optional)
- [ ] Public insights sharing
- [ ] Enterprise features

---

**Built with ❤️ by the RelivChats team**

---

## 🔗 Quick Links

- [API Documentation](http://localhost:8000/docs)
- [Product Context](CONTEXT.md)
- [Database Schema](docs/database-schema.md)
- [Deployment Guide](docs/deployment.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

---

**Last Updated**: November 2025  
**Version**: 2.0.0  
**Status**: Active Development

```

---
```
