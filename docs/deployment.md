# RelivChats API - Production Deployment Guide

**Status**: Production-ready after completing critical fixes ✅
**Last Updated**: January 2026

---

## Prerequisites

Before deploying, ensure you have completed the **5 critical fixes**:

- [x] ✅ Rate limiting enabled (slowapi configured)
- [x] ✅ Sentry error monitoring enabled
- [x] ✅ CORS configured with frontend whitelist
- [x] ✅ `.env.example` created for deployment teams
- [ ] ⚠️ Payment webhook tests written (optional but recommended)

---

## Quick Start (Production Deployment)

### 1. Set Up Infrastructure

**Required Services:**

- PostgreSQL 15+ (Recommend: [Neon](https://neon.tech) - serverless, auto-scaling)
- Redis 7+ (Recommend: [Redis Cloud](https://redis.com/try-free/) - free tier available)
- Qdrant vector database (Recommend: [Qdrant Cloud](https://qdrant.tech/cloud/) - 1GB free)

**Server Requirements:**

- 2 vCPU, 4GB RAM minimum (for API + Celery worker)
- 20GB disk space (logs, uploads)
- Ubuntu 22.04 LTS or Docker environment

---

### 2. Deploy Backend API

#### Option A: Docker (Recommended)

```bash
# Clone repository
git clone <your-repo-url>
cd relivchats-api

# Copy environment template
cp .env.example .env

# Edit .env with production values (see below)
nano .env

# Build Docker image
docker build -t relivchats-api:latest .

# Run API container
docker run -d \
  --name relivchats-api \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  relivchats-api:latest

# Run Celery worker container
docker run -d \
  --name relivchats-celery \
  --env-file .env \
  -e CELERY_WORKER=true \
  --restart unless-stopped \
  relivchats-api:latest \
  celery -A src.celery_app worker --loglevel=info --concurrency=1
```

#### Option B: Traditional (systemd)

```bash
# Install dependencies
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql-client redis-tools

# Clone and setup
git clone <your-repo-url>
cd relivchats-api
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt

# Configure environment
cp .env.example .env
nano .env  # Fill in production values

# Run database migrations
alembic upgrade head

# Create systemd service for API
sudo nano /etc/systemd/system/relivchats-api.service
```

**API Service File:**

```ini
[Unit]
Description=RelivChats API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/relivchats-api
Environment="PATH=/opt/relivchats-api/venv/bin"
ExecStart=/opt/relivchats-api/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Celery Worker Service File:**

```ini
[Unit]
Description=RelivChats Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/relivchats-api
Environment="PATH=/opt/relivchats-api/venv/bin"
Environment="CELERY_WORKER=true"
ExecStart=/opt/relivchats-api/venv/bin/celery -A src.celery_app worker --loglevel=info --concurrency=1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start services:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable relivchats-api relivchats-celery
sudo systemctl start relivchats-api relivchats-celery
sudo systemctl status relivchats-api relivchats-celery
```

---

### 3. Configure Environment Variables

**CRITICAL - Production .env Setup:**

```bash
# Copy template
cp .env.example .env

# Edit with production values
nano .env
```

**Required Changes for Production:**

1. **Set Environment:**

   ```
   ENVIRONMENT=production
   LOG_FORMAT=json
   LOG_LEVEL=INFO
   ```

2. **Database URL** (example for Neon):

   ```
   DATABASE_URL=postgresql://user:STRONG_PASSWORD@ep-xyz.us-east-1.aws.neon.tech/relivchats?sslmode=require
   ```

3. **CORS Origins** (your frontend domains):

   ```
   CORS_ORIGINS=["https://relivchats.com","https://www.relivchats.com","https://app.relivchats.com","https://relivchats.mkpatidar.in","https://www.relivchats.mkpatidar.in","https://app.relivchats.in"]
   ```

4. **Payment Keys** (LIVE, not TEST):

   ```
   RAZORPAY_KEY_ID=rzp_live_XXXXX
   RAZORPAY_KEY_SECRET=XXXXX
   STRIPE_SECRET_KEY=sk_live_XXXXX
   ```

5. **Sentry DSN** (create project at sentry.io):

   ```
   SENTRY_DSN=https://public_key@o123456.ingest.sentry.io/789012
   ```

6. **All API Keys** (rotate from development keys):
   - Generate fresh Gemini API key
   - Create new Qdrant cluster (production)
   - Rotate Clerk secret key
   - Generate new payment webhook secrets

---

### 4. Set Up Reverse Proxy (Nginx)

```bash
sudo apt install nginx certbot python3-certbot-nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/relivchats-api
```

**Nginx Configuration:**

```nginx
server {
    listen 80;
    server_name api.relivchats.com;  # Your API domain

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.relivchats.com;

    # SSL certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/api.relivchats.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.relivchats.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # File upload size limit
    client_max_body_size 25M;
}
```

**Enable site and get SSL:**

```bash
sudo ln -s /etc/nginx/sites-available/relivchats-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get Let's Encrypt SSL certificate
sudo certbot --nginx -d api.relivchats.com
```

---

### 5. Database Migration & Seeding

```bash
# Run migrations
alembic upgrade head

# Seed initial data (categories, insight types, packages)
# Option 1: Using psql (if you have .sql files)
psql $DATABASE_URL < seed/analysis_category.sql
psql $DATABASE_URL < seed/insight_types.sql
psql $DATABASE_URL < seed/category_insight_types.sql
psql $DATABASE_URL < seed/credit_packages.sql

# Option 2: Check if data already exists
# Connect to DB and verify:
psql $DATABASE_URL
SELECT COUNT(*) FROM analysis_categories;
SELECT COUNT(*) FROM insight_types;
SELECT COUNT(*) FROM credit_packages;
```

**Expected Seed Data:**

- **6 analysis categories**: Romantic, Friendship, Family, Professional, Group Chat, General
- **12 insight types**: Communication Basics, Conflict Resolution, Emotional Intelligence, etc.
- **4-5 credit packages**: Starter, Basic, Pro, Ultimate

---

### 6. Configure Payment Webhooks

**Razorpay Webhook Setup:**

1. Go to [Razorpay Dashboard > Settings > Webhooks](https://dashboard.razorpay.com/app/webhooks)
2. Create webhook:
   - URL: `https://api.relivchats.com/api/payments/webhook/razorpay`
   - Events: `payment.captured`, `payment.failed`, `refund.created`
   - Secret: Generate and save to `RAZORPAY_WEBHOOK_SECRET` in `.env`

**Stripe Webhook Setup:**

1. Go to [Stripe Dashboard > Developers > Webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint:
   - URL: `https://api.relivchats.com/api/payments/webhook/stripe`
   - Events: `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`
   - Secret: Save to `STRIPE_WEBHOOK_SECRET` in `.env`

**Test Webhooks:**

```bash
# Razorpay
curl -X POST https://api.relivchats.com/api/payments/webhook/razorpay \
  -H "Content-Type: application/json" \
  -H "x-razorpay-signature: test" \
  -d '{"event":"payment.captured"}'

# Stripe
stripe listen --forward-to https://api.relivchats.com/api/payments/webhook/stripe
```

---

### 7. Monitoring Setup

**Sentry (Error Tracking):**

1. Create account at [sentry.io](https://sentry.io)
2. Create new project (Python/FastAPI)
3. Copy DSN to `.env`:
   ```
   SENTRY_DSN=https://...@sentry.io/...
   ```
4. Verify in Dashboard > Performance > Transactions

**Health Checks:**

```bash
# API health
curl https://api.relivchats.com/health

# Database pool status
curl https://api.relivchats.com/health/db-pool

# Sentry test event
curl -X GET https://api.relivchats.com/sentry-debug  # If you add this endpoint
```

**Log Monitoring:**

```bash
# View live logs
sudo journalctl -u relivchats-api -f
sudo journalctl -u relivchats-celery -f

# Check error logs
sudo journalctl -u relivchats-api --priority=err --since "1 hour ago"
```

**Set Up Uptime Monitoring:**

- [UptimeRobot](https://uptimerobot.com/) (free): Monitor `/health` endpoint
- [Pingdom](https://www.pingdom.com/) (paid): Advanced monitoring
- Alert on: API down, response time >2s, 5xx errors >1%

---

### 8. Security Checklist

- [x] ✅ HTTPS enforced (redirect HTTP → HTTPS)
- [x] ✅ CORS whitelist configured (no `*` wildcard)
- [x] ✅ Rate limiting enabled (slowapi)
- [x] ✅ Secrets not in git (`.env` in `.gitignore`)
- [x] ✅ Webhook signature verification (Razorpay/Stripe)
- [x] ✅ SQL injection prevention (SQLAlchemy ORM)
- [x] ✅ Input validation (Pydantic schemas)
- [ ] ⚠️ Firewall configured (allow only 80, 443, 22)
- [ ] ⚠️ SSH key-only authentication (disable password login)
- [ ] ⚠️ Database backups enabled (daily)
- [ ] ⚠️ Secrets manager (AWS Secrets Manager, HashiCorp Vault)

**Firewall Setup (Ubuntu):**

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
sudo ufw status
```

---

### 9. Performance Optimization

**Database Indexing:**

```sql
-- Already created by Alembic, verify:
SHOW INDEX FROM users;
SHOW INDEX FROM chats;
SHOW INDEX FROM insights;

-- Check slow queries (if needed):
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

**Connection Pooling:**

- API uses `QueuePool` (pool_size=15, max_overflow=5)
- Celery uses `NullPool` (fresh connection per task)
- Verify: `GET /health/db-pool`

**Caching:**

- Redis caching for rate limiting
- RAG context caching (TTL: 1 hour)
- React Query caching on frontend

**CDN (Optional):**

- CloudFlare: Free tier for API caching
- AWS CloudFront: For static assets

---

### 10. Backup Strategy

**Database Backups (Neon):**

```bash
# Automated (Neon handles this)
# Manual backup:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Upload Directory:**

```bash
# Backup user-uploaded chats (if not ephemeral)
tar -czf uploads_backup.tar.gz uploads/
aws s3 cp uploads_backup.tar.gz s3://your-bucket/backups/
```

**Redis Backup:**

```bash
# Redis Cloud handles backups automatically
# Manual: Download RDB snapshot from dashboard
```

---

## Scaling Guide

### When to Scale?

**Metrics to Watch:**

- API response time > 2s (95th percentile)
- Database connections > 80% of pool
- Celery queue length > 50 tasks
- Error rate > 1% (Sentry)

### Horizontal Scaling (API)

```bash
# Add more API workers (Docker)
docker run -d --name relivchats-api-2 --env-file .env -p 8001:8000 relivchats-api:latest
docker run -d --name relivchats-api-3 --env-file .env -p 8002:8000 relivchats-api:latest

# Load balancer (Nginx)
upstream api_backend {
    least_conn;  # Load balancing method
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://api_backend;
    }
}
```

### Vertical Scaling (Celery)

```bash
# Increase worker concurrency
celery -A src.celery_app worker --concurrency=4  # Instead of 1

# Add more worker processes
docker run -d --name celery-worker-2 ... relivchats-api:latest celery ...
docker run -d --name celery-worker-3 ... relivchats-api:latest celery ...
```

### Database Scaling (Neon)

1. Upgrade plan (Neon auto-scales compute)
2. Enable read replicas
3. Add connection pooling (PgBouncer)

---

## Troubleshooting

### Common Issues

**1. "Rate limit exceeded" on health checks**

```python
# Fix: Exempt health check from rate limiting
# Already done in src/rate_limit.py:exempt_from_rate_limit()
```

**2. Celery tasks not running**

```bash
# Check if CELERY_WORKER=true is set
env | grep CELERY_WORKER

# Check Redis connection
redis-cli -u $REDIS_URL ping

# Check worker logs
sudo journalctl -u relivchats-celery -n 100
```

**3. Database connection errors**

```bash
# Check connection pool
curl https://api.relivchats.com/health/db-pool

# Verify DATABASE_URL
echo $DATABASE_URL  # Should NOT print in production (security risk)

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

**4. Insight generation hangs**

```bash
# Check Gemini API quota
# Check Qdrant health
curl $QDRANT_URL/health

# Check task timeout settings
grep INSIGHT_GENERATION_TIMEOUT .env  # Should be 600 (10 min)
```

**5. Payment webhook not working**

```bash
# Check webhook logs
grep "webhook" /var/log/relivchats-api/app.log

# Verify webhook signatures
# Check Razorpay/Stripe dashboard > Webhooks > Recent deliveries
```

---

## Rollback Plan

**If deployment fails:**

```bash
# Docker rollback
docker stop relivchats-api relivchats-celery
docker run -d --name relivchats-api relivchats-api:previous-version

# Database rollback (downgrade migration)
alembic downgrade -1

# Restore from backup
psql $DATABASE_URL < backup_20260103.sql
```

---

## Post-Deployment Checklist

- [ ] ✅ API responding at https://api.yourdomain.com/health
- [ ] ✅ Sentry receiving events
- [ ] ✅ Payment webhooks configured (test with $1 payment)
- [ ] ✅ Celery worker processing tasks (upload chat, unlock insights)
- [ ] ✅ CORS working (frontend can call API)
- [ ] ✅ Rate limiting working (test with >10 requests/minute)
- [ ] ✅ SSL certificate valid (check with ssllabs.com)
- [ ] ✅ Database backups enabled
- [ ] ✅ Monitoring alerts set up (Sentry, UptimeRobot)
- [ ] ✅ DNS records configured (A/CNAME for api.yourdomain.com)

---

## Support

**Documentation:**

- API Docs: `https://api.yourdomain.com/docs`
- CLAUDE.md: Architecture guide

**Logs:**

- Application: `/var/log/relivchats-api/app.log`
- Errors: `/var/log/relivchats-api/error.log`
- Business events: `/var/log/relivchats-api/business.log`

**Monitoring:**

- Sentry: https://sentry.io/organizations/your-org/projects/relivchats-api
- Flower (Celery): `http://localhost:5555` (if enabled)

---

**🚀 You're ready for production!** Good luck with your launch.
