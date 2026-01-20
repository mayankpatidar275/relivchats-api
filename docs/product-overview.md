# Product Overview

## What is RelivChats?

AI-powered chat analysis platform that transforms WhatsApp conversations into psychological insights.

**Value Proposition:**
- **Free**: Upload chats → Get instant statistics
- **Paid**: Unlock AI insights (400 coins for 6 romantic insights)

## Business Model

### Credit System (Not Subscription)
- **50 coins** on signup (not enough to unlock)
- **Romantic category**: 400 coins (₹399/$4.99) - 6 insights
- **Future categories**: 300 coins - Friendship, Family, Professional

### Credit Packages
1. **Starter**: ₹399 ($4.99) = 400 coins → 1 analysis
2. **Popular** ⭐: ₹799 ($9.99) = 850 coins → 2 analyses
3. **Pro**: ₹1,499 ($17.99) = 1,600 coins → 4 analyses

**Pricing Strategy**: Premium positioning (4-5x ChatBump) justified by depth (6 comprehensive insights vs basic analysis)

## Target Market

**Phase 1: India 🇮🇳**
- WhatsApp penetration: 85%
- Age 22-32, urban tier 1-2 cities
- Romantic insights = high emotional value

**Future**: UAE, Singapore, Saudi Arabia, Brazil, Mexico, Indonesia

## User Flow

### Upload Flow
```
1. User uploads WhatsApp .txt file
2. Backend parses → Stores in PostgreSQL
3. Generates free stats (1-2 sec)
4. Vector indexing: LAZY (on unlock, not upload)
5. Shows dashboard with "Unlock Insights" button
```

### Unlock Flow
```
1. User clicks "Unlock Romantic Insights (400 coins)"
2. If insufficient coins → Pricing page
3. After payment: Deduct 400 coins
4. Backend:
   - Check vector status (index if needed)
   - Create generation job
   - Launch Celery tasks (parallel)
5. Frontend polls every 2-3 sec
6. Insights appear progressively
```

## Romantic Category Insights (6 Total)

1. **Communication Basics** - Initiation, response patterns, balance
2. **Emotional Intimacy** - Vulnerability, support, affection
3. **Love Language** - Primary/secondary languages, compatibility
4. **Conflict Resolution** - Triggers, styles, repair strategies
5. **Future Planning** - Goals, alignment, shared vision
6. **Playfulness & Romance** - Humor, flirtation, spontaneity

## Competitive Advantage

**vs ChatBump:**
- 6 comprehensive dimensions vs basic analysis
- Evidence-backed with actual quotes
- Category-based bundling (complete analysis)
- India-first (handles Hinglish)
- Premium depth justifies 4-5x price

**Target Users:**
- Couples in India (22-35 years)
- Long-distance relationships
- Pre-marriage couples
- Couples seeking relationship awareness

## Cost Economics

### Per Unlock (Romantic)
```
Gemini API: $0.105 (7 insights)
Revenue: $4.99 (400 coins)
Gross margin: ~98% ($4.88 profit)
```

### Monthly Projections
```
1,000 users × 30% conversion × ₹399 = ₹1.2L/month
5,000 users × 30% conversion × ₹399 = ₹6L/month
10,000 users × 30% conversion × ₹399 = ₹12L/month
```

## Development Status

### ✅ Complete
- User auth (Clerk)
- Chat upload & parsing
- Free statistics
- Vector indexing (Qdrant)
- 6 romantic insights (prompts + schemas)
- Parallel generation (Celery)
- Credit system
- Razorpay integration
- Complete frontend UI

### 🚧 In Progress
- Edge case handling
- Error monitoring

### 📋 TODO
- Performance optimization
- User testing
- Marketing pages

### 🔮 Future (V2)
- Other categories (Friendship, Family, Professional)
- Country-based pricing (PPP)
- PDF/PNG export
- Public sharing
- Mobile app

## Key Design Decisions

**Why lazy vector indexing?**
- 95% of uploads never unlock → save embedding costs
- Faster upload experience
- Can refund if indexing fails

**Why Celery over BackgroundTasks?**
- Reliability (survives restarts)
- Automatic retries
- Horizontal scaling
- Monitoring (Flower)

**Why credit system over subscription?**
- Sporadic usage pattern
- Lower barrier ($3 vs $10/month)
- Pay-per-use flexibility
