# API Reference

**Base URL**: `http://localhost:8000` (dev) | `https://api.relivchats.com` (prod)

**Authentication**: Clerk JWT via `Authorization: Bearer <token>` header

**Interactive Docs**: `/docs` (Swagger UI)

---

## Authentication

All endpoints (except `/categories` and `/credits/packages`) require authentication.

**Header**:
```
Authorization: Bearer <clerk_jwt_token>
```

---

## Users

### Store User
```http
POST /api/users/store
```
Creates user record on first login. Grants 50 signup bonus coins.

**Response**:
```json
{
  "user_id": "clerk_abc123",
  "credit_balance": 50,
  "created_at": "2026-01-20T10:00:00Z"
}
```

### Delete Account
```http
DELETE /api/users/delete-account
```
GDPR-compliant account deletion (soft delete with 30-day grace period).

---

## Chats

### Upload Chat
```http
POST /api/chats/upload
Content-Type: multipart/form-data

file: chat.txt
category_id: <uuid> (optional)
```

**Response**:
```json
{
  "id": "uuid",
  "title": "Chat with Alice",
  "chat_metadata": {
    "total_messages": 657,
    "total_words": 3145,
    "busiest_hour": 20,
    "top_emojis": ["😂", "❤️"],
    "user_stats": {...}
  },
  "vector_status": "pending"
}
```

### List Chats
```http
GET /api/chats
```

### Get Chat Details
```http
GET /api/chats/{chat_id}
```

### Delete Chat
```http
DELETE /api/chats/{chat_id}
```
Soft delete (30-day grace period).

---

## Categories

### List Categories
```http
GET /api/categories
```

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "romantic",
    "display_name": "Romantic Relationship",
    "description": "Analyze romantic conversations",
    "icon": "❤️",
    "credit_cost": 400
  }
]
```

### Get Category Insights
```http
GET /api/categories/{category_id}/insights
```

---

## Credits

### Get Balance
```http
GET /api/credits/balance
```

**Response**:
```json
{
  "balance": 450,
  "user_id": "clerk_abc123"
}
```

### List Packages
```http
GET /api/credits/packages
```

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "Starter",
    "coins": 400,
    "price_inr": 399.00,
    "price_usd": 4.99,
    "description": "Perfect for trying your first analysis",
    "is_popular": false
  },
  {
    "id": "uuid",
    "name": "Popular",
    "coins": 850,
    "price_inr": 799.00,
    "price_usd": 9.99,
    "description": "Best value - Unlock 2 analyses",
    "is_popular": true
  }
]
```

### Transaction History
```http
GET /api/credits/transactions
```

---

## Insights

### Unlock Insights
```http
POST /api/insights/unlock
Content-Type: application/json

{
  "chat_id": "uuid",
  "category_id": "uuid"
}
```

**Response**:
```json
{
  "success": true,
  "job_id": "abc-123",
  "coins_deducted": 400,
  "remaining_balance": 50,
  "total_insights": 6,
  "estimated_seconds": 480,
  "poll_url": "/api/insights/jobs/abc-123/status"
}
```

**Error Responses**:
- `400` - Already unlocked or indexing failed
- `402` - Insufficient credits
- `404` - Chat not found
- `409` - Currently indexing

### Poll Job Status
```http
GET /api/insights/jobs/{job_id}/status
```

**Response (Generating)**:
```json
{
  "job_id": "abc-123",
  "status": "running",
  "progress_percentage": 50.0,
  "total_insights": 6,
  "completed_insights": 3,
  "failed_insights": 0,
  "started_at": "2026-01-20T10:00:00Z",
  "estimated_completion_at": "2026-01-20T10:08:00Z",
  "insights": [
    {
      "id": "uuid",
      "insight_type_name": "communication_basics",
      "display_title": "Communication Basics",
      "status": "completed",
      "content": {...}
    }
  ]
}
```

**Status Values**: `queued`, `running`, `completed`, `failed`, `partial_failure`

### Get Chat Insights
```http
GET /api/insights/chats/{chat_id}
```

**Response**:
```json
{
  "chat_id": "uuid",
  "category": {
    "id": "uuid",
    "name": "romantic",
    "display_name": "Romantic Relationship"
  },
  "generation_status": "completed",
  "unlocked_at": "2026-01-20T10:00:00Z",
  "total_requested": 6,
  "total_completed": 6,
  "total_failed": 0,
  "insights": [
    {
      "id": "uuid",
      "insight_type_id": "uuid",
      "insight_type_name": "communication_basics",
      "display_title": "Communication Basics",
      "description": "Who initiates, response patterns, balance",
      "icon": "💬",
      "content": {
        "who_initiates_more": "user",
        "initiation_ratio": {
          "user": 55,
          "partner": 45
        },
        "response_patterns": {...},
        "communication_balance_score": 8.5,
        "key_strengths": [...],
        "areas_for_growth": [...]
      },
      "status": "completed",
      "generation_metadata": {
        "tokens_used": 2500,
        "generation_time_ms": 3200,
        "rag_chunks_used": 15,
        "model_used": "gemini-2.0-flash-exp"
      },
      "created_at": "2026-01-20T10:00:00Z",
      "updated_at": "2026-01-20T10:02:00Z"
    }
  ]
}
```

---

## RAG (Internal/Testing)

### Query Chat
```http
POST /api/rag/query
Content-Type: application/json

{
  "chat_id": "uuid",
  "query": "What do we talk about most?",
  "max_chunks": 10
}
```

**Response**:
```json
{
  "answer": "Based on your conversations, you primarily discuss...",
  "chunks_used": 8,
  "tokens_used": 1500
}
```

---

## Health & Monitoring

### Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production",
  "timestamp": "2026-01-20T10:00:00Z"
}
```

### Database Pool Status
```http
GET /health/db-pool
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Insufficient credits",
  "error_code": "INSUFFICIENT_CREDITS",
  "support_email": "support@relivchats.com"
}
```

**Common Error Codes**:
- `400` - Bad request
- `401` - Unauthorized (invalid/missing token)
- `402` - Payment required (insufficient credits)
- `403` - Forbidden (access denied)
- `404` - Not found
- `409` - Conflict (already exists/in progress)
- `422` - Validation error
- `429` - Rate limit exceeded
- `500` - Internal server error

---

## Rate Limits

- **Upload**: 5 per minute, 20 per hour
- **Unlock**: 3 per minute, 10 per hour
- **Read operations**: 100 per minute

**Headers**:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1640000000
```

---

## Webhooks

### Razorpay Webhook
```http
POST /api/payments/razorpay/webhook
X-Razorpay-Signature: <signature>

{
  "event": "payment.captured",
  "payload": {...}
}
```

Verifies signature and credits user account.

---

## Polling Best Practices

**For job status:**
- Poll every 2-3 seconds
- Stop when `status` is `completed`, `failed`, or `partial_failure`
- Show progress bar: `completed_insights / total_insights * 100`
- Display individual insights as they complete (from `insights` array)

**Example (React Query)**:
```javascript
const { data } = useQuery({
  queryKey: ['job-status', jobId],
  queryFn: () => fetch(`/api/insights/jobs/${jobId}/status`),
  refetchInterval: (data) =>
    data?.status === 'running' ? 2000 : false,
  enabled: !!jobId
});
```
