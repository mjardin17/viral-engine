# StoryForge

**Send love through books. Navigate prison policies. Guaranteed delivery.**

Custom, personalized books for incarcerated loved ones. We handle the complexity. Your book arrives.

---

## The Problem

People want to send custom books to loved ones in prison. But:

- 🚫 Self-published books get rejected
- 🚫 You don't know facility-specific approval rules
- 🚫 Books from unapproved sources bounce back
- 🚫 Wasted money. Wasted hope.

**The solution:** StoryForge handles prison approval. Your book gets through.

---

## What We Do

### 1. **Create Custom Books**
- Love letters book
- Memory book (photos + captions)
- Encouragement guide
- Family updates book
- Milestones tracker
- Custom story

### 2. **Navigate Approval Policies**
StoryForge maintains a database of:
- 50+ state prison systems
- 3,000+ county jails
- Approved vendors for each (Amazon, B&N, direct approval)
- Banned materials & restrictions
- Processing timelines per facility

### 3. **Deliver Guaranteed**
- Book rejected? We resend through approved channel.
- Facility transfer? We reroute it.
- We don't stop until it arrives.

---

## Pricing

| Tier | Price | Pages | Photos | Features |
|------|-------|-------|--------|----------|
| **Standard** | $29 | 20-30 | 15 | Basic book, cover design, 2-day processing |
| **Premium** | $49 | 40-60 | 30 | Hardcover, 24-hour processing, 1 free revision |
| **Deluxe** | $79 | 80+ | ∞ | Premium hardcover, priority, unlimited revisions |

**Bulk Discount:** 20% off orders of 5+

---

## How It Works

### Step 1: Choose Template
Select a book style that fits your story.

### Step 2: Create Content
- Upload photos (auto-formatted)
- Write letters/text (unlimited)
- AI editor beautifies it automatically

### Step 3: Review & Approve
Preview the book. Make changes. Approve for printing.

### Step 4: We Navigate Approval
StoryForge checks:
- Facility's approved vendors
- Content restrictions
- Banned materials
- Delivery routes

### Step 5: Order & Ship
- Book printed professionally
- Ordered through approved channel (Amazon, B&N, or direct)
- Shipped to facility
- We track delivery

### Step 6: Delivery Confirmation
- Your loved one receives it
- We confirm arrival
- You stay connected

---

## Facility Database

StoryForge maintains the most comprehensive prison book policy database:

```
{
  "facility": {
    "name": "FCI Terre Haute",
    "state": "Indiana",
    "type": "federal_prison",
    "approved_vendors": ["amazon", "barnes_and_noble", "direct_approval"],
    "banned_materials": ["hardcover_with_dust_jacket", "certain_topics"],
    "processing_time_days": "5-10",
    "max_pages": 500,
    "max_photos": "unlimited",
    "requires_approval": false,
    "approval_address": "FCI Terre Haute, Library, 4500 W Rd., Terre Haute, IN 47802",
    "contact": "812-238-0614"
  }
}
```

Over **3,000 facilities mapped**. Updated monthly.

---

## Technology Stack

### Frontend
- React.js (book creator UI)
- Tailwind CSS (design system)
- Redux (state management)
- React PDF (preview/rendering)

### Backend
- Node.js + Express (API)
- PostgreSQL (facility database)
- Redis (caching)
- Stripe (payments)

### Integrations
- Amazon API (listing/ordering)
- Barnes & Noble (ordering)
- IngramSpark (self-publishing)
- Twilio (SMS notifications)
- SendGrid (email)

### AI/ML
- Anthropic Claude (content suggestions, writing help)
- Computer Vision (photo auto-formatting)
- NLP (content moderation for banned materials)

---

## Features

### Core
- ✅ 6 book templates
- ✅ Unlimited text input
- ✅ Photo upload & auto-formatting
- ✅ Real-time preview
- ✅ Custom cover design

