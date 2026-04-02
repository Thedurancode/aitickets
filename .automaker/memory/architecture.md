---
tags: [architecture]
summary: architecture implementation decisions and patterns
relevantTo: [architecture]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# architecture

### MCP (Model Context Protocol) as primary interface for voice agents with 125+ tools instead of traditional REST API routing (2026-02-19)
- **Context:** Voice-first platform needs to support natural language commands that route to different backend functions based on LLM interpretation
- **Why:** MCP provides a standardized protocol for AI agents to discover and call tools with proper schema validation, enabling GPT-4o-mini to understand available operations without hardcoded routing logic. This is more flexible than custom prompt engineering and scales better as tool count grows
- **Rejected:** Direct LLM prompt engineering with hardcoded instructions; custom agent framework; separate voice-specific API endpoints
- **Trade-offs:** Easier: LLM autonomously discovers tools and their requirements. Harder: Requires MCP server implementation; HTTP/SSE transport layer adds complexity; tool schemas must be extremely precise or LLM makes wrong calls
- **Breaking if changed:** Removing MCP breaks voice agent autonomy - would require returning to rigid routing or expensive LLM prompt rewriting

### Dual HTTP/SSE transport for MCP server instead of standard stdio - allows web-based client connection (2026-02-19)
- **Context:** Traditional MCP uses stdio, but need voice agents to connect via HTTP from browser or external services
- **Why:** HTTP/SSE enables browser-based clients to communicate with voice agents in real-time without spawning subprocesses, critical for SaaS model where multiple tenants share infrastructure
- **Rejected:** Pure stdio MCP (CLI-only); WebSocket (lacks SSE streaming benefits); REST with polling (too latent for real-time)
- **Trade-offs:** Easier: Web-native, firewall-friendly, works with existing FastAPI. Harder: Manual transport layer implementation; error handling for connection drops; buffering/backpressure
- **Breaking if changed:** Switching back to stdio breaks web client connectivity and requires client-side rewrite

#### [Pattern] Webhook endpoint abstraction with generic WebhookDelivery tracking instead of hard-coded Stripe integration (2026-02-19)
- **Problem solved:** System needs to handle events from Stripe (payments), integrate with multiple external services
- **Why this works:** Generic webhook model allows adding Twilio, Resend, custom webhooks without modifying core webhook handler. Each delivery is logged separately, enabling debugging and retry logic. Decouples payment logic from webhook infrastructure
- **Trade-offs:** Easier: Add new providers by creating new webhook handler. Harder: Migration complexity; requires webhook registration per provider; delivery logs grow large

#### [Gotcha] Custom migration system instead of Alembic - suggests past issues with auto-migration in production (2026-02-19)
- **Situation:** Project has custom migration directory, not standard Alembic setup
- **Root cause:** Likely had bad auto-migration experience (schema misdetection, data loss). Custom migrations require explicit SQL allowing review before production deployment
- **How to avoid:** Easier: Control over migration safety. Harder: Manual migration writing; risk of inconsistency between code and migrations