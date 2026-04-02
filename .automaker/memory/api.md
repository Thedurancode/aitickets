---
tags: [api]
summary: api implementation decisions and patterns
relevantTo: [api]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# api

#### [Pattern] Dual API surface: MCP tools + REST routers - both call identical service layer (2026-02-19)
- **Problem solved:** Need voice agents to control system (MCP) AND human users via web UI (REST), both accessing same business logic
- **Why this works:** Service layer abstraction (23 services) prevents code duplication. MCP tools become thin wrappers that validate LLM input, then call services. REST routers do same. Single source of truth for business logic reduces bugs from divergent implementations
- **Trade-offs:** Easier: Bug fix applies everywhere; feature consistency. Harder: 3-layer stack (MCP->Service->DB); more files to change; coordination needed between tool and router signatures