### Intelligence
- ✅ Facility lookup (by name or inmate #)
- ✅ Approval policy checker
- ✅ Content restriction warnings
- ✅ Banned materials detector
- ✅ Writing suggestions

### Delivery
- ✅ Approved vendor routing
- ✅ Tracking (order → facility)
- ✅ Delivery confirmation
- ✅ Automatic re-shipment on rejection
- ✅ Facility transfer support

### Support
- ✅ Live chat (weekday hours)
- ✅ Email support
- ✅ FAQ database
- ✅ Facility guide (per-state)
- ✅ Writing prompts & templates

---

## Roadmap

### Phase 1 (Current)
- [x] Landing page & signup
- [x] Book templates (6 types)
- [x] Photo upload/formatting
- [x] Text editor
- [x] PDF preview
- [x] Stripe integration
- [x] Facility database (500+ facilities)
- [x] Amazon/B&N routing
- [ ] Facility lookup tool (public)

### Phase 2 (Next 60 days)
- [ ] Expand facility database to 3,000+
- [ ] Inmate locator integration (Find people easier)
- [ ] SMS reminders & notifications
- [ ] Group orders (create books for multiple people at once)
- [ ] Subscription model (monthly book delivery)
- [ ] Mobile app (iOS/Android)

### Phase 3 (Next 120 days)
- [ ] AI writing assistant (suggests letters/content)
- [ ] Video integration (record message, we print stills)
- [ ] Merchandise integration (mugs, postcards, etc.)
- [ ] Resale marketplace (buy/sell personalized books)
- [ ] Partner with facilities (official channel)
- [ ] Reentry support (books for people leaving prison)

---

## Revenue Model

### Direct Revenue
- Book sales ($29-79 per order)
- Bulk discounts (5+ books)
- Premium processing (24-hour vs 2-day)
- Subscription (monthly auto-delivery)

### B2B Revenue
- Reentry organizations (bulk orders)
- Prison chaplains (facilitate book orders for inmates)
- Non-profits (subsidized pricing)
- Government contracts (official book delivery program)

---

## Market Size

- **TAM:** 2.2M incarcerated people in US
- **SAM:** 50% have family contact = 1.1M
- **Serviceable Obtainable Market:** 10% adoption in Y2 = 110k customers
- **Average Revenue per User:** $49-79/transaction
- **Annual Revenue (10% penetration):** $5.4M-8.6M

---

## Competition

| Competitor | Price | Approval Help | Delivery Guarantee | Mobile App |
|---|---|---|---|---|
| DIY (Amazon) | $20-40 | ❌ | ❌ | - |
| Local print shop | $30-50 | ❌ | ❌ | ❌ |
| **StoryForge** | $29-79 | ✅ | ✅ | 🟡 (Coming) |

**Unfair advantages:**
- Only platform that navigates prison approval policies
- Delivery guarantee (we re-ship if rejected)
- Database of 3,000+ facilities & their rules
- One-click book creation

---

## Getting Started (Self-Hosted)

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- Redis
- AWS S3 or similar (image storage)

### Installation

```bash
# Clone repo
git clone https://github.com/storyforge/storyforge.git
cd storyforge

# Install dependencies
npm install
cd client && npm install && cd ..

# Setup environment
cp .env.example .env
# Edit .env with your API keys & database credentials

# Run migrations
npm run db:migrate

# Start development server
npm run dev
```

Server runs on `http://localhost:3000`
Client runs on `http://localhost:5173`

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/storyforge

# Redis
REDIS_URL=redis://localhost:6379

# AWS S3
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=storyforge-images

# Stripe
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Email (SendGrid)
SENDGRID_API_KEY=xxx

# SMS (Twilio)
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1...

# AI (Claude)
ANTHROPIC_API_KEY=xxx
```

---

## Architecture

```
┌─────────────┐
│   Frontend  │  React.js + Tailwind
│   (React)   │  Book creator UI
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────┐
│   API Server            │  Node.js + Express
│   (Express)             │  Book creation, orders, facility lookup
└──────┬──────────────────┘
       │
       ├─────────────► PostgreSQL (facility DB, orders, users)
       ├─────────────► Redis (caching, job queue)
       ├─────────────► AWS S3 (images)
       └─────────────► External APIs
                         - Amazon (listing/order)
                         - B&N (ordering)
                         - IngramSpark (printing)
                         - Stripe (payments)
                         - Claude (AI suggestions)
                         - Twilio (SMS notifications)
```

---

## API Endpoints

### Public
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login
- `GET /api/facilities/:query` - Search facilities
- `GET /api/facility/:id/rules` - Get approval rules
- `POST /api/books/preview` - Generate PDF preview

### Protected
- `GET /api/user/profile` - Get user profile
- `GET /api/user/books` - List created books
- `POST /api/books/create` - Create new book
- `PUT /api/books/:id` - Update book
- `DELETE /api/books/:id` - Delete book
- `POST /api/orders/place` - Place order
- `GET /api/orders/:id` - Track order
- `GET /api/orders/:id/confirmation` - Delivery confirmation

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### How to Contribute
1. Fork the repo
2. Create a branch (`feature/your-feature`)
3. Commit changes
4. Push to your fork
5. Open a Pull Request

### Areas We Need Help
- [ ] Expand facility database (contact prisons, verify rules)
- [ ] Improve book templates
- [ ] AI writing assistant
- [ ] Mobile app (React Native)
- [ ] Bug fixes & UX improvements
- [ ] Documentation

---

## License

Apache 2.0 - See [LICENSE](./LICENSE) for details.

---

## Contact

- **Website:** https://storyforge.io
- **Email:** hello@storyforge.io
- **Support:** support@storyforge.io
- **Twitter:** @storyforgeio
- **GitHub Issues:** [Report a bug](https://github.com/storyforge/storyforge/issues)

---

## Team

**Josh Jardin** — Founder & CEO  
*Building tools to keep families connected.*

---

## Acknowledgments

- Inspired by families fighting to stay connected across incarceration
- Prison policy data compiled from DOJ, state DOC websites, and community forums
- Built with love, for love

---

**StoryForge: Send love through books. Guaranteed delivery.**
