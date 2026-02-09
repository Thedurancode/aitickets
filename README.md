# AI Tickets

**Voice-first event ticketing platform powered by AI.** Built for AI voice agents to manage the entire ticketing lifecycle through natural conversation.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)

---

## What Makes This Different

Most ticketing systems are built for clicking buttons. This one is built for talking.

```
User: "Check in John Smith for tonight's show"
Agent: "Welcome! John Smith is checked in for Jazz Night."

User: "How much revenue did we make last week?"
Agent: "Last week you sold 47 tickets for $2,350 across 3 events."

User: "Send a reminder to everyone coming tomorrow"
Agent: "Sent 23 reminders for Rock Festival - 18 emails and 5 SMS."
```

The system uses **LLM-powered routing** to understand natural language, extract names/dates/quantities, and execute the right action from 100+ available tools.

---

## Features

### Core Ticketing
- **Event Management** - Create, update, postpone, cancel events
- **Ticket Sales** - Stripe checkout, promo codes, multiple tiers
- **QR Tickets** - Generate QR codes for check-in
- **PDF Tickets** - Download or email PDF tickets
- **Apple Wallet** - Generate .pkpass files for iOS

### Voice Agent Integration
- **Natural Language Understanding** - Powered by GPT-4o-mini via OpenRouter
- **100+ MCP Tools** - Full ticketing operations exposed as callable tools
- **Speech Responses** - Returns human-friendly sentences, not JSON
- **Session Context** - Remembers last event/customer across requests

### Customer Management
- **Customer Profiles** - Purchase history, preferences, VIP status
- **Notifications** - Email (Resend) and SMS (Twilio)
- **Marketing Campaigns** - Segmented targeting, saved lists
- **Waitlist** - Auto-notify when tickets become available

### Operations
- **Live Dashboard** - Real-time TV-style operations view
- **Auto-Reminders** - Scheduled email/SMS before events
- **Check-in System** - QR scan or name lookup
- **Analytics** - Revenue reports, conversion tracking

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
```

### 3. Run the Server

```bash
python -m mcp_server.http_server --port 3001
```

### 4. Test It

```bash
# Natural language works!
curl -X POST http://localhost:3001/voice/action \
  -H "Content-Type: application/json" \
  -d '{"action": "show me all the events"}'

# Try more complex requests
curl -X POST http://localhost:3001/voice/action \
  -H "Content-Type: application/json" \
  -d '{"action": "check in John Smith for tonight"}'
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/voice/action` | POST | **Main voice agent endpoint** - natural language |
| `/tools` | GET | List all available MCP tools |
| `/tools/{name}` | POST | Call a specific tool directly |
| `/mcp/sse` | GET | MCP protocol SSE stream |
| `/mcp/message` | POST | MCP JSON-RPC messages |
| `/dashboard` | GET | Live operations dashboard |
| `/docs` | GET | Swagger API documentation |

---

## Voice Commands Examples

The LLM understands intent and extracts arguments automatically:

### Events
```
"show me all events"
"create an event called Jazz Night on March 15th at 8pm"
"postpone the Raptors game to next Saturday"
"cancel tonight's show"
```

### Tickets & Check-in
```
"check in John Smith"
"how many tickets left for the concert?"
"send Sarah her ticket PDF"
"add 50 more VIP tickets"
```

### Revenue & Analytics
```
"what was our revenue last month?"
"how many tickets did we sell this week?"
"show me the conversion rate for Jazz Night"
```

### Customers & Marketing
```
"find customer john@example.com"
"send a reminder to everyone coming tomorrow"
"create a VIP blast about the new event"
"who's on the waitlist?"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Voice Agent                               │
│                  (ElevenLabs, Vapi, etc.)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    /voice/action endpoint                        │
├─────────────────────────────────────────────────────────────────┤
│  1. LLM Router (GPT-4o-mini via OpenRouter)                     │
│     - Understands natural language                               │
│     - Picks from 100+ tools                                      │
│     - Extracts arguments (names, dates, etc.)                   │
├─────────────────────────────────────────────────────────────────┤
│  2. Tool Execution                                               │
│     - Runs the selected MCP tool                                 │
│     - Returns structured data                                    │
├─────────────────────────────────────────────────────────────────┤
│  3. Speech Response Generator                                    │
│     - Converts result to natural sentence                        │
│     - "Checked in John Smith for Jazz Night"                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Integrations                                │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│    Stripe    │    Resend    │    Twilio    │   Apple Wallet    │
│   Payments   │    Email     │     SMS      │     .pkpass       │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

---

## LLM Providers

The system supports multiple LLM providers for voice routing:

| Provider | Model | Config |
|----------|-------|--------|
| **OpenRouter** (recommended) | `openai/gpt-4o-mini` | `OPENROUTER_API_KEY` |
| OpenAI Direct | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Zhipu AI | `glm-4` | `ZHIPU_API_KEY` |

OpenRouter is recommended because it provides access to many models through one API, with usage-based pricing and no monthly commitment.

---

## MCP Protocol Support

This server implements the [Model Context Protocol](https://modelcontextprotocol.io/) for AI agent integration:

```bash
# Connect via SSE
curl http://localhost:3001/mcp/sse

# Send MCP messages
curl -X POST http://localhost:3001/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

Compatible with:
- ElevenLabs Conversational AI
- Claude Desktop
- Custom MCP clients

---

## Dashboard

Access the live operations dashboard at `http://localhost:3001/dashboard`

Features:
- Today's event with countdown
- Real-time check-in feed
- Ticket sales stats
- Activity feed (tool calls)
- Auto-updates via SSE

---

## Project Structure

```
ai-tickets/
├── app/
│   ├── config.py           # Environment settings
│   ├── database.py         # SQLAlchemy setup
│   ├── models.py           # Data models
│   ├── routers/            # API routes
│   └── services/
│       ├── llm_router.py   # LLM-based command routing
│       ├── email.py        # Resend integration
│       ├── scheduler.py    # Auto-reminders
│       └── ...
├── mcp_server/
│   ├── server.py           # MCP tool definitions (100+)
│   └── http_server.py      # HTTP/SSE transport
├── templates/              # Email templates
├── requirements.txt
└── .env.example
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with FastAPI, SQLAlchemy, and a lot of coffee.
