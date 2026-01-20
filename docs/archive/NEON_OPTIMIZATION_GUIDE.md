# Neon DB Production Optimization Guide

## Problem Statement

Your application experiences **4-11 second latencies** on simple queries like `/api/categories` which should take **100-300ms**. This is caused by Neon's "Scale to Zero" feature suspending compute after 5 minutes of inactivity.

## Root Cause Analysis

### The Scale-to-Zero Penalty
- Neon free tier automatically **suspends compute after 5 minutes of inactivity**
- When requests come in, the compute must **spin back up** (3-10 second cold start)
- Every request shows this pattern in logs: `SELECT 1` takes 3-11 seconds

### Secondary Issues
1. **Undersized connection pool**: Only 2 connections - too small for concurrent requests
2. **SQL echo enabled**: `echo=True` in database.py adds ~5-10% overhead
3. **Aggressive pool recycling**: `pool_recycle=280` (4.5 min) causes unnecessary reconnections
4. **No statement caching**: Every query is re-parsed by the database
5. **No request-level caching**: Categories fetched from DB every request

---

## Optimizations Implemented

### 1. Connection Pool Optimization (SQLAlchemy)

**File**: `src/database.py`

#### Changes:
- **Async pool size**: Increased from 2 to 15 persistent connections
- **Max overflow**: Added 5 additional overflow connections (total: 20)
- **Pool timeout**: Reduced from 30s to 10s (fail faster if exhausted)
- **Pool recycle**: Increased from 280s to 3600s (hourly instead of 4.5 min)
- **Statement caching**: Enabled (was disabled)
- **Prepared statements**: Enabled (was disabled)
- **SQL echo**: Conditional - only in DEBUG mode

#### Impact:
- Reduces connection wait times
- Fewer reconnections
- Better query planning through caching

### 2. Scale-to-Zero Mitigation (Keepalive)

**File**: `src/main.py`

#### Implementation:
```python
# Background task runs every 4 minutes in production
# Executes: SELECT 1
# Prevents compute suspension between user requests
```

#### How it works:
- Starts on application startup (only in production)
- Runs every 240 seconds (4 minutes)
- Sends lightweight `SELECT 1` query to keep compute active
- Automatically cancels on shutdown

#### Impact:
- **Prevents Scale-to-Zero suspension** between requests
- Eliminates the 3-10 second cold start penalty
- Cost: negligible (one lightweight query every 4 min)

### 3. Redis Caching Layer

**File**: `src/categories/router.py`

#### Implementation:
- **Cache key**: `categories:all`
- **TTL**: 3600 seconds (1 hour)
- **Fallback**: Gracefully degrades if Redis unavailable

#### Logic Flow:
1. Check Redis cache
2. If cached: Return in ~10-50ms
3. If not cached: Query database
4. Cache the result for future requests
5. If cache fails: Continue without caching (non-blocking)

#### Impact:
- First request: 100-300ms (database)
- Subsequent requests: 10-50ms (Redis)
- **~10-20x faster for cached requests**

### 4. Configuration Management

**File**: `src/config.py`

#### New settings:
```python
DB_POOL_SIZE = 15
DB_MAX_OVERFLOW = 5
DB_POOL_TIMEOUT = 10
DB_POOL_RECYCLE = 3600
DB_ECHO_ENABLED = False
DB_STATEMENT_CACHE_SIZE = 20
DB_PREPARED_STMT_CACHE_SIZE = 10
```

---

## Expected Performance Improvements

### Before Optimization
```
GET /api/categories (first request):  9,700ms (cold start)
GET /api/categories (subsequent):     4,800ms (Scale-to-Zero suspension)
```

### After Optimization (Production)
```
GET /api/categories (first request):  200-300ms (database hit + keepalive active)
GET /api/categories (cached):         10-50ms   (Redis cache)
GET /api/categories (sustained load): 150-250ms (keepalive prevents cold starts)
```

### Optimization Breakdown
- **Keepalive task**: Eliminates 3-10s cold start penalty
- **Connection pooling**: Reduces queue wait time by 50-70%
- **Statement caching**: Reduces per-query overhead by 5-15%
- **Redis caching**: Reduces categories endpoint to 10-50ms (non-DB hits)

**Expected total improvement: 10-30x faster queries**

---

## Neon DB Free Tier Limitations & Workarounds

### Limitation 1: Scale-to-Zero
- **Free tier**: Suspends after 5 minutes inactivity
- **Workaround**: Our keepalive task (SELECT 1 every 4 minutes)
- **Cost**: Negligible

### Limitation 2: 2 CU Max Autoscaling
- **Free tier**: Can only scale to 0.25-2 CUs
- **Workaround**: Connection pooling + statement caching (maximize efficiency)
- **Future**: Upgrade to paid tier if needed

### Limitation 3: No Read Replicas
- **Free tier**: Single compute endpoint
- **Workaround**: Redis caching for read-heavy endpoints
- **Future**: Upgrade to use read replicas

### Limitation 4: 100 connections @ 1GB RAM
- **Free tier**: ~100 concurrent connections
- **Our usage**: 15 persistent + 5 overflow = 20 connections (well within limits)

---

## Production Deployment Checklist

### Before deploying to production:

