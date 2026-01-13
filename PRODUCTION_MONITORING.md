# Production Monitoring Guide

Quick reference for monitoring, debugging, and maintaining RelivChats API in production.

---

## Docker Service Management

### Check Running Services
```bash
# View all running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Check specific service status
docker-compose ps
```

### Service Logs

#### Real-time Logs (Follow Mode)
```bash
# All services
docker-compose logs -f

# Specific service (API)
docker-compose logs -f relivchats-api

# Celery worker only
docker-compose logs -f celery_worker

# Last 100 lines, then follow
docker-compose logs -f --tail=100 relivchats-api

# Multiple services
docker-compose logs -f relivchats-api celery_worker
```

#### Historical Logs
```bash
# Last 200 lines
docker-compose logs --tail=200 relivchats-api

# Logs since specific time
docker-compose logs --since=1h relivchats-api
docker-compose logs --since="2024-01-13T08:00:00" relivchats-api

# Logs until specific time
docker-compose logs --until="2024-01-13T09:00:00" relivchats-api
```

#### Filter Logs by Content
```bash
# Search for errors
docker-compose logs relivchats-api | grep ERROR

# Search for specific user activity
docker-compose logs relivchats-api | grep "user_35O41Xw3BIECxUc22RACtYOK2AP"

# Search for quota errors
docker-compose logs relivchats-api | grep "RESOURCE_EXHAUSTED"

# Search for database errors
docker-compose logs relivchats-api | grep "sqlalchemy"

# Multiple patterns
docker-compose logs relivchats-api | grep -E "ERROR|CRITICAL|Failed"
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart relivchats-api
docker-compose restart celery_worker

# Restart with rebuild (after code changes)
docker-compose up -d --build relivchats-api
docker-compose up -d --build celery_worker
```

### Stop/Start Services
```bash
# Stop all services
docker-compose stop

# Stop specific service
docker-compose stop celery_worker

# Start services
docker-compose start

# Stop and remove containers (clean restart)
docker-compose down
docker-compose up -d
```

---

## Application Health Monitoring

### Health Check Endpoints
```bash
# Basic health check
curl http://localhost:8000/health
# Returns: {"status": "healthy", "timestamp": "...", "version": "..."}

# Database pool status
curl http://localhost:8000/health/db-pool
# Returns connection pool stats (size, overflow, checked_out)

# With JSON formatting (requires jq)
curl -s http://localhost:8000/health | jq .
```

### API Status Checks
```bash
# Check if API is responding
curl -I http://localhost:8000/health
# Should return: HTTP/1.1 200 OK

# Check Swagger docs are accessible
curl -I http://localhost:8000/docs

# Test authentication endpoint
curl -X POST http://localhost:8000/api/auth/test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Database Monitoring

### Connect to PostgreSQL
```bash
# Using docker exec (if DB in container)
docker exec -it neondb psql -U neondb_owner -d neondb

# Direct connection (if DB is remote/Neon)
psql "postgresql://neondb_owner:password@host/neondb"
```

### Useful Database Queries

#### Check Active Connections
```sql
-- View all active connections
SELECT pid, usename, application_name, client_addr, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'neondb'
ORDER BY query_start DESC;

-- Count connections by state
SELECT state, COUNT(*)
FROM pg_stat_activity
WHERE datname = 'neondb'
GROUP BY state;
```

#### Monitor Long-Running Queries
```sql
-- Queries running longer than 30 seconds
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '30 seconds'
  AND datname = 'neondb'
ORDER BY duration DESC;
```

#### Check Table Sizes
```sql
-- Largest tables
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

#### Recent User Activity
```sql
-- Recent credit transactions
SELECT
    user_id,
    transaction_type,
    amount,
    balance_after,
    created_at
FROM credit_transactions
ORDER BY created_at DESC
LIMIT 20;

-- Recent insight generation jobs
SELECT
    job_id,
    chat_id,
    status,
    completed_insights,
    failed_insights,
    created_at,
    completed_at
FROM insight_generation_jobs
ORDER BY created_at DESC
LIMIT 20;

-- Active coin reservations (should timeout after 30 min)
SELECT
    user_id,
    coins_reserved,
    reason,
    expires_at,
    created_at
FROM coin_reservations
WHERE status = 'active'
ORDER BY created_at;
```

