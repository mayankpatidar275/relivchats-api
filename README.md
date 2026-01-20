# RelivChats API

> AI-powered chat analysis platform that transforms WhatsApp conversations into actionable psychological insights.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quick Start

```bash
# Setup
git clone <repo>
cd relivchats-api
python -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt

# Configure
cp .env.example .env
# Edit .env with API keys

# Start services
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
alembic upgrade head

# Start Celery worker (separate terminal)
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info --concurrency=1

# Start API
uvicorn src.main:app --reload
```

**Access:**
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## What is RelivChats?

Upload WhatsApp chats → Get free statistics → Unlock AI psychological insights (400 coins for 6 romantic insights).

**Features:**
- 🧠 **AI-Powered**: Google Gemini 2.0 for structured insights
- 📊 **Free Statistics**: Message counts, activity patterns, emoji analysis
- 💰 **Credit System**: Pay-per-use (no subscriptions)
- ⚡ **Real-time Generation**: Parallel processing with Celery
- 🔒 **Privacy First**: Lazy vector indexing, GDPR compliant

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI 0.104+ |
| **Database** | PostgreSQL 15 |
| **Vector DB** | Qdrant |
| **Cache** | Redis 7 |
| **Queue** | Celery 5.4 |
| **AI** | Google Gemini 2.0 |
| **Auth** | Clerk |
| **Payments** | Razorpay |

---

## Documentation

### Core Docs
- **[Getting Started](docs/getting-started.md)** - Setup & installation
- **[Product Overview](docs/product-overview.md)** - Business context & features
- **[Architecture](docs/architecture.md)** - Tech stack & design patterns
- **[API Reference](docs/api-reference.md)** - Endpoints & schemas

### Operations
- **[Deployment](docs/deployment.md)** - Production deployment guide
- **[Operations](docs/operations.md)** - Monitoring & troubleshooting
- **[Debugging](docs/debugging.md)** - Production debugging commands
- **[Logging & Errors](docs/logging-errors.md)** - Error handling system
- **[Sentry Setup](docs/sentry-setup.md)** - Error tracking configuration

### For AI Assistants
- **[CLAUDE.md](CLAUDE.md)** - Complete context for AI development assistants

---

## Project Structure

```
src/
├── auth/           # Clerk JWT authentication
├── users/          # User management, credit balance
├── chats/          # Chat upload, parsing, storage
├── categories/     # Analysis categories
├── credits/        # Credit system & transactions
├── insights/       # Insight unlock endpoints
├── rag/            # AI generation, Celery tasks
├── vector/         # Qdrant operations, chunking
├── payments/       # Razorpay/Stripe integration
└── main.py         # FastAPI app
```

---

## Development Commands

```bash
# Run API
uvicorn src.main:app --reload

# Run Celery worker
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info

# Run tests
pytest tests/ -v

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

---

## Deployment

**Required Services:**
- PostgreSQL 15+ (Neon recommended)
- Redis 7+ (Redis Cloud)
- Qdrant (Qdrant Cloud - 1GB free)

**Server Requirements:**
- 2 vCPU, 4GB RAM minimum
- Ubuntu 22.04 LTS or Docker

See [Deployment Guide](docs/deployment.md) for details.

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://localhost:6379/0

# AI
GEMINI_API_KEY=your_key
GEMINI_LLM_MODEL=gemini-2.0-flash-exp
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_key

# Auth
CLERK_SECRET_KEY=your_key

# Payments
RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
```

---

## Key Features

### Romantic Category (400 coins)
1. **Communication Basics** - Initiation, response patterns, balance
2. **Emotional Intimacy** - Vulnerability, support, affection
3. **Love Language** - Primary/secondary languages, compatibility
4. **Conflict Resolution** - Triggers, styles, repair strategies
5. **Future Planning** - Goals, alignment, shared vision
6. **Playfulness & Romance** - Humor, flirtation, spontaneity

### Pricing
- **Starter**: ₹399 ($4.99) = 400 coins → 1 analysis
- **Popular** ⭐: ₹799 ($9.99) = 850 coins → 2 analyses
- **Pro**: ₹1,499 ($17.99) = 1,600 coins → 4 analyses

---

## Monitoring

```bash
# Health check
curl http://localhost:8000/health | jq .

# View logs
docker-compose logs -f relivchats-api

# Celery status
docker exec celery_worker celery -A src.celery_app inspect active

# Restart services
docker-compose restart relivchats-api
```

See [Operations Guide](docs/operations.md) for more commands.

---

## Troubleshooting

**Celery tasks not running:**
```bash
# Ensure CELERY_WORKER=true env var is set
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info
```

**Database connection errors:**
- API uses QueuePool, workers must use NullPool
- Set `CELERY_WORKER=true` for workers

**Vector indexing fails:**
```bash
curl http://localhost:6333/health  # Check Qdrant
docker-compose restart qdrant
```

---

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/chats/test_parser.py -v
```

---

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes & write tests
4. Run linting: `black src/ && isort src/`
5. Commit & push
6. Create Pull Request

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/relivchats-api/issues)
- **Email**: support@relivchats.com

---

**Built with ❤️ by the RelivChats team**

**Last Updated**: January 2026
**Version**: 2.0.0
**Status**: Active Development