#### 1. Configure Neon Dashboard
- [ ] Go to Neon console: `https://console.neon.tech`
- [ ] Select your project
- [ ] Go to **Compute** settings
- [ ] **Disable "Scale to Zero"** (or set minimum to 0.25 CU)
  - This costs ~$0.40/month
  - Makes this keepalive task unnecessary (but harmless if enabled)
- [ ] Set **autoscaling minimum**: 0.25 CU
- [ ] Set **autoscaling maximum**: 2 CU (free tier max)

#### 2. Enable Environment Variable
- [ ] Set `ENVIRONMENT=production` in production deployment
- [ ] This activates the keepalive task automatically

#### 3. Database Indexes
- [ ] Verify indexes on frequently queried columns:
  ```sql
  -- Check existing indexes
  SELECT * FROM pg_stat_user_indexes;

  -- Recommended indexes:
  CREATE INDEX idx_analysis_category_is_active
    ON analysis_categories(is_active)
    WHERE is_active = true;

  CREATE INDEX idx_category_insight_type_category_id
    ON category_insight_types(category_id);

  CREATE INDEX idx_insight_type_active
    ON insight_types(is_active)
    WHERE is_active = true;
  ```

#### 4. Monitor Performance
- [ ] Use `/health/db-pool` endpoint to monitor connection pool status
- [ ] Watch logs for "Neon keepalive: connection refreshed"
- [ ] Monitor Redis memory usage (if using caching)

---

## Monitoring & Troubleshooting

### Health Check Endpoints

```bash
# Check overall health
curl http://localhost:8000/health

# Check database pool status
curl http://localhost:8000/health/db-pool
```

### Expected Response (db-pool):
```json
{
  "pool_type": "QueuePool",
  "pooling_enabled": true,
  "pool_size": 15,
  "checked_out": 2,
  "overflow": 0,
  "checked_in": 13,
  "total_connections": 15,
  "available": 13,
  "status": "healthy"
}
```

### Troubleshooting

#### Problem: Still seeing 4-10s query times
- [ ] Check if `ENVIRONMENT=production` is set
- [ ] Verify keepalive task is running (check logs)
- [ ] Check if Neon Scale-to-Zero is disabled in dashboard
- [ ] Look for "Scale-to-Zero suspension" messages in logs

#### Problem: Redis connection errors
- [ ] Verify `REDIS_URL` is correct
- [ ] Check if Redis is running: `docker-compose ps`
- [ ] Restart Redis: `docker-compose restart redis`
- [ ] Caching will gracefully degrade if Redis unavailable

#### Problem: Connection pool exhaustion
- [ ] Monitor `/health/db-pool` endpoint
- [ ] Increase `DB_POOL_SIZE` if checked_out > 10
- [ ] Check for connection leaks in application code

### Performance Metrics to Track

1. **Query Latency**
   ```
   Slow query threshold: 1000ms (config.py: SLOW_DATABASE_QUERY_THRESHOLD_MS)
   Target: < 300ms for simple queries
   ```

2. **Connection Pool Health**
   ```
   Target: < 70% utilization
   Available connections should be > 5
   ```

3. **Cache Hit Rate**
   ```
   Monitor Redis: MONITOR command
   Track % of requests served from cache
   ```

---

## Advanced Configuration Options

### Scale Compute Up If Needed
For higher performance, upgrade to a paid Neon plan:

| Plan | Cost | Max Compute | Features |
|------|------|-------------|----------|
| Free | $0 | 2 CU | Scale-to-Zero, no read replicas |
| Growth | $15/month | 4 CU | 24/7 availability option, read replicas |
| Pro | $25/month | 8 CU | Priority support, auto-failover |

### Use PgBouncer Connection Pooler
Neon provides a built-in connection pooler:
- Connection string: `postgres://user:pass@ep-xxxx-pooler.neon.tech/dbname`
- Replaces SQLAlchemy pooling
- Supports up to 10,000 concurrent connections
- [Docs](https://neon.com/docs/guides/connection-pooling)

**Current setup** uses SQLAlchemy pooling + keepalive, which is sufficient for free tier.

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `src/database.py` | Pool size 2→15, statement caching enabled | Reduce queue wait, enable query optimization |
| `src/main.py` | Add keepalive background task | Prevent Scale-to-Zero suspension |
| `src/config.py` | Add performance settings | Centralized configuration |
| `src/categories/router.py` | Add Redis caching | 10-20x faster for cached requests |

---

## References

- [Neon Connection Pooling Guide](https://neon.com/docs/manage/endpoints)
- [Neon Performance Tips](https://neon.com/blog/performance-tips-for-neon-postgres)
- [SQLAlchemy Connection Pooling Docs](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [Redis Async Python Docs](https://redis-py.readthedocs.io/en/stable/connections.html)

---

## Next Steps for Further Optimization

### Phase 2 (Optional)
1. Add indexes on frequently queried columns
2. Implement query result caching for other endpoints
3. Use Neon's PgBouncer connection pooler directly
4. Add query performance monitoring with pg_stat_statements

### Phase 3 (If Scaling)
1. Upgrade to paid Neon tier for 24/7 availability
2. Enable read replicas for read-heavy queries
3. Implement application-level query caching (Redis)
4. Consider connection pooling layer (PgBouncer standalone)

