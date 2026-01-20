# Production Server Debugging Commands

## SSH into your server first
```bash
ssh user@your-server-ip
```

---

## 1. Check Current Environment Variables

```bash
# See all environment variables in the running Docker container
docker exec relivchats-api env | grep -E "ENVIRONMENT|SENTRY_DSN|GEMINI_API_KEY"

# Check if ENVIRONMENT is set to production
docker exec relivchats-api printenv ENVIRONMENT

# Check if Sentry DSN is set
docker exec relivchats-api printenv SENTRY_DSN

# See the full .env file (if mounted)
docker exec relivchats-api cat .env
```

**Expected output (production)**:
```
ENVIRONMENT=production
SENTRY_DSN=https://d63241f5c0483af58b04c32703feff3b@...
```

---

## 2. Analyze Gemini API Usage in Logs

```bash
# Count how many times Gemini API was called today
docker logs relivchats-api 2>&1 | grep "generate_embedding" | wc -l

# See all 429 errors (quota exceeded)
docker logs relivchats-api 2>&1 | grep "429" | tail -50

# Find which user/request triggered embeddings
docker logs relivchats-api 2>&1 | grep "unlock_chat_insights" | tail -20

# See full error context for Gemini failures
docker logs relivchats-api 2>&1 | grep -A 10 "RESOURCE_EXHAUSTED"

# Check timestamps of Gemini API calls (see if it's a loop)
docker logs relivchats-api --since 1h 2>&1 | grep "generate_embedding" | awk '{print $1, $2}'
```

---

## 3. Find Who Is Triggering the Requests

```bash
# Find all insight unlock requests with user IDs
docker logs relivchats-api 2>&1 | grep "unlock_chat_insights" | grep -o "user_id=[^,]*"

# Find all insight unlock requests with request IDs
docker logs relivchats-api 2>&1 | grep "unlock_chat_insights" | grep -o "request_id=[^,]*"

# See IP addresses making requests
docker logs relivchats-api 2>&1 | grep "POST /api/insights/unlock" | awk '{print $1}' | sort | uniq -c

# Find the specific chat being indexed
docker logs relivchats-api 2>&1 | grep "create_chat_chunks" | grep -o "chat_id=[^,]*"
```

---

## 4. Check Gemini API Rate Limits

**Google AI Studio Dashboard:**
1. Go to https://aistudio.google.com/app/apikey
2. Click on your API key
3. Check "Usage" tab to see:
   - Requests per minute (RPM): Usually 60/min for free tier
   - Requests per day (RPD): Usually 1,500/day for free tier

**Or check via CLI:**
```bash
# See how many embedding calls were made in last hour
docker logs relivchats-api --since 1h 2>&1 | grep "generate_embedding" | wc -l
```

**If you see 300+ calls in short time** → That's your problem!

---

## 5. Monitor Real-Time API Calls

```bash
# Watch live logs (see requests in real-time)
docker logs -f relivchats-api

# Filter for Gemini API calls only
docker logs -f relivchats-api 2>&1 | grep --line-buffered "generate_embedding"

# Filter for errors only
docker logs -f relivchats-api 2>&1 | grep --line-buffered "ERROR"
```

**Press Ctrl+C to stop**

---

## 6. Check Database for Recent Activity

```bash
# Connect to PostgreSQL inside Docker
docker exec -it relivchats-api psql $DATABASE_URL

# Or if psql not in container, connect from host
psql "postgresql://neondb_owner:npg_Ssa2wryPA5qf@ep-restless-water-a1y5ofd8-pooler.ap-southeast-1.aws.neon.tech/neondb"
```

**SQL queries to run:**
```sql
-- Find recent insight unlocks
SELECT id, user_id, chat_id, category, unlocked_at
FROM chat_insights
WHERE unlocked_at > NOW() - INTERVAL '1 day'
ORDER BY unlocked_at DESC
LIMIT 20;

-- Find large chats (likely causing many embeddings)
SELECT id, user_id, created_at,
       (SELECT COUNT(*) FROM messages WHERE chat_id = chats.id) as message_count
FROM chats
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY message_count DESC;

-- Check if a chat is stuck in "indexing" status
SELECT id, user_id, status, created_at
FROM chats
WHERE status = 'indexing'
ORDER BY created_at DESC;
```

---

