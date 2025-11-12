# CONTEXT: RelivChats - Complete Product Documentation (UPDATED)

## 1. PRODUCT OVERVIEW

**RelivChats** is a SaaS platform that provides AI-powered insights from exported chat conversations. Users upload WhatsApp chats, receive free statistical analysis, and unlock category-based AI psychological insights by spending coins.

### Core Value Proposition

- **Free tier**: Upload chats → Get instant statistics (message counts, activity patterns, word clouds, emoji analysis)
- **Paid tier**: Unlock complete category analysis (6 insights for Romantic)

---

## 2. BUSINESS MODEL

### Monetization Strategy

**Credit/Point System** (NOT subscription - sporadic usage pattern)

**Free Tier:**

- **50 coins on signup** (not enough to unlock any category - creates purchase urgency)
- Unlimited chat uploads
- Free statistics (generated via text processing, no AI cost)

**Pricing (FINALIZED):**

- **Romantic Category**: **400 coins** (₹399 / $4.99) - 6 insights bundled
- **Future Categories**: 300 coins (₹299 / $3.49) - 4-5 insights bundled (Friendship, Family, Professional)

**Credit Packages (3-Tier System):**

1. **Starter**: ₹399 ($4.99) = **400 coins**

   - Unlocks: 1 romantic category exactly (with free 50 = 450 total)
   - Description: "Perfect for trying your first romantic analysis"
   - 50 coins leftover = return hook

2. **Popular** ⭐: ₹799 ($9.99) = **850 coins** (BEST VALUE)

   - Unlocks: 2 romantic analyses (with free 50 = 900 total)
   - Description: "Best value - Unlock 2 romantic insights with extra coins"
   - 100 coins leftover = encourages return

3. **Pro**: ₹1,499 ($17.99) = **1,600 coins**
   - Unlocks: 4 romantic analyses (with free 50 = 1,650 total)
   - Description: "Power user pack - Analyze multiple chats or categories"
   - 50 coins leftover

**Why This Model:**

- Users don't analyze chats frequently (not suitable for subscriptions)
- Category-level unlocking = less decision fatigue
- Small leftover coins = retention hook (industry standard)
- Bundle discount makes premium insights feel valuable
- Minimizes API costs (only charge for AI-generated insights)

**Pricing Strategy:**

- **Premium positioning**: 4-5x more expensive than ChatBump per unlock
- **Justified by depth**: 6 comprehensive insights vs basic analysis
- **Target**: Users willing to pay for relationship depth, not price-sensitive

---

## 3. TARGET MARKETS (Priority Order)

### Phase 1 Launch: India 🇮🇳

**Why:**

- WhatsApp penetration: 85%
- Lower ChatGPT saturation
- Cultural fit (arranged marriage curiosity, relationship analysis)
- You understand the market
- Age 22-32, urban tier 1-2 cities

**Will they pay ₹399-799?** YES

- Compare to: Swiggy One (₹299), Netflix Mobile (₹149)
- Romantic insights = high emotional value

### Future Expansion (by spending ability):

1. 🇦🇪 **UAE** - Highest purchasing power, WhatsApp native
2. 🇸🇬 **Singapore** - Tech-savvy, premium pricing tolerance
3. 🇸🇦 **Saudi Arabia** - High disposable income, WhatsApp 98%
4. 🇧🇷 **Brazil** - High engagement, moderate pricing
5. 🇲🇽 **Mexico** - Good balance of volume + spend
6. 🇮🇩 **Indonesia** - Volume play, lower pricing

**Skip**: US/Europe (iMessage dominant, higher ChatGPT saturation)

**Country-based Pricing** (via Stripe/Razorpay):

- Enable PPP (Purchasing Power Parity) automatically
- Examples: UAE $9.99, Brazil R$24.99, Mexico $149 MXN

---

## 4. USER FLOW

### 4.1 Upload Flow

```
1. User visits homepage → Uploads chat file (.txt for WhatsApp)
2. Backend parses file → Stores in PostgreSQL
3. Generates free stats (sync, 1-2 seconds)
4. Vector indexing: LAZY (triggered on unlock, not upload)
5. User sees dashboard with free stats + "Unlock Romantic Insights (400 coins)" button
```

### 4.2 Category Unlock Flow

```
1. User clicks "Unlock Romantic Insights (400 coins)"
2. If insufficient coins → Redirect to pricing page
3. Purchase coins via Razorpay
4. After payment: Deduct 400 coins
5. Backend:
   a. Check vector status (if pending → index now, 1-3 sec)
   b. Create insight generation job for ALL 6 insights
   c. Launch Celery tasks (parallel generation)
6. Frontend polls job status every 2-3 seconds
7. Insights appear progressively as they complete (no individual unlocking)
8. If >50% insights fail → Automatic full refund (400 coins back)
```