#### Check Vector Indexing Status
```sql
-- Chats by vector status
SELECT
    vector_status,
    COUNT(*) as count
FROM chats
GROUP BY vector_status;

-- Chats stuck in indexing (more than 1 hour)
SELECT
    id,
    user_id,
    vector_status,
    updated_at
FROM chats
WHERE vector_status = 'indexing'
  AND updated_at < NOW() - INTERVAL '1 hour';

-- Insights by status
SELECT
    status,
    COUNT(*) as count
FROM insights
GROUP BY status;
```

### Database Migrations Status
```bash
# Check current migration version
docker exec relivchats-api alembic current

# Check migration history
docker exec relivchats-api alembic history

# Check if migrations need to run
docker exec relivchats-api alembic heads
docker exec relivchats-api alembic current
# If different, run: alembic upgrade head
```

---

## Celery Worker Monitoring

### Check Worker Status
```bash
# View Celery worker logs
docker-compose logs -f celery_worker

# Inspect active tasks
docker exec celery_worker celery -A src.celery_app inspect active

# Check registered tasks
docker exec celery_worker celery -A src.celery_app inspect registered

# Check worker stats
docker exec celery_worker celery -A src.celery_app inspect stats

# Check scheduled tasks
docker exec celery_worker celery -A src.celery_app inspect scheduled

# Check reserved tasks (queued but not started)
docker exec celery_worker celery -A src.celery_app inspect reserved
```

### Celery Task Management
```bash
# Revoke a specific task
docker exec celery_worker celery -A src.celery_app control revoke TASK_ID

# Purge all pending tasks (DANGEROUS!)
docker exec celery_worker celery -A src.celery_app purge
```

### Flower Dashboard (Task Monitoring UI)
```bash
# Start Flower (if not already running)
docker exec -d celery_worker celery -A src.celery_app flower --port=5555

# Access in browser
# http://your-server:5555
```

---

## Redis Monitoring

### Connect to Redis
```bash
# Connect to Redis CLI
docker exec -it redis redis-cli

# Or if Redis is external
redis-cli -h your-redis-host -p 6379 -a your-password
```

### Useful Redis Commands
```redis
# Check Redis is responding
PING
# Returns: PONG

# Get Redis info
INFO
INFO stats
INFO memory

# Check number of keys
DBSIZE

# View all keys (CAREFUL in production - use SCAN instead)
KEYS *

# Better way to view keys (pagination)
SCAN 0 MATCH celery* COUNT 100

# Check specific key
GET celery-task-meta-TASK_ID

# View list length (for queues)
LLEN celery

# Monitor commands in real-time
MONITOR
```

### Check Celery Queue Status
```redis
# Check queue length
LLEN celery
# Returns number of pending tasks

# Peek at first task in queue (without removing)
LRANGE celery 0 0

# Check task results
KEYS celery-task-meta-*
```

---

## Qdrant Vector Database Monitoring

### Check Qdrant Health
```bash
# Health check
curl http://localhost:6333/health

# Get collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/chat_messages

# Collection stats (with API key if needed)
curl -X GET 'http://localhost:6333/collections/chat_messages' \
  -H 'api-key: YOUR_QDRANT_API_KEY'
```

### Qdrant Metrics
```bash
# Get metrics (Prometheus format)
curl http://localhost:6333/metrics

# Count vectors in collection
curl -X POST 'http://localhost:6333/collections/chat_messages/points/count' \
  -H 'Content-Type: application/json' \
  -H 'api-key: YOUR_QDRANT_API_KEY' \
  -d '{}'
```

---

## Log Analysis & Debugging

### Extract Specific Request Logs
```bash
# Follow a specific request ID
docker-compose logs relivchats-api | grep "req=741beea2"

# Extract all logs for a user
docker-compose logs relivchats-api | grep "user_35O41Xw3BIECxUc22RACtYOK2AP"

# Find all slow requests
docker-compose logs relivchats-api | grep "Slow request detected"

# Find all 500 errors
docker-compose logs relivchats-api | grep " - 500 "

# Find all failed Celery tasks
docker-compose logs celery_worker | grep "Task.*failed"
```