## 7. Check Redis for Rate Limiting

```bash
# Connect to Redis
docker exec -it relivchats-redis redis-cli

# Check if rate limiting is working
KEYS slowapi:*

# See rate limit for specific user (replace with actual user_id)
GET slowapi:user:usr_abc123:/api/insights/unlock:10/hour

# See all rate limit keys
SCAN 0 MATCH slowapi:* COUNT 100
```

---

## 8. Fix Production Environment Issues

### Issue 1: Set ENVIRONMENT=production

```bash
# Edit .env file on the server
nano /path/to/your/.env

# Change this line:
# ENVIRONMENT=development
# To:
ENVIRONMENT=production

# Save and exit (Ctrl+X, Y, Enter)
```

### Issue 2: Add Sentry DSN

```bash
# Add this line to .env:
SENTRY_DSN=https://d63241f5c0483af58b04c32703feff3b@o4508500998094848.ingest.us.sentry.io/4510647585210368

# Also add sampling rate:
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Issue 3: Restart Docker Container

```bash
# Restart the API container to pick up new env vars
docker restart relivchats-api

# Or if using docker-compose:
docker-compose restart api

# Wait 10 seconds, then verify:
docker logs relivchats-api 2>&1 | grep "environment"
# Should show: "environment": "production"

docker logs relivchats-api 2>&1 | grep "Sentry"
# Should show: ✓ Sentry initialized
```

---

## 9. Stop the Gemini API Spam (Emergency)

**If embeddings are being called in a loop, stop it immediately:**

```bash
# Option 1: Temporarily disable embedding generation
docker exec relivchats-api bash -c "echo 'GEMINI_API_KEY=disabled' >> /tmp/override.env"

# Option 2: Stop the specific Celery worker (if running)
docker exec relivchats-celery celery -A src.celery_app control shutdown

# Option 3: Restart the API to clear any stuck tasks
docker restart relivchats-api
```

---

## 10. Check System Resources

```bash
# See CPU and memory usage of containers
docker stats --no-stream

# Check disk space (Qdrant can fill up)
df -h

# See running processes
docker ps -a
```

---

## 11. Useful Log Filtering Patterns

```bash
# All errors today
docker logs relivchats-api 2>&1 | grep "ERROR" | grep "$(date +%Y-%m-%d)"

# All requests to /api/insights/unlock
docker logs relivchats-api 2>&1 | grep "POST /api/insights/unlock"

# See response times (slow requests)
docker logs relivchats-api 2>&1 | grep "took" | grep -E "[5-9]\.[0-9]+s"

# Find failed requests (status code 5xx)
docker logs relivchats-api 2>&1 | grep -E "HTTP/1.1\" 5[0-9]{2}"
```

---

## 12. Export Logs for Analysis

```bash
# Save last 1000 lines to file
docker logs relivchats-api --tail 1000 > /tmp/api_logs.txt

# Save logs from last 24 hours
docker logs relivchats-api --since 24h > /tmp/api_logs_24h.txt

# Download to your local machine (run from local terminal)
scp user@server-ip:/tmp/api_logs.txt ~/Desktop/
```

---

## Quick Troubleshooting Checklist

Run these commands in order:

```bash
# 1. Check environment
docker exec relivchats-api printenv ENVIRONMENT

# 2. Check Sentry
docker exec relivchats-api printenv SENTRY_DSN

# 3. Count Gemini API calls in last hour
docker logs relivchats-api --since 1h 2>&1 | grep "generate_embedding" | wc -l

# 4. See who triggered embeddings
docker logs relivchats-api --since 1h 2>&1 | grep "unlock_chat_insights" | tail -5

# 5. Check for errors
docker logs relivchats-api --tail 50 2>&1 | grep "ERROR"
```

---

## Summary of Issues from Your Logs

**Issue 1**: `"environment": "development"` → Should be `production`
**Issue 2**: No "Sentry initialized" log → Missing `SENTRY_DSN`
**Issue 3**: Someone tried `GET /.env` → Bot attack (blocked ✓)
**Issue 4**: Gemini API 429 errors → Quota exhausted from embedding generation

**Fix Priority:**
1. ✅ Fix environment and Sentry (10 minutes)
2. ⚠️ Debug Gemini API usage (find the culprit)
3. 🔧 Implement embedding rate limiting (prevent future quota issues)