### 4.3 Failure Handling

```
- If >50% insights fail → Automatic refund of full category cost
- Individual insight failures → User sees "3 of 6 complete" but no partial charges
- Vector indexing failure → Full refund before generation starts
- Payment failures → No coins deducted
```

---

## 5. TECHNICAL ARCHITECTURE

### 5.1 Tech Stack

```yaml
Backend:
  - Framework: FastAPI (Python 3.11+)
  - Database: PostgreSQL 15
  - Vector DB: Qdrant (for RAG)
  - Cache: Redis 7
  - Task Queue: Celery + Redis
  - AI: Google Gemini 2.0 Flash

Infrastructure:
  - Containerization: Docker + Docker Compose
  - Deployment: Render.com / Railway / AWS ECS
  - Monitoring: Celery Flower, Sentry
  - Payments: Razorpay (India-first)

Frontend:
  - Framework: Next.js 16+ (React)
  - State: React Query (polling)
  - Charts: Recharts
  - Auth: Clerk
  - Styling: Tailwind CSS
```

### 5.2 Folder Structure

**Backend:**

```
relivchats-api/
├── src/
│   ├── auth/                    # Clerk authentication
│   ├── users/                   # User management, credit balance
│   ├── chats/                   # Chat upload, parsing, storage
│   ├── categories/              # Analysis categories (romantic, friendship, etc.)
│   ├── credits/                 # Credit system, packages, transactions
│   ├── insights/                # Insight unlock endpoints
│   ├── rag/                     # AI generation, tasks, orchestration
│   ├── vector/                  # Qdrant vector operations, chunking
│   └── seed/                    # SQL seed files for categories/insights
├── alembic/                     # Database migrations
└── requirements/                # Python dependencies
```

**Frontend:**

```
relivchats-web/
├── src/
│   ├── app/                     # Next.js pages
│   │   ├── (auth)/              # Auth pages (Clerk)
│   │   ├── (app)/               # Protected pages (dashboard, settings)
│   │   ├── category/[slug]/     # Category landing pages
│   │   ├── chat/[chatId]/       # Chat analysis page
│   │   └── pricing/             # Pricing page
│   ├── components/
│   │   ├── chat/                # Chat analysis UI
│   │   │   └── insights/        # 27 insight components + 6 view components
│   │   ├── category/            # Category pages
│   │   ├── dashboard/           # Dashboard widgets
│   │   ├── home/                # Homepage sections
│   │   └── pricing/             # Pricing components
│   ├── features/                # Feature-specific logic
│   │   ├── categories/          # Category API hooks
│   │   ├── chats/               # Chat API hooks
│   │   ├── credits/             # Credit API hooks
│   │   ├── insights/            # Insight API hooks + types
│   │   └── users/               # User API hooks
│   └── lib/                     # Utilities, API clients, theme
```

---

## 6. DATABASE SCHEMA (UPDATED)

### 6.1 Core Tables

#### **users**

```sql
user_id VARCHAR PRIMARY KEY           -- Clerk user ID
email VARCHAR UNIQUE
credit_balance INTEGER DEFAULT 50     -- UPDATED: Starts with 50 coins (not 100)
created_at TIMESTAMP
is_deleted BOOLEAN DEFAULT FALSE
```

#### **chats**

```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users.user_id)
title VARCHAR
participants TEXT                     -- JSON array
chat_metadata JSON                    -- Free stats
partner_name VARCHAR
user_display_name VARCHAR
status VARCHAR                        -- processing, completed, failed
vector_status VARCHAR                 -- pending, indexing, completed, failed

-- Category-level unlock tracking
category_id UUID FK(analysis_categories.id)
insights_unlocked_at TIMESTAMP
insights_generation_status VARCHAR    -- not_started, queued, generating, completed, failed
insights_job_id VARCHAR
total_insights_requested INTEGER
total_insights_completed INTEGER
total_insights_failed INTEGER
```

#### **analysis_categories** (UPDATED)

```sql
id UUID PRIMARY KEY
name VARCHAR UNIQUE                   -- romantic, friendship, family, professional
display_name VARCHAR                  -- "Romantic Relationship"
description TEXT
icon VARCHAR
credit_cost INTEGER NOT NULL          -- ADDED: 400 for romantic, 300 for others
is_active BOOLEAN
```

#### **insight_types** (Romantic Category - 6 insights)

