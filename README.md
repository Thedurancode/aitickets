# AI Tickets

**Voice-first event ticketing platform powered by AI.** Built for AI voice agents to manage the entire ticketing lifecycle through natural conversation — from selling tickets to checking in guests to running marketing campaigns.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)
![Tests](https://img.shields.io/badge/tests-149%20passing-brightgreen.svg)

**Live:** [ai-tickets.fly.dev](https://ai-tickets.fly.dev)

---

## What Makes This Different

Most ticketing systems are built for clicking buttons. This one is built for talking.

```
User: "Check in John Smith for tonight's show"
Agent: "Welcome! John Smith is checked in for Jazz Night."

User: "How much revenue did we make last week?"
Agent: "Last week you sold 47 tickets for $2,350 across 3 events."

User: "Add Ed Duran as CEO to the About page"
Agent: "Added Ed Duran (CEO) to the About Us team section."
```

The system uses **LLM-powered routing** to understand natural language, extract names/dates/quantities, and execute the right action from **125+ available MCP tools**.

---

## Features

### Core Ticketing
- **Event Management** — Create, update, postpone, cancel events; recurring event series
- **Multi-Tier Pricing** — Multiple ticket tiers per event with inventory tracking
- **Stripe Payments** — Checkout sessions, payment links, webhook handling, refunds
- **Promo Codes** — Percentage or fixed-amount discounts, per-event or global, usage limits
- **QR Code Tickets** — Generate unique QR tokens for check-in validation
- **PDF Tickets** — Downloadable PDF tickets with event details and QR code
- **Apple Wallet** — Generate `.pkpass` files for iOS Wallet
- **Waitlist** — Auto-managed waitlist with position tracking and notification on availability

### Voice Agent / MCP Integration
- **125+ MCP Tools** — Full ticketing operations exposed as callable tools
- **Natural Language Understanding** — GPT-4o-mini via OpenRouter for intent routing
- **Multi-Turn Conversations** — Session context remembers last event/customer across requests
- **Speech Responses** — Returns human-friendly sentences, not raw JSON
- **Real-Time SSE** — Server-Sent Events for live updates to connected agents
- **Entity Context Tracking** — Maintains focus on current customer/event across tool calls

### Customer Intelligence
- **Customer Profiles** — Purchase history, preferences, VIP status, lifetime spend
- **Smart Search** — Fuzzy name search, exact phone/email lookup, guest finder
- **Customer Notes** — AI-captured insights from conversations (preferences, issues, VIP flags)
- **Family/Group Detection** — Intelligent relationship resolver for group attendees
- **Churn Prediction** — Identify at-risk customers before they leave
- **Personalization** — Preferred seating, language, contact method, favorite event types

### Marketing & Notifications
- **Email Notifications** — Via Resend: confirmations, reminders, updates, cancellations
- **SMS Notifications** — Via Twilio: ticket delivery, reminders, marketing blasts
- **Marketing Campaigns** — Segmented targeting with saved audience lists
- **Auto-Triggers** — Automated campaigns on low sell-through, almost sold-out, post-event
- **Cart Recovery** — Detect and recover abandoned checkout sessions
- **Post-Event Surveys** — Automated survey emails with 1-10 rating and comments
- **Social Media** — Post to social channels via Postiz integration

### Analytics & Insights
- **Revenue Reports** — Sales by event, tier, time period with revenue forecasting
- **Conversion Tracking** — Page view → purchase funnel with UTM attribution
- **Demand Prediction** — Mathematical models for ticket demand forecasting
- **Pricing Suggestions** — Dynamic pricing recommendations based on demand signals
- **Trending Events** — Identify hot-selling events across the platform
- **Event Recommendations** — Suggest events to customers based on history

### Knowledge Base (RAG)
- **Document Upload** — PDF, TXT, Markdown file ingestion
- **Content Paste** — Quick FAQ/info paste for venue or event knowledge
- **Semantic Search** — OpenAI embeddings with cosine similarity search
- **Voice Q&A** — Voice agents can answer FAQ questions from the knowledge base

### Outbound Webhooks
- **Event Subscriptions** — Subscribe to: `ticket.purchased`, `ticket.checked_in`, `ticket.refunded`, `event.created`, `event.updated`, `event.deleted`, `customer.registered`
- **HMAC-SHA256 Signing** — Every payload signed with a shared secret
- **Automatic Retry** — Up to 3 attempts with exponential backoff
- **Delivery Logging** — Full audit trail of every delivery attempt
- **Wildcard Support** — Subscribe to `*` for all event types
- **Test Ping** — Verify endpoint connectivity before going live

### Voice-Controlled About Page
- **Database-Driven CMS** — All content stored in DB, editable via API or voice
- **Section Management** — Hero, mission, story, team members, contact, social links
- **Team Member Management** — Add/remove team members with name, role, bio, photo
- **Public Page** — Beautiful responsive page with scroll animations, brand theming
- **4 MCP Tools** — `get_about_page`, `update_about_section`, `add_team_member`, `remove_team_member`

### Public Website
- **Event Listing** — Browse events with category filtering and search
- **Event Detail Pages** — Full event info, ticket tiers, purchase flow, photo gallery
- **Photo Gallery** — Public photo upload and viewing for event attendees
- **Event Admin Dashboard** — Magic-link protected admin with analytics
- **About Us Page** — Voice-editable org page with team, mission, contact info
- **Brand Theming** — Org name, color, and logo applied across all pages

### Operations & Admin
- **Check-In System** — QR scan or name lookup with undo capability
- **Magic Link Auth** — Passwordless admin access via SMS verification
- **Auto-Reminders** — Configurable hours-before reminder scheduling
- **Health Checks** — DB-aware health endpoint for monitoring
- **Rate Limiting** — API rate limiting via SlowAPI
- **CORS Support** — Configurable allowed origins

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/Thedurancode/aitickets.git
cd aitickets
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required for LLM routing (get key at https://openrouter.ai)
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_ROUTER_MODEL=openai/gpt-4o-mini

# Required for payments
STRIPE_SECRET_KEY=sk_test_...

# Optional: Email notifications
RESEND_API_KEY=re_...

# Optional: SMS notifications
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Optional: RAG knowledge base
OPENAI_API_KEY=sk-...

# Branding
ORG_NAME=Your Organization
ORG_COLOR=#CE1141
ORG_LOGO_URL=https://...
```

### 3. Run the Server

```bash
# REST API + Public Pages
uvicorn app.main:app --port 8000

# MCP Server (voice agent)
python -m mcp_server.http_server --port 3001
```

### 4. Test It

```bash
# Natural language works!
curl -X POST http://localhost:3001/voice/action \
  -H "Content-Type: application/json" \
  -d '{"action": "show me all the events"}'

# REST API
curl http://localhost:8000/api/events

# Browse the site
open http://localhost:8000/events
```

### 5. Run Tests

```bash
pytest tests/ -q
# 149 passed
```

---

## API Endpoints

### Voice / MCP
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/voice/action` | POST | Main voice agent endpoint — natural language |
| `/tools` | GET | List all 125+ MCP tools |
| `/tools/{name}` | POST | Call a specific tool directly |
| `/mcp/sse` | GET | MCP protocol SSE stream |
| `/mcp/message` | POST | MCP JSON-RPC messages |

### REST API (`/api`)
| Resource | Endpoints | Description |
|----------|-----------|-------------|
| **Events** | `GET/POST /events`, `GET/PUT/DELETE /events/{id}` | Event CRUD |
| **Venues** | `GET/POST /venues`, `GET/PUT/DELETE /venues/{id}` | Venue management |
| **Ticket Tiers** | `GET/POST /events/{id}/tiers`, `PUT/DELETE /tiers/{id}` | Tier management |
| **Tickets** | `POST /tickets/events/{id}/purchase`, `POST /tickets/validate/{qr}` | Purchase & check-in |
| **Event Goers** | `GET/POST /event-goers`, `GET/PUT /event-goers/{id}` | Customer profiles |
| **Categories** | `GET/POST /categories`, `GET/PUT/DELETE /categories/{id}` | Event categories |
| **Promo Codes** | `GET/POST /promo-codes`, `POST /promo-codes/validate` | Discount codes |
| **Notifications** | `POST /notifications/reminders`, `POST /notifications/campaigns` | Email & SMS |
| **Analytics** | `GET /analytics/overview`, `GET /analytics/events/{id}` | Stats & insights |
| **Knowledge** | `POST /knowledge/upload`, `POST /knowledge/paste`, `GET /knowledge/search` | RAG documents |
| **Webhooks** | `POST/GET /webhooks/outbound`, `POST /webhooks/outbound/{id}/test` | Outbound webhooks |
| **About** | `GET/PUT /about`, `POST/DELETE /about/team-member` | About page CMS |

### Public Pages
| Path | Description |
|------|-------------|
| `/events` | Event listing with search & category filters |
| `/events/{id}` | Event detail with ticket purchase |
| `/events/{id}/admin?token=...` | Magic-link protected admin dashboard |
| `/events/{id}/photos` | Photo gallery with upload |
| `/about` | About Us page |
| `/docs` | Swagger API documentation |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Voice Agent                            │
│                (ElevenLabs, Vapi, etc.)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  /voice/action endpoint                     │
├─────────────────────────────────────────────────────────────┤
│  1. LLM Router (GPT-4o-mini via OpenRouter)                │
│     - Understands natural language                          │
│     - Picks from 125+ tools                                │
│     - Extracts arguments (names, dates, etc.)              │
├─────────────────────────────────────────────────────────────┤
│  2. MCP Tool Execution                                     │
│     - 125+ tools across 15 categories                      │
│     - Session context for multi-turn conversations         │
│     - Entity tracking (current customer/event)             │
├─────────────────────────────────────────────────────────────┤
│  3. Speech Response Generator                              │
│     - Converts result to natural sentence                  │
│     - "Checked in John Smith for Jazz Night"               │
└─────────────────────────────────────────────────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
┌──────────────┬──────────────┬──────────────┬──────────────┐
│   Stripe     │   Resend     │   Twilio     │   OpenAI     │
│  Payments    │   Email      │    SMS       │  Embeddings  │
├──────────────┼──────────────┼──────────────┼──────────────┤
│   Postiz     │ Apple Wallet │  Webhooks    │  PostgreSQL  │
│ Social Media │   .pkpass    │ HMAC-signed  │   Database   │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## Project Structure

```
ai-tickets/
├── app/
│   ├── config.py              # Environment settings & branding
│   ├── database.py            # SQLAlchemy + custom migration system
│   ├── models.py              # 25 database models
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── rate_limit.py          # SlowAPI rate limiting
│   ├── routers/               # 16 API routers
│   │   ├── events.py          #   Event CRUD
│   │   ├── tickets.py         #   Purchase & check-in
│   │   ├── notifications.py   #   Email/SMS notifications
│   │   ├── webhooks.py        #   Outbound webhooks
│   │   ├── knowledge.py       #   RAG knowledge base
│   │   ├── about.py           #   About page CMS
│   │   ├── public.py          #   HTML pages
│   │   └── ...
│   ├── services/              # 20 backend services
│   │   ├── llm_router.py      #   LLM command routing
│   │   ├── rag.py             #   RAG embeddings & search
│   │   ├── webhooks.py        #   HMAC signing & delivery
│   │   ├── analytics_engine.py #  Revenue forecasting
│   │   └── ...
│   ├── migrations/            # Custom migration files
│   └── templates/public/      # Jinja2 HTML templates
├── mcp_server/
│   ├── server.py              # 125+ MCP tool definitions
│   └── http_server.py         # HTTP/SSE transport
├── tests/                     # 149 tests across 13 files
├── templates/                 # Email templates
├── fly.toml                   # Fly.io deployment config
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Deployment

### Fly.io (Production)

```bash
fly deploy --remote-only
```

The app runs on Fly.io with PostgreSQL. See `fly.toml` for configuration.

### Environment Variables (Production)

Set via `fly secrets set`:
- `DATABASE_URL` — PostgreSQL connection string
- `STRIPE_SECRET_KEY` — Stripe payments
- `RESEND_API_KEY` — Email delivery
- `BASE_URL` — Public URL (e.g., `https://ai-tickets.fly.dev`)
- `OPENROUTER_API_KEY` — LLM routing
- `OPENAI_API_KEY` — RAG embeddings (optional)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI + Uvicorn |
| **Database** | PostgreSQL (prod) / SQLite (dev/test) |
| **ORM** | SQLAlchemy |
| **Templates** | Jinja2 + Tailwind CSS |
| **Payments** | Stripe |
| **Email** | Resend |
| **SMS** | Twilio |
| **AI/LLM** | OpenRouter (GPT-4o-mini), OpenAI (embeddings) |
| **Voice Protocol** | MCP (Model Context Protocol) |
| **Hosting** | Fly.io |
| **CI** | GitHub Actions (lint + test) |

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -q`
5. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with FastAPI, SQLAlchemy, and a lot of coffee.
