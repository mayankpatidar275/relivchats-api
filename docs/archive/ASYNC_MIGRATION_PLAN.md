# Async Migration Plan - RelivChats API
**Status**: Draft for Review
**Created**: December 2025
**Scope**: Full synchronous-to-asynchronous migration for all FastAPI endpoints
**Database**: PostgreSQL + AsyncPG for async engine (separate from Celery's NullPool)

---

## Executive Summary

This plan migrates all 29 FastAPI endpoints from synchronous to asynchronous execution while maintaining a separate synchronous engine for Celery workers (as previously confirmed as best practice). The migration is structured in 4 phases to minimize risk, ensure thorough testing, and maintain production stability.

**Key Principles:**
- ✅ Dual-engine architecture: Async engine for FastAPI, Sync engine for Celery (NullPool)
- ✅ Production-grade: Comprehensive error handling, connection pooling, transaction management
- ✅ Future-proof: Supports horizontal scaling, monitoring, and observability
- ✅ Zero downtime: Incremental rollout with feature flags and rollback capabilities

---

## Phase 1: Foundation & Infrastructure (Week 1)

### 1.1 Database Layer Enhancements

**Location**: `src/database.py`

**Changes Required:**
1. **Async Session Configuration**
   - Current: Already has `async_engine` and `async_session` factory ✓
   - Enhance: Add connection lifecycle hooks for debugging
   - Add: Explicit transaction isolation level (`REPEATABLE READ`)
   - Add: Statement caching tuning (20 prepared statements)

2. **Connection Pool Monitoring**
   - Current: `/health/db-pool` endpoint exists ✓
   - Enhance: Add metrics for pool exhaustion warnings
   - Add: Pool pre-warming on startup (optional warm-up connections)
   - Add: Event listeners for pool overflow events

3. **Async Context Manager Wrapper**
   - Create: `get_async_db_with_transaction()` context manager
   - Purpose: Auto-rollback on exceptions, proper cleanup
   - Pattern: Replaces raw `async with async_session() as db:` calls
   ```python
   @asynccontextmanager
   async def get_async_db_transaction():
       async with async_session() as db:
           try:
               yield db
               await db.commit()
           except Exception as e:
               await db.rollback()
               logger.error("Transaction rollback", extra={"error": str(e)})
               raise
           finally:
               await db.close()
   ```

4. **Soft Delete Filter Implementation**
   - Problem: `User`, `Chat`, `AIConversation` have `is_deleted` field but queries don't filter
   - Solution: Add automatic soft-delete filtering using SQLAlchemy `@declared_attr`
   - Implementation:
   ```python
   @declared_attr
   def __mapper_args__(cls):
       return {
           "filters": [cls.is_deleted == False]  # Auto-filter deleted records
       }
   ```
   - Files affected: `users/models.py`, `chats/models.py`, `rag/models.py` (AIConversation)

**Deliverables:**
- [ ] Enhanced `database.py` with soft-delete support
- [ ] Updated `main.py` startup to test async connection pool
- [ ] Monitoring queries for `/health/db-pool` endpoint

---

### 1.2 Celery-Async Separation

**Objective**: Ensure Celery uses separate sync engine, FastAPI uses async engine

**Changes Required:**
1. **Verify Dual-Engine Isolation** (`src/database.py`)
   - Current: Already correctly configured ✓
   - Verify: `CELERY_WORKER=true` → NullPool
   - Verify: FastAPI → QueuePool with asyncpg
   - Add: Logging to confirm which engine is being used

2. **Celery Task Update** (`src/rag/tasks.py`)
   - Current: Uses `SessionLocal()` (sync) ✓
   - Verify: All 6 tasks use sync session
   - No changes needed - keep as-is

3. **Remove Hybrid Async/Sync Pattern** (`src/rag/sync_generation_service.py`)
   - Current: Uses `asyncio.run()` to call async CreditService inside sync Celery
   - Action: Create sync-only version of `CreditService` methods OR
   - Action: Create bridge that doesn't require `asyncio.run()` overhead
   - Details in Phase 2

**Deliverables:**
- [ ] Confirmation that Celery uses NullPool (no connection pooling)
- [ ] Confirmation that FastAPI async endpoints use AsyncQueuePool
- [ ] Logging to distinguish engine usage

---

### 1.3 High-Risk Model Preparation

**Objective**: Prepare database models for async queries, especially those with unique constraints

**Models Requiring Special Handling:**

1. **Insight Model** (`src/rag/models.py`)
   - Problem: `UNIQUE(chat_id, insight_type_id)` can race in concurrent generation
   - Solution: Add UPSERT logic in insight creation
   ```python
   # Instead of:
   # new_insight = Insight(...)
   # db.add(new_insight); await db.commit()

   # Use INSERT ... ON CONFLICT DO UPDATE:
   stmt = insert(Insight).values(...).on_conflict_do_update(
       index_elements=['chat_id', 'insight_type_id'],
       set_={Insight.status: 'pending'}
   )
   await db.execute(stmt)
   ```

2. **InsightGenerationJob Model** (`src/rag/models.py`)
   - Problem: `job_id` UNIQUE constraint, critical for idempotency
   - Solution: Use `INSERT ... ON CONFLICT DO NOTHING` with check after
   ```python
   stmt = insert(InsightGenerationJob).values(...).on_conflict_do_nothing()
   await db.execute(stmt)

   # Then query to get the job (either new or existing)
   job = await db.scalar(select(InsightGenerationJob).filter_by(job_id=...))
   ```

3. **CreditTransaction Model** (`src/credits/models.py`)
   - Problem: Row-level locking with `with_for_update()` can deadlock
   - Solution: Add lock timeout and retry logic
   ```python
   stmt = select(User).where(User.user_id == user_id).with_for_update(nowait=True)
   try:
       result = await db.execute(stmt)
   except OperationalError as e:
       if "lock not available" in str(e):
           # Retry with exponential backoff
           await asyncio.sleep(random.uniform(0.1, 0.5))
       raise
   ```

4. **PaymentOrder Model** (`src/payments/models.py`)
   - Problem: Multiple UNIQUE constraints (`provider_order_id`, `idempotency_key`)
   - Solution: Use UPSERT with proper handling
   - Ensure: Webhook idempotency enforced at DB level

**Deliverables:**
- [ ] UPSERT implementations for Insight and InsightGenerationJob
- [ ] Lock timeout handling in CreditService
- [ ] Deadlock retry logic with exponential backoff

---

### 1.4 Async Dependency Injection Updates

**Objective**: Prepare FastAPI dependencies for async database access

**Location**: `src/auth/dependencies.py`, router files

**Changes Required:**

1. **Create Async DB Dependency**
   - Current: Endpoints use `Depends(get_db)` for sync sessions
   - New: Create `get_async_db()` dependency
   ```python
   async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
       async with async_session() as session:
           yield session
   ```

2. **Update Router Endpoints**
   - Gradual migration: Each endpoint updated individually
   - Pattern: `def endpoint(db: Session = Depends(get_db))` → `async def endpoint(db: AsyncSession = Depends(get_async_db))`
   - Validation: All DB calls converted from `db.query()` to `select()` + `await db.execute()`

3. **Error Handling for Async**
   - AsyncSession raises different exceptions than sync
   - Add: `asyncio.TimeoutError`, `asyncpg.exceptions`
   - Update: `error_handlers.py` to handle async-specific exceptions

**Deliverables:**
- [ ] `get_async_db()` dependency implemented
- [ ] Error handler for async database exceptions
- [ ] Dependency injection examples for all 7 routers

---

## Phase 2: Router Migration (Weeks 2-3)

**Total Endpoints**: 29
**Priority Order**: Based on usage frequency and risk level

### Priority 1: Low-Risk, Async-Ready (Week 2)

**These endpoints have minimal database operations and no complex transactions.**

#### 2.1 Categories Router (3 endpoints) - EASIEST
**File**: `src/categories/router.py`

**Endpoints:**
1. `GET /api/categories` - Get all categories
2. `GET /api/categories/{category_id}/insights` - Get insight types for category

**Current State**: Already uses `get_async_db()` ✓

**Action**: Verify only (no changes needed)

---

#### 2.2 Users Router (2 endpoints) - EASY
**File**: `src/users/router.py`

**Endpoints:**
1. `POST /api/users/store` - Store user on first login
2. `DELETE /api/users/delete-account` - GDPR account deletion

**Current State**: Already async ✓

**Action**: Verify only, enhance soft-delete cleanup:
- When deleting user, also soft-delete related chats/conversations
- Implement background task for hard-delete after 30 days

---

#### 2.3 Credits Router (3 endpoints) - EASY
**File**: `src/credits/router.py`

**Endpoints:**
1. `GET /api/credits/balance` - Get user's credit balance
2. `GET /api/credits/transactions` - Get transaction history
3. `GET /api/credits/packages` - Get available packages

**Current State**: Already async ✓

**Action**: Verify pagination performance with async queries

---

#### 2.4 Health & Status Endpoints (3 endpoints) - TRIVIAL
**File**: `src/main.py`

**Endpoints:**
1. `GET /health` - Health check
2. `GET /health/db-pool` - Connection pool status
3. `GET /` - Welcome message

**Current State**: Already async ✓

**Action**: Verify only

---

### Priority 2: Medium-Risk, Transaction Heavy (Week 2-3)

#### 2.5 Insights Router (3 endpoints) - CRITICAL
**File**: `src/insights/router.py`

**Endpoints:**
1. `POST /api/insights/unlock` - Unlock insights for a category
2. `GET /api/insights/jobs/{job_id}/status` - Get generation job status
3. `GET /api/insights/chats/{chat_id}` - Get all insights for a chat

**Current State**: Already async ✓

**Action**: Review and enhance:
- Verify `unlock_insights_for_category()` in credits/service.py is fully async
- Add lock timeout handling (Phase 1 prep)
- Test concurrent unlocks from same user

---

#### 2.6 Payments Router (4 endpoints) - CRITICAL
**File**: `src/payments/router.py`

**Endpoints:**
1. `POST /api/payments/orders` - Create payment order
2. `POST /api/payments/webhooks/razorpay` - Razorpay webhook
3. `POST /api/payments/webhooks/stripe` - Stripe webhook
4. `GET /api/payments/orders/{order_id}` - Get order status

**Current State**: Already async ✓

**Migration Tasks:**
1. Verify idempotency key logic works with async
2. Test webhook race conditions (duplicate webhooks)
3. Ensure transaction isolation (REPEATABLE READ) for payment updates

---

### Priority 3: High-Risk, Complex Queries (Weeks 2-3)

#### 2.7 Chats Router (8 endpoints) - HIGHEST RISK
**File**: `src/chats/router.py`

**Endpoints:**
1. `POST /api/chats/upload` - Upload WhatsApp chat (SYNC)
2. `GET /api/chats` - List user's chats
3. `GET /api/chats/{chat_id}` - Get chat details
4. `GET /api/chats/{chat_id}/messages` - Get messages
5. `GET /api/chats/{chat_id}/vector-status` - Vector indexing status
6. `DELETE /api/chats/{chat_id}` - Delete chat
7. `GET /api/chats/public/{chat_id}/stats` - Public stats (no auth)
8. `PUT /api/chats/{chat_id}/display-name` - Update display name

**Current State**: ALL SYNC - highest priority for migration

**Challenges:**
- File upload processing is CPU-bound (blocking)
- Large chat parsing (whatstk library)
- Complex relationships (Chat → Messages, Insights, AIConversations)
- Soft delete not consistently applied

**Migration Strategy:**

**Step 1: File Upload Handling** (lines 50-120)
- Problem: `process_whatsapp_file()` is CPU-bound, blocks request
- Solution: Use `ThreadPoolExecutor` for file parsing
```python
@app.post("/api/chats/upload")
async def upload_chat(file: UploadFile, db: AsyncSession = Depends(get_async_db)):
    # Run CPU-intensive parsing in thread pool
    loop = asyncio.get_event_loop()
    parsed_messages = await loop.run_in_executor(
        ThreadPoolExecutor(max_workers=2),
        process_whatsapp_file,
        await file.read()
    )
    # Then use async db operations
    chat = Chat(...)
    db.add(chat)
    await db.commit()
```

**Step 2: Query Conversion** (lines 150-300)
- Replace `db.query()` with `select()` + `await db.execute()`
- Add eager loading with `joinedload()` and `selectinload()`
- Example:
```python
# OLD:
chat = db.query(Chat).filter(Chat.id == chat_id).first()

# NEW:
stmt = select(Chat).where(Chat.id == chat_id).options(
    joinedload(Chat.category),
    selectinload(Chat.insights)
)
result = await db.execute(stmt)
chat = result.scalar_one_or_none()
```

**Step 3: Soft Delete Enforcement**
- Add `is_deleted = False` filters to all Chat queries
- Already handled by SQLAlchemy filter in Phase 1

**Step 4: Transaction Boundaries**
- Use async context manager for multi-step operations
- Ensure `await db.commit()` at transaction end

**Deliverables for Chats:**
- [ ] ThreadPoolExecutor implementation for file upload
- [ ] All query conversions completed
- [ ] Soft delete filters verified
- [ ] Tested with uploads of 500+ messages

---

#### 2.8 RAG Router (2 endpoints) - HIGHEST RISK
**File**: `src/rag/router.py`

**Endpoints:**
1. `POST /api/rag/query` - Ask question about chat (conversational RAG)
2. `POST /api/rag/generate` - Generate insight (DEPRECATED)

**Current State**: SYNC

**Challenges:**
- Synchronous Qdrant client blocking
- Synchronous Gemini API calls
- RAG context extraction is expensive (10+ second operation)

**Migration Strategy:**

**Step 1: Wrap Qdrant Calls**
- Current: Qdrant client is synchronous
- Solution: Keep sync for now, OR wrap in executor
```python
loop = asyncio.get_event_loop()
results = await loop.run_in_executor(
    None,  # Use default executor
    qdrant_client.search,
    query_vector, 5  # top-5 results
)
```

**Step 2: Wrap Gemini Calls**
- Current: `client.models.generate_content()` is blocking
- Solution: Use executor OR use official async client (if available)
- Check: Google Gemini API async support (Phase 1 research)

**Step 3: RAG Context Caching**
- Current: Pre-extracted context stored in Redis ✓
- Enhance: Add async Redis access (use `aioredis` if needed)

**Step 4: Convert Service Methods**
- Target: Make `rag/service.py` functions async
- Pattern: `async def fetch_rag_chunks(...) -> List[str]:`
- Use: ThreadPoolExecutor or async wrappers for external calls

**Deliverables for RAG:**
- [ ] ThreadPoolExecutor for Qdrant searches
- [ ] ThreadPoolExecutor or async client for Gemini
- [ ] Async Redis access (optional enhancement)
- [ ] Load test with 10 concurrent RAG queries

---

### Phase 2 Summary

**Completion Metrics:**
- [ ] All 29 endpoints converted to async def
- [ ] Zero sync `.query()` calls in router files
- [ ] All file I/O wrapped in executor (upload processing)
- [ ] All external API calls (Gemini, Qdrant) wrapped in executor
- [ ] Connection pool pool_size tested under load (10+ concurrent requests)

---

## Phase 3: Celery Worker Hardening (Week 3)

**Objective**: Ensure Celery remains synchronous but robust for async-aware world

### 3.1 Sync-Only Celery Verification

**File**: `src/rag/tasks.py`, `src/celery_app.py`

**Tasks:**

1. **Remove `asyncio.run()` Overhead** (`sync_generation_service.py:240-268`)
   - Current: `CreditService.charge_reserved_coins_async()` called via `asyncio.run()`
   - Problem: Creates new event loop per call (expensive)
   - Solution: Create `CreditService.charge_reserved_coins_sync()` parallel method
   ```python
   # In credits/service.py
   @staticmethod
   def charge_reserved_coins_sync(
       db: Session,
       user_id: str,
       coins_to_charge: int
   ) -> bool:
       """Synchronous version for Celery tasks"""
       # Same logic, but using sync session
       user = db.query(User).filter(...).with_for_update().first()
       # ... charge logic ...
       db.commit()
       return True
   ```

2. **Lock Timeout Configuration** (`src/rag/tasks.py`)
   - Add: Exponential backoff for deadlock retries
   ```python
   MAX_LOCK_RETRIES = 3
   BASE_RETRY_DELAY = 0.1

   for attempt in range(MAX_LOCK_RETRIES):
       try:
           insight = db.query(Insight).filter(...).with_for_update(nowait=True).first()
           break
       except OperationalError as e:
           if "lock not available" in str(e) and attempt < MAX_LOCK_RETRIES - 1:
               time.sleep(BASE_RETRY_DELAY * (2 ** attempt))
           else:
               raise
   ```

3. **Connection Pool Verification** (`src/database.py`)
   - Verify: `CELERY_WORKER=true` → NullPool (no pooling)
   - Confirm: Each task gets fresh connection
   - Monitor: No connection leaks in logs

4. **Reservation Cleanup Task**
   - Current: `cleanup_expired_reservations` task exists ✓
   - Enhance: Add async option for future migration
   - Schedule: Runs every 5 minutes (Celery Beat)

**Deliverables:**
- [ ] Sync version of `CreditService` methods for Celery
- [ ] Lock timeout + retry logic implemented
- [ ] Zero `asyncio.run()` calls in Celery tasks
- [ ] Connection pool verified as NullPool

---

### 3.2 Celery Monitoring & Observability

**Objective**: Ensure Celery remains production-ready during FastAPI async transition

**Tasks:**

1. **Task Timeout Monitoring**
   - Current: `INSIGHT_GENERATION_TIMEOUT = 120 seconds` ✓
   - Add: Alerts for tasks approaching timeout
   - Add: Metrics for task duration distribution

2. **Deadlock Monitoring**
   - Add: Log deadlock retries with exponential backoff
   - Add: Alert if retry count exceeds threshold (3+)
   - Monitor: Lock hold times

3. **Celery Task Metrics**
   - Track: Task success rate, latency, failure reasons
   - Add: Custom logging for business events
   ```python
   logger.info(
       "Insight generation completed",
       extra={"extra_data": {
           "job_id": job_id,
           "total_insights": 6,
           "tokens_used": 15000,
           "duration_ms": 45000
       }}
   )
   ```

**Deliverables:**
- [ ] Celery task metrics exposed (Prometheus or similar)
- [ ] Deadlock retry logging
- [ ] Task timeout alerts configured

---

## Phase 4: Testing, Optimization & Rollout (Week 4)

### 4.1 Comprehensive Testing

**Objective**: Ensure no regressions, verify async correctness

**Test Coverage:**

1. **Unit Tests** (Individual async functions)
   ```python
   @pytest.mark.asyncio
   async def test_upload_chat_async():
       async with AsyncSession(engine) as db:
           response = await client.post("/api/chats/upload", files=...)
           assert response.status_code == 200
   ```

2. **Integration Tests** (Full request flow)
   ```python
   @pytest.mark.asyncio
   async def test_unlock_insights_flow():
       # 1. Upload chat
       # 2. Unlock insights
       # 3. Check job status
       # 4. Verify coins deducted
   ```

3. **Concurrency Tests** (Race conditions)
   ```python
   @pytest.mark.asyncio
   async def test_concurrent_unlocks():
       # Multiple users unlocking same chat category simultaneously
       tasks = [unlock_insights(...) for _ in range(10)]
       results = await asyncio.gather(*tasks)
       assert all(r.status_code == 200 for r in results)
   ```

4. **Connection Pool Tests**
   ```python
   @pytest.mark.asyncio
   async def test_pool_exhaustion():
       # Simulate 50 concurrent requests
       # Verify pool_size=10, max_overflow=5 works correctly
       # Verify timeout behavior when pool exhausted
   ```

5. **Deadlock Detection Tests**
   ```python
   @pytest.mark.asyncio
   async def test_deadlock_retry():
       # Trigger FOR UPDATE lock
       # Simulate concurrent modification
       # Verify retry with exponential backoff
   ```

**Test Files Location**: `tests/` directory (mirrors src structure)

**Deliverables:**
- [ ] Unit tests for all 29 endpoints (async)
- [ ] Integration tests for critical flows (unlock, payment, upload)
- [ ] Concurrency tests with 50+ simultaneous requests
- [ ] Connection pool stress tests
- [ ] Coverage report: >80%

---

### 4.2 Performance Optimization

**Objective**: Ensure async provides measurable improvement

**Benchmarks to Establish:**

1. **Endpoint Latency**
   - Baseline: Current sync latency (measure before migration)
   - Target: 20-30% reduction with async
   - Measure: p50, p95, p99 latencies

2. **Throughput**
   - Baseline: Requests per second (current sync)
   - Target: 3-5x improvement with async concurrency
   - Measure: Under sustained load (100+ RPS)

3. **Connection Pool**
   - Baseline: Current pool utilization (if monitored)
   - Target: <30% pool utilization at 100 RPS
   - Measure: Active connections, queued requests, timeouts

4. **RAG/Gemini Query Time**
   - Baseline: Current 8-12s per insight
   - Target: No change (external service bound)
   - Optimize: Parallel insight generation (Celery chord already does this)

**Optimization Tasks:**

1. **Query Optimization**
   - Use `explain analyze` on slow queries
   - Add indexes if needed (Phase 1 analysis identified key candidates)
   - Use `selectinload()` to prevent N+1 queries

2. **Caching Optimization**
   - Redis: Extend context cache TTL if safe (current 20 min)
   - Browser: Add Cache-Control headers to read-only endpoints

3. **Connection Pool Tuning**
   - Current: `pool_size=10, max_overflow=5`
   - Test: Adjust based on load tests
   - Target: <20% overflow usage

**Deliverables:**
- [ ] Latency baseline measured and documented
- [ ] Throughput benchmark (at least 3x improvement target)
- [ ] Connection pool tuning completed
- [ ] Performance report generated

---

### 4.3 Feature Flags & Rollout Strategy

**Objective**: Zero-downtime deployment with easy rollback

**Implementation:**

1. **Feature Flag System**
   - Use: Redis or environment variable based flags
   - Flag: `ASYNC_ENDPOINTS_ENABLED=true/false`
   - Purpose: Toggle individual endpoint or all endpoints

2. **Gradual Rollout**
   - Phase 1: Deploy to staging, run full test suite
   - Phase 2: Deploy to 10% of production (canary)
   - Phase 3: Monitor metrics for 1 hour
   - Phase 4: Deploy to 50% of production
   - Phase 5: Monitor for 2 hours
   - Phase 6: Deploy to 100% of production

3. **Rollback Plan**
   - If error rate increases >1%: Rollback to sync
   - If latency increases >50ms: Rollback to sync
   - If pool exhaustion occurs: Rollback to sync

4. **Monitoring Dashboard**
   - Track: Error rate, latency (p50/p95/p99), pool utilization
   - Alert: Immediate notification on anomalies
   - Dashboard: Real-time view of all metrics

**Deliverables:**
- [ ] Feature flag implementation in config.py
- [ ] Canary deployment script
- [ ] Monitoring dashboard setup
- [ ] Rollback procedure documented

---

### 4.4 Documentation & Handoff

**Deliverables:**

1. **Migration Summary Document**
   - What changed (all endpoints async)
   - What stayed same (Celery sync, NullPool)
   - Performance improvements measured
   - Deployment instructions

2. **Code Comments**
   - Add `# async` comment to all async endpoints
   - Add context manager usage examples
   - Document any executor patterns used

3. **Runbooks**
   - Debugging async database issues
   - Handling pool exhaustion
   - Lock timeout retries
   - Rollback procedure

4. **Team Training**
   - Async/await patterns in FastAPI
   - AsyncSession usage
   - Common pitfalls (detached instances, session scope)
   - Debugging with asyncio

---

## Implementation Priority & Timeline

### Week 1: Foundation
- [ ] Phase 1.1-1.4: Database enhancements, soft-delete filters, error handling
- [ ] Estimated: 20-25 hours
- [ ] Risk: LOW (infrastructure, no endpoint changes)

### Week 2: Easy Routes
- [ ] Phase 2.1-2.4: Categories, Users, Credits, Health endpoints
- [ ] Estimated: 10-15 hours
- [ ] Risk: LOW (mostly already async)

### Week 3: Complex Routes & Hardening
- [ ] Phase 2.5-2.8: Insights, Payments, Chats, RAG routers
- [ ] Phase 3.1-3.2: Celery hardening
- [ ] Estimated: 30-40 hours
- [ ] Risk: HIGH (complex transactions, file I/O, external APIs)

### Week 4: Testing & Rollout
- [ ] Phase 4.1-4.4: Testing, optimization, deployment
- [ ] Estimated: 25-30 hours
- [ ] Risk: MEDIUM (requires load testing infrastructure)

**Total Estimated Effort**: 85-110 hours (2.5-3 weeks for 1 developer)

---

## Risk Mitigation

### High-Risk Areas & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Deadlock in credit deduction** | Lock timeout + exponential backoff retry (Phase 3) |
| **Duplicate insight generation** | UPSERT with ON CONFLICT (Phase 1.3) |
| **Connection pool exhaustion** | Monitoring + alerts + pool size tuning (Phase 2, 4.2) |
| **Large file upload hangs** | ThreadPoolExecutor for CPU-bound parsing (Phase 2.7) |
| **Soft delete data leaks** | Auto-filter via SQLAlchemy `@declared_attr` (Phase 1.1) |
| **Async Qdrant/Gemini calls block** | Wrap in ThreadPoolExecutor (Phase 2.8) |
| **Celery-FastAPI race conditions** | Separate NullPool for Celery, AsyncQueuePool for FastAPI (already done) |

---

## Success Criteria

**Deployment is successful when:**
- ✅ All 29 endpoints are async (`async def`)
- ✅ Zero sync `.query()` calls in routers
- ✅ All tests pass (>80% coverage)
- ✅ Latency improved 20-30% (measured)
- ✅ Throughput improved 3-5x (measured)
- ✅ No increase in error rate (<0.5%)
- ✅ Connection pool healthy (<30% utilization at 100 RPS)
- ✅ Celery workers continue using NullPool (verified)
- ✅ Zero deadlocks in production (monitored)
- ✅ Soft-delete queries work correctly (verified)

---

## Post-Migration (Maintenance)

### 1. Monitoring & Alerts
- Connection pool status (daily)
- Async query latency (continuously)
- Deadlock retry rates (weekly)
- Error rate by endpoint (continuously)

### 2. Documentation
- Keep ASYNC_MIGRATION_PLAN.md updated
- Document any custom patterns used
- Add async best practices guide to CLAUDE.md

### 3. Future Enhancements
- Consider async Celery (Celery 5.4+ supports it)
- Migrate vector indexing to async
- Add async streaming for large file uploads
- Implement async WebSocket support for real-time insights

---

## Appendix: File Changes Summary

### New/Modified Files

| File | Change | Priority |
|------|--------|----------|
| `src/database.py` | Add soft-delete filters, transaction wrapper | Phase 1 |
| `src/main.py` | Update startup to test async pool | Phase 1 |
| `src/auth/dependencies.py` | Add `get_async_db()` dependency | Phase 1 |
| `src/error_handlers.py` | Add async exception handlers | Phase 1 |
| `src/users/router.py` | Verify async (no changes) | Phase 2 |
| `src/categories/router.py` | Verify async (no changes) | Phase 2 |
| `src/credits/router.py` | Verify async (no changes) | Phase 2 |
| `src/insights/router.py` | Enhance with lock timeout | Phase 2 |
| `src/payments/router.py` | Verify idempotency | Phase 2 |
| `src/chats/router.py` | Convert to async + ThreadPoolExecutor | Phase 2 |
| `src/chats/service.py` | Convert queries to async | Phase 2 |
| `src/rag/router.py` | Convert to async + ThreadPoolExecutor | Phase 2 |
| `src/rag/service.py` | Convert to async | Phase 2 |
| `src/rag/sync_generation_service.py` | Remove `asyncio.run()` pattern | Phase 3 |
| `src/credits/service.py` | Add sync version for Celery | Phase 3 |
| `tests/` | Comprehensive async test suite | Phase 4 |

---

**Status**: Ready for Review & Approval

**Next Step**: Review this plan, ask clarifying questions, then proceed to Phase 1 implementation.