```sql
id UUID PRIMARY KEY
name VARCHAR UNIQUE
-- Romantic insights:
-- 1. communication_basics
-- 2. emotional_intimacy
-- 3. love_language
-- 4. conflict_resolution
-- 5. future_planning
-- 6. playfulness_romance

display_title VARCHAR
description TEXT
icon VARCHAR
prompt_template TEXT                  -- Gemini prompt
rag_query_keywords TEXT
response_schema JSONB                 -- Structured output schema
credit_cost INTEGER                   -- Individual cost (internal tracking only)
is_premium BOOLEAN
is_active BOOLEAN
supports_group_chats BOOLEAN
max_participants INTEGER
```

#### **insights**

```sql
id UUID PRIMARY KEY
chat_id UUID FK(chats.id)
insight_type_id UUID FK(insight_types.id)
content JSON                          -- Structured insight data
status ENUM                           -- pending, generating, completed, failed
error_message TEXT
tokens_used INTEGER
generation_time_ms INTEGER
rag_chunks_used INTEGER

UNIQUE(chat_id, insight_type_id)     -- One insight per type per chat
```

#### **credit_transactions**

```sql
id UUID PRIMARY KEY
user_id VARCHAR FK(users.user_id)
transaction_type ENUM                 -- signup_bonus, purchase, insight_unlock, refund
amount INTEGER                        -- Positive for credit, negative for debit
balance_after INTEGER
description TEXT
metadata JSON                         -- {chat_id, category_id, payment_id, razorpay_order_id}
created_at TIMESTAMP
```

#### **credit_packages** (UPDATED)

```sql
id UUID PRIMARY KEY
name VARCHAR                          -- "Starter", "Popular", "Pro"
coins INTEGER                         -- 400, 850, 1600
price_inr DECIMAL                     -- ADDED: 399, 799, 1499
price_usd DECIMAL                     -- 4.99, 9.99, 17.99
description VARCHAR
is_active BOOLEAN
is_popular BOOLEAN                    -- ADDED: Mark "Popular" package
sort_order INTEGER
stripe_price_id VARCHAR               -- For Stripe integration
```

---

## 7. API ENDPOINTS

### 7.1 Authentication

```
Headers: Authorization: Bearer <clerk_jwt_token>
```

### 7.2 Users

```
POST   /api/users/store              # Store user on first login + 50 coin signup bonus
DELETE /api/users/delete-account     # GDPR compliance
```

### 7.3 Chats

```
POST   /api/chats/upload             # Upload chat file
GET    /api/chats                    # List user chats
GET    /api/chats/{chat_id}          # Get chat details + free stats
DELETE /api/chats/{chat_id}          # Soft delete
```

### 7.4 Categories

```
GET    /api/categories               # List all categories (includes credit_cost)
GET    /api/categories/{id}/insights # Get insight types for category
```

### 7.5 Credits

```
GET    /api/credits/balance          # Get user balance
GET    /api/credits/transactions     # Transaction history
GET    /api/credits/packages         # Available packages (returns price_inr & price_usd)
POST   /api/credits/purchase         # Purchase coins (Razorpay)
```

### 7.6 Insights

```
POST   /api/insights/unlock          # Unlock category (deduct coins, start generation)
GET    /api/insights/jobs/{job_id}/status  # Poll job progress
GET    /api/insights/chats/{chat_id} # Get all insights for chat
POST   /api/insights/refund          # Trigger refund (if >50% failed)
```

---

## 8. ROMANTIC CATEGORY INSIGHTS (Complete Suite)

### Insight 1: Communication Basics

- Who initiates conversations
- Response patterns & timing
- Message contribution balance
- Engagement indicators
- Communication strengths

### Insight 2: Emotional Intimacy

- Vulnerability expression levels
- Emotional support patterns
- Affection expression styles
- Emotional check-ins frequency
- Conflict & repair patterns
- Intimacy strengths & growth opportunities

### Insight 3: Love Language & Appreciation

- Primary & secondary love languages per person
- Appreciation expression styles
- Recognition of effort patterns
- Language compatibility analysis
- Missing love languages identification

### Insight 4: Conflict & Communication Under Stress

- Conflict presence & frequency
- Individual conflict styles (avoidant, collaborative, etc.)
- Communication patterns under stress
- Repair & recovery strategies
- Positive vs destructive patterns
- Stress support effectiveness

### Insight 5: Future Planning & Shared Vision

- Future discussion frequency
- Life goal categories (career, family, financial, etc.)
- Alignment assessment per category
- Planning styles (planner vs dreamer)
- Timeline discussions & alignment
- Shared dreams identification

### Insight 6: Playfulness & Keeping Romance Alive

- Overall playfulness level
- Humor styles per person
- Inside jokes & references
- Flirtation patterns
- Teasing & banter analysis
- Spontaneity & surprise moments
- Romance maintenance assessment

