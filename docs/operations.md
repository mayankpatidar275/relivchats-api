# Operations Guide

Production monitoring, debugging, and maintenance reference.

---

## Quick Health Check (30 seconds)

```bash
# 1. Services status
docker ps

# 2. Recent errors
docker-compose logs --since=1h relivchats-api | grep ERROR

# 3. API health
curl -s http://localhost:8000/health | jq .

# 4. Celery worker
docker exec celery_worker celery -A src.celery_app inspect active

# 5. Redis
docker exec redis redis-cli PING
```

---

## Emergency Commands

```bash
# Restart API
docker-compose restart relivchats-api

# Restart Celery
docker-compose restart celery_worker

# View logs (last 100 lines)
docker-compose logs --tail=100 -f relivchats-api

# Health check
curl http://localhost:8000/health | jq .
```

---

## Service Management

### Logs

**Real-time:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f relivchats-api
docker-compose logs -f celery_worker

# Last 100 lines, then follow
docker-compose logs -f --tail=100 relivchats-api
```

**Historical:**
```bash
# Last 200 lines
docker-compose logs --tail=200 relivchats-api

# Last hour
docker-compose logs --since=1h relivchats-api

# Search for errors
docker-compose logs relivchats-api | grep ERROR | tail -50

# Search for user activity
docker-compose logs relivchats-api | grep "user_XXX"

# Multiple patterns
docker-compose logs relivchats-api | grep -E "ERROR|CRITICAL|Failed"
```

### Restart Services

```bash
# Restart specific service
docker-compose restart relivchats-api

# Restart with rebuild (after code changes)
docker-compose up -d --build relivchats-api

# Stop and clean restart
docker-compose down
docker-compose up -d
```

---

## Database Monitoring

### Connect
```bash
# Remote DB (Neon)
psql "postgresql://user:pass@host/db"
```

### Quick Checks
```sql
-- Active connections
SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'neondb';

-- Recent transactions
SELECT * FROM credit_transactions ORDER BY created_at DESC LIMIT 10;

-- Vector indexing status
SELECT vector_status, COUNT(*) FROM chats GROUP BY vector_status;

-- Active generation jobs
SELECT job_id, status, completed_insights, total_insights, created_at
FROM insight_generation_jobs
WHERE status IN ('queued', 'running')
ORDER BY created_at DESC;

-- Failed insights
SELECT chat_id, insight_type_id, error_message, created_at
FROM insights
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 20;

-- Stuck coin reservations (should be empty)
SELECT * FROM coin_reservations
WHERE status = 'active'
  AND expires_at < NOW();

-- Long-running queries (>30s)
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '30 seconds'
ORDER BY duration DESC;
```

---

## Celery Monitoring

```bash
# Active tasks
docker exec celery_worker celery -A src.celery_app inspect active

# Worker stats
docker exec celery_worker celery -A src.celery_app inspect stats

# Registered tasks
docker exec celery_worker celery -A src.celery_app inspect registered

# Scheduled tasks
docker exec celery_worker celery -A src.celery_app inspect scheduled
```

---

## Performance Monitoring

```bash
# Docker resource usage
docker stats --no-stream

# Disk usage
docker system df
df -h

# Memory usage
free -h

# Top processes in container
docker exec relivchats-api ps aux --sort=-%mem | head -10
```

---

## Health Endpoints

```bash
# Basic health
curl http://localhost:8000/health

# Database pool status
curl http://localhost:8000/health/db-pool

# With JSON formatting
curl -s http://localhost:8000/health | jq .
```

---

## Troubleshooting

### Issue: Quota Errors (Gemini)

**Symptoms**: `RESOURCE_EXHAUSTED` errors in logs

**Check:**
```bash
# Count quota errors
docker-compose logs --since=1h relivchats-api | grep "RESOURCE_EXHAUSTED" | wc -l

# See failed batches
docker-compose logs relivchats-api | grep "failed after 3 attempts"
```

**Fix:**
- Check Gemini quota: https://ai.google.dev/gemini-api/docs/quota
- Reduce `MAX_CONCURRENT_INSIGHTS` in .env
- Wait for quota reset (usually 1 minute)

---

### Issue: Stuck Celery Tasks

**Symptoms**: Insights stuck in "generating" status

**Check:**
```bash
# Active tasks
docker exec celery_worker celery -A src.celery_app inspect active

# Worker logs
docker-compose logs --tail=50 celery_worker
```

**Fix:**
```bash
# Restart worker
docker-compose restart celery_worker

# If still stuck, check database for job status
psql ... -c "SELECT * FROM insight_generation_jobs WHERE status = 'running';"
```

---

### Issue: Database Connection Errors

**Symptoms**: `OperationalError: too many connections`

**Check:**
```bash
# Pool status
curl http://localhost:8000/health/db-pool | jq .

# Connections in DB
psql ... -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'neondb';"
```

**Fix:**
```bash
# Restart API to reset pool
docker-compose restart relivchats-api

# Ensure CELERY_WORKER=true for workers (uses NullPool)
docker-compose logs celery_worker | grep "CELERY_WORKER"
```

---

### Issue: High Memory Usage

**Check:**
```bash
# Which service?
docker stats --no-stream
```

**Fix:**
```bash
# Restart offending service
docker-compose restart relivchats-api
# or
docker-compose restart celery_worker
```

---

### Issue: Vector Indexing Fails

**Symptoms**: `vector_status = 'failed'` in database

**Check:**
```bash
# Qdrant health
curl http://localhost:6333/health

# Qdrant logs
docker-compose logs qdrant
```

**Fix:**
```bash
# Restart Qdrant
docker-compose restart qdrant

# Reindex chat (manual)
curl -X POST http://localhost:8000/api/chats/{chat_id}/reindex
```

---

## Maintenance

```bash
# Clean Docker
docker container prune -f
docker image prune -f

# Check migrations
docker exec relivchats-api alembic current

# Apply pending migrations
docker exec relivchats-api alembic upgrade head

# View logs size
du -sh /var/lib/docker/containers/*
```

---

## Bash Aliases (Optional)

Add to `~/.bashrc`:

```bash
alias dc='docker-compose'
alias api-logs='docker-compose logs -f relivchats-api'
alias celery-logs='docker-compose logs -f celery_worker'
alias api-errors='docker-compose logs relivchats-api | grep ERROR | tail -20'
alias health='curl -s http://localhost:8000/health | jq .'
```

---

## When to Escalate

### Critical (Immediate)
- ❌ API health returns 500 or timeout
- ❌ All insight generations failing
- ❌ Database connection errors
- ❌ Disk usage > 90%

### Warning (Monitor)
- ⚠️ Error rate > 10% in last hour
- ⚠️ Frequent quota errors
- ⚠️ Celery queue > 100 tasks
- ⚠️ Memory steadily increasing

---

## Key Metrics to Track

- Upload success rate (target: >99%)
- Unlock conversion rate
- Insight generation success rate (target: >95%)
- Average generation time per insight (target: <90s)
- Credit refund rate (target: <5%)
- API p95 response time (target: <500ms)
