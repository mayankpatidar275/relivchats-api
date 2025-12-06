# Neon Dashboard Configuration for Production

This guide shows you exactly how to configure your Neon project for optimal performance.

## Quick Start

Your code changes are ready. Now configure Neon to prevent Scale-to-Zero suspension.

---

## Configuration Options

### Option A: Disable Scale-to-Zero (RECOMMENDED)

**Cost**: +$0.40/month (always-on compute)
**Performance**: Guaranteed no cold starts
**Best For**: Production with consistent traffic

#### Steps:
1. Go to [Neon Console](https://console.neon.tech)
2. Select your project
3. Click **Compute**
4. Find your primary endpoint
5. Toggle **"Scale to Zero"** to **OFF**

```
Scale to Zero: OFF ✓
Auto-suspension: DISABLED
Compute will always be available
```

**Result**: No more 9-10 second cold starts. Queries stay at 100-300ms.

---

### Option B: Keep Scale-to-Zero Enabled (FREE)

**Cost**: $0 (free tier)
**Performance**: Keepalive task maintains 100-300ms response
**Best For**: Budget-conscious or low-traffic apps

#### How It Works:
Our keepalive task runs every 4 minutes in production, keeping compute active.

#### What We Did:
```python
# In src/main.py
async def _neon_keepalive():
    while True:
        await asyncio.sleep(240)  # Every 4 minutes
        await session.execute(text("SELECT 1"))
```

**Result**: Same performance as Option A, but free.

#### Setup:
1. Code is already deployed (see `src/main.py`)
2. Set `ENVIRONMENT=production` in your deployment
3. That's it! Keepalive runs automatically

---

## Auto-Scaling Configuration

Ensure auto-scaling is properly configured for free tier:

1. Go to [Neon Console](https://console.neon.tech)
2. Select your project
3. Click **Compute**
4. Check **"Auto-scaling"** settings:
   - **Min**: 0.25 CU (minimum allowed)
   - **Max**: 2 CU (free tier maximum)

```
Auto-scaling: ENABLED ✓
Min: 0.25 CU
Max: 2 CU
```

This allows Neon to scale within free tier limits based on load.

---

## Verification Checklist

After configuration, verify everything is working:

### 1. Check Neon Dashboard
- [ ] Go to console.neon.tech
- [ ] Verify compute is running (green status)
- [ ] If using Option A: "Scale to Zero" is OFF
- [ ] If using Option B: "Scale to Zero" is ON (keepalive will manage it)
- [ ] Auto-scaling: Min 0.25, Max 2 CU

### 2. Check Application Logs
```bash
# Look for this message on startup
docker logs your-app-container | grep "Neon keepalive"

# Expected output (if using Option B):
# ✓ Neon keepalive task started (prevents Scale-to-Zero suspension)
# DEBUG: Neon keepalive: connection refreshed  [every 4 minutes]
```

### 3. Test Performance
```bash
# Wait 5+ minutes (let compute suspend if Scale-to-Zero is ON)
sleep 300

# Test response time
time curl https://your-api.com/api/categories

# Expected: < 300ms
# Before: 9,000-11,000ms (cold start)
```

### 4. Check Connection Pool
```bash
curl https://your-api.com/health/db-pool

# Expected response:
{
  "pool_type": "QueuePool",
  "pooling_enabled": true,
  "pool_size": 15,
  "checked_out": 2,
  "overflow": 0,
  "available": 13,
  "status": "healthy"
}
```

---

## Connection String Format

Depending on your configuration:

### Standard Connection (No Pooler)
```
postgresql://user:password@ep-xxxx.neon.tech/dbname
```
- Used by our SQLAlchemy setup
- Application-level pooling handles the connection pool

### With Neon PgBouncer (Optional)
```
postgresql://user:password@ep-xxxx-pooler.neon.tech/dbname
```
- If you want to use Neon's built-in pooler instead of SQLAlchemy
- Our code uses SQLAlchemy pooling (recommended for async Python)

**Current setup uses the standard connection with SQLAlchemy pooling** ✓

---

## Monitoring Dashboard

Create a monitoring plan:

### Daily Checks
- [ ] Application health: `curl /health` returns `{"status": "healthy"}`
- [ ] DB pool health: `curl /health/db-pool` shows `status: healthy`
- [ ] Logs for errors: No critical errors in last 24 hours

### Weekly Checks
- [ ] Query latency: Sample `/api/categories` - should be 50-300ms
- [ ] Neon compute uptime: 99%+ (check Neon console)
- [ ] Redis memory: < 50% used

### Monthly Checks
- [ ] Review Neon bill (should be $0 for free tier)
- [ ] Check if auto-scaling is working (CPU metrics in Neon console)
- [ ] Plan for scale-up if approaching limits

---

## Troubleshooting

### Symptom: Still seeing 9-10 second response times

**Check 1: Environment Variable**
```bash
# Verify ENVIRONMENT is set to 'production'
echo $ENVIRONMENT
# Output: production
```

**Check 2: Neon Configuration**
```
Go to Neon Console:
- If Scale-to-Zero is OFF: ✓ Good, should not have cold starts
- If Scale-to-Zero is ON: Keepalive task must be running
```

**Check 3: Keepalive Task Running**
```bash
# Check application logs
docker logs your-app | grep "keepalive"

# Should see:
# ✓ Neon keepalive task started (prevents Scale-to-Zero suspension)
# DEBUG: Neon keepalive: connection refreshed
```

**Check 4: Database Connection**
```bash
# Test connection pool
curl http://localhost:8000/health/db-pool

# status should be "healthy"
```

### Symptom: Neon compute keeps suspending

**If using Option A (Scale-to-Zero OFF)**:
1. Go to Neon Console
2. Verify the toggle is actually OFF
3. Wait 1-2 minutes for change to take effect
4. Test again

**If using Option B (Scale-to-Zero ON)**:
1. Verify `ENVIRONMENT=production` is set
2. Check logs for keepalive startup message
3. Verify code was deployed (includes `src/main.py` changes)

### Symptom: High database query times

**Check these in order**:
1. Is compute running? (Check Neon console - should be green)
2. Is compute sized correctly? (Should be at least 0.5 CU)
3. Are there any slow queries? (Check Neon query analytics)
4. Is the pool exhausted? (Check `/health/db-pool` - should have available connections)

---

## Cost Breakdown

### Free Tier Costs
```
Base Features:
- Compute (0.25-2 CU):    $0
- Storage (3GB):          $0
- Branches (2):           $0
- Backups (7 days):       $0
- Scale-to-Zero:          $0 (feature is free)

Your Additions:
- Keepalive queries (~1/min): <$0.01/month

Total: $0 to $0.01/month
```

### Upgrade Path (If Needed)
If you need better performance:

| Plan | Cost | Compute Range | Key Feature |
|------|------|---------------|-------------|
| Free | $0 | 0.25-2 CU | Development |
| Growth | $15/month | 0.25-4 CU | Always-on + read replicas |
| Pro | $25/month | 0.25-8 CU | Priority support |

---

## Next Steps

### Immediate (Today)
- [ ] Configure Neon dashboard (Option A or B)
- [ ] Verify logs show "keepalive task started"
- [ ] Test `/api/categories` response time

### Short-term (This Week)
- [ ] Monitor database performance for 3-5 days
- [ ] Add database indexes if needed (see `NEON_OPTIMIZATION_GUIDE.md`)
- [ ] Review Neon metrics in dashboard

### Medium-term (This Month)
- [ ] Monitor query latency trends
- [ ] Decide: Is Option A (paid) or Option B (keepalive) better for your traffic?
- [ ] Plan for scale-up if approaching limits

---

## Neon Console Navigation

### Find Your Project
1. Go to https://console.neon.tech
2. Click on your project name
3. You should see: **Compute**, **Databases**, **Branches**, **Settings**

### Access Compute Settings
1. Click **Compute** in the left menu
2. Click on your endpoint name (usually "main")
3. You'll see:
   - Compute size (0.25, 0.5, 1, 2 CU for free tier)
   - Auto-scaling toggle
   - Scale-to-Zero toggle
   - Connection info

### View Query Analytics
1. Click **Monitoring** (if available)
2. View slow queries
3. Check compute CPU/memory usage

---

## Support Resources

### Official Neon Documentation
- [Connection Pooling](https://neon.com/docs/manage/endpoints)
- [Performance Tuning](https://neon.com/docs/guides/performance-tuning)
- [Scale-to-Zero Feature](https://neon.com/docs/introduction/scale-to-zero)
- [Support](https://neon.com/docs/introduction/support)

### Our Guides
- `PERFORMANCE_OPTIMIZATION_SUMMARY.md` - Overview of changes
- `NEON_OPTIMIZATION_GUIDE.md` - Deep technical details
- `NEON_DASHBOARD_SETUP.md` - This file

---

## Common Questions

**Q: Will Scale-to-Zero cause issues with our keepalive task?**
A: No! Our keepalive task (every 4 min) runs faster than Scale-to-Zero suspension (5 min idle). It prevents suspension without needing dashboard changes.

**Q: Can we use Neon's PgBouncer instead of SQLAlchemy pooling?**
A: Yes, but our current setup (SQLAlchemy pooling) is better for async Python applications like FastAPI.

**Q: What if we get heavy traffic?**
A: Auto-scaling will scale compute up to 2 CU (free tier limit). If that's not enough, upgrade to Growth plan ($15/mo).

**Q: Does the keepalive query cost anything?**
A: Negligible (<$0.01/month). It's ~360 light queries per day.

**Q: Can we disable keepalive in development?**
A: Yes, it only runs when `ENVIRONMENT=production`.

---

## Final Checklist

Before considering the optimization complete:

- [ ] Code deployed with all 4 files updated
- [ ] `ENVIRONMENT=production` set in production
- [ ] Neon dashboard configured (Option A or B chosen)
- [ ] Logs show "✓ Neon keepalive task started" (if Option B)
- [ ] `/health/db-pool` returns healthy status
- [ ] `/api/categories` responds in < 300ms
- [ ] No more 9-10 second cold starts

**You're production-ready!** 🚀

