# Quick Reference Card - Production Commands

Copy-paste commands for daily production monitoring.

---

## 🚨 Emergency Commands

```bash
# Check if everything is running
docker ps

# Restart API
docker-compose restart relivchats-api

# Restart Celery worker
docker-compose restart celery_worker

# View last 100 API logs
docker-compose logs --tail=100 -f relivchats-api

# Check API health
curl http://localhost:8000/health | jq .
```

---

## 📊 Daily Health Check (30 seconds)

```bash
# 1. Services status
docker ps

# 2. Recent errors (last hour)
docker-compose logs --since=1h relivchats-api | grep ERROR

# 3. API health
curl -s http://localhost:8000/health | jq .

# 4. Celery worker status
docker exec celery_worker celery -A src.celery_app inspect active

# 5. Redis health
docker exec redis redis-cli PING
```

---

## 🔍 Log Viewing

```bash
# Follow API logs
docker-compose logs -f relivchats-api

# Follow Celery logs
docker-compose logs -f celery_worker

# Last 200 lines
docker-compose logs --tail=200 relivchats-api

# Last hour
docker-compose logs --since=1h relivchats-api

# Search for errors
docker-compose logs relivchats-api | grep ERROR

# Search for user activity
docker-compose logs relivchats-api | grep "user_XXX"

# Search for quota errors
docker-compose logs relivchats-api | grep "RESOURCE_EXHAUSTED"
```

---

## 🗄️ Database Quick Checks

```bash
# Connect to PostgreSQL
psql "postgresql://user:pass@host/db"

# Then run:
```

```sql
-- Check active connections
SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'neondb';

-- Recent transactions
SELECT * FROM credit_transactions ORDER BY created_at DESC LIMIT 10;

-- Vector indexing status
SELECT vector_status, COUNT(*) FROM chats GROUP BY vector_status;

-- Active jobs
SELECT * FROM insight_generation_jobs
WHERE status = 'running'
ORDER BY created_at DESC;

-- Stuck reservations (should be empty)
SELECT * FROM coin_reservations
WHERE status = 'active'
  AND expires_at < NOW();
```

---

## 🔄 Celery Monitoring

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

## 📈 Performance Monitoring

```bash
# Docker resource usage
docker stats --no-stream

# Disk usage
docker system df

# Memory usage
free -h

# Top processes
docker exec relivchats-api ps aux --sort=-%mem | head -10
```

---

## 🧹 Maintenance

```bash
# Clean Docker
docker container prune -f
docker image prune -f

# Restart all services
docker-compose restart

# Full restart with rebuild
docker-compose down
docker-compose up -d --build

# Check migrations
docker exec relivchats-api alembic current
```

---

## 🐛 Troubleshooting Specific Issues

### Quota Errors (Gemini)
```bash
# Count quota errors in last hour
docker-compose logs --since=1h relivchats-api | grep "RESOURCE_EXHAUSTED" | wc -l

# See which batches failed
docker-compose logs relivchats-api | grep "failed after 3 attempts"

# Check Gemini usage: https://ai.dev/rate-limit
```

### Stuck Celery Tasks
```bash
# Check active tasks
docker exec celery_worker celery -A src.celery_app inspect active

# Check worker logs
docker-compose logs --tail=50 celery_worker

# Restart worker
docker-compose restart celery_worker
```

### Database Connection Issues
```bash
# Check pool status
curl http://localhost:8000/health/db-pool | jq .

# Check connections in DB
psql ... -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'neondb';"

# Restart API to reset pool
docker-compose restart relivchats-api
```

### High Memory Usage
```bash
# Check which service
docker stats --no-stream

# Restart offending service
docker-compose restart relivchats-api
# or
docker-compose restart celery_worker
```

---

## 📱 Set Up Bash Aliases (Optional)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Quick docker-compose
alias dc='docker-compose'
alias dcl='docker-compose logs -f --tail=100'
alias dcr='docker-compose restart'

# Quick logs
alias api-logs='docker-compose logs -f relivchats-api'
alias celery-logs='docker-compose logs -f celery_worker'
alias api-errors='docker-compose logs relivchats-api | grep ERROR | tail -20'

# Health checks
alias health='curl -s http://localhost:8000/health | jq .'
alias status='docker ps && echo "\n--- Health ---" && curl -s http://localhost:8000/health | jq .'
```

Then: `source ~/.bashrc` and use:
- `api-logs` instead of `docker-compose logs -f relivchats-api`
- `health` instead of `curl http://localhost:8000/health | jq .`
- `status` to see everything at once

---

## 📞 When to Escalate

### Critical Issues (Immediate Action)
- ❌ API health endpoint returns 500 or timeout
- ❌ All insight generations failing
- ❌ Database connection errors
- ❌ Disk usage > 90%

### Warning Signs (Monitor Closely)
- ⚠️ Error rate > 10% in last hour
- ⚠️ Quota errors occurring frequently
- ⚠️ Celery queue building up (>100 tasks)
- ⚠️ Memory usage steadily increasing

---

**💡 Tip**: Open this file in a second terminal while monitoring production!

**📚 Full Guide**: See `PRODUCTION_MONITORING.md` for detailed explanations