### Performance Monitoring
```bash
# Find requests taking > 5 seconds
docker-compose logs relivchats-api | grep "Request completed" | \
  awk '{print $NF}' | sort -rn | head -20

# Count requests by endpoint
docker-compose logs relivchats-api | grep "Incoming request" | \
  awk '{print $8}' | sort | uniq -c | sort -rn

# Count errors by type
docker-compose logs relivchats-api | grep ERROR | \
  awk -F'|' '{print $3}' | sort | uniq -c | sort -rn
```

### Export Logs for Analysis
```bash
# Export last 24 hours to file
docker-compose logs --since=24h relivchats-api > logs_$(date +%Y%m%d).log

# Export logs between specific times
docker-compose logs \
  --since="2024-01-13T08:00:00" \
  --until="2024-01-13T09:00:00" \
  relivchats-api > logs_incident.log

# Export only errors
docker-compose logs relivchats-api | grep ERROR > errors_$(date +%Y%m%d).log
```

---

## Resource Monitoring

### Docker Resource Usage
```bash
# Real-time resource usage
docker stats

# Specific container stats
docker stats relivchats-api celery_worker

# One-time snapshot
docker stats --no-stream
```

### Disk Usage
```bash
# Docker disk usage summary
docker system df

# Detailed view
docker system df -v

# Check logs directory size
du -sh /var/lib/docker/containers/*/

# Application logs size (if using volume)
du -sh ./logs/
```

### System Resources
```bash
# Memory usage
free -h

# CPU usage
top -bn1 | head -20

# Disk usage
df -h

# Network connections
netstat -tupln | grep :8000
```

---

## Cleanup & Maintenance

### Clean Docker Resources
```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -f

# Remove unused volumes (CAREFUL!)
docker volume prune -f

# Full cleanup (DANGEROUS - removes everything unused)
docker system prune -a --volumes -f
```

### Database Maintenance
```sql
-- Vacuum analyze (reclaim space & update stats)
VACUUM ANALYZE;

-- Check table bloat
SELECT
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clear old logs/transactions (example - adjust retention)
DELETE FROM credit_transactions
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## Troubleshooting Common Issues

### Issue: API Not Responding
```bash
# Check if container is running
docker ps | grep relivchats-api

# Check container logs for errors
docker-compose logs --tail=100 relivchats-api

# Check resource usage
docker stats relivchats-api --no-stream

# Restart API
docker-compose restart relivchats-api
```

### Issue: Celery Tasks Stuck
```bash
# Check worker is running
docker ps | grep celery_worker

# Check active tasks
docker exec celery_worker celery -A src.celery_app inspect active

# Check worker logs
docker-compose logs --tail=100 celery_worker

# Restart worker
docker-compose restart celery_worker

# If tasks are stuck, purge queue (CAREFUL!)
docker exec celery_worker celery -A src.celery_app purge
```

### Issue: Database Connection Errors
```bash
# Check PostgreSQL is accepting connections
psql "postgresql://user:pass@host/db" -c "SELECT 1"

# Check connection pool status
curl http://localhost:8000/health/db-pool

# Check active connections in DB
# (Run SQL query from Database Monitoring section)

# Restart API to reset connection pool
docker-compose restart relivchats-api
```

### Issue: High Memory Usage
```bash
# Check which container is using memory
docker stats --no-stream

# Check Python processes inside container
docker exec relivchats-api ps aux

# Check for memory leaks in logs
docker-compose logs relivchats-api | grep -i "memory"

# Restart service to clear memory
docker-compose restart relivchats-api
```

### Issue: Quota Errors (Gemini API)
```bash
# Check recent quota errors
docker-compose logs relivchats-api | grep "RESOURCE_EXHAUSTED" | tail -20

# Count quota errors in last hour
docker-compose logs --since=1h relivchats-api | grep "RESOURCE_EXHAUSTED" | wc -l