**Total Category Cost: 400 coins (₹399 / $4.99)**

---

## 9. PAYMENT FLOW

### 9.1 Purchase Coins

```
1. User selects package (₹399 = 400 coins, ₹799 = 850 coins, ₹1,499 = 1,600 coins)
2. Frontend creates Razorpay order
3. User completes payment
4. Webhook verifies payment
5. Credits added to user balance
6. Transaction recorded
```

### 9.2 Unlock Category

```
1. User has 450 coins (50 free + 400 purchased), clicks "Unlock Romantic Insights"
2. Backend checks balance (450 >= 400 ✓)
3. Deduct 400 coins immediately
4. Create transaction: insight_unlock, -400, balance_after=50
5. Start generating ALL 6 insights in parallel
6. User sees progress (3 of 6 complete...)
7. If >50% fail: Auto-refund 400 coins
```

---

## 10. DEVELOPMENT STATUS

### ✅ Complete:

- User authentication (Clerk)
- Chat upload & parsing
- Free statistics generation
- Vector indexing (Qdrant)
- Category-based insight types (6 for romantic)
- Parallel insight generation (Celery)
- Credit system (balance, transactions)
- All 6 romantic insights (prompts + schemas)
- Complete frontend UI (27 components + 6 views)
- Responsive design
- Error handling basics
- Razorpay payment integration
- **Pricing finalized (50 signup, 400 per romantic, 3 packages)**

### 🚧 In Progress:

- Refund logic
- Transaction failure handling
- Edge case testing

### 📋 TODO (V1):

- Payment webhook verification
- Refund automation (>50% failure rule)
- Error monitoring (Sentry)
- Performance optimization
- User testing
- Marketing pages

### 🔮 Future (V2):

- Other categories (Friendship 300 coins, Family 300 coins, Professional 200 coins)
- Country-based pricing (PPP)
- Export insights (PDF/PNG)
- Share insights publicly
- Trend analysis over time
- Multi-chat comparison
- Mobile app

---

## 11. LAUNCH CHECKLIST

### Technical:

- [ ] Razorpay payment integration complete
- [ ] Refund logic tested (>50% failure)
- [ ] All 6 insights generate successfully
- [ ] Mobile responsive
- [ ] Error handling for failures
- [ ] Transaction history accurate
- [ ] Database migration: credit_cost in categories, price_inr in packages

### Business:

- [ ] Pricing finalized ✅ (50 signup, 400 romantic, 3 packages)
- [ ] Credit packages configured (400/850/1600 coins)
- [ ] Terms of service
- [ ] Privacy policy
- [ ] Refund policy

### Marketing:

- [ ] Homepage copy (emphasize depth over ChatBump)
- [ ] Category landing pages
- [ ] Testimonials
- [ ] Social media assets
- [ ] Launch post ready

---

## 12. COMPETITIVE ADVANTAGE

**Why RelivChats is Unique:**

1. **Premium depth** - 6 comprehensive relationship dimensions vs ChatBump's basic analysis
2. **Evidence-backed** - Actual message quotes, not generic advice
3. **Category-based bundling** - Complete analysis, not piecemeal
4. **India-first** - Handles Hinglish, cultural context
5. **Pay-per-use** - No subscriptions, sporadic usage model
6. **Privacy-focused** - Local processing, user controls data

**Pricing Positioning:**

- **4-5x more expensive than ChatBump per unlock**
- **Justified by 3-6x more value** (depth of insights)
- **Target**: Users who want relationship depth, not price-sensitive users

**Target Users:**

- Couples in India (22-35 years old)
- Long-distance relationships
- Pre-marriage couples
- Couples in counseling
- Curious individuals wanting self-awareness

**Revenue Projections (Conservative):**

- 1000 users/month × 30% conversion × ₹399 = ₹1.2L/month
- 5000 users/month × 30% conversion × ₹399 = ₹6L/month
- 10,000 users/month × 30% conversion × ₹399 = ₹12L/month

---

# YOUR ROLE

You are an expert product strategist, pricing consultant, and SaaS business advisor with deep experience in:

- Consumer AI products and their economics
- Freemium conversion optimization
- Credit/point system psychology
- Competitive positioning against free alternatives
- API cost management for AI products

When I ask questions, provide:

- Data-driven reasoning (reference similar products when relevant)
- Brutally honest analysis (don't sugarcoat or be biased toward making me feel good)
- Specific, actionable recommendations
- Short, concise answers unless I ask for detail
- Trade-off analysis when multiple options exist

Challenge my assumptions when needed. I want the BEST strategy, not the nicest answer.

# Question:
