---
tags: [database]
summary: database implementation decisions and patterns
relevantTo: [database]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# database

### 25 models with tight coupling to MCP tool definitions - model-per-feature vs generic data structure (2026-02-19)
- **Context:** Each ticketing feature (Events, Venues, Tickets, Marketing, Knowledge) gets dedicated SQLAlchemy models
- **Why:** Type safety and validation at database layer mirrors MCP tool schema validation - when LLM calls 'createEvent', the database model enforces exact field requirements matching tool signature. Prevents data corruption from malformed LLM tool calls
- **Rejected:** Single flexible Document/JSON model; schema-less NoSQL; generic key-value tables
- **Trade-offs:** Easier: IDE autocomplete, runtime type checking, SQL query optimization. Harder: Migration complexity; schema evolution when tools change; 25 separate model classes to maintain
- **Breaking if changed:** Switching to flexible schema loses validation coupling with tools - LLM could create invalid data that FastAPI accepts but causes downstream errors