# Check Gemini usage dashboard
# Visit: https://ai.dev/rate-limit
```

---

## Monitoring Checklist (Daily)

```bash
# 1. Check all services are running
docker ps

# 2. Check API health
curl http://localhost:8000/health

# 3. Check recent errors (last hour)
docker-compose logs --since=1h relivchats-api | grep ERROR | wc -l

# 4. Check Celery worker status
docker exec celery_worker celery -A src.celery_app inspect active

# 5. Check disk usage
docker system df

# 6. Check database connections
# Run SQL: SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'neondb';

# 7. Check Redis
docker exec redis redis-cli PING
```

---

## Quick Incident Response

### When API Goes Down
```bash
# 1. Check container status
docker ps -a | grep relivchats-api

# 2. Check last 50 log lines
docker-compose logs --tail=50 relivchats-api

# 3. Check resources
docker stats relivchats-api --no-stream

# 4. Restart API
docker-compose restart relivchats-api

# 5. Monitor startup
docker-compose logs -f relivchats-api

# 6. Test health endpoint
curl http://localhost:8000/health
```

### When Insights Generation Fails
```bash
# 1. Check Celery worker logs
docker-compose logs --tail=100 celery_worker | grep ERROR

# 2. Check specific job status in database
# Run SQL: SELECT * FROM insight_generation_jobs WHERE job_id = 'xxx';

# 3. Check Gemini API quota
docker-compose logs relivchats-api | grep "RESOURCE_EXHAUSTED"

# 4. Check Qdrant health
curl http://localhost:6333/health

# 5. Check if worker is processing
docker exec celery_worker celery -A src.celery_app inspect active

# 6. Restart worker if needed
docker-compose restart celery_worker
```

---

## Useful Aliases (Add to ~/.bashrc or ~/.zshrc)

```bash
# Docker compose shortcuts
alias dc='docker-compose'
alias dcl='docker-compose logs -f --tail=100'
alias dps='docker ps'
alias dcu='docker-compose up -d'
alias dcd='docker-compose down'
alias dcr='docker-compose restart'

# Log viewing
alias api-logs='docker-compose logs -f relivchats-api'
alias celery-logs='docker-compose logs -f celery_worker'
alias api-errors='docker-compose logs relivchats-api | grep ERROR'

# Health checks
alias api-health='curl -s http://localhost:8000/health | jq .'
alias api-db='curl -s http://localhost:8000/health/db-pool | jq .'

# Quick status
alias status='docker ps && echo "\n--- API Health ---" && curl -s http://localhost:8000/health | jq .'
```

---

## Alerting & Monitoring Tools (Recommended)

### Application Monitoring
- **Sentry**: Already integrated for error tracking
  - Dashboard: https://sentry.io/organizations/your-org/projects/
  - Check for new errors, performance issues

### Infrastructure Monitoring
- **Uptime Robot**: Free uptime monitoring
  - Monitor: http://your-api.com/health
  - Email/SMS alerts on downtime

### Log Management
- **Papertrail** or **LogDNA**: Centralized log aggregation
- **Grafana Loki**: Self-hosted log aggregation

### Metrics & Dashboards
- **Prometheus + Grafana**: Metrics collection & visualization
- **DataDog**: All-in-one monitoring (paid)

---

## Emergency Contacts & Resources

### Quick Reference URLs
- **API Docs**: http://your-domain.com/docs
- **Sentry Dashboard**: https://sentry.io/your-org
- **Flower (Celery)**: http://your-domain:5555
- **Qdrant Dashboard**: http://your-qdrant:6333/dashboard

### Important Environment Variables
```bash
# Check current environment
docker exec relivchats-api env | grep ENVIRONMENT

# Check key settings
docker exec relivchats-api env | grep -E "DATABASE_URL|REDIS_URL|GEMINI_API_KEY|QDRANT_URL"
```

---

**Last Updated**: January 2026
**For**: RelivChats API Production Monitoring
**Stack**: FastAPI, PostgreSQL, Celery, Redis, Qdrant, Docker
