# Getting Started

## Quick Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

### Installation

```bash
# Clone & setup
git clone <repo>
cd relivchats-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
alembic upgrade head

# Start Celery worker (separate terminal)
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info --concurrency=1

# Start API
uvicorn src.main:app --reload --port 8000
```

### Access
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Essential Commands

### Development
```bash
# Run API
uvicorn src.main:app --reload

# Run Celery worker
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info --concurrency=1

# Monitor tasks
celery -A src.celery_app flower --port 5555
```

### Database
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing
```bash
# Run tests
pytest tests/ -v

# With coverage
pytest --cov=src --cov-report=html
```

### Docker
```bash
# Full stack
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f app

# Stop
docker-compose -f docker-compose.dev.yml down
```

## Common Issues

**Celery tasks not running**
```bash
# Check worker
celery -A src.celery_app inspect active

# Restart worker with correct env var
CELERY_WORKER=true celery -A src.celery_app worker --loglevel=info
```

**Database connection errors**
- Ensure `CELERY_WORKER=true` when starting workers (uses NullPool)
- API uses QueuePool, workers must use NullPool

**Vector indexing fails**
```bash
# Check Qdrant
curl http://localhost:6333/health

# Restart Qdrant
docker-compose -f docker-compose.dev.yml restart qdrant
```

## Next Steps
- Read [Product Overview](./product-overview.md) for business context
- See [Architecture](./architecture.md) for technical details
- Check [API Reference](./api-reference.md) for endpoints
